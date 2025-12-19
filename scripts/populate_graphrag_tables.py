#!/usr/bin/env python3
"""
Populate GraphRAG Tables for Knowledge Graph Features

This script creates and populates the RAG.Entities and RAG.EntityRelationships tables
with synthetic medical data. It's designed to be idempotent - running multiple times
won't create duplicate data.

Tables created:
- RAG.Entities: Medical entities (symptoms, conditions, medications, etc.)
- RAG.EntityRelationships: Relationships between entities

Usage:
    python scripts/populate_graphrag_tables.py [--force] [--dry-run]

Options:
    --force     Force recreation of tables (drops existing data)
    --dry-run   Preview SQL without executing
"""

import sys
import os
import argparse
import random
from typing import List, Tuple, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Medical conditions with related entities
CONDITIONS_DATA = [
    {
        "condition": "diabetes mellitus type 2",
        "type": "CONDITION",
        "medications": ["metformin", "insulin glargine", "glipizide", "sitagliptin"],
        "symptoms": ["hyperglycemia", "polyuria", "polydipsia", "fatigue", "blurred vision", "neuropathy"],
        "anatomy": ["pancreas", "liver", "kidney"],
        "procedures": ["glucose monitoring", "HbA1c test", "foot examination"],
    },
    {
        "condition": "hypertension",
        "type": "CONDITION",
        "medications": ["lisinopril", "amlodipine", "hydrochlorothiazide", "metoprolol", "losartan"],
        "symptoms": ["elevated blood pressure", "headache", "dizziness", "chest pain"],
        "anatomy": ["heart", "blood vessels", "kidney"],
        "procedures": ["blood pressure monitoring", "echocardiogram", "renal function test"],
    },
    {
        "condition": "congestive heart failure",
        "type": "CONDITION",
        "medications": ["furosemide", "carvedilol", "lisinopril", "spironolactone", "digoxin"],
        "symptoms": ["shortness of breath", "dyspnea", "edema", "fatigue", "orthopnea", "jugular venous distension"],
        "anatomy": ["heart", "lungs", "lower extremities"],
        "procedures": ["echocardiogram", "BNP test", "chest x-ray", "cardiac catheterization"],
    },
    {
        "condition": "pneumonia",
        "type": "CONDITION",
        "medications": ["amoxicillin", "azithromycin", "levofloxacin", "ceftriaxone"],
        "symptoms": ["cough", "fever", "dyspnea", "chest pain", "productive sputum", "chills"],
        "anatomy": ["lungs", "bronchi", "pleura"],
        "procedures": ["chest x-ray", "sputum culture", "blood culture", "CT scan chest"],
    },
    {
        "condition": "chronic obstructive pulmonary disease",
        "type": "CONDITION",
        "medications": ["tiotropium", "fluticasone", "albuterol", "salmeterol", "prednisone"],
        "symptoms": ["dyspnea", "chronic cough", "wheezing", "exercise intolerance", "barrel chest"],
        "anatomy": ["lungs", "bronchi", "diaphragm"],
        "procedures": ["pulmonary function test", "spirometry", "chest x-ray", "ABG analysis"],
    },
    {
        "condition": "acute myocardial infarction",
        "type": "CONDITION",
        "medications": ["aspirin", "heparin", "nitroglycerin", "morphine", "clopidogrel", "atorvastatin"],
        "symptoms": ["chest pain", "diaphoresis", "nausea", "shortness of breath", "arm pain", "jaw pain"],
        "anatomy": ["heart", "coronary arteries", "left ventricle"],
        "procedures": ["ECG", "cardiac catheterization", "troponin test", "coronary angiography", "PCI"],
    },
    {
        "condition": "atrial fibrillation",
        "type": "CONDITION",
        "medications": ["warfarin", "apixaban", "rivaroxaban", "metoprolol", "diltiazem", "amiodarone"],
        "symptoms": ["palpitations", "irregular heartbeat", "fatigue", "dizziness", "syncope"],
        "anatomy": ["heart", "atria", "AV node"],
        "procedures": ["ECG", "Holter monitor", "echocardiogram", "cardioversion", "ablation"],
    },
    {
        "condition": "chronic kidney disease",
        "type": "CONDITION",
        "medications": ["epoetin alfa", "sevelamer", "calcitriol", "sodium bicarbonate"],
        "symptoms": ["fatigue", "edema", "anemia", "nausea", "decreased urine output", "pruritus"],
        "anatomy": ["kidney", "ureter", "bladder"],
        "procedures": ["GFR test", "creatinine test", "renal ultrasound", "kidney biopsy", "dialysis"],
    },
    {
        "condition": "sepsis",
        "type": "CONDITION",
        "medications": ["vancomycin", "piperacillin-tazobactam", "norepinephrine", "hydrocortisone"],
        "symptoms": ["fever", "tachycardia", "hypotension", "altered mental status", "tachypnea"],
        "anatomy": ["blood", "multiple organ systems"],
        "procedures": ["blood culture", "lactate test", "procalcitonin", "central line placement"],
    },
    {
        "condition": "stroke",
        "type": "CONDITION",
        "medications": ["alteplase", "aspirin", "clopidogrel", "atorvastatin", "heparin"],
        "symptoms": ["hemiparesis", "aphasia", "facial droop", "dysarthria", "visual disturbance", "ataxia"],
        "anatomy": ["brain", "cerebral arteries", "carotid artery"],
        "procedures": ["CT head", "MRI brain", "carotid ultrasound", "thrombectomy", "tPA administration"],
    },
]


def get_db_connection():
    """Get database connection using project's connection module."""
    try:
        from src.db.connection import get_connection
        return get_connection()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Make sure IRIS_HOST and IRIS_PORT environment variables are set.")
        sys.exit(1)


def create_rag_schema(cursor, dry_run: bool = False) -> bool:
    """Create RAG schema if it doesn't exist."""
    sql = "CREATE SCHEMA IF NOT EXISTS RAG"
    if dry_run:
        print(f"[DRY RUN] {sql}")
        return True
    try:
        cursor.execute(sql)
        print("✓ RAG schema created/verified")
        return True
    except Exception as e:
        # Schema might already exist
        if "already exists" in str(e).lower():
            print("✓ RAG schema already exists")
            return True
        print(f"✗ Error creating RAG schema: {e}")
        return False


def create_entities_table(cursor, force: bool = False, dry_run: bool = False) -> bool:
    """Create RAG.Entities table."""
    if force and not dry_run:
        try:
            cursor.execute("DROP TABLE IF EXISTS RAG.Entities")
            print("  Dropped existing RAG.Entities table")
        except Exception:
            pass

    sql = """
    CREATE TABLE IF NOT EXISTS RAG.Entities (
        EntityID INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
        EntityText VARCHAR(500) NOT NULL,
        EntityType VARCHAR(50) NOT NULL,
        Confidence DOUBLE DEFAULT 0.8,
        ResourceID VARCHAR(100),
        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    if dry_run:
        print(f"[DRY RUN] CREATE TABLE RAG.Entities (...)")
        return True
    try:
        cursor.execute(sql)
        print("✓ RAG.Entities table created/verified")
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            print("✓ RAG.Entities table already exists")
            return True
        print(f"✗ Error creating RAG.Entities: {e}")
        return False


def create_relationships_table(cursor, force: bool = False, dry_run: bool = False) -> bool:
    """Create RAG.EntityRelationships table."""
    if force and not dry_run:
        try:
            cursor.execute("DROP TABLE IF EXISTS RAG.EntityRelationships")
            print("  Dropped existing RAG.EntityRelationships table")
        except Exception:
            pass

    sql = """
    CREATE TABLE IF NOT EXISTS RAG.EntityRelationships (
        RelationshipID INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
        SourceEntityID INT NOT NULL,
        TargetEntityID INT NOT NULL,
        RelationshipType VARCHAR(100) DEFAULT 'related',
        Confidence DOUBLE DEFAULT 0.7,
        ResourceID VARCHAR(100),
        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    if dry_run:
        print(f"[DRY RUN] CREATE TABLE RAG.EntityRelationships (...)")
        return True
    try:
        cursor.execute(sql)
        print("✓ RAG.EntityRelationships table created/verified")
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            print("✓ RAG.EntityRelationships table already exists")
            return True
        print(f"✗ Error creating RAG.EntityRelationships: {e}")
        return False


def create_indexes(cursor, dry_run: bool = False) -> bool:
    """Create indexes for efficient queries."""
    indexes = [
        ("idx_entities_text", "RAG.Entities", "EntityText"),
        ("idx_entities_type", "RAG.Entities", "EntityType"),
        ("idx_entities_resource", "RAG.Entities", "ResourceID"),
        ("idx_rel_source", "RAG.EntityRelationships", "SourceEntityID"),
        ("idx_rel_target", "RAG.EntityRelationships", "TargetEntityID"),
        ("idx_rel_type", "RAG.EntityRelationships", "RelationshipType"),
    ]

    for idx_name, table, column in indexes:
        sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"
        if dry_run:
            print(f"[DRY RUN] {sql}")
            continue
        try:
            cursor.execute(sql)
        except Exception as e:
            if "already exists" not in str(e).lower():
                print(f"  Warning: Could not create index {idx_name}: {e}")

    if not dry_run:
        print("✓ Indexes created/verified")
    return True


def check_existing_data(cursor) -> Tuple[int, int]:
    """Check existing entity and relationship counts."""
    try:
        cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
        entity_count = cursor.fetchone()[0]
    except Exception:
        entity_count = 0

    try:
        cursor.execute("SELECT COUNT(*) FROM RAG.EntityRelationships")
        rel_count = cursor.fetchone()[0]
    except Exception:
        rel_count = 0

    return entity_count, rel_count


def insert_entity(cursor, text: str, entity_type: str, confidence: float = None, resource_id: str = None) -> Optional[int]:
    """Insert an entity and return its ID. Returns None if already exists."""
    if confidence is None:
        confidence = round(random.uniform(0.7, 0.95), 2)

    # Check if entity already exists (idempotency)
    cursor.execute(
        "SELECT EntityID FROM RAG.Entities WHERE EntityText = ? AND EntityType = ?",
        (text, entity_type)
    )
    existing = cursor.fetchone()
    if existing:
        return existing[0]  # Return existing ID

    # Insert new entity
    cursor.execute(
        """INSERT INTO RAG.Entities (EntityText, EntityType, Confidence, ResourceID)
           VALUES (?, ?, ?, ?)""",
        (text, entity_type, confidence, resource_id)
    )

    # Get the inserted ID
    cursor.execute("SELECT LAST_IDENTITY()")
    return cursor.fetchone()[0]


def insert_relationship(cursor, source_id: int, target_id: int, rel_type: str, confidence: float = None, resource_id: str = None) -> bool:
    """Insert a relationship. Returns False if already exists."""
    if confidence is None:
        confidence = round(random.uniform(0.6, 0.9), 2)

    # Check if relationship already exists (idempotency)
    cursor.execute(
        """SELECT RelationshipID FROM RAG.EntityRelationships
           WHERE SourceEntityID = ? AND TargetEntityID = ? AND RelationshipType = ?""",
        (source_id, target_id, rel_type)
    )
    if cursor.fetchone():
        return False  # Already exists

    # Insert new relationship
    cursor.execute(
        """INSERT INTO RAG.EntityRelationships (SourceEntityID, TargetEntityID, RelationshipType, Confidence, ResourceID)
           VALUES (?, ?, ?, ?, ?)""",
        (source_id, target_id, rel_type, confidence, resource_id)
    )
    return True


def populate_data(cursor, dry_run: bool = False) -> Tuple[int, int]:
    """Populate entities and relationships from medical data."""
    if dry_run:
        print("[DRY RUN] Would populate medical entities and relationships")
        return 0, 0

    entities_added = 0
    relationships_added = 0
    entity_ids: Dict[str, int] = {}  # Track entity text -> ID mapping

    print("\nPopulating medical knowledge graph data...")

    for condition_data in CONDITIONS_DATA:
        condition_name = condition_data["condition"]
        resource_id = f"doc-{condition_name.replace(' ', '-')[:20]}"

        # Insert the main condition
        condition_id = insert_entity(cursor, condition_name, "CONDITION", 0.95, resource_id)
        if condition_id not in entity_ids.values():
            entities_added += 1
        entity_ids[condition_name] = condition_id

        # Insert medications and create relationships
        for med in condition_data.get("medications", []):
            med_id = insert_entity(cursor, med, "MEDICATION", None, resource_id)
            if med_id not in entity_ids.values():
                entities_added += 1
            entity_ids[med] = med_id

            # Relationship: condition --treated_by--> medication
            if insert_relationship(cursor, condition_id, med_id, "treated_by", None, resource_id):
                relationships_added += 1

        # Insert symptoms and create relationships
        for symptom in condition_data.get("symptoms", []):
            symptom_id = insert_entity(cursor, symptom, "SYMPTOM", None, resource_id)
            if symptom_id not in entity_ids.values():
                entities_added += 1
            entity_ids[symptom] = symptom_id

            # Relationship: condition --presents_with--> symptom
            if insert_relationship(cursor, condition_id, symptom_id, "presents_with", None, resource_id):
                relationships_added += 1

        # Insert anatomy and create relationships
        for anatomy in condition_data.get("anatomy", []):
            anatomy_id = insert_entity(cursor, anatomy, "ANATOMY", None, resource_id)
            if anatomy_id not in entity_ids.values():
                entities_added += 1
            entity_ids[anatomy] = anatomy_id

            # Relationship: condition --affects--> anatomy
            if insert_relationship(cursor, condition_id, anatomy_id, "affects", None, resource_id):
                relationships_added += 1

        # Insert procedures and create relationships
        for procedure in condition_data.get("procedures", []):
            proc_id = insert_entity(cursor, procedure, "PROCEDURE", None, resource_id)
            if proc_id not in entity_ids.values():
                entities_added += 1
            entity_ids[procedure] = proc_id

            # Relationship: condition --diagnosed_by--> procedure
            if insert_relationship(cursor, condition_id, proc_id, "diagnosed_by", None, resource_id):
                relationships_added += 1

    # Add cross-condition relationships (e.g., comorbidities)
    comorbidities = [
        ("diabetes mellitus type 2", "hypertension", "comorbid_with"),
        ("diabetes mellitus type 2", "chronic kidney disease", "leads_to"),
        ("hypertension", "stroke", "risk_factor_for"),
        ("hypertension", "congestive heart failure", "contributes_to"),
        ("atrial fibrillation", "stroke", "risk_factor_for"),
        ("congestive heart failure", "chronic kidney disease", "associated_with"),
        ("acute myocardial infarction", "congestive heart failure", "can_cause"),
        ("sepsis", "acute myocardial infarction", "can_trigger"),
    ]

    for source, target, rel_type in comorbidities:
        if source in entity_ids and target in entity_ids:
            if insert_relationship(cursor, entity_ids[source], entity_ids[target], rel_type):
                relationships_added += 1

    return entities_added, relationships_added


def main():
    parser = argparse.ArgumentParser(description="Populate GraphRAG tables with medical knowledge data")
    parser.add_argument("--force", action="store_true", help="Force recreation of tables (drops existing data)")
    parser.add_argument("--dry-run", action="store_true", help="Preview SQL without executing")
    args = parser.parse_args()

    print("=" * 60)
    print("GraphRAG Tables Population Script")
    print("=" * 60)

    if args.dry_run:
        print("[DRY RUN MODE - No changes will be made]")

    if args.force:
        print("[FORCE MODE - Tables will be recreated]")

    # Connect to database
    print("\nConnecting to IRIS database...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check existing data
    existing_entities, existing_rels = check_existing_data(cursor)
    print(f"Existing data: {existing_entities} entities, {existing_rels} relationships")

    if existing_entities > 0 and not args.force and not args.dry_run:
        print(f"\n✓ GraphRAG tables already populated with {existing_entities} entities.")
        print("  Use --force to recreate tables, or run without options to add missing data.")
        if existing_entities >= 100:  # Sufficient data exists
            cursor.close()
            conn.close()
            return

    # Create schema and tables
    print("\nCreating/verifying schema and tables...")
    if not create_rag_schema(cursor, args.dry_run):
        sys.exit(1)

    if not create_entities_table(cursor, args.force, args.dry_run):
        sys.exit(1)

    if not create_relationships_table(cursor, args.force, args.dry_run):
        sys.exit(1)

    if not create_indexes(cursor, args.dry_run):
        sys.exit(1)

    # Populate data
    entities_added, rels_added = populate_data(cursor, args.dry_run)

    if not args.dry_run:
        conn.commit()

        # Final counts
        final_entities, final_rels = check_existing_data(cursor)

        print("\n" + "=" * 60)
        print("POPULATION COMPLETE")
        print("=" * 60)
        print(f"Entities:      {final_entities} total ({entities_added} new)")
        print(f"Relationships: {final_rels} total ({rels_added} new)")
        print("=" * 60)

    cursor.close()
    conn.close()
    print("\n✓ GraphRAG population complete!")


if __name__ == "__main__":
    main()
