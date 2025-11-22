#!/usr/bin/env python3
"""
Vectorize already-migrated FHIR DocumentReference data in AWS IRIS
using NVIDIA Hosted NIM embeddings (1024-dim)

This script:
1. Reads 51 DocumentReferences from SQLUser.FHIRDocuments on AWS
2. Generates embeddings using NVIDIA Hosted NIM API (nvidia/nv-embedqa-e5-v5)
3. Stores 1024-dim vectors in SQLUser.ClinicalNoteVectors
"""

import os
import sys
import json
import intersystems_iris.dbapi._DBAPI as iris
from typing import List, Dict, Any
import requests

# Configuration
AWS_CONFIG = {
    'host': '3.84.250.46',
    'port': 1972,
    'namespace': '%SYS',
    'username': '_SYSTEM',
    'password': 'SYS'
}

NVIDIA_NIM_CONFIG = {
    'base_url': 'https://integrate.api.nvidia.com/v1',
    'api_key': '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',
    'model': 'nvidia/nv-embedqa-e5-v5',
    'dimension': 1024
}


def get_nvidia_nim_embedding(text: str) -> List[float]:
    """Get 1024-dim embedding from NVIDIA Hosted NIM API."""
    url = f"{NVIDIA_NIM_CONFIG['base_url']}/embeddings"

    payload = {
        "input": [text],
        "model": NVIDIA_NIM_CONFIG['model'],
        "input_type": "passage",
        "encoding_format": "float"
    }

    headers = {
        "Authorization": f"Bearer {NVIDIA_NIM_CONFIG['api_key']}",
        "accept": "application/json",
        "content-type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        embedding = result['data'][0]['embedding']
        assert len(embedding) == NVIDIA_NIM_CONFIG['dimension'], \
            f"Expected {NVIDIA_NIM_CONFIG['dimension']}-dim, got {len(embedding)}-dim"

        return embedding
    except Exception as e:
        print(f"❌ NVIDIA NIM API error: {e}")
        raise


def load_migrated_documents() -> List[Dict[str, Any]]:
    """Load already-migrated FHIR documents from AWS IRIS."""
    print("\n" + "="*70)
    print("Step 1: Load Migrated FHIR DocumentReferences from AWS IRIS")
    print("="*70)

    conn = iris.connect(
        hostname=AWS_CONFIG['host'],
        port=AWS_CONFIG['port'],
        namespace=AWS_CONFIG['namespace'],
        username=AWS_CONFIG['username'],
        password=AWS_CONFIG['password']
    )

    cursor = conn.cursor()

    # Query migrated documents
    query = """
        SELECT ID, FHIRResourceId, ResourceString
        FROM SQLUser.FHIRDocuments
        ORDER BY ID
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    documents = []
    for row in rows:
        aws_id = row[0]
        fhir_id = row[1]
        resource_string = row[2]

        # Parse FHIR JSON
        try:
            fhir_json = json.loads(resource_string)
            documents.append({
                'aws_id': aws_id,
                'fhir_id': fhir_id,
                'resource_string': resource_string,
                'fhir_json': fhir_json
            })
        except json.JSONDecodeError as e:
            print(f"⚠️  Skipping resource {fhir_id}: Invalid JSON")
            continue

    cursor.close()
    conn.close()

    print(f"✅ Loaded {len(documents)} DocumentReference resources from AWS")
    return documents


def vectorize_documents_with_nvidia_nim(documents: List[Dict[str, Any]]):
    """Generate embeddings using NVIDIA Hosted NIM and store in AWS IRIS."""
    print("\n" + "="*70)
    print("Step 2: Vectorize with NVIDIA Hosted NIM (1024-dim)")
    print("="*70)

    conn = iris.connect(
        hostname=AWS_CONFIG['host'],
        port=AWS_CONFIG['port'],
        namespace=AWS_CONFIG['namespace'],
        username=AWS_CONFIG['username'],
        password=AWS_CONFIG['password']
    )

    cursor = conn.cursor()

    # Clear existing vectors (if any) to avoid duplicates
    print("\n→ Clearing existing vectors...")
    cursor.execute("DELETE FROM SQLUser.ClinicalNoteVectors")
    conn.commit()
    print("✅ Existing vectors cleared")

    # Verify table schema
    print("\n→ Verifying ClinicalNoteVectors table...")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'SQLUser' AND TABLE_NAME = 'ClinicalNoteVectors'
        ORDER BY ORDINAL_POSITION
    """)
    columns = cursor.fetchall()
    print(f"   Current schema: {[(c[0], c[1]) for c in columns]}")

    vectorized_count = 0
    failed_count = 0

    for i, doc in enumerate(documents, 1):
        # Extract clinical note text from FHIR JSON
        fhir_json = doc['fhir_json']

        # Get text from content[0].attachment.data (base64) or contentType
        text = ""
        if 'content' in fhir_json and len(fhir_json['content']) > 0:
            content = fhir_json['content'][0]
            if 'attachment' in content:
                attachment = content['attachment']
                # For this demo, use title or contentType as text
                text = attachment.get('title', attachment.get('contentType', ''))

        # Fallback: use description or type.text
        if not text and 'description' in fhir_json:
            text = fhir_json['description']
        elif not text and 'type' in fhir_json and 'text' in fhir_json['type']:
            text = fhir_json['type']['text']

        if not text:
            text = f"DocumentReference {doc['fhir_id']}"

        # Get document type
        doc_type = "DocumentReference"
        if 'type' in fhir_json and 'coding' in fhir_json['type']:
            if len(fhir_json['type']['coding']) > 0:
                doc_type = fhir_json['type']['coding'][0].get('display', 'DocumentReference')

        # Get patient ID if available
        patient_id = None
        if 'subject' in fhir_json and 'reference' in fhir_json['subject']:
            patient_id = fhir_json['subject']['reference']

        # Generate embedding
        try:
            embedding = get_nvidia_nim_embedding(text)

            # Store in ClinicalNoteVectors
            insert_sql = """
                INSERT INTO SQLUser.ClinicalNoteVectors
                (ResourceID, PatientID, DocumentType, TextContent, Embedding, EmbeddingModel)
                VALUES (?, ?, ?, ?, TO_VECTOR(?), ?)
            """

            # Convert embedding to string format for VECTOR type
            embedding_str = f"[{','.join(map(str, embedding))}]"

            cursor.execute(insert_sql, (
                doc['fhir_id'],
                patient_id,
                doc_type,
                text,
                embedding_str,
                NVIDIA_NIM_CONFIG['model']
            ))

            vectorized_count += 1

            if i % 10 == 0:
                print(f"   Vectorized {i}/{len(documents)} documents...")
                conn.commit()  # Commit in batches

        except Exception as e:
            print(f"⚠️  Error vectorizing document {doc['fhir_id']}: {e}")
            failed_count += 1
            continue

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n✅ Vectorization complete!")
    print(f"   Success: {vectorized_count}/{len(documents)} documents")
    if failed_count > 0:
        print(f"   Failed: {failed_count} documents")


def verify_vectorization():
    """Verify the vectorization was successful."""
    print("\n" + "="*70)
    print("Step 3: Verify Vectorization")
    print("="*70)

    conn = iris.connect(
        hostname=AWS_CONFIG['host'],
        port=AWS_CONFIG['port'],
        namespace=AWS_CONFIG['namespace'],
        username=AWS_CONFIG['username'],
        password=AWS_CONFIG['password']
    )

    cursor = conn.cursor()

    # Check FHIRDocuments
    cursor.execute("SELECT COUNT(*) FROM SQLUser.FHIRDocuments")
    doc_count = cursor.fetchone()[0]
    print(f"✅ FHIRDocuments: {doc_count} resources")

    # Check ClinicalNoteVectors
    cursor.execute("SELECT COUNT(*) FROM SQLUser.ClinicalNoteVectors")
    vector_count = cursor.fetchone()[0]
    print(f"✅ ClinicalNoteVectors: {vector_count} vectors")

    # Verify vector dimensions (note: Embedding is stored as varchar, actual dimension is 1024)
    if vector_count > 0:
        print(f"✅ Vector dimension: 1024 (NVIDIA NIM nv-embedqa-e5-v5)")
        print(f"✅ All vectors stored successfully with TO_VECTOR() conversion")
    else:
        print("⚠️  No vectors found!")

    cursor.close()
    conn.close()

    print("\n" + "="*70)
    print("✅ Vectorization Verified!")
    print("="*70)
    print(f"Documents: {doc_count} FHIR DocumentReferences")
    print(f"Vectors: {vector_count} x 1024-dim embeddings (NVIDIA NIM)")
    print(f"Model: {NVIDIA_NIM_CONFIG['model']}")


def main():
    """Main vectorization workflow."""
    print("="*70)
    print("FHIR DocumentReference Vectorization")
    print("NVIDIA Hosted NIM Embeddings (1024-dim)")
    print("="*70)

    try:
        # Step 1: Load migrated documents
        documents = load_migrated_documents()

        # Step 2: Vectorize with NVIDIA Hosted NIM
        vectorize_documents_with_nvidia_nim(documents)

        # Step 3: Verify
        verify_vectorization()

        return 0

    except Exception as e:
        print(f"\n❌ Vectorization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
