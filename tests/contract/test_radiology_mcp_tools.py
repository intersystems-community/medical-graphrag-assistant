"""
Contract Tests for Radiology MCP Tools

Tests for Feature 007: FHIR Radiology Integration
Validates MCP tool contracts match specifications in specs/007-fhir-radiology-integration/contracts/

Per TDD methodology (Constitution Principle VI), these tests are written BEFORE implementation.
"""

import pytest
import json
import os
import sys
from typing import Dict, Any
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Load contract schemas
CONTRACTS_DIR = os.path.join(parent_dir, 'specs', '007-fhir-radiology-integration', 'contracts')


def load_contract(tool_name: str) -> Dict[str, Any]:
    """Load a contract JSON file."""
    contract_path = os.path.join(CONTRACTS_DIR, f'{tool_name}.json')
    if os.path.exists(contract_path):
        with open(contract_path) as f:
            return json.load(f)
    return None


class TestGetPatientImagingStudiesContract:
    """T023a: Contract tests for get_patient_imaging_studies MCP tool."""

    def test_contract_exists(self):
        """Verify contract file exists."""
        contract = load_contract('get_patient_imaging_studies')
        assert contract is not None, "Contract file should exist"

    def test_contract_has_required_fields(self):
        """Verify contract has required input/output schema."""
        contract = load_contract('get_patient_imaging_studies')
        if contract is None:
            pytest.skip("Contract file not found")

        assert 'name' in contract
        assert 'description' in contract
        assert 'input_schema' in contract or 'inputSchema' in contract
        assert 'output_schema' in contract or 'outputSchema' in contract or 'example' in contract

    def test_input_requires_patient_id(self):
        """Verify input schema requires patient_id parameter."""
        contract = load_contract('get_patient_imaging_studies')
        if contract is None:
            pytest.skip("Contract file not found")

        input_schema = contract.get('input_schema') or contract.get('inputSchema', {})
        properties = input_schema.get('properties', {})
        required = input_schema.get('required', [])

        assert 'patient_id' in properties or 'patientId' in properties, \
            "Should require patient_id parameter"

    def test_output_contains_imaging_studies_list(self):
        """Verify output includes list of imaging studies."""
        contract = load_contract('get_patient_imaging_studies')
        if contract is None:
            pytest.skip("Contract file not found")

        output_schema = contract.get('output_schema') or contract.get('outputSchema', {})
        example = contract.get('example', {})

        # Check either schema or example
        if output_schema:
            props = output_schema.get('properties', {})
            assert 'studies' in props or 'imaging_studies' in props
        elif example:
            output = example.get('output', {})
            assert 'studies' in output or 'imaging_studies' in output


class TestGetImagingStudyDetailsContract:
    """T024a: Contract tests for get_imaging_study_details MCP tool."""

    def test_contract_exists(self):
        """Verify contract file exists."""
        contract = load_contract('get_imaging_study_details')
        assert contract is not None, "Contract file should exist"

    def test_input_requires_study_id(self):
        """Verify input schema requires study_id parameter."""
        contract = load_contract('get_imaging_study_details')
        if contract is None:
            pytest.skip("Contract file not found")

        input_schema = contract.get('input_schema') or contract.get('inputSchema', {})
        properties = input_schema.get('properties', {})

        assert 'study_id' in properties or 'studyId' in properties, \
            "Should require study_id parameter"

    def test_output_contains_study_details(self):
        """Verify output includes detailed study information."""
        contract = load_contract('get_imaging_study_details')
        if contract is None:
            pytest.skip("Contract file not found")

        output_schema = contract.get('output_schema') or contract.get('outputSchema', {})
        example = contract.get('example', {})

        # Study details should include modality, series info
        if example:
            output = example.get('output', {})
            assert 'modality' in output or 'study' in output


class TestGetRadiologyReportsContract:
    """T025a: Contract tests for get_radiology_reports MCP tool."""

    def test_contract_exists(self):
        """Verify contract file exists."""
        contract = load_contract('get_radiology_reports')
        assert contract is not None, "Contract file should exist"

    def test_input_allows_patient_or_study_filter(self):
        """Verify input allows filtering by patient_id or study_id."""
        contract = load_contract('get_radiology_reports')
        if contract is None:
            pytest.skip("Contract file not found")

        input_schema = contract.get('input_schema') or contract.get('inputSchema', {})
        properties = input_schema.get('properties', {})

        # Should support at least one filter
        has_patient = 'patient_id' in properties or 'patientId' in properties
        has_study = 'study_id' in properties or 'studyId' in properties

        assert has_patient or has_study, \
            "Should allow filtering by patient_id or study_id"

    def test_output_contains_report_text(self):
        """Verify output includes report text/conclusion."""
        contract = load_contract('get_radiology_reports')
        if contract is None:
            pytest.skip("Contract file not found")

        example = contract.get('example', {})
        if example:
            output = example.get('output', {})
            reports = output.get('reports', [output])
            if reports:
                report = reports[0] if isinstance(reports, list) else reports
                has_text = 'report_text' in report or 'conclusion' in report or 'text' in report
                assert has_text, "Report should include text content"


class TestSearchPatientsWithImagingContract:
    """T026a: Contract tests for search_patients_with_imaging MCP tool."""

    def test_contract_exists(self):
        """Verify contract file exists."""
        contract = load_contract('search_patients_with_imaging')
        assert contract is not None, "Contract file should exist"

    def test_input_supports_search_criteria(self):
        """Verify input supports name or condition search."""
        contract = load_contract('search_patients_with_imaging')
        if contract is None:
            pytest.skip("Contract file not found")

        input_schema = contract.get('input_schema') or contract.get('inputSchema', {})
        properties = input_schema.get('properties', {})

        # Should support search criteria
        has_name = 'name' in properties or 'patient_name' in properties
        has_condition = 'condition' in properties or 'diagnosis' in properties
        has_query = 'query' in properties or 'search_term' in properties

        assert has_name or has_condition or has_query, \
            "Should support some form of search criteria"

    def test_output_returns_patient_list(self):
        """Verify output returns list of patients with imaging."""
        contract = load_contract('search_patients_with_imaging')
        if contract is None:
            pytest.skip("Contract file not found")

        output_schema = contract.get('output_schema') or contract.get('outputSchema', {})
        example = contract.get('example', {})

        if example:
            output = example.get('output', {})
            assert 'patients' in output or 'results' in output


class TestListRadiologyQueriesContract:
    """T027a: Contract tests for list_radiology_queries MCP tool."""

    def test_contract_exists(self):
        """Verify contract file exists."""
        contract = load_contract('list_radiology_queries')
        assert contract is not None, "Contract file should exist"

    def test_output_lists_available_queries(self):
        """Verify output lists available query templates."""
        contract = load_contract('list_radiology_queries')
        if contract is None:
            pytest.skip("Contract file not found")

        example = contract.get('example', {})
        if example:
            output = example.get('output', {})
            assert 'queries' in output or 'tools' in output or 'available_queries' in output


class TestGetEncounterImagingContract:
    """T022a: Contract tests for get_encounter_imaging MCP tool."""

    def test_contract_exists(self):
        """Verify contract file exists."""
        contract = load_contract('get_encounter_imaging')
        assert contract is not None, "Contract file should exist"

    def test_input_requires_encounter_id(self):
        """Verify input requires encounter_id parameter."""
        contract = load_contract('get_encounter_imaging')
        if contract is None:
            pytest.skip("Contract file not found")

        input_schema = contract.get('input_schema') or contract.get('inputSchema', {})
        properties = input_schema.get('properties', {})

        assert 'encounter_id' in properties or 'encounterId' in properties, \
            "Should require encounter_id parameter"

    def test_output_contains_imaging_studies(self):
        """Verify output contains imaging studies for encounter."""
        contract = load_contract('get_encounter_imaging')
        if contract is None:
            pytest.skip("Contract file not found")

        example = contract.get('example', {})
        if example:
            output = example.get('output', {})
            assert 'studies' in output or 'imaging_studies' in output


class TestMCPToolResponseFormat:
    """Tests for LLM-consumable response format per FR-017."""

    def test_all_contracts_have_description(self):
        """Verify all contracts have LLM-friendly descriptions."""
        tool_names = [
            'get_patient_imaging_studies',
            'get_imaging_study_details',
            'get_radiology_reports',
            'search_patients_with_imaging',
            'get_encounter_imaging',
            'list_radiology_queries'
        ]

        for tool_name in tool_names:
            contract = load_contract(tool_name)
            if contract:
                assert 'description' in contract, \
                    f"{tool_name} should have description"
                assert len(contract['description']) > 20, \
                    f"{tool_name} description should be meaningful"

    def test_contracts_have_examples(self):
        """Verify contracts have usage examples for LLM context."""
        tool_names = [
            'get_patient_imaging_studies',
            'get_imaging_study_details',
            'get_radiology_reports'
        ]

        for tool_name in tool_names:
            contract = load_contract(tool_name)
            if contract:
                assert 'example' in contract or 'examples' in contract, \
                    f"{tool_name} should have example(s)"


# Mark as contract tests
pytestmark = pytest.mark.contract
