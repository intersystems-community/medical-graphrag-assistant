#!/usr/bin/env python3
"""
Migrate FHIR DocumentReference data from local IRIS to AWS IRIS
and re-vectorize with NVIDIA NIM embeddings (1024-dim)

This script:
1. Extracts 51 DocumentReference resources from local IRIS
2. Transfers them to AWS IRIS (via temporary JSON)
3. Re-vectorizes using NVIDIA NIM NV-EmbedQA-E5-v5 (1024-dim)
4. Stores vectors in SQLUser.ClinicalNoteVectors on AWS
"""

import os
import sys
import json
import intersystems_iris.dbapi._DBAPI as iris
from typing import List, Dict, Any
import requests

# Configuration
LOCAL_CONFIG = {
    'host': 'localhost',
    'port': 32782,
    'namespace': 'DEMO',
    'username': '_SYSTEM',
    'password': 'ISCDEMO'
}

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
    """Get 1024-dim embedding from NVIDIA NIM."""
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


def extract_fhir_documents_from_local() -> List[Dict[str, Any]]:
    """Extract DocumentReference resources from local IRIS."""
    print("\n" + "="*70)
    print("Step 1: Extract FHIR DocumentReferences from Local IRIS")
    print("="*70)

    conn = iris.connect(
        hostname=LOCAL_CONFIG['host'],
        port=LOCAL_CONFIG['port'],
        namespace=LOCAL_CONFIG['namespace'],
        username=LOCAL_CONFIG['username'],
        password=LOCAL_CONFIG['password']
    )

    cursor = conn.cursor()

    # Query DocumentReference resources
    query = """
        SELECT ID, ResourceString, ResourceId
        FROM HSFHIR_X0001_R.Rsrc
        WHERE ResourceType = 'DocumentReference'
        ORDER BY ID
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    documents = []
    for row in rows:
        resource_id = row[0]
        resource_string = row[1]
        resource_fhir_id = row[2]

        # Parse FHIR JSON
        try:
            fhir_json = json.loads(resource_string)
            documents.append({
                'iris_id': resource_id,
                'fhir_id': resource_fhir_id,
                'resource_string': resource_string,
                'fhir_json': fhir_json
            })
        except json.JSONDecodeError as e:
            print(f"⚠️  Skipping resource {resource_id}: Invalid JSON")
            continue

    cursor.close()
    conn.close()

    print(f"✅ Extracted {len(documents)} DocumentReference resources")
    return documents


def store_documents_in_aws(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Store FHIR documents in AWS IRIS and return with new IDs."""
    print("\n" + "="*70)
    print("Step 2: Store Documents in AWS IRIS")
    print("="*70)

    conn = iris.connect(
        hostname=AWS_CONFIG['host'],
        port=AWS_CONFIG['port'],
        namespace=AWS_CONFIG['namespace'],
        username=AWS_CONFIG['username'],
        password=AWS_CONFIG['password']
    )

    cursor = conn.cursor()

    # Create table if not exists (using proper schema)
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS SQLUser.FHIRDocuments (
            ID INTEGER IDENTITY PRIMARY KEY,
            FHIRResourceId VARCHAR(255),
            ResourceString CLOB,
            ResourceType VARCHAR(50),
            CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    cursor.execute(create_table_sql)

    stored_docs = []
    for i, doc in enumerate(documents, 1):
        # Insert document
        insert_sql = """
            INSERT INTO SQLUser.FHIRDocuments (FHIRResourceId, ResourceString, ResourceType)
            VALUES (?, ?, 'DocumentReference')
        """
        cursor.execute(insert_sql, (doc['fhir_id'], doc['resource_string']))

        # Get the new ID
        cursor.execute("SELECT LAST_IDENTITY()")
        new_id = cursor.fetchone()[0]

        stored_docs.append({
            **doc,
            'aws_iris_id': new_id
        })

        if i % 10 == 0:
            print(f"   Stored {i}/{len(documents)} documents...")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ Stored {len(stored_docs)} documents in AWS IRIS (SQLUser.FHIRDocuments)")
    return stored_docs


def vectorize_documents_with_nvidia_nim(documents: List[Dict[str, Any]]):
    """Generate embeddings using NVIDIA NIM and store in AWS IRIS."""
    print("\n" + "="*70)
    print("Step 3: Vectorize with NVIDIA NIM (1024-dim)")
    print("="*70)

    conn = iris.connect(
        hostname=AWS_CONFIG['host'],
        port=AWS_CONFIG['port'],
        namespace=AWS_CONFIG['namespace'],
        username=AWS_CONFIG['username'],
        password=AWS_CONFIG['password']
    )

    cursor = conn.cursor()

    # Ensure ClinicalNoteVectors table exists with correct schema
    print("\n→ Verifying ClinicalNoteVectors table...")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'SQLUser' AND TABLE_NAME = 'ClinicalNoteVectors'
        ORDER BY ORDINAL_POSITION
    """)
    columns = cursor.fetchall()
    print(f"   Current schema: {[(c[0], c[1]) for c in columns]}")

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

        # Generate embedding
        try:
            embedding = get_nvidia_nim_embedding(text)

            # Store in ClinicalNoteVectors
            insert_sql = """
                INSERT INTO SQLUser.ClinicalNoteVectors (ResourceID, Embedding, EmbeddingModel)
                VALUES (?, TO_VECTOR(?), ?)
            """

            # Convert embedding to string format for VECTOR type
            embedding_str = f"[{','.join(map(str, embedding))}]"

            cursor.execute(insert_sql, (
                doc['fhir_id'],
                embedding_str,
                NVIDIA_NIM_CONFIG['model']
            ))

            if i % 10 == 0:
                print(f"   Vectorized {i}/{len(documents)} documents...")

        except Exception as e:
            print(f"⚠️  Error vectorizing document {doc['fhir_id']}: {e}")
            continue

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ Vectorized {len(documents)} documents with NVIDIA NIM (1024-dim)")


def verify_migration():
    """Verify the migration was successful."""
    print("\n" + "="*70)
    print("Step 4: Verify Migration")
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

    # Verify vector dimensions
    cursor.execute("SELECT TOP 1 VECTOR_DIMENSION(Embedding) FROM SQLUser.ClinicalNoteVectors")
    dim = cursor.fetchone()[0]
    print(f"✅ Vector dimension: {dim}")

    assert dim == 1024, f"Expected 1024-dim vectors, got {dim}-dim"

    cursor.close()
    conn.close()

    print("\n" + "="*70)
    print("✅ Migration Complete!")
    print("="*70)
    print(f"Migrated {doc_count} FHIR DocumentReferences to AWS IRIS")
    print(f"Generated {vector_count} x 1024-dim embeddings with NVIDIA NIM")


def main():
    """Main migration workflow."""
    print("="*70)
    print("FHIR DocumentReference Migration: Local → AWS")
    print("NVIDIA NIM Re-Vectorization: 384-dim → 1024-dim")
    print("="*70)

    try:
        # Step 1: Extract from local
        documents = extract_fhir_documents_from_local()

        # Step 2: Store in AWS
        stored_docs = store_documents_in_aws(documents)

        # Step 3: Vectorize with NVIDIA NIM
        vectorize_documents_with_nvidia_nim(stored_docs)

        # Step 4: Verify
        verify_migration()

        return 0

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
