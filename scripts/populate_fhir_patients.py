#!/usr/bin/env python3
"""
Populate FHIR Patient resources from MIMIC-CXR subjects.

Reads unique SubjectIDs from VectorSearch.MIMICCXRImages table
and creates corresponding FHIR Patient resources.

Usage:
    python scripts/populate_fhir_patients.py

Environment Variables:
    IRIS_HOST       IRIS database host (default: localhost)
    IRIS_PORT       IRIS SuperServer port (default: 32782)
    FHIR_BASE_URL   FHIR API endpoint (default: http://localhost:32783/csp/healthshare/demo/fhir/r4)
"""

import os
import sys
import json
import requests
from typing import List, Dict, Optional

# Add project root to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.db.connection import get_connection


def get_unique_subjects() -> List[str]:
    """Get unique SubjectIDs from VectorSearch.MIMICCXRImages table."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT DISTINCT SubjectID FROM VectorSearch.MIMICCXRImages ORDER BY SubjectID")
        subjects = [row[0] for row in cursor.fetchall()]
        return subjects
    finally:
        cursor.close()
        conn.close()


def check_patient_exists(fhir_base_url: str, subject_id: str, session: requests.Session) -> bool:
    """Check if a Patient with the given MIMIC subject ID already exists."""
    try:
        url = f"{fhir_base_url}/Patient"
        params = {"identifier": f"urn:mimic-cxr:subject|{subject_id}"}
        response = session.get(url, params=params, timeout=10)

        if response.status_code == 200:
            bundle = response.json()
            return bundle.get("total", 0) > 0
    except Exception as e:
        print(f"  Warning: Error checking patient {subject_id}: {e}")

    return False


def create_patient(fhir_base_url: str, subject_id: str, session: requests.Session) -> Optional[str]:
    """Create a FHIR Patient resource for a MIMIC subject."""
    # Build Patient resource
    patient = {
        "resourceType": "Patient",
        "identifier": [
            {
                "system": "urn:mimic-cxr:subject",
                "value": subject_id
            }
        ],
        "active": True,
        "name": [
            {
                "use": "official",
                "family": f"MIMIC-{subject_id[-4:]}",  # Last 4 chars as pseudo-family name
                "given": ["Subject"]
            }
        ],
        "gender": "unknown",  # MIMIC-CXR doesn't provide gender in file paths
        "meta": {
            "tag": [
                {
                    "system": "urn:mimic-cxr:source",
                    "code": "mimic-cxr",
                    "display": "MIMIC-CXR Dataset"
                }
            ]
        }
    }

    try:
        url = f"{fhir_base_url}/Patient"
        headers = {"Content-Type": "application/fhir+json"}
        response = session.post(url, json=patient, headers=headers, timeout=10)

        if response.status_code in (200, 201):
            result = response.json()
            return result.get("id")
        else:
            print(f"  Error creating patient {subject_id}: HTTP {response.status_code}")
            print(f"    Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"  Error creating patient {subject_id}: {e}")
        return None


def update_patient_mapping(subject_id: str, fhir_patient_id: str):
    """Update VectorSearch.PatientImageMapping with the FHIR Patient ID."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if mapping table exists and create if not
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'VectorSearch' AND TABLE_NAME = 'PatientImageMapping'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                CREATE TABLE VectorSearch.PatientImageMapping (
                    MIMICSubjectID VARCHAR(20) PRIMARY KEY,
                    FHIRPatientID VARCHAR(100) NOT NULL,
                    FHIRPatientName VARCHAR(200),
                    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

        # Insert or update mapping
        cursor.execute("""
            INSERT OR REPLACE INTO VectorSearch.PatientImageMapping
            (MIMICSubjectID, FHIRPatientID, FHIRPatientName)
            VALUES (?, ?, ?)
        """, (subject_id, fhir_patient_id, f"Subject MIMIC-{subject_id[-4:]}"))
        conn.commit()
    except Exception as e:
        print(f"  Warning: Could not update patient mapping for {subject_id}: {e}")
    finally:
        cursor.close()
        conn.close()


def main():
    """Main function to populate FHIR Patient resources."""
    fhir_base_url = os.environ.get(
        "FHIR_BASE_URL",
        "http://localhost:32783/csp/healthshare/demo/fhir/r4"
    )

    print("=" * 60)
    print("FHIR Patient Population from MIMIC-CXR Subjects")
    print("=" * 60)
    print(f"FHIR Base URL: {fhir_base_url}")
    print()

    # Get unique subjects from database
    print("Fetching unique subjects from VectorSearch.MIMICCXRImages...")
    subjects = get_unique_subjects()
    print(f"Found {len(subjects)} unique subjects")
    print()

    if not subjects:
        print("No subjects found. Please run the MIMIC-CXR ingestion first.")
        return

    # Test FHIR connection
    session = requests.Session()
    print("Testing FHIR connection...")
    try:
        response = session.get(f"{fhir_base_url}/metadata", timeout=10)
        if response.status_code == 200:
            print("FHIR server is available")
        else:
            print(f"Warning: FHIR metadata returned HTTP {response.status_code}")
    except Exception as e:
        print(f"Error connecting to FHIR server: {e}")
        print("Please ensure the FHIR server is running and accessible.")
        return
    print()

    # Create Patient resources
    print("Creating FHIR Patient resources...")
    created = 0
    skipped = 0
    errors = 0

    for i, subject_id in enumerate(subjects, 1):
        # Check if already exists
        if check_patient_exists(fhir_base_url, subject_id, session):
            skipped += 1
            if i % 20 == 0:
                print(f"  Progress: {i}/{len(subjects)} (created: {created}, skipped: {skipped})")
            continue

        # Create patient
        patient_id = create_patient(fhir_base_url, subject_id, session)

        if patient_id:
            created += 1
            # Update mapping table
            update_patient_mapping(subject_id, patient_id)
        else:
            errors += 1

        # Progress update
        if i % 20 == 0:
            print(f"  Progress: {i}/{len(subjects)} (created: {created}, skipped: {skipped}, errors: {errors})")

    # Summary
    print()
    print("=" * 60)
    print("Population Complete!")
    print("=" * 60)
    print(f"Total subjects: {len(subjects)}")
    print(f"  Created: {created}")
    print(f"  Skipped (already exist): {skipped}")
    print(f"  Errors: {errors}")
    print()

    # Verify count
    try:
        response = session.get(f"{fhir_base_url}/Patient?_summary=count", timeout=10)
        if response.status_code == 200:
            bundle = response.json()
            total = bundle.get("total", 0)
            print(f"Total Patient resources in FHIR repo: {total}")
    except Exception as e:
        print(f"Could not verify patient count: {e}")


if __name__ == "__main__":
    main()
