#!/usr/bin/env python3
"""
Recreate MedicalImageVectors table with correct VECTOR schema.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.db.connection import get_connection

def recreate_table():
    """Drop and recreate MedicalImageVectors with proper VECTOR type."""
    conn = get_connection()
    cursor = conn.cursor()

    print("Recreating MedicalImageVectors table with correct schema...\n")

    # Drop existing table
    try:
        print("→ Dropping existing table...")
        cursor.execute("DROP TABLE SQLUser.MedicalImageVectors")
        conn.commit()
        print("✓ Table dropped")
    except Exception as e:
        print(f"Note: {e}")
        conn.rollback()

    # Create table with correct VECTOR type
    print("\n→ Creating table with VECTOR(DOUBLE, 1024)...")
    cursor.execute("""
        CREATE TABLE SQLUser.MedicalImageVectors (
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
    print("✓ Table created with VECTOR(DOUBLE, 512)")

    # Create indexes
    print("\n→ Creating indexes...")
    try:
        cursor.execute("CREATE INDEX idx_image_patient ON SQLUser.MedicalImageVectors(PatientID)")
        cursor.execute("CREATE INDEX idx_study_type ON SQLUser.MedicalImageVectors(StudyType)")
        conn.commit()
        print("✓ Indexes created")
    except Exception as e:
        print(f"Note: {e}")

    cursor.close()
    conn.close()

    print("\n✅ Done! Table recreated successfully")
    print("\nNow run: python load_sample_images.py --limit 5")

if __name__ == "__main__":
    recreate_table()
