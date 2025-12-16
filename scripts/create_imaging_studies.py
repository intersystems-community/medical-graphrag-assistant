#!/usr/bin/env python3
"""Create sample ImagingStudy FHIR resources for existing patients."""
import json
import urllib.request
import urllib.error
import base64

BASE_URL = "http://localhost:52773/csp/healthshare/demo/fhir/r4"
# IRIS credentials - base64 encoded for Basic auth
AUTH_HEADER = "Basic " + base64.b64encode(b"_SYSTEM:sys").decode()

# Patient IDs from FHIR server
patient_ids = ["1", "2", "315", "553", "1283", "1475"]

for i, patient_id in enumerate(patient_ids):
    study = {
        "resourceType": "ImagingStudy",
        "status": "available",
        "subject": {"reference": "Patient/" + patient_id},
        "started": "2024-03-{:02d}T10:30:00Z".format(15 + i),
        "modality": [{"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CR", "display": "Computed Radiography"}],
        "identifier": [{"system": "urn:mimic-cxr:study", "value": "study-{:05d}".format(10001 + i)}],
        "numberOfSeries": 1,
        "numberOfInstances": 1,
        "description": "Chest X-ray PA view"
    }

    data = json.dumps(study).encode("utf-8")
    req = urllib.request.Request(BASE_URL + "/ImagingStudy", data=data)
    req.add_header("Content-Type", "application/fhir+json")
    req.add_header("Accept", "application/fhir+json")
    req.add_header("Authorization", AUTH_HEADER)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            print("Created ImagingStudy for Patient/{}: ID={}".format(patient_id, result.get("id", "unknown")))
    except urllib.error.HTTPError as e:
        print("HTTPError for Patient/{}: {} - {}".format(patient_id, e.code, e.read().decode()[:200]))
    except Exception as e:
        print("Error for Patient/{}: {}".format(patient_id, e))

print("\nDone creating ImagingStudy resources")

# Verify count
try:
    req = urllib.request.Request(BASE_URL + "/ImagingStudy?_summary=count")
    req.add_header("Accept", "application/fhir+json")
    req.add_header("Authorization", AUTH_HEADER)
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        print("Total ImagingStudy count: {}".format(result.get("total", "unknown")))
except Exception as e:
    print("Could not verify count: {}".format(e))
