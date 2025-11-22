#!/usr/bin/env python3
"""
Setup IRIS Vector Database Schema
Creates namespace and vector tables for FHIR AI Hackathon Kit
"""

import iris
import sys

def main():
    try:
        # Connect to IRIS as SuperUser on %SYS namespace
        print("→ Connecting to IRIS %SYS namespace...")
        conn = iris.connect('localhost', 1972, '%SYS', '_SYSTEM', 'SYS')
        print("✓ Connected to IRIS")

        cursor = conn.cursor()

        # Create DEMO namespace/schema
        print("\n→ Creating DEMO namespace...")
        try:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS DEMO")
            print("✓ DEMO schema created/verified")
        except Exception as e:
            print(f"! Schema creation: {e}")
            if "already exists" not in str(e).lower():
                raise

        # Switch to DEMO namespace for table creation
        print("\n→ Switching to DEMO namespace...")
        cursor.execute("USE DEMO")
        print("✓ Switched to DEMO namespace")

        # Create ClinicalNoteVectors table
        print("\n→ Creating ClinicalNoteVectors table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ClinicalNoteVectors (
                ResourceID VARCHAR(255) PRIMARY KEY,
                PatientID VARCHAR(255) NOT NULL,
                DocumentType VARCHAR(255) NOT NULL,
                TextContent VARCHAR(65535) NOT NULL,
                Embedding VECTOR(DOUBLE, 1024) NOT NULL,
                SourceBundle VARCHAR(500),
                EmbeddingModel VARCHAR(255),
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("✓ ClinicalNoteVectors table created")

        # Create indexes for ClinicalNoteVectors
        print("→ Creating indexes on ClinicalNoteVectors...")
        try:
            cursor.execute("CREATE INDEX idx_patient ON ClinicalNoteVectors(PatientID)")
        except:
            pass  # Index might already exist
        try:
            cursor.execute("CREATE INDEX idx_doc_type ON ClinicalNoteVectors(DocumentType)")
        except:
            pass  # Index might already exist
        conn.commit()
        print("✓ Indexes created")

        # Create MedicalImageVectors table
        print("\n→ Creating MedicalImageVectors table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS MedicalImageVectors (
                ImageID VARCHAR(255) PRIMARY KEY,
                PatientID VARCHAR(255) NOT NULL,
                StudyType VARCHAR(255) NOT NULL,
                ImagePath VARCHAR(1000) NOT NULL,
                Embedding VECTOR(DOUBLE, 1024) NOT NULL,
                RelatedReportID VARCHAR(255),
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("✓ MedicalImageVectors table created")

        # Create indexes for MedicalImageVectors
        print("→ Creating indexes on MedicalImageVectors...")
        try:
            cursor.execute("CREATE INDEX idx_image_patient ON MedicalImageVectors(PatientID)")
        except:
            pass  # Index might already exist
        try:
            cursor.execute("CREATE INDEX idx_study_type ON MedicalImageVectors(StudyType)")
        except:
            pass  # Index might already exist
        conn.commit()
        print("✓ Indexes created")

        # Verify tables exist
        print("\n→ Verifying tables...")
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'DEMO'
            ORDER BY TABLE_NAME
        """)
        tables = cursor.fetchall()
        print(f"✓ Found {len(tables)} tables in DEMO namespace:")
        for table in tables:
            print(f"  - {table[0]}")

        conn.close()
        print("\n✓ IRIS schema setup complete!")
        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
