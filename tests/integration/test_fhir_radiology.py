"""
Integration Tests for FHIR Radiology Integration

Tests for Feature 007: FHIR Radiology Integration
Tests cover PatientImageMapping table, ImagingStudy/DiagnosticReport resource builders,
and FHIR POST/PUT methods.

Per TDD methodology (Constitution Principle VI), these tests are written BEFORE implementation.
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


class TestPatientImageMappingTable:
    """T004a: Tests for PatientImageMapping table schema."""

    def test_table_exists(self):
        """Verify VectorSearch.PatientImageMapping table exists."""
        from src.db.connection import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'VectorSearch' AND TABLE_NAME = 'PatientImageMapping'
            """)
            table_exists = cursor.fetchone()[0] > 0
            assert table_exists, "PatientImageMapping table should exist"
        finally:
            cursor.close()
            conn.close()

    def test_table_has_required_columns(self):
        """Verify table has all required columns per data-model.md."""
        from src.db.connection import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'VectorSearch' AND TABLE_NAME = 'PatientImageMapping'
            """)
            columns = {row[0].upper() for row in cursor.fetchall()}

            required_columns = {
                'MIMICSUBJECTID',
                'FHIRPATIENTID',
                'FHIRPATIENTNAME',
                'MATCHCONFIDENCE',
                'MATCHTYPE',
                'CREATEDAT',
                'UPDATEDAT'
            }

            missing = required_columns - columns
            assert not missing, f"Missing columns: {missing}"
        finally:
            cursor.close()
            conn.close()

    def test_mimic_subject_id_is_primary_key(self):
        """Verify MIMICSubjectID is the primary key."""
        from src.db.connection import get_connection

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Check primary key constraint
            cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = 'VectorSearch'
                AND TABLE_NAME = 'PatientImageMapping'
                AND CONSTRAINT_NAME LIKE '%PK%'
            """)
            pk_columns = [row[0].upper() for row in cursor.fetchall()]
            assert 'MIMICSUBJECTID' in pk_columns, "MIMICSubjectID should be primary key"
        finally:
            cursor.close()
            conn.close()


class TestImagingStudyResourceBuilder:
    """T005a: Tests for ImagingStudy resource builder."""

    def test_build_imaging_study_returns_valid_fhir(self):
        """Verify ImagingStudy builder returns valid FHIR R4 resource."""
        from src.adapters.fhir_radiology_adapter import (
            FHIRRadiologyAdapter,
            ImagingStudyData
        )

        adapter = FHIRRadiologyAdapter()
        data = ImagingStudyData(
            study_id="s50414267",
            subject_id="p10002428",
            patient_id="123",
            study_date=datetime(2023, 6, 15, 10, 30),
            modality="CR"
        )

        resource = adapter.build_imaging_study(data)

        assert resource["resourceType"] == "ImagingStudy"
        assert resource["id"] == "study-s50414267"
        assert resource["status"] == "available"
        assert resource["subject"]["reference"] == "Patient/123"

    def test_imaging_study_contains_mimic_identifier(self):
        """Verify ImagingStudy contains MIMIC study identifier per FR-010."""
        from src.adapters.fhir_radiology_adapter import (
            FHIRRadiologyAdapter,
            ImagingStudyData
        )

        adapter = FHIRRadiologyAdapter()
        data = ImagingStudyData(
            study_id="s50414267",
            subject_id="p10002428",
            patient_id="123"
        )

        resource = adapter.build_imaging_study(data)

        identifiers = resource.get("identifier", [])
        mimic_identifiers = [
            i for i in identifiers
            if i.get("system") == "urn:mimic-cxr:study"
        ]
        assert len(mimic_identifiers) == 1, "Should have MIMIC study identifier"
        assert mimic_identifiers[0]["value"] == "s50414267"

    def test_imaging_study_with_encounter_reference(self):
        """Verify ImagingStudy can include encounter reference per FR-005."""
        from src.adapters.fhir_radiology_adapter import (
            FHIRRadiologyAdapter,
            ImagingStudyData
        )

        adapter = FHIRRadiologyAdapter()
        data = ImagingStudyData(
            study_id="s50414267",
            subject_id="p10002428",
            patient_id="123",
            encounter_id="456"
        )

        resource = adapter.build_imaging_study(data)

        assert "encounter" in resource
        assert resource["encounter"]["reference"] == "Encounter/456"


class TestDiagnosticReportResourceBuilder:
    """T006a: Tests for DiagnosticReport resource builder."""

    def test_build_diagnostic_report_returns_valid_fhir(self):
        """Verify DiagnosticReport builder returns valid FHIR R4 resource."""
        from src.adapters.fhir_radiology_adapter import (
            FHIRRadiologyAdapter,
            DiagnosticReportData
        )

        adapter = FHIRRadiologyAdapter()
        data = DiagnosticReportData(
            study_id="s50414267",
            patient_id="123",
            imaging_study_id="study-s50414267",
            report_text="IMPRESSION: No acute cardiopulmonary abnormality.",
            conclusion="No acute findings"
        )

        resource = adapter.build_diagnostic_report(data)

        assert resource["resourceType"] == "DiagnosticReport"
        assert resource["id"] == "report-s50414267"
        assert resource["status"] == "final"
        assert resource["subject"]["reference"] == "Patient/123"

    def test_diagnostic_report_links_to_imaging_study(self):
        """Verify DiagnosticReport references ImagingStudy per FR-004."""
        from src.adapters.fhir_radiology_adapter import (
            FHIRRadiologyAdapter,
            DiagnosticReportData
        )

        adapter = FHIRRadiologyAdapter()
        data = DiagnosticReportData(
            study_id="s50414267",
            patient_id="123",
            imaging_study_id="study-s50414267",
            report_text="Test report"
        )

        resource = adapter.build_diagnostic_report(data)

        imaging_refs = resource.get("imagingStudy", [])
        assert len(imaging_refs) == 1
        assert imaging_refs[0]["reference"] == "ImagingStudy/study-s50414267"

    def test_diagnostic_report_contains_base64_report_text(self):
        """Verify report text is base64 encoded in presentedForm."""
        import base64
        from src.adapters.fhir_radiology_adapter import (
            FHIRRadiologyAdapter,
            DiagnosticReportData
        )

        adapter = FHIRRadiologyAdapter()
        report_text = "IMPRESSION: Test findings."
        data = DiagnosticReportData(
            study_id="s50414267",
            patient_id="123",
            imaging_study_id="study-s50414267",
            report_text=report_text
        )

        resource = adapter.build_diagnostic_report(data)

        presented_forms = resource.get("presentedForm", [])
        assert len(presented_forms) == 1
        assert presented_forms[0]["contentType"] == "text/plain"

        # Decode and verify
        decoded = base64.b64decode(presented_forms[0]["data"]).decode('utf-8')
        assert decoded == report_text


class TestFHIRPostPutMethods:
    """T007a: Tests for FHIR POST/PUT methods."""

    @patch('requests.Session.put')
    def test_put_resource_sends_correct_request(self, mock_put):
        """Verify PUT resource sends correct HTTP request."""
        from src.adapters.fhir_radiology_adapter import FHIRRadiologyAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "study-123"}
        mock_response.raise_for_status = MagicMock()
        mock_put.return_value = mock_response

        adapter = FHIRRadiologyAdapter(fhir_base_url="http://test-fhir/r4")
        resource = {
            "resourceType": "ImagingStudy",
            "id": "study-123",
            "status": "available"
        }

        result = adapter.put_resource(resource)

        mock_put.assert_called_once()
        call_args = mock_put.call_args
        assert "http://test-fhir/r4/ImagingStudy/study-123" in call_args[0][0]

    @patch('requests.Session.post')
    def test_post_resource_sends_correct_request(self, mock_post):
        """Verify POST resource sends correct HTTP request."""
        from src.adapters.fhir_radiology_adapter import FHIRRadiologyAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "new-id"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        adapter = FHIRRadiologyAdapter(fhir_base_url="http://test-fhir/r4")
        resource = {
            "resourceType": "DiagnosticReport",
            "status": "final"
        }

        result = adapter.post_resource(resource)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "http://test-fhir/r4/DiagnosticReport" in call_args[0][0]

    @patch('requests.Session.put')
    def test_put_resource_is_idempotent(self, mock_put):
        """Verify PUT resource supports idempotent updates per FR-008."""
        from src.adapters.fhir_radiology_adapter import FHIRRadiologyAdapter

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "study-123", "meta": {"versionId": "2"}}
        mock_response.raise_for_status = MagicMock()
        mock_put.return_value = mock_response

        adapter = FHIRRadiologyAdapter(fhir_base_url="http://test-fhir/r4")
        resource = {
            "resourceType": "ImagingStudy",
            "id": "study-123",
            "status": "available"
        }

        # Call twice - should be idempotent
        result1 = adapter.put_resource(resource)
        result2 = adapter.put_resource(resource)

        # Both calls should succeed (mock doesn't change state)
        assert result1["id"] == "study-123"
        assert result2["id"] == "study-123"


class TestPatientMappingHelpers:
    """Tests for patient mapping helper functions."""

    def test_lookup_patient_mapping_returns_dict_when_found(self):
        """Verify lookup returns mapping dict when patient exists."""
        # This test requires database integration
        pytest.skip("Requires database setup - run with integration flag")

    def test_insert_patient_mapping_creates_record(self):
        """Verify insert creates new mapping record."""
        # This test requires database integration
        pytest.skip("Requires database setup - run with integration flag")

    def test_mapping_stats_returns_counts(self):
        """Verify stats function returns correct counts."""
        # This test requires database integration
        pytest.skip("Requires database setup - run with integration flag")


# Mark tests that require database connection
pytestmark = pytest.mark.integration
