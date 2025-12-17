#!/usr/bin/env python3
"""
Create Patient-Image Mapping Table in IRIS (Repeatable)

Creates the VectorSearch.PatientImageMapping table that links MIMIC-CXR
subject_ids to FHIR Patient resource IDs. Idempotent - safe to run multiple times.

Part of Feature 007: FHIR Radiology Integration
"""

import sys
import os

# Add project root to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.db.connection import get_connection


def create_patient_mapping_table(drop_existing=False):
    """
    Create VectorSearch.PatientImageMapping table.

    Links MIMIC-CXR subject_ids to FHIR Patient resource IDs, enabling
    patient context display in image search results.

    Args:
        drop_existing: If True, drop existing table first (WARNING: destroys data)

    Table Schema:
        - MIMICSubjectID (VARCHAR(255)) - PRIMARY KEY, MIMIC subject identifier (e.g., "p10002428")
        - FHIRPatientID (VARCHAR(255)) - FHIR Patient resource ID
        - FHIRPatientName (VARCHAR(500)) - Patient display name
        - MatchConfidence (DECIMAL(3,2)) - Confidence score (0.00-1.00)
        - MatchType (VARCHAR(50)) - 'exact', 'synthea_generated', 'manual'
        - CreatedAt (TIMESTAMP) - Record creation time
        - UpdatedAt (TIMESTAMP) - Last modification time
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if VectorSearch schema exists
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.SCHEMATA
            WHERE SCHEMA_NAME = 'VectorSearch'
        """)
        schema_exists = cursor.fetchone()[0] > 0

        if not schema_exists:
            print("📦 Creating VectorSearch schema...")
            cursor.execute("CREATE SCHEMA VectorSearch")
            conn.commit()
            print("✅ VectorSearch schema created")
        else:
            print("✅ VectorSearch schema exists")

        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'VectorSearch' AND TABLE_NAME = 'PatientImageMapping'
        """)
        table_exists = cursor.fetchone()[0] > 0

        if table_exists:
            if drop_existing:
                print("🗑️  Dropping existing PatientImageMapping table...")
                cursor.execute("DROP TABLE VectorSearch.PatientImageMapping")
                conn.commit()
                print("✅ Existing table dropped")
                table_exists = False
            else:
                print("✅ PatientImageMapping table already exists")
                # Check row count
                cursor.execute("SELECT COUNT(*) FROM VectorSearch.PatientImageMapping")
                count = cursor.fetchone()[0]
                print(f"   Current row count: {count}")
                return

        if not table_exists:
            print("📊 Creating VectorSearch.PatientImageMapping table...")

            cursor.execute("""
                CREATE TABLE VectorSearch.PatientImageMapping (
                    MIMICSubjectID VARCHAR(255) PRIMARY KEY,
                    FHIRPatientID VARCHAR(255) NOT NULL,
                    FHIRPatientName VARCHAR(500),
                    MatchConfidence DECIMAL(3,2) DEFAULT 1.00,
                    MatchType VARCHAR(50),
                    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UpdatedAt TIMESTAMP
                )
            """)

            conn.commit()
            print("✅ PatientImageMapping table created successfully")

            # Create indexes for performance
            print("📑 Creating indexes...")

            cursor.execute("""
                CREATE INDEX idx_patient_mapping_fhir ON VectorSearch.PatientImageMapping(FHIRPatientID)
            """)

            cursor.execute("""
                CREATE INDEX idx_patient_mapping_type ON VectorSearch.PatientImageMapping(MatchType)
            """)

            conn.commit()
            print("✅ Indexes created")

        print("\n" + "="*60)
        print("✅ Patient-Image Mapping table setup complete!")
        print("="*60)
        print("\nTable structure:")
        print("  - MIMICSubjectID (VARCHAR(255)) - Primary key, MIMIC subject ID")
        print("  - FHIRPatientID (VARCHAR(255)) - FHIR Patient resource ID")
        print("  - FHIRPatientName (VARCHAR(500)) - Patient display name")
        print("  - MatchConfidence (DECIMAL(3,2)) - Match confidence (0.00-1.00)")
        print("  - MatchType (VARCHAR(50)) - How the match was made")
        print("  - CreatedAt/UpdatedAt - Timestamps")
        print("\nIndexes:")
        print("  - FHIRPatientID for reverse lookups")
        print("  - MatchType for filtering by match method")
        print("\nReady for:")
        print("  - Linking MIMIC-CXR subjects to FHIR Patients")
        print("  - Patient context display in image search results")
        print("  - Integration with search_medical_images MCP tool")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def lookup_patient_mapping(mimic_subject_id: str) -> dict | None:
    """
    Look up FHIR Patient mapping for a MIMIC subject ID.

    Args:
        mimic_subject_id: MIMIC-CXR subject identifier (e.g., "p10002428")

    Returns:
        Dict with patient info or None if not found
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT MIMICSubjectID, FHIRPatientID, FHIRPatientName,
                   MatchConfidence, MatchType, CreatedAt
            FROM VectorSearch.PatientImageMapping
            WHERE MIMICSubjectID = ?
        """, [mimic_subject_id])

        row = cursor.fetchone()
        if row:
            return {
                'mimic_subject_id': row[0],
                'fhir_patient_id': row[1],
                'patient_name': row[2],
                'match_confidence': float(row[3]) if row[3] else 1.0,
                'match_type': row[4],
                'created_at': row[5]
            }
        return None

    finally:
        cursor.close()
        conn.close()


def insert_patient_mapping(
    mimic_subject_id: str,
    fhir_patient_id: str,
    patient_name: str = None,
    match_confidence: float = 1.0,
    match_type: str = 'exact'
) -> bool:
    """
    Insert a new patient mapping record.

    Args:
        mimic_subject_id: MIMIC-CXR subject identifier
        fhir_patient_id: FHIR Patient resource ID
        patient_name: Patient display name (optional)
        match_confidence: Confidence score 0.0-1.0 (default 1.0)
        match_type: How match was made ('exact', 'synthea_generated', 'manual')

    Returns:
        True if inserted successfully, False otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO VectorSearch.PatientImageMapping
            (MIMICSubjectID, FHIRPatientID, FHIRPatientName, MatchConfidence, MatchType, UpdatedAt)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [mimic_subject_id, fhir_patient_id, patient_name, match_confidence, match_type])

        conn.commit()
        return True

    except Exception as e:
        print(f"[ERROR] Failed to insert patient mapping: {e}")
        conn.rollback()
        return False

    finally:
        cursor.close()
        conn.close()


def get_mapping_stats() -> dict:
    """
    Get statistics about patient mappings.

    Returns:
        Dict with mapping statistics
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Total mappings
        cursor.execute("SELECT COUNT(*) FROM VectorSearch.PatientImageMapping")
        total = cursor.fetchone()[0]

        # By match type
        cursor.execute("""
            SELECT MatchType, COUNT(*)
            FROM VectorSearch.PatientImageMapping
            GROUP BY MatchType
        """)
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # Average confidence
        cursor.execute("SELECT AVG(MatchConfidence) FROM VectorSearch.PatientImageMapping")
        avg_confidence = cursor.fetchone()[0]

        return {
            'total_mappings': total,
            'by_match_type': by_type,
            'average_confidence': float(avg_confidence) if avg_confidence else 0.0
        }

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Create Patient-Image Mapping table in IRIS')
    parser.add_argument('--drop', action='store_true',
                       help='Drop existing table first (WARNING: destroys data)')
    parser.add_argument('--force', action='store_true',
                       help='Required with --drop to confirm data destruction')
    parser.add_argument('--stats', action='store_true',
                       help='Show mapping statistics')

    args = parser.parse_args()

    if args.stats:
        stats = get_mapping_stats()
        print("📊 Patient Mapping Statistics:")
        print(f"   Total mappings: {stats['total_mappings']}")
        print(f"   By type: {stats['by_match_type']}")
        print(f"   Avg confidence: {stats['average_confidence']:.2f}")
        sys.exit(0)

    if args.drop and not args.force:
        print("❌ Error: --drop requires --force to confirm data destruction")
        print("   Usage: python create_patient_mapping.py --drop --force")
        sys.exit(1)

    if args.drop:
        print("⚠️  WARNING: About to drop existing table and destroy all data!")
        response = input("Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)

    create_patient_mapping_table(drop_existing=args.drop)
