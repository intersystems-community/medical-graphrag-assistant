#!/usr/bin/env python3
"""
Test the image search functionality with MedicalImageVectors table.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.db.connection import get_connection

def test_keyword_search():
    """Test keyword-based image search."""
    print("Testing keyword search...")
    print("-" * 60)

    conn = get_connection()
    cursor = conn.cursor()

    query = "chest x-ray"
    limit = 5

    # Keyword search (same logic as MCP server fallback)
    keywords = query.lower().split()
    conditions = []
    params = []
    for kw in keywords:
        conditions.append("(LOWER(StudyType) LIKE ? OR LOWER(ImageID) LIKE ?)")
        params.extend([f'%{kw}%', f'%{kw}%'])

    where_clause = " OR ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT TOP ?
            ImageID, PatientID, StudyType, ImagePath
        FROM SQLUser.MedicalImageVectors
        WHERE {where_clause}
    """

    cursor.execute(sql, [limit] + params)

    results = []
    for row in cursor.fetchall():
        image_id, patient_id, study_type, image_path = row
        results.append({
            "image_id": image_id,
            "patient_id": patient_id,
            "study_type": study_type,
            "image_path": image_path,
            "description": f"{study_type} for patient {patient_id}"
        })

    cursor.close()
    conn.close()

    print(f"Query: '{query}'")
    print(f"Results found: {len(results)}\n")

    if results:
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['image_id']}")
            print(f"   Patient: {result['patient_id']}")
            print(f"   Study: {result['study_type']}")
            print(f"   Path: {result['image_path']}")
            print(f"   Description: {result['description']}")
            print()
        print("✓ Keyword search working correctly")
        return True
    else:
        print("✗ No results found")
        return False


def test_semantic_search():
    """Test semantic (vector) search - if embedder available."""
    print("\nTesting semantic search...")
    print("-" * 60)

    try:
        from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings
        embedder = NVCLIPEmbeddings()
        print("✓ NV-CLIP embedder initialized")
    except Exception as e:
        print(f"⚠ NV-CLIP not available: {e}")
        print("Semantic search requires NV-CLIP embeddings")
        return None

    conn = get_connection()
    cursor = conn.cursor()

    query = "chest x-ray pneumonia"
    limit = 5

    try:
        # Generate query embedding
        query_vector = embedder.embed_text(query)
        vector_str = ','.join(map(str, query_vector))

        # Vector search (same logic as MCP server)
        sql = f"""
            SELECT TOP ?
                ImageID, PatientID, StudyType, ImagePath,
                VECTOR_COSINE(Embedding, TO_VECTOR(?, double)) AS Similarity
            FROM SQLUser.MedicalImageVectors
            ORDER BY Similarity DESC
        """

        cursor.execute(sql, (limit, vector_str))

        results = []
        for row in cursor.fetchall():
            image_id, patient_id, study_type, image_path, similarity = row
            similarity_score = float(similarity) if similarity is not None else 0.0

            results.append({
                "image_id": image_id,
                "patient_id": patient_id,
                "study_type": study_type,
                "image_path": image_path,
                "similarity_score": similarity_score,
                "description": f"{study_type} for patient {patient_id}"
            })

        cursor.close()
        conn.close()

        print(f"Query: '{query}'")
        print(f"Results found: {len(results)}\n")

        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['image_id']} (similarity: {result['similarity_score']:.4f})")
                print(f"   Patient: {result['patient_id']}")
                print(f"   Study: {result['study_type']}")
                print(f"   Path: {result['image_path']}")
                print()
            print("✓ Semantic search working correctly")
            return True
        else:
            print("✗ No results found")
            return False

    except Exception as e:
        cursor.close()
        conn.close()
        print(f"✗ Error during semantic search: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_table_contents():
    """Check what's in the table."""
    print("\nChecking table contents...")
    print("-" * 60)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM SQLUser.MedicalImageVectors")
    count = cursor.fetchone()[0]
    print(f"Total images in table: {count}")

    if count > 0:
        cursor.execute("""
            SELECT ImageID, PatientID, StudyType
            FROM SQLUser.MedicalImageVectors
        """)
        print("\nAll images:")
        for image_id, patient_id, study_type in cursor.fetchall():
            print(f"  - {image_id}: {study_type} (Patient {patient_id})")

    cursor.close()
    conn.close()
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Medical Image Search Test")
    print("=" * 60)
    print()

    # Check table contents first
    test_table_contents()

    # Test keyword search
    keyword_ok = test_keyword_search()

    # Test semantic search (if available)
    semantic_ok = test_semantic_search()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Keyword search: {'✓ PASS' if keyword_ok else '✗ FAIL'}")
    if semantic_ok is not None:
        print(f"Semantic search: {'✓ PASS' if semantic_ok else '✗ FAIL'}")
    else:
        print("Semantic search: ⚠ SKIPPED (NV-CLIP not available)")
    print()
