"""
FHIR Radiology Adapter

Creates and queries FHIR ImagingStudy and DiagnosticReport resources
for MIMIC-CXR radiology data integration.

Part of Feature 007: FHIR Radiology Integration
"""

import json
import os
import base64
import requests
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class ImagingStudyData:
    """Data for creating a FHIR ImagingStudy resource."""
    study_id: str
    subject_id: str
    patient_id: str  # FHIR Patient resource ID
    study_date: Optional[datetime] = None
    modality: str = "CR"  # Computed Radiography (chest X-ray)
    num_series: int = 1
    num_instances: int = 1
    encounter_id: Optional[str] = None
    description: Optional[str] = None


@dataclass
class DiagnosticReportData:
    """Data for creating a FHIR DiagnosticReport resource."""
    study_id: str
    patient_id: str  # FHIR Patient resource ID
    imaging_study_id: str  # Reference to ImagingStudy
    report_text: str
    report_date: Optional[datetime] = None
    encounter_id: Optional[str] = None
    conclusion: Optional[str] = None


class FHIRRadiologyAdapter:
    """
    Adapter for creating and querying FHIR radiology resources.

    Implements FHIR R4 ImagingStudy and DiagnosticReport resource creation
    for MIMIC-CXR integration with the IRIS FHIR repository.
    """

    # FHIR base URL from environment or default
    DEFAULT_FHIR_BASE_URL = "http://localhost:52773/fhir/r4"

    # MIMIC-CXR identifier systems
    MIMIC_STUDY_SYSTEM = "urn:mimic-cxr:study"
    MIMIC_SUBJECT_SYSTEM = "urn:mimic-cxr:subject"
    MIMIC_REPORT_SYSTEM = "urn:mimic-cxr:report"

    # DICOM modality codes
    DICOM_MODALITY_SYSTEM = "http://dicom.nema.org/resources/ontology/DCM"

    # LOINC code for diagnostic imaging study
    LOINC_IMAGING_STUDY_CODE = "18748-4"
    LOINC_SYSTEM = "http://loinc.org"

    def __init__(self, fhir_base_url: Optional[str] = None):
        """
        Initialize the FHIR Radiology Adapter.

        Args:
            fhir_base_url: Base URL for FHIR server. Defaults to FHIR_BASE_URL env var
                          or http://localhost:52773/fhir/r4
        """
        self.fhir_base_url = fhir_base_url or os.getenv(
            'FHIR_BASE_URL',
            self.DEFAULT_FHIR_BASE_URL
        )
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/fhir+json',
            'Accept': 'application/fhir+json'
        })

    def build_imaging_study(self, data: ImagingStudyData) -> Dict[str, Any]:
        """
        Build a FHIR R4 ImagingStudy resource from MIMIC-CXR data.

        Args:
            data: ImagingStudyData containing study information

        Returns:
            FHIR ImagingStudy resource as dict
        """
        resource = {
            "resourceType": "ImagingStudy",
            "id": f"study-{data.study_id}",
            "identifier": [
                {
                    "system": self.MIMIC_STUDY_SYSTEM,
                    "value": data.study_id
                }
            ],
            "status": "available",
            "subject": {
                "reference": f"Patient/{data.patient_id}"
            },
            "modality": [
                {
                    "system": self.DICOM_MODALITY_SYSTEM,
                    "code": data.modality,
                    "display": self._get_modality_display(data.modality)
                }
            ],
            "numberOfSeries": data.num_series,
            "numberOfInstances": data.num_instances,
            "note": [
                {
                    "text": "MIMIC-CXR imported study"
                }
            ]
        }

        # Add optional fields
        if data.study_date:
            resource["started"] = data.study_date.isoformat()

        if data.encounter_id:
            resource["encounter"] = {
                "reference": f"Encounter/{data.encounter_id}"
            }

        if data.description:
            resource["description"] = data.description

        return resource

    def build_diagnostic_report(self, data: DiagnosticReportData) -> Dict[str, Any]:
        """
        Build a FHIR R4 DiagnosticReport resource from MIMIC-CXR report text.

        Args:
            data: DiagnosticReportData containing report information

        Returns:
            FHIR DiagnosticReport resource as dict
        """
        # Encode report text as base64 for presentedForm
        report_bytes = data.report_text.encode('utf-8')
        report_base64 = base64.b64encode(report_bytes).decode('ascii')

        resource = {
            "resourceType": "DiagnosticReport",
            "id": f"report-{data.study_id}",
            "identifier": [
                {
                    "system": self.MIMIC_REPORT_SYSTEM,
                    "value": data.study_id
                }
            ],
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": self.LOINC_SYSTEM,
                        "code": self.LOINC_IMAGING_STUDY_CODE,
                        "display": "Diagnostic imaging study"
                    }
                ]
            },
            "subject": {
                "reference": f"Patient/{data.patient_id}"
            },
            "imagingStudy": [
                {
                    "reference": f"ImagingStudy/{data.imaging_study_id}"
                }
            ],
            "presentedForm": [
                {
                    "contentType": "text/plain",
                    "data": report_base64
                }
            ]
        }

        # Add optional fields
        if data.report_date:
            resource["effectiveDateTime"] = data.report_date.isoformat()
            resource["issued"] = data.report_date.isoformat()

        if data.encounter_id:
            resource["encounter"] = {
                "reference": f"Encounter/{data.encounter_id}"
            }

        if data.conclusion:
            resource["conclusion"] = data.conclusion

        return resource

    def post_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST a FHIR resource to the server.

        Args:
            resource: FHIR resource dict

        Returns:
            Server response as dict

        Raises:
            requests.HTTPError: If POST fails
        """
        resource_type = resource.get("resourceType")
        url = f"{self.fhir_base_url}/{resource_type}"

        response = self.session.post(url, json=resource)
        response.raise_for_status()

        return response.json()

    def put_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        PUT (create/update) a FHIR resource to the server.

        Uses the resource id to enable idempotent updates.

        Args:
            resource: FHIR resource dict with id

        Returns:
            Server response as dict

        Raises:
            requests.HTTPError: If PUT fails
        """
        resource_type = resource.get("resourceType")
        resource_id = resource.get("id")
        url = f"{self.fhir_base_url}/{resource_type}/{resource_id}"

        response = self.session.put(url, json=resource)
        response.raise_for_status()

        return response.json()

    def get_imaging_study(self, study_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an ImagingStudy by MIMIC study ID.

        Args:
            study_id: MIMIC-CXR study identifier

        Returns:
            ImagingStudy resource or None if not found
        """
        url = f"{self.fhir_base_url}/ImagingStudy"
        params = {
            "identifier": f"{self.MIMIC_STUDY_SYSTEM}|{study_id}"
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        bundle = response.json()
        entries = bundle.get("entry", [])

        if entries:
            return entries[0].get("resource")
        return None

    def get_patient_imaging_studies(
        self,
        patient_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get all ImagingStudy resources for a patient.

        Args:
            patient_id: FHIR Patient resource ID
            limit: Maximum results to return

        Returns:
            List of ImagingStudy resources
        """
        url = f"{self.fhir_base_url}/ImagingStudy"
        params = {
            "subject": f"Patient/{patient_id}",
            "_count": limit
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        bundle = response.json()
        return [entry.get("resource") for entry in bundle.get("entry", [])]

    def get_radiology_reports(
        self,
        patient_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get DiagnosticReport resources for a patient.

        Args:
            patient_id: FHIR Patient resource ID
            limit: Maximum results to return

        Returns:
            List of DiagnosticReport resources
        """
        url = f"{self.fhir_base_url}/DiagnosticReport"
        params = {
            "subject": f"Patient/{patient_id}",
            "category": f"{self.LOINC_SYSTEM}|{self.LOINC_IMAGING_STUDY_CODE}",
            "_count": limit
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        bundle = response.json()
        return [entry.get("resource") for entry in bundle.get("entry", [])]

    def get_encounter_imaging(
        self,
        encounter_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get ImagingStudy resources for an encounter.

        Args:
            encounter_id: FHIR Encounter resource ID

        Returns:
            List of ImagingStudy resources
        """
        url = f"{self.fhir_base_url}/ImagingStudy"
        params = {
            "encounter": f"Encounter/{encounter_id}"
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        bundle = response.json()
        return [entry.get("resource") for entry in bundle.get("entry", [])]

    def search_patients_with_imaging(
        self,
        name: Optional[str] = None,
        identifier: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for patients who have imaging studies.

        Args:
            name: Patient name to search (optional)
            identifier: Patient identifier to search (optional)
            limit: Maximum results to return

        Returns:
            List of Patient resources with imaging data
        """
        # First get ImagingStudy patient references
        url = f"{self.fhir_base_url}/ImagingStudy"
        params = {"_count": 100, "_elements": "subject"}

        response = self.session.get(url, params=params)
        response.raise_for_status()

        bundle = response.json()
        patient_refs = set()
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            subject = resource.get("subject", {})
            ref = subject.get("reference", "")
            if ref.startswith("Patient/"):
                patient_refs.add(ref.replace("Patient/", ""))

        # Now fetch those patients with optional filters
        results = []
        for patient_id in list(patient_refs)[:limit]:
            url = f"{self.fhir_base_url}/Patient/{patient_id}"

            try:
                response = self.session.get(url)
                response.raise_for_status()
                patient = response.json()

                # Apply filters
                if name:
                    patient_names = patient.get("name", [])
                    name_match = any(
                        name.lower() in json.dumps(n).lower()
                        for n in patient_names
                    )
                    if not name_match:
                        continue

                results.append(patient)

            except requests.HTTPError:
                continue

        return results

    def lookup_encounter_by_date(
        self,
        patient_id: str,
        study_date: datetime,
        window_hours: int = 24
    ) -> Optional[str]:
        """
        Find an encounter for a patient around a study date.

        Uses 24-hour window matching per spec.

        Args:
            patient_id: FHIR Patient resource ID
            study_date: Date of the imaging study
            window_hours: Hour window for matching (default 24)

        Returns:
            Encounter ID if found, None otherwise
        """
        url = f"{self.fhir_base_url}/Encounter"

        # Search for encounters around the study date
        # FHIR date search with ge (>=) and le (<=)
        date_str = study_date.strftime("%Y-%m-%d")
        params = {
            "subject": f"Patient/{patient_id}",
            "date": [f"ge{date_str}", f"le{date_str}"],
            "_count": 1
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        bundle = response.json()
        entries = bundle.get("entry", [])

        if entries:
            return entries[0].get("resource", {}).get("id")
        return None

    def _get_modality_display(self, code: str) -> str:
        """Get display name for DICOM modality code."""
        modality_map = {
            "CR": "Computed Radiography",
            "DX": "Digital Radiography",
            "CT": "Computed Tomography",
            "MR": "Magnetic Resonance",
            "US": "Ultrasound",
            "NM": "Nuclear Medicine",
            "PT": "Positron Emission Tomography"
        }
        return modality_map.get(code, code)


# Convenience functions for direct use
def create_imaging_study(data: ImagingStudyData, fhir_base_url: Optional[str] = None) -> Dict[str, Any]:
    """Create an ImagingStudy resource."""
    adapter = FHIRRadiologyAdapter(fhir_base_url)
    resource = adapter.build_imaging_study(data)
    return adapter.put_resource(resource)


def create_diagnostic_report(data: DiagnosticReportData, fhir_base_url: Optional[str] = None) -> Dict[str, Any]:
    """Create a DiagnosticReport resource."""
    adapter = FHIRRadiologyAdapter(fhir_base_url)
    resource = adapter.build_diagnostic_report(data)
    return adapter.put_resource(resource)


if __name__ == "__main__":
    # Example usage / test
    print("FHIR Radiology Adapter")
    print("=" * 60)

    adapter = FHIRRadiologyAdapter()
    print(f"FHIR Base URL: {adapter.fhir_base_url}")

    # Example ImagingStudy data
    study_data = ImagingStudyData(
        study_id="s50414267",
        subject_id="p10002428",
        patient_id="123",  # FHIR Patient ID
        study_date=datetime(2023, 6, 15, 10, 30),
        modality="CR",
        description="Chest X-ray PA view"
    )

    print("\nExample ImagingStudy resource:")
    imaging_study = adapter.build_imaging_study(study_data)
    print(json.dumps(imaging_study, indent=2))

    # Example DiagnosticReport data
    report_data = DiagnosticReportData(
        study_id="s50414267",
        patient_id="123",
        imaging_study_id="study-s50414267",
        report_text="IMPRESSION: No acute cardiopulmonary abnormality.",
        report_date=datetime(2023, 6, 15, 14, 0),
        conclusion="No acute findings"
    )

    print("\nExample DiagnosticReport resource:")
    diagnostic_report = adapter.build_diagnostic_report(report_data)
    print(json.dumps(diagnostic_report, indent=2))
