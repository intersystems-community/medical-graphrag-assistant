#!/usr/bin/env python3
"""
Populate FHIR server with sample Patient and ImagingStudy resources.

This script creates demo data for Feature 007: FHIR Radiology Integration.
It first creates Patient resources, then creates ImagingStudy and
DiagnosticReport resources linked to those patients.
"""
import json
import urllib.request
import urllib.error
import base64
import sys

# FHIR server configuration
BASE_URL = "http://localhost:52773/csp/healthshare/demo/fhir/r4"
AUTH_HEADER = "Basic " + base64.b64encode(b"_SYSTEM:sys").decode()

# Sample patients to create
SAMPLE_PATIENTS = [
    {
        "resourceType": "Patient",
        "id": "1",
        "name": [{"family": "Smith", "given": ["John"]}],
        "gender": "male",
        "birthDate": "1965-03-15"
    },
    {
        "resourceType": "Patient",
        "id": "2",
        "name": [{"family": "Garcia", "given": ["Maria"]}],
        "gender": "female",
        "birthDate": "1978-07-22"
    },
    {
        "resourceType": "Patient",
        "id": "315",
        "name": [{"family": "Johnson", "given": ["Robert"]}],
        "gender": "male",
        "birthDate": "1952-11-08"
    },
    {
        "resourceType": "Patient",
        "id": "553",
        "name": [{"family": "Williams", "given": ["Sarah"]}],
        "gender": "female",
        "birthDate": "1990-01-30"
    },
    {
        "resourceType": "Patient",
        "id": "1283",
        "name": [{"family": "Brown", "given": ["Michael"]}],
        "gender": "male",
        "birthDate": "1975-06-18"
    }
]

# Sample ImagingStudy resources
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
    },
    {
        "resourceType": "ImagingStudy",
        "id": "study-s50414270",
        "status": "available",
        "subject": {"reference": "Patient/553", "display": "Sarah Williams"},
        "started": "2024-03-18T11:45:00Z",
        "modality": [{"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CR", "display": "Computed Radiography"}],
        "identifier": [{"system": "urn:mimic-cxr:study", "value": "s50414270"}],
        "numberOfSeries": 1,
        "numberOfInstances": 1,
        "description": "Chest X-ray PA view - Clear lungs"
    },
    {
        "resourceType": "ImagingStudy",
        "id": "study-s50414271",
        "status": "available",
        "subject": {"reference": "Patient/1283", "display": "Michael Brown"},
        "started": "2024-03-19T08:30:00Z",
        "modality": [{"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CR", "display": "Computed Radiography"}],
        "identifier": [{"system": "urn:mimic-cxr:study", "value": "s50414271"}],
        "numberOfSeries": 1,
        "numberOfInstances": 1,
        "description": "Chest X-ray - Possible pneumonia right lower lobe"
    }
]

# Sample DiagnosticReport resources
SAMPLE_DIAGNOSTIC_REPORTS = [
    {
        "resourceType": "DiagnosticReport",
        "id": "report-s50414267",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "18748-4", "display": "Diagnostic imaging study"}]},
        "subject": {"reference": "Patient/1", "display": "John Smith"},
        "imagingStudy": [{"reference": "ImagingStudy/study-s50414267"}],
        "conclusion": "No acute cardiopulmonary findings. Heart size normal. Lungs clear.",
        "effectiveDateTime": "2024-03-15T11:30:00Z",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "RAD", "display": "Radiology"}]}]
    },
    {
        "resourceType": "DiagnosticReport",
        "id": "report-s50414268",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "18748-4", "display": "Diagnostic imaging study"}]},
        "subject": {"reference": "Patient/2", "display": "Maria Garcia"},
        "imagingStudy": [{"reference": "ImagingStudy/study-s50414268"}],
        "conclusion": "Mild cardiomegaly. No focal consolidation. Recommend follow-up.",
        "effectiveDateTime": "2024-03-16T15:00:00Z",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "RAD", "display": "Radiology"}]}]
    },
    {
        "resourceType": "DiagnosticReport",
        "id": "report-s50414269",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "18748-4", "display": "Diagnostic imaging study"}]},
        "subject": {"reference": "Patient/315", "display": "Robert Johnson"},
        "imagingStudy": [{"reference": "ImagingStudy/study-s50414269"}],
        "conclusion": "Bilateral pulmonary infiltrates consistent with pneumonia. Recommend clinical correlation.",
        "effectiveDateTime": "2024-03-17T10:00:00Z",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "RAD", "display": "Radiology"}]}]
    },
    {
        "resourceType": "DiagnosticReport",
        "id": "report-s50414271",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "18748-4", "display": "Diagnostic imaging study"}]},
        "subject": {"reference": "Patient/1283", "display": "Michael Brown"},
        "imagingStudy": [{"reference": "ImagingStudy/study-s50414271"}],
        "conclusion": "Right lower lobe opacity concerning for pneumonia. Consider antibiotic therapy.",
        "effectiveDateTime": "2024-03-19T09:30:00Z",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "RAD", "display": "Radiology"}]}]
    }
]

# Sample Encounter resources (for get_encounter_imaging tests)
SAMPLE_ENCOUNTERS = [
    {
        "resourceType": "Encounter",
        "id": "enc-001",
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP", "display": "inpatient encounter"},
        "subject": {"reference": "Patient/1", "display": "John Smith"},
        "period": {"start": "2024-03-15T08:00:00Z", "end": "2024-03-15T18:00:00Z"}
    },
    {
        "resourceType": "Encounter",
        "id": "enc-002",
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB", "display": "ambulatory"},
        "subject": {"reference": "Patient/2", "display": "Maria Garcia"},
        "period": {"start": "2024-03-16T12:00:00Z", "end": "2024-03-16T16:00:00Z"}
    }
]


def put_resource(resource, resource_type=None, resource_id=None):
    """PUT a FHIR resource to create or update it."""
    if resource_type is None:
        resource_type = resource.get("resourceType")
    if resource_id is None:
        resource_id = resource.get("id")

    url = f"{BASE_URL}/{resource_type}/{resource_id}"
    data = json.dumps(resource).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Content-Type", "application/fhir+json")
    req.add_header("Accept", "application/fhir+json")
    req.add_header("Authorization", AUTH_HEADER)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return True, result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:200]
        return False, f"HTTPError {e.code}: {error_body}"
    except Exception as e:
        return False, str(e)


def get_resource_count(resource_type):
    """Get count of resources of a given type."""
    url = f"{BASE_URL}/{resource_type}?_summary=count"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/fhir+json")
    req.add_header("Authorization", AUTH_HEADER)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result.get("total", 0)
    except Exception as e:
        return f"Error: {e}"


def main():
    print("=" * 60)
    print("FHIR Radiology Data Population Script")
    print("=" * 60)
    print(f"FHIR Server: {BASE_URL}")
    print()

    # Create Patients
    print("Creating Patient resources...")
    patient_success = 0
    for patient in SAMPLE_PATIENTS:
        success, result = put_resource(patient)
        if success:
            print(f"  ✓ Patient/{patient['id']} - {patient['name'][0]['given'][0]} {patient['name'][0]['family']}")
            patient_success += 1
        else:
            print(f"  ✗ Patient/{patient['id']} - {result}")
    print(f"  Patients created: {patient_success}/{len(SAMPLE_PATIENTS)}")
    print()

    # Create Encounters
    print("Creating Encounter resources...")
    encounter_success = 0
    for encounter in SAMPLE_ENCOUNTERS:
        success, result = put_resource(encounter)
        if success:
            print(f"  ✓ Encounter/{encounter['id']}")
            encounter_success += 1
        else:
            print(f"  ✗ Encounter/{encounter['id']} - {result}")
    print(f"  Encounters created: {encounter_success}/{len(SAMPLE_ENCOUNTERS)}")
    print()

    # Create ImagingStudies
    print("Creating ImagingStudy resources...")
    study_success = 0
    for study in SAMPLE_IMAGING_STUDIES:
        success, result = put_resource(study)
        if success:
            print(f"  ✓ ImagingStudy/{study['id']} - {study['subject']['display']}")
            study_success += 1
        else:
            print(f"  ✗ ImagingStudy/{study['id']} - {result}")
    print(f"  ImagingStudies created: {study_success}/{len(SAMPLE_IMAGING_STUDIES)}")
    print()

    # Create DiagnosticReports
    print("Creating DiagnosticReport resources...")
    report_success = 0
    for report in SAMPLE_DIAGNOSTIC_REPORTS:
        success, result = put_resource(report)
        if success:
            print(f"  ✓ DiagnosticReport/{report['id']} - {report['conclusion'][:40]}...")
            report_success += 1
        else:
            print(f"  ✗ DiagnosticReport/{report['id']} - {result}")
    print(f"  DiagnosticReports created: {report_success}/{len(SAMPLE_DIAGNOSTIC_REPORTS)}")
    print()

    # Verify counts
    print("=" * 60)
    print("Verification - Resource Counts:")
    print(f"  Patient:          {get_resource_count('Patient')}")
    print(f"  Encounter:        {get_resource_count('Encounter')}")
    print(f"  ImagingStudy:     {get_resource_count('ImagingStudy')}")
    print(f"  DiagnosticReport: {get_resource_count('DiagnosticReport')}")
    print("=" * 60)

    total_success = patient_success + encounter_success + study_success + report_success
    total_expected = len(SAMPLE_PATIENTS) + len(SAMPLE_ENCOUNTERS) + len(SAMPLE_IMAGING_STUDIES) + len(SAMPLE_DIAGNOSTIC_REPORTS)

    if total_success == total_expected:
        print("✓ All resources created successfully!")
        return 0
    else:
        print(f"⚠ Created {total_success}/{total_expected} resources")
        return 1


if __name__ == "__main__":
    sys.exit(main())
