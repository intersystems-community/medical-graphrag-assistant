#!/usr/bin/env python3
"""
Populate FHIR server and IRIS GraphRAG tables with 50 patients.

This script creates comprehensive demo data including:
- 50 FHIR Patient resources
- ImagingStudy and DiagnosticReport resources
- Clinical notes with embeddings (ClinicalNoteVectors)
- Entities extracted from clinical notes (Entity table)
- Relationships between entities (Relationship table)
- Medical image vector placeholders (MedicalImageVectors)

Usage:
    # Run locally (requires FHIR_BASE_URL and IRIS connection)
    python scripts/populate_full_graphrag_data.py

    # Run with custom FHIR URL
    FHIR_BASE_URL=http://localhost:32783/csp/healthshare/demo/fhir/r4 python scripts/populate_full_graphrag_data.py
"""
import json
import urllib.request
import urllib.error
import base64
import sys
import os
import random
import subprocess
from datetime import datetime, timedelta

# Configuration
FHIR_BASE_URL = os.getenv('FHIR_BASE_URL', "http://localhost:32783/csp/healthshare/demo/fhir/r4")
FHIR_USERNAME = os.getenv('FHIR_USERNAME', "_SYSTEM")
FHIR_PASSWORD = os.getenv('FHIR_PASSWORD', "sys")

# IRIS connection - for local Docker
IRIS_HOST = os.getenv('IRIS_HOST', 'localhost')
IRIS_PORT = os.getenv('IRIS_PORT', '32782')
IRIS_NAMESPACE = os.getenv('IRIS_NAMESPACE', '%SYS')

# Data generation configuration
NUM_PATIENTS = 50

# Realistic medical data pools
FIRST_NAMES_MALE = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
                    "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua"]
FIRST_NAMES_FEMALE = ["Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen",
                      "Lisa", "Nancy", "Betty", "Margaret", "Sandra", "Ashley", "Kimberly", "Emily", "Donna", "Michelle"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
              "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"]

CONDITIONS = [
    ("diabetes mellitus type 2", "Condition", ["metformin", "insulin glargine", "hyperglycemia", "neuropathy", "retinopathy"]),
    ("hypertension", "Condition", ["lisinopril", "amlodipine", "elevated blood pressure", "headache", "dizziness"]),
    ("congestive heart failure", "Condition", ["furosemide", "carvedilol", "shortness of breath", "peripheral edema", "fatigue"]),
    ("chronic kidney disease", "Condition", ["creatinine elevated", "proteinuria", "anemia", "fatigue", "fluid retention"]),
    ("pneumonia", "Condition", ["ceftriaxone", "azithromycin", "fever", "cough", "chest pain", "dyspnea"]),
    ("COPD", "Condition", ["albuterol", "tiotropium", "prednisone", "wheezing", "chronic cough", "dyspnea"]),
    ("atrial fibrillation", "Condition", ["warfarin", "apixaban", "metoprolol", "palpitations", "irregular heartbeat"]),
    ("coronary artery disease", "Condition", ["aspirin", "atorvastatin", "nitroglycerin", "chest pain", "angina"]),
    ("hypothyroidism", "Condition", ["levothyroxine", "fatigue", "weight gain", "cold intolerance"]),
    ("depression", "Condition", ["sertraline", "escitalopram", "insomnia", "fatigue", "appetite changes"]),
    ("anxiety disorder", "Condition", ["lorazepam", "buspirone", "panic attacks", "restlessness", "insomnia"]),
    ("osteoarthritis", "Condition", ["acetaminophen", "ibuprofen", "joint pain", "stiffness", "limited mobility"]),
    ("asthma", "Condition", ["albuterol", "fluticasone", "wheezing", "shortness of breath", "cough"]),
    ("migraine", "Condition", ["sumatriptan", "topiramate", "headache", "nausea", "photophobia"]),
    ("gastroesophageal reflux", "Condition", ["omeprazole", "pantoprazole", "heartburn", "regurgitation", "dysphagia"]),
    ("urinary tract infection", "Condition", ["ciprofloxacin", "nitrofurantoin", "dysuria", "frequency", "urgency"]),
    ("anemia", "Condition", ["ferrous sulfate", "vitamin B12", "fatigue", "pallor", "weakness"]),
    ("hyperlipidemia", "Condition", ["atorvastatin", "rosuvastatin", "elevated cholesterol", "elevated LDL"]),
    ("obesity", "Condition", ["diet modification", "exercise program", "elevated BMI", "metabolic syndrome"]),
    ("sleep apnea", "Condition", ["CPAP therapy", "snoring", "daytime sleepiness", "fatigue"]),
]

IMAGING_FINDINGS = [
    ("No acute cardiopulmonary findings", "normal"),
    ("Mild cardiomegaly", "abnormal"),
    ("Clear lungs, no focal consolidation", "normal"),
    ("Bilateral pulmonary infiltrates", "abnormal"),
    ("Right lower lobe opacity concerning for pneumonia", "abnormal"),
    ("Pleural effusion, small bilateral", "abnormal"),
    ("Pulmonary edema", "abnormal"),
    ("Emphysematous changes", "abnormal"),
    ("No active disease", "normal"),
    ("Possible pneumothorax, recommend CT", "abnormal"),
]

NOTE_TEMPLATES = [
    "Patient presents with {symptom1}. History of {condition}. Currently on {medication}. Vital signs stable. Assessment: {condition} {status}. Plan: Continue current medications, follow up in {days} days.",
    "Chief complaint: {symptom1}. PMH significant for {condition}. Current medications include {medication}. Physical exam notable for {symptom2}. Impression: {condition} with {symptom1}. Recommend {treatment}.",
    "Follow-up visit for {condition}. Patient reports {symptom1} and {symptom2}. Taking {medication} as prescribed. Labs show {finding}. Plan: Adjust {medication} dose, recheck labs in {days} weeks.",
    "Emergency presentation with acute {symptom1}. Known {condition}. Started on {medication}. Chest X-ray shows {imaging_finding}. Admit for observation and treatment.",
    "Routine evaluation of {condition}. Patient feeling {status}. {medication} well-tolerated. No new complaints. Continue current regimen. Return visit scheduled.",
]


def generate_patient_data():
    """Generate data for 50 patients with conditions, notes, entities, relationships."""
    patients = []

    for i in range(1, NUM_PATIENTS + 1):
        gender = random.choice(["male", "female"])
        first_names = FIRST_NAMES_MALE if gender == "male" else FIRST_NAMES_FEMALE
        first_name = random.choice(first_names)
        last_name = random.choice(LAST_NAMES)

        # Random birth date between 1940 and 2000
        year = random.randint(1940, 2000)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        birth_date = f"{year}-{month:02d}-{day:02d}"

        # Assign 1-3 conditions to each patient
        num_conditions = random.randint(1, 3)
        patient_conditions = random.sample(CONDITIONS, num_conditions)

        # Generate clinical notes for this patient
        notes = []
        entities = []
        relationships = []

        for cond_idx, (condition, cond_type, related_items) in enumerate(patient_conditions):
            note_id = f"note-p{i:03d}-{cond_idx + 1}"

            # Pick related items
            medications = [item for item in related_items if not any(s in item.lower() for s in ["pain", "cough", "fever", "fatigue", "edema", "elevated", "nausea"])]
            symptoms = [item for item in related_items if item not in medications]

            if not medications:
                medications = ["supportive care"]
            if not symptoms:
                symptoms = ["general malaise"]

            # Generate note text
            template = random.choice(NOTE_TEMPLATES)
            note_text = template.format(
                symptom1=symptoms[0] if symptoms else "symptoms",
                symptom2=symptoms[1] if len(symptoms) > 1 else symptoms[0] if symptoms else "discomfort",
                condition=condition,
                medication=medications[0] if medications else "medications",
                status=random.choice(["stable", "improving", "controlled", "worsening"]),
                days=random.randint(7, 30),
                treatment=random.choice(["physical therapy", "medication adjustment", "lifestyle modifications", "follow-up imaging"]),
                finding=random.choice(["within normal limits", "mildly elevated", "stable from prior"]),
                imaging_finding=random.choice(IMAGING_FINDINGS)[0]
            )

            notes.append({
                "note_id": note_id,
                "patient_id": f"patient-{i}",
                "document_type": random.choice(["Progress Note", "Discharge Summary", "Consultation", "H&P"]),
                "text_content": note_text,
            })

            # Generate entities for this note
            entity_base_id = len(entities) + (i - 1) * 10 + 1

            # Condition entity
            entities.append({
                "entity_id": f"ent-{i:03d}-{entity_base_id:03d}",
                "entity_type": "Condition",
                "entity_text": condition,
                "source_document_id": note_id,
                "patient_id": f"patient-{i}",
                "confidence": round(random.uniform(0.85, 0.99), 2)
            })

            # Medication entities
            for med_idx, med in enumerate(medications[:2]):
                entities.append({
                    "entity_id": f"ent-{i:03d}-{entity_base_id + 1 + med_idx:03d}",
                    "entity_type": "Medication",
                    "entity_text": med,
                    "source_document_id": note_id,
                    "patient_id": f"patient-{i}",
                    "confidence": round(random.uniform(0.85, 0.99), 2)
                })

            # Symptom entities
            for sym_idx, sym in enumerate(symptoms[:2]):
                entities.append({
                    "entity_id": f"ent-{i:03d}-{entity_base_id + 3 + sym_idx:03d}",
                    "entity_type": "Symptom",
                    "entity_text": sym,
                    "source_document_id": note_id,
                    "patient_id": f"patient-{i}",
                    "confidence": round(random.uniform(0.85, 0.99), 2)
                })

            # Generate relationships
            condition_entity_id = f"ent-{i:03d}-{entity_base_id:03d}"

            for med_idx, med in enumerate(medications[:2]):
                med_entity_id = f"ent-{i:03d}-{entity_base_id + 1 + med_idx:03d}"
                relationships.append({
                    "relationship_id": f"rel-{i:03d}-{len(relationships) + 1:03d}",
                    "source_entity_id": med_entity_id,
                    "target_entity_id": condition_entity_id,
                    "relation_type": "TREATS",
                    "source_document_id": note_id,
                    "confidence": round(random.uniform(0.80, 0.95), 2)
                })

            for sym_idx, sym in enumerate(symptoms[:2]):
                sym_entity_id = f"ent-{i:03d}-{entity_base_id + 3 + sym_idx:03d}"
                relationships.append({
                    "relationship_id": f"rel-{i:03d}-{len(relationships) + 1:03d}",
                    "source_entity_id": condition_entity_id,
                    "target_entity_id": sym_entity_id,
                    "relation_type": "CAUSES",
                    "source_document_id": note_id,
                    "confidence": round(random.uniform(0.80, 0.95), 2)
                })

        # Generate imaging study
        imaging_finding, finding_type = random.choice(IMAGING_FINDINGS)
        study_date = datetime.now() - timedelta(days=random.randint(1, 365))

        patients.append({
            "id": str(i),
            "first_name": first_name,
            "last_name": last_name,
            "gender": gender,
            "birth_date": birth_date,
            "conditions": patient_conditions,
            "notes": notes,
            "entities": entities,
            "relationships": relationships,
            "imaging_study": {
                "study_id": f"study-s{50414267 + i}",
                "finding": imaging_finding,
                "finding_type": finding_type,
                "date": study_date.isoformat() + "Z",
            }
        })

    return patients


def get_auth_header():
    """Get Basic Auth header from environment."""
    user = os.getenv('FHIR_USERNAME', "_SYSTEM")
    pw = os.getenv('FHIR_PASSWORD', "sys")
    return "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()


def put_fhir_resource(resource, resource_type=None, resource_id=None):
    """PUT a FHIR resource to create or update it."""
    if resource_type is None:
        resource_type = resource.get("resourceType")
    if resource_id is None:
        resource_id = resource.get("id")

    url = f"{FHIR_BASE_URL}/{resource_type}/{resource_id}"
    data = json.dumps(resource).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Content-Type", "application/fhir+json")
    req.add_header("Accept", "application/fhir+json")
    req.add_header("Authorization", get_auth_header())


    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return True, result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:200]
        return False, f"HTTPError {e.code}: {error_body}"
    except Exception as e:
        return False, str(e)


from src.db.connection import get_connection

def execute_iris_sql(sql, params=None):
    """Execute SQL against IRIS database via DBAPI."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
            
        conn.commit()
        cursor.close()
        conn.close()
        
        # Return success
        return True, "Success"
    except Exception as e:
        return False, str(e)


def execute_iris_sql_remote(sql, params=None, host="13.218.19.254"):
    """Execute SQL against remote IRIS database (delegates to local execute_iris_sql if on host)."""
    # If we are on the EC2, we should just use execute_iris_sql
    return execute_iris_sql(sql, params)


def generate_mock_embedding():
    """Generate a mock 1024-dim embedding vector."""
    # Generate deterministic but varied embeddings based on content
    return [round(random.uniform(-0.5, 0.5), 4) for _ in range(1024)]


def main():
    print("=" * 70)
    print("Full GraphRAG Data Population Script")
    print("=" * 70)
    print(f"FHIR Server: {FHIR_BASE_URL}")
    print(f"Generating data for {NUM_PATIENTS} patients...")
    print()

    # Generate all patient data
    patients = generate_patient_data()

    # Statistics
    stats = {
        "patients_created": 0,
        "imaging_studies_created": 0,
        "diagnostic_reports_created": 0,
        "clinical_notes_created": 0,
        "entities_created": 0,
        "relationships_created": 0,
        "errors": []
    }

    # 1. Create FHIR Patient resources
    print("Creating FHIR Patient resources...")
    for patient in patients:
        fhir_patient = {
            "resourceType": "Patient",
            "id": patient["id"],
            "name": [{"family": patient["last_name"], "given": [patient["first_name"]]}],
            "gender": patient["gender"],
            "birthDate": patient["birth_date"]
        }

        success, result = put_fhir_resource(fhir_patient)
        if success:
            stats["patients_created"] += 1
        else:
            stats["errors"].append(f"Patient/{patient['id']}: {result}")

        if stats["patients_created"] % 10 == 0:
            print(f"  Created {stats['patients_created']} patients...")

    print(f"  ✓ Patients created: {stats['patients_created']}/{NUM_PATIENTS}")
    print()

    # 2. Create ImagingStudy and DiagnosticReport resources
    print("Creating ImagingStudy and DiagnosticReport resources...")
    for patient in patients:
        study = patient["imaging_study"]

        # ImagingStudy
        imaging_study = {
            "resourceType": "ImagingStudy",
            "id": study["study_id"],
            "status": "available",
            "subject": {"reference": f"Patient/{patient['id']}", "display": f"{patient['first_name']} {patient['last_name']}"},
            "started": study["date"],
            "modality": [{"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CR", "display": "Computed Radiography"}],
            "identifier": [{"system": "urn:mimic-cxr:study", "value": study["study_id"].replace("study-", "")}],
            "numberOfSeries": 1,
            "numberOfInstances": 1,
            "description": f"Chest X-ray - {study['finding']}"
        }

        success, result = put_fhir_resource(imaging_study)
        if success:
            stats["imaging_studies_created"] += 1

        # DiagnosticReport
        diagnostic_report = {
            "resourceType": "DiagnosticReport",
            "id": f"report-{study['study_id'].replace('study-', '')}",
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "18748-4", "display": "Diagnostic imaging study"}]},
            "subject": {"reference": f"Patient/{patient['id']}", "display": f"{patient['first_name']} {patient['last_name']}"},
            "imagingStudy": [{"reference": f"ImagingStudy/{study['study_id']}"}],
            "conclusion": study["finding"],
            "effectiveDateTime": study["date"],
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "RAD", "display": "Radiology"}]}]
        }

        success, result = put_fhir_resource(diagnostic_report)
        if success:
            stats["diagnostic_reports_created"] += 1

    print(f"  ✓ ImagingStudies created: {stats['imaging_studies_created']}/{NUM_PATIENTS}")
    print(f"  ✓ DiagnosticReports created: {stats['diagnostic_reports_created']}/{NUM_PATIENTS}")
    print()

    # 3. Create Clinical Notes in IRIS (ClinicalNoteVectors table)
    print("Creating Clinical Notes in IRIS ClinicalNoteVectors table...")

    # Check if we're running locally or need remote execution
    is_remote = IRIS_HOST != "localhost" or os.getenv("USE_REMOTE_IRIS", "false").lower() == "true"
    execute_sql = execute_iris_sql_remote if is_remote else execute_iris_sql

    for patient in patients:
        for note in patient["notes"]:
            # Generate mock embedding
            embedding = generate_mock_embedding()
            embedding_str = ",".join(str(v) for v in embedding)

            sql = f"""INSERT INTO SQLUser.ClinicalNoteVectors
                (ResourceID, PatientID, DocumentType, TextContent, Embedding, EmbeddingModel, SourceBundle, CreatedAt)
                VALUES (?, ?, ?, ?, TO_VECTOR(?, DOUBLE, 1024), ?, ?, NOW())"""

            params = (
                note["note_id"], 
                note["patient_id"], 
                note["document_type"],
                note["text_content"], 
                embedding_str,
                'nvidia/nv-embedqa-e5-v5', 
                'synthetic-data.json'
            )

            success, result = execute_sql(sql, params)
            if success:
                stats["clinical_notes_created"] += 1
            else:
                stats["errors"].append(f"SQL Error (Note): {result}")

        if stats["clinical_notes_created"] % 20 == 0:
            print(f"  Created {stats['clinical_notes_created']} clinical notes...")

    print(f"  ✓ Clinical notes created: {stats['clinical_notes_created']}")
    print()

    # 4. Create Entities in IRIS
    print("Creating Entities in IRIS RAG.Entities table...")
    for patient in patients:
        for entity in patient["entities"]:
            sql = f"""INSERT INTO RAG.Entities
                (EntityID, EntityType, EntityText, SourceDocumentID, PatientID, Confidence)
                VALUES (?, ?, ?, ?, ?, ?)"""

            params = (
                entity["entity_id"], 
                entity["entity_type"], 
                entity["entity_text"],
                entity["source_document_id"], 
                entity["patient_id"], 
                entity["confidence"]
            )

            success, result = execute_sql(sql, params)
            if success:
                stats["entities_created"] += 1
            else:
                stats["errors"].append(f"SQL Error (Entity): {result}")

        if stats["entities_created"] % 50 == 0:
            print(f"  Created {stats['entities_created']} entities...")

    print(f"  ✓ Entities created: {stats['entities_created']}")
    print()

    # 5. Create Relationships in IRIS
    print("Creating Relationships in IRIS RAG.EntityRelationships table...")
    for patient in patients:
        for rel in patient["relationships"]:
            sql = f"""INSERT INTO RAG.EntityRelationships
                (RelationshipID, SourceEntityID, TargetEntityID, RelationType, SourceDocumentID, Confidence)
                VALUES (?, ?, ?, ?, ?, ?)"""

            params = (
                rel["relationship_id"], 
                rel["source_entity_id"], 
                rel["target_entity_id"],
                rel["relation_type"], 
                rel["source_document_id"], 
                rel["confidence"]
            )

            success, result = execute_sql(sql, params)
            if success:
                stats["relationships_created"] += 1
            else:
                stats["errors"].append(f"SQL Error (Relationship): {result}")

        if stats["relationships_created"] % 50 == 0:
            print(f"  Created {stats['relationships_created']} relationships...")

    print(f"  ✓ Relationships created: {stats['relationships_created']}")
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"FHIR Resources:")
    print(f"  Patients:          {stats['patients_created']}")
    print(f"  ImagingStudies:    {stats['imaging_studies_created']}")
    print(f"  DiagnosticReports: {stats['diagnostic_reports_created']}")
    print()
    print(f"IRIS GraphRAG Tables:")
    print(f"  ClinicalNoteVectors: {stats['clinical_notes_created']}")
    print(f"  Entities:            {stats['entities_created']}")
    print(f"  Relationships:       {stats['relationships_created']}")
    print()

    if stats["errors"]:
        print(f"Errors ({len(stats['errors'])}):")
        for err in stats["errors"][:10]:
            print(f"  - {err}")
        if len(stats["errors"]) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more")

    total_success = (
        stats["patients_created"] >= NUM_PATIENTS * 0.9 and
        stats["entities_created"] > 0 and
        stats["relationships_created"] > 0
    )

    if total_success:
        print()
        print("✓ Data population completed successfully!")
        return 0
    else:
        print()
        print("⚠ Data population completed with some failures")
        return 1


if __name__ == "__main__":
    sys.exit(main())
