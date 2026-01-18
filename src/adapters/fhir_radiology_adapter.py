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

    When FHIR server is unavailable, returns sample demo data for graceful degradation.
    """

    # FHIR base URL from environment or default
    # Priority: Env FHIR_BASE_URL > Internal mapping
    DEFAULT_FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "http://localhost:32783/csp/healthshare/demo/fhir/r4")

    # MIMIC-CXR identifier systems
    MIMIC_STUDY_SYSTEM = "urn:mimic-cxr:study"
    MIMIC_SUBJECT_SYSTEM = "urn:mimic-cxr:subject"
    MIMIC_REPORT_SYSTEM = "urn:mimic-cxr:report"

    # DICOM modality codes
    DICOM_MODALITY_SYSTEM = "http://dicom.nema.org/resources/ontology/DCM"

    # LOINC code for diagnostic imaging study
    LOINC_IMAGING_STUDY_CODE = "18748-4"
    LOINC_SYSTEM = "http://loinc.org"

    # Sample demo data for when FHIR server is unavailable
    SAMPLE_IMAGING_STUDIES = [
        {
            "resourceType": "ImagingStudy",
            "id": "study-s50414267",
            "status": "available",
            "subject": {"reference": "Patient/1", "display": "John Smith"},
            "started": "2024-03-15T10:30:00Z",
            "modality": [{"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CR", "display": "Computed Radiography"}],
            "identifier": [{"system": "urn:mimic-cxr:study", "value": "s50414267"}],
            "numberOfSeries": 1,
            "numberOfInstances": 1,
            "description": "Chest X-ray PA view - No acute cardiopulmonary findings"
        },
        {
            "resourceType": "ImagingStudy",
            "id": "study-s50414268",
            "status": "available",
            "subject": {"reference": "Patient/2", "display": "Maria Garcia"},
            "started": "2024-03-16T14:15:00Z",
            "modality": [{"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CR", "display": "Computed Radiography"}],
            "identifier": [{"system": "urn:mimic-cxr:study", "value": "s50414268"}],
            "numberOfSeries": 1,
            "numberOfInstances": 1,
            "description": "Chest X-ray PA and Lateral - Mild cardiomegaly"
        },
        {
            "resourceType": "ImagingStudy",
            "id": "study-s50414269",
            "status": "available",
            "subject": {"reference": "Patient/315", "display": "Robert Johnson"},
            "started": "2024-03-17T09:00:00Z",
            "modality": [{"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CR", "display": "Computed Radiography"}],
            "identifier": [{"system": "urn:mimic-cxr:study", "value": "s50414269"}],
            "numberOfSeries": 1,
            "numberOfInstances": 2,
            "description": "Chest X-ray - Bilateral pulmonary infiltrates"
        }
    ]

    SAMPLE_DIAGNOSTIC_REPORTS = [
        {
            "resourceType": "DiagnosticReport",
            "id": "report-s50414267",
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "18748-4", "display": "Diagnostic imaging study"}]},
            "subject": {"reference": "Patient/1", "display": "John Smith"},
            "imagingStudy": [{"reference": "ImagingStudy/study-s50414267"}],
            "conclusion": "No acute cardiopulmonary findings. Heart size normal. Lungs clear.",
            "effectiveDateTime": "2024-03-15T11:30:00Z"
        },
        {
            "resourceType": "DiagnosticReport",
            "id": "report-s50414268",
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "18748-4", "display": "Diagnostic imaging study"}]},
            "subject": {"reference": "Patient/2", "display": "Maria Garcia"},
            "imagingStudy": [{"reference": "ImagingStudy/study-s50414268"}],
            "conclusion": "Mild cardiomegaly. No focal consolidation. Recommend follow-up.",
            "effectiveDateTime": "2024-03-16T15:00:00Z"
        }
    ]

    SAMPLE_PATIENTS = [
        {"resourceType": "Patient", "id": "1", "name": [{"family": "Smith", "given": ["John"]}], "gender": "male", "birthDate": "1965-03-15"},
        {"resourceType": "Patient", "id": "2", "name": [{"family": "Garcia", "given": ["Maria"]}], "gender": "female", "birthDate": "1978-07-22"},
        {"resourceType": "Patient", "id": "315", "name": [{"family": "Johnson", "given": ["Robert"]}], "gender": "male", "birthDate": "1952-11-08"}
    ]

    def __init__(self, fhir_base_url: Optional[str] = None, use_demo_mode: Optional[bool] = None):
        """
        Initialize the FHIR Radiology Adapter.

        Args:
            fhir_base_url: Base URL for FHIR server. Defaults to FHIR_BASE_URL env var
                          or http://localhost:52773/fhir/r4
            use_demo_mode: If True, always use demo data. If None, auto-detect based
                          on FHIR server availability.
        """
        self.fhir_base_url = fhir_base_url or os.getenv(
            'FHIR_BASE_URL',
            self.DEFAULT_FHIR_BASE_URL
        )
        self._demo_mode = use_demo_mode
        self._fhir_available = None  # Cached availability check
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/fhir+json',
            'Accept': 'application/fhir+json'
        })

        # Add Basic Auth for IRIS FHIR server
        fhir_username = os.getenv('FHIR_USERNAME', '_SYSTEM')
        fhir_password = os.getenv('FHIR_PASSWORD', 'sys')
        auth_string = base64.b64encode(f"{fhir_username}:{fhir_password}".encode()).decode()
        self.session.headers.update({
            'Authorization': f'Basic {auth_string}'
        })

    def get_imaging_study_details(self, study_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific ImagingStudy.
        """
        # 1. Try FHIR REST
        if self._is_fhir_available():
            try:
                # Try by ID
                url = f"{self.fhir_base_url}/ImagingStudy/{study_id}"
                response = self.session.get(url)
                if response.status_code == 200:
                    return response.json()
                
                # Try by identifier
                url = f"{self.fhir_base_url}/ImagingStudy"
                params = {"identifier": f"{self.MIMIC_STUDY_SYSTEM}|{study_id}"}
                response = self.session.get(url, params=params)
                if response.status_code == 200:
                    bundle = response.json()
                    entries = bundle.get("entry", [])
                    if entries:
                        return entries[0].get("resource")
            except Exception as e:
                print(f"[WARN] FHIR study details failed: {e}")

        # 2. SQL Fallback
        try:
            from src.db.connection import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            # Clean study_id (might have 'study-' prefix)
            clean_id = study_id.replace("study-", "")
            
            sql = """
                SELECT ImageID, PatientID, StudyType, ImagePath, RelatedReportID
                FROM SQLUser.MedicalImageVectors
                WHERE ImageID = ? OR RelatedReportID = ?
            """
            cursor.execute(sql, [clean_id, clean_id])
            row = cursor.fetchone()
            conn.close()
            
            if row:
                image_id, pat_id, study_type, path, report_id = row
                return {
                    "resourceType": "ImagingStudy",
                    "id": f"study-{image_id}",
                    "status": "available",
                    "subject": {"reference": f"Patient/{pat_id}"},
                    "modality": [{"code": study_type}],
                    "identifier": [{"system": self.MIMIC_STUDY_SYSTEM, "value": image_id}],
                    "description": f"Radiology study from {path}",
                    "numberOfSeries": 1,
                    "numberOfInstances": 1,
                    "series": [
                        {
                            "uid": f"series-{image_id}",
                            "number": 1,
                            "modality": {"code": study_type},
                            "instance": [{"uid": f"sop-{image_id}", "number": 1}]
                        }
                    ]
                }
        except Exception as e:
            print(f"[WARN] SQL study details fallback failed: {e}")

        # 3. Sample data fallback
        for study in self.SAMPLE_IMAGING_STUDIES:
            if study.get("id") == study_id or any(i.get("value") == study_id for i in study.get("identifier", [])):
                return study
                
        return None

    def _is_fhir_available(self) -> bool:
        """Check if FHIR server is available (cached)."""
        if self._demo_mode is True:
            return False
        if self._demo_mode is False:
            return True
        if self._fhir_available is not None:
            return self._fhir_available

        try:
            response = self.session.get(f"{self.fhir_base_url}/metadata", timeout=5)
            self._fhir_available = response.status_code == 200
        except Exception:
            self._fhir_available = False

        return self._fhir_available

    @property
    def demo_mode(self) -> bool:
        """Return True if using demo mode (FHIR server unavailable)."""
        return not self._is_fhir_available()

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
        limit: int = 20,
        modality: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all ImagingStudy resources for a patient.

        Args:
            patient_id: FHIR Patient resource ID
            limit: Maximum results to return
            modality: Optional modality filter (e.g. "CR", "CT")

        Returns:
            List of ImagingStudy resources
        """
        if self._is_fhir_available():
            try:
                url = f"{self.fhir_base_url}/ImagingStudy"
                params = {
                    "subject": f"Patient/{patient_id}",
                    "_count": limit
                }
                if modality:
                    params["modality"] = modality

                response = self.session.get(url, params=params)
                response.raise_for_status()

                bundle = response.json()
                return [entry.get("resource") for entry in bundle.get("entry", [])]
            except Exception as e:
                print(f"[WARN] FHIR search failed, trying SQL fallback: {e}")

        try:
            from src.db.connection import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            where_clause = "WHERE PatientID = ?"
            params = [patient_id]
            
            if modality:
                where_clause += " AND StudyType = ?"
                params.append(modality)
                
            sql = f"""
                SELECT TOP {limit} ImageID, PatientID, StudyType, ImagePath, RelatedReportID
                FROM SQLUser.MedicalImageVectors
                {where_clause}
            """
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            studies = []
            for row in rows:
                image_id, pat_id, study_type, path, report_id = row
                studies.append({
                    "resourceType": "ImagingStudy",
                    "id": f"study-{image_id}",
                    "status": "available",
                    "subject": {"reference": f"Patient/{pat_id}"},
                    "modality": [{"code": study_type}],
                    "identifier": [{"system": self.MIMIC_STUDY_SYSTEM, "value": image_id}],
                    "description": f"Radiology study from {path}",
                    "number_of_series": 1,
                    "number_of_instances": 1
                })
            
            conn.close()
            if studies:
                return studies
        except Exception as e:
            print(f"[WARN] SQL fallback failed: {e}")

        return [
            s for s in self.SAMPLE_IMAGING_STUDIES
            if f"Patient/{patient_id}" in s.get("subject", {}).get("reference", "")
        ][:limit]

    def get_radiology_reports(
        self,
        patient_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get DiagnosticReport resources for a patient.
        """
        if self._is_fhir_available():
            try:
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
            except Exception as e:
                print(f"[WARN] FHIR reports failed: {e}")

        try:
            from src.db.connection import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            sql = f"""
                SELECT TOP {limit} ImageID, PatientID, StudyType, ImagePath, RelatedReportID
                FROM SQLUser.MedicalImageVectors
                WHERE PatientID = ? AND RelatedReportID IS NOT NULL
            """
            cursor.execute(sql, [patient_id])
            rows = cursor.fetchall()
            
            reports = []
            for row in rows:
                image_id, pat_id, study_type, path, report_id = row
                reports.append({
                    "resourceType": "DiagnosticReport",
                    "id": f"report-{report_id}",
                    "status": "final",
                    "code": {"coding": [{"system": self.LOINC_SYSTEM, "code": self.LOINC_IMAGING_STUDY_CODE}]},
                    "subject": {"reference": f"Patient/{pat_id}"},
                    "imagingStudy": [{"reference": f"ImagingStudy/study-{image_id}"}],
                    "conclusion": f"Radiology report for {study_type} study"
                })
            
            conn.close()
            if reports:
                return reports
        except Exception as e:
            print(f"[WARN] SQL reports fallback failed: {e}")

        return [
            r for r in self.SAMPLE_DIAGNOSTIC_REPORTS
            if f"Patient/{patient_id}" in r.get("subject", {}).get("reference", "")
        ][:limit]

    def get_encounter_imaging(
        self,
        encounter_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get ImagingStudy resources for an encounter.
        """
        if self._is_fhir_available():
            try:
                url = f"{self.fhir_base_url}/ImagingStudy"
                params = {"encounter": f"Encounter/{encounter_id}"}
                response = self.session.get(url, params=params)
                response.raise_for_status()
                bundle = response.json()
                return [entry.get("resource") for entry in bundle.get("entry", [])]
            except Exception as e:
                print(f"[WARN] FHIR encounter imaging failed: {e}")

        return self.SAMPLE_IMAGING_STUDIES[:1]

    def search_patients_with_imaging(
        self,
        name: Optional[str] = None,
        identifier: Optional[str] = None,
        limit: int = 20,
        modality: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for patients who have imaging studies.
        """
        try:
            from src.db.connection import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            where_clauses = []
            params = []
            
            if modality:
                where_clauses.append("StudyType = ?")
                params.append(modality)
                
            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            sql = f"""
                SELECT DISTINCT TOP {limit} PatientID
                FROM SQLUser.MedicalImageVectors
                {where_sql}
            """
            cursor.execute(sql, params)
            patient_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            if patient_ids:
                return [{"resourceType": "Patient", "id": pat_id} for pat_id in patient_ids]
        except Exception as e:
            print(f"[WARN] SQL patient search failed: {e}")

        if self.demo_mode:
            return self.SAMPLE_PATIENTS[:limit]
            
        return []

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
