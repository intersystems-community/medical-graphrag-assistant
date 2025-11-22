#!/usr/bin/env python3
"""
Create MIMIC-CXR Images Table in IRIS (Repeatable)

Creates the VectorSearch.MIMICCXRImages table with proper vector support
for NV-CLIP embeddings. Idempotent - safe to run multiple times.
"""

import sys
import os

# Add project root to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.db.connection import get_connection


def create_mimic_images_table(drop_existing=False):
    """
    Create VectorSearch.MIMICCXRImages table with vector support.

    Args:
        drop_existing: If True, drop existing table first (WARNING: destroys data)
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
            WHERE TABLE_SCHEMA = 'VectorSearch' AND TABLE_NAME = 'MIMICCXRImages'
        """)
        table_exists = cursor.fetchone()[0] > 0

        if table_exists:
            if drop_existing:
                print("🗑️  Dropping existing MIMICCXRImages table...")
                cursor.execute("DROP TABLE VectorSearch.MIMICCXRImages")
                conn.commit()
                print("✅ Existing table dropped")
                table_exists = False
            else:
                print("✅ MIMICCXRImages table already exists")
                # Check row count
                cursor.execute("SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages")
                count = cursor.fetchone()[0]
                print(f"   Current row count: {count}")
                return

        if not table_exists:
            print("📊 Creating VectorSearch.MIMICCXRImages table...")

            cursor.execute("""
                CREATE TABLE VectorSearch.MIMICCXRImages (
                    ImageID VARCHAR(255) PRIMARY KEY,
                    StudyID VARCHAR(255) NOT NULL,
                    SubjectID VARCHAR(255) NOT NULL,
                    ViewPosition VARCHAR(50),
                    ImagePath VARCHAR(1000),
                    Vector VECTOR(DOUBLE, 1024),
                    Metadata VARCHAR(4000),
                    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            print("✅ MIMICCXRImages table created successfully")

            # Create indexes for performance
            print("📑 Creating indexes...")

            cursor.execute("""
                CREATE INDEX idx_mimic_study ON VectorSearch.MIMICCXRImages(StudyID)
            """)

            cursor.execute("""
                CREATE INDEX idx_mimic_subject ON VectorSearch.MIMICCXRImages(SubjectID)
            """)

            cursor.execute("""
                CREATE INDEX idx_mimic_view ON VectorSearch.MIMICCXRImages(ViewPosition)
            """)

            conn.commit()
            print("✅ Indexes created")

        print("\n" + "="*60)
        print("✅ MIMIC-CXR Images table setup complete!")
        print("="*60)
        print("\nTable structure:")
        print("  - ImageID (VARCHAR(255)) - Primary key, DICOM file ID")
        print("  - StudyID (VARCHAR(255)) - Study identifier")
        print("  - SubjectID (VARCHAR(255)) - Patient identifier")
        print("  - ViewPosition (VARCHAR(50)) - PA, AP, LATERAL, etc.")
        print("  - ImagePath (VARCHAR(1000)) - Path to DICOM file")
        print("  - Vector (VECTOR(DOUBLE, 1024)) - NV-CLIP embedding")
        print("  - Metadata (VARCHAR(4000)) - JSON metadata")
        print("  - CreatedAt/UpdatedAt - Timestamps")
        print("\nIndexes:")
        print("  - StudyID, SubjectID, ViewPosition for fast filtering")
        print("\nReady for:")
        print("  - Medical image ingestion with NV-CLIP embeddings")
        print("  - Semantic vector search via VECTOR_COSINE")
        print("  - Integration with MCP search_medical_images tool")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Create MIMIC-CXR Images table in IRIS')
    parser.add_argument('--drop', action='store_true',
                       help='Drop existing table first (WARNING: destroys data)')
    parser.add_argument('--force', action='store_true',
                       help='Required with --drop to confirm data destruction')

    args = parser.parse_args()

    if args.drop and not args.force:
        print("❌ Error: --drop requires --force to confirm data destruction")
        print("   Usage: python create_mimic_images_table.py --drop --force")
        sys.exit(1)

    if args.drop:
        print("⚠️  WARNING: About to drop existing table and destroy all data!")
        response = input("Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)

    create_mimic_images_table(drop_existing=args.drop)
