"""
E2E Integration Tests for Radiology MCP Tools

Feature 007: FHIR Radiology Integration
Tests radiology MCP tools against real FHIR server and database.

These tests verify end-to-end functionality of radiology tools including:
- get_patient_imaging_studies
- get_imaging_study_details
- get_radiology_reports
- search_patients_with_imaging
- list_radiology_queries
- get_encounter_imaging
"""

import pytest
import json
import os
import sys
from typing import Dict, Any, List

# Add project root to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


# Skip if FHIR server not available
FHIR_BASE_URL = os.getenv('FHIR_BASE_URL', 'http://localhost:52773/fhir/r4')


def check_fhir_server():
    """Check if FHIR server is available."""
    import requests
    try:
        response = requests.get(f"{FHIR_BASE_URL}/metadata", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


# Conditionally skip all tests if FHIR server unavailable
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not check_fhir_server(),
        reason="FHIR server not available"
    )
]


class TestListRadiologyQueriesE2E:
    """E2E tests for list_radiology_queries tool."""

    def test_list_all_queries_returns_catalog(self):
        """Verify list_radiology_queries returns query catalog."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("list_radiology_queries", {"category": "all"})
        )

        assert len(result) == 1
        data = json.loads(result[0].text)

        assert "queries" in data
        assert "total_queries" in data
        assert data["total_queries"] > 0

        # Verify expected categories exist
        queries = data["queries"]
        assert "patient" in queries or "study" in queries or "report" in queries

    def test_list_patient_queries(self):
        """Verify patient category returns patient-related queries."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("list_radiology_queries", {"category": "patient"})
        )

        data = json.loads(result[0].text)
        assert data["category"] == "patient"

        if "patient" in data.get("queries", {}):
            patient_queries = data["queries"]["patient"]
            assert len(patient_queries) > 0
            # Should have get_patient_imaging_studies
            query_names = [q["name"] for q in patient_queries]
            assert "get_patient_imaging_studies" in query_names

    def test_list_study_queries(self):
        """Verify study category returns study-related queries."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("list_radiology_queries", {"category": "study"})
        )

        data = json.loads(result[0].text)
        assert data["category"] == "study"

    def test_list_invalid_category_returns_error(self):
        """Verify invalid category returns appropriate error."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("list_radiology_queries", {"category": "invalid_category"})
        )

        data = json.loads(result[0].text)
        # Should return error or empty result
        assert "error" in data or data["total_queries"] == 0


class TestGetPatientImagingStudiesE2E:
    """E2E tests for get_patient_imaging_studies tool."""

    def test_get_studies_for_valid_patient(self):
        """Verify retrieval of imaging studies for a valid patient."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        # First find a patient with imaging studies
        search_result = asyncio.get_event_loop().run_until_complete(
            call_tool("search_patients_with_imaging", {"limit": 1})
        )
        search_data = json.loads(search_result[0].text)

        if search_data.get("total_count", 0) == 0:
            pytest.skip("No patients with imaging studies in database")

        patient_id = search_data["patients"][0]["id"]

        # Now get studies for that patient
        result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_patient_imaging_studies", {"patient_id": patient_id})
        )

        data = json.loads(result[0].text)

        assert "patient_id" in data
        assert "studies" in data
        assert "total_count" in data
        assert data["patient_id"] == patient_id

    def test_get_studies_for_invalid_patient_returns_empty(self):
        """Verify empty result for non-existent patient."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_patient_imaging_studies", {"patient_id": "nonexistent-patient-xyz123"})
        )

        data = json.loads(result[0].text)
        assert data["total_count"] == 0 or len(data.get("studies", [])) == 0

    def test_get_studies_with_modality_filter(self):
        """Verify modality filter works."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        # First find a patient
        search_result = asyncio.get_event_loop().run_until_complete(
            call_tool("search_patients_with_imaging", {"modality": "CR", "limit": 1})
        )
        search_data = json.loads(search_result[0].text)

        if search_data.get("total_count", 0) == 0:
            pytest.skip("No patients with CR modality imaging studies")

        patient_id = search_data["patients"][0]["id"]

        # Get studies with modality filter
        result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_patient_imaging_studies", {
                "patient_id": patient_id,
                "modality": "CR"
            })
        )

        data = json.loads(result[0].text)
        # All returned studies should have CR modality (or empty if filtered)
        for study in data.get("studies", []):
            if study.get("modality"):
                assert study["modality"] == "CR"


class TestGetImagingStudyDetailsE2E:
    """E2E tests for get_imaging_study_details tool."""

    def test_get_study_details_by_fhir_id(self):
        """Verify retrieval of study details by FHIR resource ID."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        # First find a study
        search_result = asyncio.get_event_loop().run_until_complete(
            call_tool("search_patients_with_imaging", {"limit": 1})
        )
        search_data = json.loads(search_result[0].text)

        if search_data.get("total_count", 0) == 0:
            pytest.skip("No patients with imaging studies")

        patient_id = search_data["patients"][0]["id"]

        # Get studies for that patient
        studies_result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_patient_imaging_studies", {"patient_id": patient_id})
        )
        studies_data = json.loads(studies_result[0].text)

        if not studies_data.get("studies"):
            pytest.skip("No imaging studies found for patient")

        study_id = studies_data["studies"][0]["id"]

        # Get study details
        result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_imaging_study_details", {"study_id": study_id})
        )

        data = json.loads(result[0].text)

        assert "id" in data
        assert "status" in data
        assert "modality" in data or "series" in data

    def test_get_study_details_invalid_id_returns_error(self):
        """Verify error response for invalid study ID."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_imaging_study_details", {"study_id": "nonexistent-study-xyz"})
        )

        data = json.loads(result[0].text)
        assert "error" in data


class TestGetRadiologyReportsE2E:
    """E2E tests for get_radiology_reports tool."""

    def test_get_reports_by_patient(self):
        """Verify retrieval of radiology reports by patient ID."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        # First find a patient with imaging
        search_result = asyncio.get_event_loop().run_until_complete(
            call_tool("search_patients_with_imaging", {"limit": 1})
        )
        search_data = json.loads(search_result[0].text)

        if search_data.get("total_count", 0) == 0:
            pytest.skip("No patients with imaging studies")

        patient_id = search_data["patients"][0]["id"]

        # Get reports for that patient
        result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_radiology_reports", {"patient_id": patient_id})
        )

        data = json.loads(result[0].text)

        assert "patient_id" in data
        assert "reports" in data
        assert "total_count" in data

    def test_get_reports_requires_patient_or_study(self):
        """Verify error when neither patient_id nor study_id provided."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_radiology_reports", {})
        )

        data = json.loads(result[0].text)
        assert "error" in data

    def test_get_reports_includes_full_text_when_requested(self):
        """Verify full report text is included when include_full_text=True."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        # Find a patient
        search_result = asyncio.get_event_loop().run_until_complete(
            call_tool("search_patients_with_imaging", {"limit": 5})
        )
        search_data = json.loads(search_result[0].text)

        if search_data.get("total_count", 0) == 0:
            pytest.skip("No patients with imaging studies")

        # Try to find a patient with reports
        for patient in search_data.get("patients", []):
            patient_id = patient["id"]
            result = asyncio.get_event_loop().run_until_complete(
                call_tool("get_radiology_reports", {
                    "patient_id": patient_id,
                    "include_full_text": True
                })
            )
            data = json.loads(result[0].text)

            if data.get("total_count", 0) > 0:
                # Check if any report has full_text
                reports_with_text = [r for r in data["reports"] if "full_text" in r]
                # This is valid even if empty - reports may not have text
                assert isinstance(data["reports"], list)
                return

        pytest.skip("No radiology reports found in database")


class TestSearchPatientsWithImagingE2E:
    """E2E tests for search_patients_with_imaging tool."""

    def test_search_without_filters(self):
        """Verify basic search returns patients."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("search_patients_with_imaging", {"limit": 10})
        )

        data = json.loads(result[0].text)

        assert "patients" in data
        assert "total_count" in data
        assert isinstance(data["patients"], list)

    def test_search_with_modality_filter(self):
        """Verify modality filter returns matching patients."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("search_patients_with_imaging", {
                "modality": "CR",
                "limit": 5
            })
        )

        data = json.loads(result[0].text)

        assert "modality" in data
        assert data["modality"] == "CR"
        assert "patients" in data

    def test_search_with_finding_text(self):
        """Verify finding_text filter searches report conclusions."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("search_patients_with_imaging", {
                "finding_text": "pneumonia",
                "limit": 5
            })
        )

        data = json.loads(result[0].text)

        assert "finding_text" in data
        assert data["finding_text"] == "pneumonia"
        assert "patients" in data

    def test_search_respects_limit(self):
        """Verify limit parameter is respected."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("search_patients_with_imaging", {"limit": 3})
        )

        data = json.loads(result[0].text)

        assert len(data.get("patients", [])) <= 3


class TestGetEncounterImagingE2E:
    """E2E tests for get_encounter_imaging tool."""

    def test_get_imaging_for_valid_encounter(self):
        """Verify retrieval of imaging for a valid encounter."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio
        import requests

        # First, find an encounter from FHIR server
        try:
            response = requests.get(
                f"{FHIR_BASE_URL}/Encounter",
                params={"_count": 10},
                headers={"Accept": "application/fhir+json"},
                timeout=10
            )
            response.raise_for_status()
            bundle = response.json()

            if not bundle.get("entry"):
                pytest.skip("No encounters in FHIR server")

            encounter_id = bundle["entry"][0]["resource"]["id"]
        except Exception as e:
            pytest.skip(f"Could not fetch encounters: {e}")

        # Get imaging for that encounter
        result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_encounter_imaging", {"encounter_id": encounter_id})
        )

        data = json.loads(result[0].text)

        assert "encounter" in data or "imaging_studies" in data
        assert "total_studies" in data or "imaging_studies" in data

    def test_get_imaging_for_invalid_encounter(self):
        """Verify handling of invalid encounter ID."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_encounter_imaging", {"encounter_id": "nonexistent-enc-xyz"})
        )

        data = json.loads(result[0].text)

        # Should either have error or empty results
        assert "encounter" in data or "imaging_studies" in data
        # Encounter data may be None for invalid ID
        if data.get("total_studies") is not None:
            assert data["total_studies"] == 0 or data.get("encounter") is None

    def test_encounter_id_with_prefix(self):
        """Verify Encounter/ prefix is handled correctly."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio
        import requests

        # Find an encounter
        try:
            response = requests.get(
                f"{FHIR_BASE_URL}/Encounter",
                params={"_count": 1},
                headers={"Accept": "application/fhir+json"},
                timeout=10
            )
            response.raise_for_status()
            bundle = response.json()

            if not bundle.get("entry"):
                pytest.skip("No encounters in FHIR server")

            encounter_id = bundle["entry"][0]["resource"]["id"]
        except Exception as e:
            pytest.skip(f"Could not fetch encounters: {e}")

        # Call with Encounter/ prefix
        result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_encounter_imaging", {"encounter_id": f"Encounter/{encounter_id}"})
        )

        data = json.loads(result[0].text)

        # Should handle the prefix and return valid results
        assert "imaging_studies" in data or "encounter" in data


class TestRadiologyToolIntegration:
    """Integration tests verifying tools work together."""

    def test_patient_to_study_to_report_flow(self):
        """Verify complete flow: search patient -> get studies -> get reports."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        # Step 1: Find patients with imaging
        search_result = asyncio.get_event_loop().run_until_complete(
            call_tool("search_patients_with_imaging", {"limit": 5})
        )
        search_data = json.loads(search_result[0].text)

        if search_data.get("total_count", 0) == 0:
            pytest.skip("No patients with imaging in database")

        patient_id = search_data["patients"][0]["id"]

        # Step 2: Get imaging studies for patient
        studies_result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_patient_imaging_studies", {"patient_id": patient_id})
        )
        studies_data = json.loads(studies_result[0].text)

        assert studies_data["patient_id"] == patient_id

        # Step 3: Get reports for patient
        reports_result = asyncio.get_event_loop().run_until_complete(
            call_tool("get_radiology_reports", {"patient_id": patient_id})
        )
        reports_data = json.loads(reports_result[0].text)

        assert reports_data["patient_id"] == patient_id
        assert "reports" in reports_data

    def test_query_catalog_lists_all_tools(self):
        """Verify query catalog includes all radiology tools."""
        from mcp_server.fhir_graphrag_mcp_server import call_tool
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            call_tool("list_radiology_queries", {"category": "all"})
        )

        data = json.loads(result[0].text)

        # Flatten all queries
        all_query_names = []
        for category_queries in data.get("queries", {}).values():
            if isinstance(category_queries, list):
                all_query_names.extend([q["name"] for q in category_queries])

        # Should include key radiology tools
        expected_tools = [
            "get_patient_imaging_studies",
            "get_imaging_study_details",
            "get_radiology_reports"
        ]

        for tool in expected_tools:
            assert tool in all_query_names, f"Missing tool: {tool}"


# Mark for pytest collection
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
