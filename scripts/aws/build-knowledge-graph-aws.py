#!/usr/bin/env python3
"""
Build knowledge graph on AWS using iris-vector-rag v0.5.4 GraphRAG pipeline

This script uses the iris-vector-rag abstraction layer instead of raw SQL:
- ConfigurationManager for settings
- IRISVectorStore for vector operations
- Entity extraction pipelines
- Schema management for table creation
"""

import os
import sys
from pathlib import Path

# Set environment variables for iris-vector-rag
os.environ['VECTOR_DIMENSION'] = '1024'
os.environ['IRIS_HOST'] = '3.84.250.46'
os.environ['IRIS_PORT'] = '1972'
os.environ['IRIS_NAMESPACE'] = '%SYS'
os.environ['IRIS_USER'] = '_SYSTEM'
os.environ['IRIS_PASSWORD'] = 'SYS'

try:
    from iris_vector_rag.config.manager import ConfigurationManager
    from iris_vector_rag.storage.vector_store_iris import IRISVectorStore
    from iris_vector_rag.core.connection import ConnectionManager
    from iris_vector_rag.core.models import Document
    from iris_vector_rag.pipelines import GraphRAGPipeline
    print("✅ iris-vector-rag imports successful")
except ImportError as e:
    print(f"❌ Failed to import iris-vector-rag: {e}")
    print("Run: pip install iris-vector-rag")
    sys.exit(1)

import intersystems_iris.dbapi._DBAPI as iris
import json


def main():
    """Build knowledge graph using iris-vector-rag pipeline."""
    print("="*70)
    print("AWS GraphRAG Knowledge Graph Build")
    print("Using iris-vector-rag v0.5.4 Pipeline")
    print("="*70)

    # Use AWS config
    config_path = Path(__file__).parent.parent.parent / "config" / "fhir_graphrag_config.aws.yaml"

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return 1

    print(f"\n→ Loading configuration from {config_path}")
    config = ConfigurationManager(config_path=str(config_path))

    print(f"✅ Configuration loaded")
    print(f"   Host: {config.get('database:iris:host')}")
    print(f"   Namespace: {config.get('database:iris:namespace')}")
    print(f"   Vector dimension: {config.get('storage:vector_dimension')}")

    # Initialize vector store
    print(f"\n→ Initializing IRISVectorStore...")
    vector_store = IRISVectorStore(config_manager=config)
    print(f"✅ Vector store initialized")
    print(f"   Table: {vector_store.table_name}")
    print(f"   Dimension: {vector_store.vector_dimension}")

    # Load FHIR documents from AWS
    print(f"\n→ Loading FHIR documents from AWS IRIS...")

    conn = iris.connect(
        hostname='3.84.250.46',
        port=1972,
        namespace='%SYS',
        username='_SYSTEM',
        password='SYS'
    )

    cursor = conn.cursor()
    cursor.execute("""
        SELECT FHIRResourceId, ResourceString
        FROM SQLUser.FHIRDocuments
        ORDER BY ID
    """)
    rows = cursor.fetchall()

    documents = []
    for fhir_id, resource_string in rows:
        try:
            fhir_json = json.loads(resource_string)

            # Extract hex-encoded clinical note
            text = ""
            if 'content' in fhir_json and len(fhir_json['content']) > 0:
                content = fhir_json['content'][0]
                if 'attachment' in content and 'data' in content['attachment']:
                    try:
                        decoded_bytes = bytes.fromhex(content['attachment']['data'])
                        text = decoded_bytes.decode('utf-8')
                    except Exception as e:
                        print(f"⚠️  Failed to decode document {fhir_id}: {e}")
                        continue

            if text:
                # Create Document object for iris-vector-rag
                doc = Document(
                    page_content=text,
                    id=str(fhir_id),
                    metadata={
                        'resource_type': 'DocumentReference',
                        'fhir_id': fhir_id
                    }
                )
                documents.append(doc)
        except Exception as e:
            print(f"⚠️  Error processing document {fhir_id}: {e}")
            continue

    cursor.close()
    conn.close()

    print(f"✅ Loaded {len(documents)} FHIR documents")

    if len(documents) == 0:
        print("❌ No documents to process")
        return 1

    # Show sample document
    print(f"\n→ Sample document:")
    print(f"   ID: {documents[0].id}")
    print(f"   Content preview: {documents[0].page_content[:100]}...")

    # Initialize GraphRAG pipeline
    print(f"\n→ Initializing GraphRAG pipeline...")
    try:
        pipeline = GraphRAGPipeline(
            config_manager=config,
            vector_store=vector_store
        )
        print(f"✅ GraphRAG pipeline initialized")
    except Exception as e:
        print(f"❌ Failed to initialize pipeline: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Ingest documents into knowledge graph
    print(f"\n→ Ingesting {len(documents)} documents into knowledge graph...")
    try:
        pipeline.ingest(documents)
        print(f"✅ Documents ingested successfully")
    except Exception as e:
        print(f"❌ Failed to ingest documents: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Test query
    print(f"\n→ Testing knowledge graph query...")
    try:
        results = pipeline.query("chest pain", top_k=3)
        print(f"✅ Query successful!")
        print(f"   Found {len(results)} results")
        for i, result in enumerate(results[:3], 1):
            print(f"   {i}. {result.get('content', '')[:80]}...")
    except Exception as e:
        print(f"⚠️  Query failed: {e}")
        # Non-fatal - knowledge graph may still be built

    print(f"\n{'='*70}")
    print(f"✅ GraphRAG Knowledge Graph Complete!")
    print(f"{'='*70}")
    print(f"Documents processed: {len(documents)}")
    print(f"Using iris-vector-rag v0.5.4 GraphRAG pipeline")

    return 0


if __name__ == "__main__":
    sys.exit(main())
