#!/usr/bin/env python3
"""
Populate IRIS GraphRAG tables with 50 patients (bypassing FHIR).

This script populates Entity, Relationship, and ClinicalNoteVectors tables
directly via IRIS SQL, without requiring FHIR to be functional.

Usage:
    python scripts/populate_graphrag_only.py
"""
import subprocess
import random
import sys

EC2_HOST = "13.218.19.254"
SSH_KEY = "~/.ssh/fhir-ai-key-recovery.pem"
NUM_PATIENTS = 50

# Medical data pools
CONDITIONS = [
    ("diabetes mellitus type 2", "Condition", ["metformin", "insulin glargine", "hyperglycemia", "neuropathy"]),
    ("hypertension", "Condition", ["lisinopril", "amlodipine", "elevated blood pressure", "headache"]),
    ("congestive heart failure", "Condition", ["furosemide", "carvedilol", "shortness of breath", "edema"]),
    ("chronic kidney disease", "Condition", ["creatinine elevated", "proteinuria", "anemia", "fatigue"]),
    ("pneumonia", "Condition", ["ceftriaxone", "azithromycin", "fever", "cough", "chest pain"]),
    ("COPD", "Condition", ["albuterol", "tiotropium", "prednisone", "wheezing", "chronic cough"]),
    ("atrial fibrillation", "Condition", ["warfarin", "apixaban", "metoprolol", "palpitations"]),
    ("coronary artery disease", "Condition", ["aspirin", "atorvastatin", "nitroglycerin", "chest pain"]),
    ("hypothyroidism", "Condition", ["levothyroxine", "fatigue", "weight gain", "cold intolerance"]),
    ("depression", "Condition", ["sertraline", "escitalopram", "insomnia", "fatigue"]),
    ("anxiety disorder", "Condition", ["lorazepam", "buspirone", "panic attacks", "restlessness"]),
    ("osteoarthritis", "Condition", ["acetaminophen", "ibuprofen", "joint pain", "stiffness"]),
    ("asthma", "Condition", ["albuterol", "fluticasone", "wheezing", "shortness of breath"]),
    ("migraine", "Condition", ["sumatriptan", "topiramate", "headache", "nausea"]),
    ("gastroesophageal reflux", "Condition", ["omeprazole", "pantoprazole", "heartburn", "dysphagia"]),
]

FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
               "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"]


def execute_sql(sql):
    """Execute SQL via SSH to EC2 docker container."""
    # Escape quotes for nested shell
    escaped_sql = sql.replace("'", "'\\''")

    cmd = f"""ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -i {SSH_KEY} ubuntu@{EC2_HOST} "docker exec iris-fhir bash -c 'echo \\"{escaped_sql}\\" | iris sql IRIS -U DEMO 2>/dev/null'" 2>/dev/null"""

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        output = result.stdout
        if "ERROR #" in output:
            return False, output
        if "Row" in output and "Affected" in output:
            return True, output
        return True, output
    except Exception as e:
        return False, str(e)


def generate_patient_data():
    """Generate data for 50 patients."""
    patients = []

    for i in range(1, NUM_PATIENTS + 1):
        patient_id = f"patient-{i}"
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)

        # Assign 1-3 conditions
        num_conditions = random.randint(1, 3)
        patient_conditions = random.sample(CONDITIONS, num_conditions)

        entities = []
        relationships = []
        notes = []

        for cond_idx, (condition, cond_type, related_items) in enumerate(patient_conditions):
            note_id = f"note-p{i:03d}-{cond_idx + 1}"

            # Split related items into medications and symptoms
            medications = [x for x in related_items if x[0].islower() and not any(s in x for s in ["pain", "cough", "fatigue"])]
            symptoms = [x for x in related_items if x not in medications]

            if not medications:
                medications = ["supportive care"]
            if not symptoms:
                symptoms = ["general discomfort"]

            # Create note text
            note_text = f"Patient {first_name} {last_name} presents with {symptoms[0]}. History of {condition}. Currently on {medications[0]}. Assessment: {condition} stable. Plan: Continue current medications."

            notes.append({
                "note_id": note_id,
                "patient_id": patient_id,
                "document_type": random.choice(["Progress Note", "Discharge Summary", "Consultation"]),
                "text_content": note_text,
            })

            # Entity base ID
            base_id = len(entities) + (i - 1) * 10 + 1

            # Condition entity
            cond_entity_id = f"ent-{i:03d}-{base_id:03d}"
            entities.append({
                "entity_id": cond_entity_id,
                "entity_type": "Condition",
                "entity_text": condition,
                "source_document_id": note_id,
                "patient_id": patient_id,
                "confidence": round(random.uniform(0.85, 0.99), 2)
            })

            # Medication entities and relationships
            for med_idx, med in enumerate(medications[:2]):
                med_entity_id = f"ent-{i:03d}-{base_id + 1 + med_idx:03d}"
                entities.append({
                    "entity_id": med_entity_id,
                    "entity_type": "Medication",
                    "entity_text": med,
                    "source_document_id": note_id,
                    "patient_id": patient_id,
                    "confidence": round(random.uniform(0.85, 0.99), 2)
                })
                relationships.append({
                    "rel_id": f"rel-{i:03d}-{len(relationships) + 1:03d}",
                    "source_id": med_entity_id,
                    "target_id": cond_entity_id,
                    "rel_type": "TREATS",
                    "source_doc": note_id,
                    "confidence": round(random.uniform(0.80, 0.95), 2)
                })

            # Symptom entities and relationships
            for sym_idx, sym in enumerate(symptoms[:2]):
                sym_entity_id = f"ent-{i:03d}-{base_id + 3 + sym_idx:03d}"
                entities.append({
                    "entity_id": sym_entity_id,
                    "entity_type": "Symptom",
                    "entity_text": sym,
                    "source_document_id": note_id,
                    "patient_id": patient_id,
                    "confidence": round(random.uniform(0.85, 0.99), 2)
                })
                relationships.append({
                    "rel_id": f"rel-{i:03d}-{len(relationships) + 1:03d}",
                    "source_id": cond_entity_id,
                    "target_id": sym_entity_id,
                    "rel_type": "CAUSES",
                    "source_doc": note_id,
                    "confidence": round(random.uniform(0.80, 0.95), 2)
                })

        patients.append({
            "patient_id": patient_id,
            "name": f"{first_name} {last_name}",
            "entities": entities,
            "relationships": relationships,
            "notes": notes,
        })

    return patients


def main():
    print("=" * 60)
    print("GraphRAG Data Population (IRIS SQL Direct)")
    print("=" * 60)
    print(f"Target: {EC2_HOST}")
    print(f"Patients: {NUM_PATIENTS}")
    print()

    # Generate data
    print("Generating patient data...")
    patients = generate_patient_data()

    stats = {"entities": 0, "relationships": 0, "notes": 0, "errors": []}

    # Insert Entities
    print("\nInserting Entities...")
    for patient in patients:
        for entity in patient["entities"]:
            text = entity["entity_text"].replace("'", "''")
            sql = f"INSERT INTO SQLUser.Entity (EntityID, EntityType, EntityText, SourceDocumentID, PatientID, Confidence) VALUES ('{entity['entity_id']}', '{entity['entity_type']}', '{text}', '{entity['source_document_id']}', '{entity['patient_id']}', {entity['confidence']})"

            success, result = execute_sql(sql)
            if success:
                stats["entities"] += 1
            else:
                stats["errors"].append(f"Entity {entity['entity_id']}: {result[:100]}")

        if stats["entities"] % 50 == 0:
            print(f"  Inserted {stats['entities']} entities...")

    print(f"  Total entities: {stats['entities']}")

    # Insert Relationships
    print("\nInserting Relationships...")
    for patient in patients:
        for rel in patient["relationships"]:
            sql = f"INSERT INTO SQLUser.Relationship (RelationshipID, SourceEntityID, TargetEntityID, RelationType, SourceDocumentID, Confidence) VALUES ('{rel['rel_id']}', '{rel['source_id']}', '{rel['target_id']}', '{rel['rel_type']}', '{rel['source_doc']}', {rel['confidence']})"

            success, result = execute_sql(sql)
            if success:
                stats["relationships"] += 1
            else:
                stats["errors"].append(f"Relationship {rel['rel_id']}: {result[:100]}")

        if stats["relationships"] % 50 == 0:
            print(f"  Inserted {stats['relationships']} relationships...")

    print(f"  Total relationships: {stats['relationships']}")

    # Insert Clinical Notes (without vectors for now - simpler)
    print("\nInserting Clinical Notes...")
    for patient in patients:
        for note in patient["notes"]:
            text = note["text_content"].replace("'", "''")
            # Skip embedding for speed - just insert text
            sql = f"INSERT INTO SQLUser.ClinicalNoteVectors (ResourceID, PatientID, DocumentType, TextContent, EmbeddingModel, SourceBundle, CreatedAt) VALUES ('{note['note_id']}', '{note['patient_id']}', '{note['document_type']}', '{text}', 'text-only', 'graphrag-populate', NOW())"

            success, result = execute_sql(sql)
            if success:
                stats["notes"] += 1
            else:
                stats["errors"].append(f"Note {note['note_id']}: {result[:100]}")

        if stats["notes"] % 20 == 0:
            print(f"  Inserted {stats['notes']} notes...")

    print(f"  Total notes: {stats['notes']}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Entities:      {stats['entities']}")
    print(f"Relationships: {stats['relationships']}")
    print(f"Notes:         {stats['notes']}")

    if stats["errors"]:
        print(f"\nErrors ({len(stats['errors'])}):")
        for err in stats["errors"][:5]:
            print(f"  - {err}")

    if stats["entities"] > 100 and stats["relationships"] > 50:
        print("\n SUCCESS: GraphRAG data populated!")
        return 0
    else:
        print("\n WARNING: Some data may not have been inserted")
        return 1


if __name__ == "__main__":
    sys.exit(main())
