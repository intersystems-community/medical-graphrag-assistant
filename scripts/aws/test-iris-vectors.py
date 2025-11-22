#!/usr/bin/env python3
"""
Test IRIS Vector Database Operations
Verifies vector insertion and similarity search on AWS EC2
"""

import iris
import sys
import random

def main():
    try:
        print("→ Connecting to IRIS...")
        conn = iris.connect('localhost', 1972, '%SYS', '_SYSTEM', 'SYS')
        cursor = conn.cursor()
        print("✓ Connected to IRIS")

        # Generate sample 1024-dimensional vectors
        print("\n→ Generating sample vectors...")
        random.seed(42)
        vector1 = [random.gauss(0, 1) for _ in range(1024)]
        vector2 = [random.gauss(0, 1) for _ in range(1024)]
        vector3 = [random.gauss(0, 1) for _ in range(1024)]

        # Convert to IRIS VECTOR format (comma-separated string)
        vector1_str = ','.join(map(str, vector1))
        vector2_str = ','.join(map(str, vector2))
        vector3_str = ','.join(map(str, vector3))
        print("✓ Sample vectors generated (1024 dimensions each)")

        # Insert test records into ClinicalNoteVectors
        print("\n→ Inserting test clinical notes...")
        cursor.execute("""
            DELETE FROM SQLUser.ClinicalNoteVectors
            WHERE ResourceID LIKE 'TEST_%'
        """)

        cursor.execute("""
            INSERT INTO SQLUser.ClinicalNoteVectors
            (ResourceID, PatientID, DocumentType, TextContent, Embedding, EmbeddingModel)
            VALUES ('TEST_001', 'PATIENT_001', 'Progress Note',
                    'Patient presents with chest pain and shortness of breath.',
                    TO_VECTOR('%s'), 'NV-EmbedQA-E5-v5')
        """ % vector1_str)

        cursor.execute("""
            INSERT INTO SQLUser.ClinicalNoteVectors
            (ResourceID, PatientID, DocumentType, TextContent, Embedding, EmbeddingModel)
            VALUES ('TEST_002', 'PATIENT_002', 'Discharge Summary',
                    'Patient discharged after successful cardiac catheterization.',
                    TO_VECTOR('%s'), 'NV-EmbedQA-E5-v5')
        """ % vector2_str)

        cursor.execute("""
            INSERT INTO SQLUser.ClinicalNoteVectors
            (ResourceID, PatientID, DocumentType, TextContent, Embedding, EmbeddingModel)
            VALUES ('TEST_003', 'PATIENT_003', 'Consultation Note',
                    'Cardiology consultation for atrial fibrillation management.',
                    TO_VECTOR('%s'), 'NV-EmbedQA-E5-v5')
        """ % vector3_str)

        conn.commit()
        print("✓ Inserted 3 test clinical notes")

        # Verify records exist
        print("\n→ Verifying inserted records...")
        cursor.execute("""
            SELECT ResourceID, PatientID, DocumentType,
                   SUBSTRING(TextContent, 1, 50) AS TextPreview,
                   EmbeddingModel
            FROM SQLUser.ClinicalNoteVectors
            WHERE ResourceID LIKE 'TEST_%'
            ORDER BY ResourceID
        """)

        records = cursor.fetchall()
        print(f"✓ Found {len(records)} test records:")
        for record in records:
            print(f"  - {record[0]}: {record[1]}, {record[2]}, \"{record[3]}...\"")

        # Test vector similarity search
        print("\n→ Testing vector similarity search...")
        query_vector_str = ','.join(map(str, vector1))  # Use vector1 as query

        cursor.execute("""
            SELECT TOP 3
                ResourceID,
                PatientID,
                SUBSTRING(TextContent, 1, 50) AS TextPreview,
                VECTOR_DOT_PRODUCT(Embedding, TO_VECTOR('%s', DOUBLE, 1024)) AS Similarity
            FROM SQLUser.ClinicalNoteVectors
            WHERE ResourceID LIKE 'TEST_%%'
            ORDER BY Similarity DESC
        """ % query_vector_str)

        results = cursor.fetchall()
        print("✓ Top 3 similar clinical notes:")
        for idx, result in enumerate(results, 1):
            similarity = float(result[3]) if result[3] else 0.0
            print(f"  {idx}. {result[0]} (similarity: {similarity:.4f})")
            print(f"     Text: \"{result[2]}...\"")

        # Test image vectors
        print("\n→ Testing medical image vectors...")
        cursor.execute("""
            INSERT INTO SQLUser.MedicalImageVectors
            (ImageID, PatientID, StudyType, ImagePath, Embedding, EmbeddingModel)
            VALUES ('TEST_IMG_001', 'PATIENT_001', 'Chest X-Ray',
                    '/images/patient001_cxr.dcm',
                    TO_VECTOR('%s'), 'Nemotron-Nano-VL')
        """ % vector1_str)

        conn.commit()
        print("✓ Inserted test medical image")

        # Verify image record
        cursor.execute("""
            SELECT ImageID, PatientID, StudyType, ImagePath, EmbeddingModel
            FROM SQLUser.MedicalImageVectors
            WHERE ImageID = 'TEST_IMG_001'
        """)

        img_record = cursor.fetchone()
        if img_record:
            print(f"✓ Image record verified: {img_record[0]}, {img_record[2]}, {img_record[3]}")

        # Cleanup test data
        print("\n→ Cleaning up test data...")
        cursor.execute("DELETE FROM SQLUser.ClinicalNoteVectors WHERE ResourceID LIKE 'TEST_%'")
        cursor.execute("DELETE FROM SQLUser.MedicalImageVectors WHERE ImageID LIKE 'TEST_%'")
        conn.commit()
        print("✓ Test data cleaned up")

        conn.close()
        print("\n✅ All IRIS vector operations working correctly!")
        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
