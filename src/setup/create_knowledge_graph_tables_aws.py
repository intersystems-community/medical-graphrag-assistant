#!/usr/bin/env python3
"""
Create Knowledge Graph Tables for FHIR GraphRAG on AWS

This script creates the SQLUser.Entities and SQLUser.EntityRelationships tables
required for the GraphRAG knowledge graph implementation on AWS IRIS.

Differences from local version:
- Uses %SYS namespace for connection (DEMO has access restrictions)
- Uses SQLUser schema instead of RAG schema
- Uses fully qualified table names
- Uses 1024-dimensional vectors (NVIDIA NIM embeddings)
- Reads from config file instead of hardcoded values

Tables created:
- SQLUser.Entities: Medical entity storage with embeddings
- SQLUser.EntityRelationships: Entity relationship storage with confidence scores

Usage:
    python3 src/setup/create_knowledge_graph_tables_aws.py --config config/fhir_graphrag_config.aws.yaml
"""

import sys
import os
import argparse
import yaml
import iris

# Pain Point #1 for iris-vector-rag team:
# The original script has hardcoded connection settings.
# For production use, configuration should be loaded from files or environment variables.

def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


# DDL for RAG.Entities table
# Pain Point #2 for iris-vector-rag team:
# Vector dimension should be configurable. Hardcoding 384 is inflexible.
# NVIDIA NIM uses 1024-dimensional vectors, so we need to support that.
CREATE_ENTITIES_TABLE = """
CREATE TABLE RAG.Entities (
  EntityID BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  EntityText VARCHAR(500) NOT NULL,
  EntityType VARCHAR(50) NOT NULL,
  ResourceID BIGINT NOT NULL,
  Confidence FLOAT NOT NULL,
  EmbeddingVector VECTOR(DOUBLE, 1024),
  ExtractedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ExtractedBy VARCHAR(100) DEFAULT 'hybrid'
)
"""

# Indexes for RAG.Entities
CREATE_ENTITIES_INDEXES = [
    "CREATE INDEX idx_entities_type ON RAG.Entities(EntityType)",
    "CREATE INDEX idx_entities_confidence ON RAG.Entities(Confidence)",
    "CREATE INDEX idx_entities_resource ON RAG.Entities(ResourceID)"
]

# DDL for RAG.EntityRelationships table
CREATE_RELATIONSHIPS_TABLE = """
CREATE TABLE RAG.EntityRelationships (
  RelationshipID BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  SourceEntityID BIGINT NOT NULL,
  TargetEntityID BIGINT NOT NULL,
  RelationshipType VARCHAR(50) NOT NULL,
  ResourceID BIGINT NOT NULL,
  Confidence FLOAT NOT NULL,
  ExtractedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  Context VARCHAR(1000)
)
"""

# Indexes for RAG.EntityRelationships
CREATE_RELATIONSHIPS_INDEXES = [
    "CREATE INDEX idx_relationships_type ON RAG.EntityRelationships(RelationshipType)",
    "CREATE INDEX idx_relationships_source ON RAG.EntityRelationships(SourceEntityID)",
    "CREATE INDEX idx_relationships_target ON RAG.EntityRelationships(TargetEntityID)",
    "CREATE INDEX idx_relationships_source_type ON RAG.EntityRelationships(SourceEntityID, RelationshipType)"
]


def create_tables_aws(config_path: str):
    """Create knowledge graph tables on AWS IRIS."""
    try:
        # Load configuration
        print(f"[INFO] Loading configuration from {config_path}...")
        config = load_config(config_path)

        # Merge config with environment variables via DatabaseConnection
        from src.db.connection import DatabaseConnection
        db_config = DatabaseConnection.get_config()
        
        host = db_config.get('hostname')
        port = db_config.get('port')
        namespace = db_config.get('namespace')
        username = db_config.get('username')
        password = db_config.get('password')

        # Pain Point #3 for iris-vector-rag team:
        # The namespace access issue is AWS-specific but not well documented.
        # On AWS IRIS Community Edition, DEMO namespace has access restrictions.
        # Must connect to %SYS and use fully qualified table names.

        print(f"[INFO] Connecting to AWS IRIS at {host}:{port}, namespace {namespace}...")
        print(f"[INFO] Note: Using namespace '{namespace}' with fully qualified table names")

        # Use centralized connection logic to handle driver quirks
        from src.db.connection import DatabaseConnection
        conn = DatabaseConnection.get_connection(
            hostname=host, port=port, namespace=namespace,
            username=username, password=password
        )
        cursor = conn.cursor()
        print("[INFO] ✅ Connected to AWS IRIS")

        # Drop existing tables if they exist
        print("[INFO] Dropping existing tables if they exist...")
        try:
            cursor.execute("DROP TABLE IF EXISTS RAG.EntityRelationships")
            cursor.execute("DROP TABLE IF EXISTS RAG.Entities")
            print("[INFO] ✅ Existing tables dropped")
        except Exception as e:
            print(f"[WARN] Could not drop tables (may not exist): {e}")

        # Create RAG.Entities table
        print("[INFO] Creating RAG.Entities table with VECTOR(DOUBLE, 1024)...")
        cursor.execute(CREATE_ENTITIES_TABLE)
        print("[INFO] ✅ Created table RAG.Entities")

        # Create indexes for RAG.Entities
        print("[INFO] Creating indexes on RAG.Entities...")
        for i, idx_sql in enumerate(CREATE_ENTITIES_INDEXES, 1):
            try:
                cursor.execute(idx_sql)
                print(f"[INFO]   ✅ Created index {i}/{len(CREATE_ENTITIES_INDEXES)}")
            except Exception as e:
                print(f"[WARN]   ⚠ Could not create index {i} (may already exist): {e}")

        # Create RAG.EntityRelationships table
        print("[INFO] Creating RAG.EntityRelationships table...")
        cursor.execute(CREATE_RELATIONSHIPS_TABLE)
        print("[INFO] ✅ Created table RAG.EntityRelationships")

        # Create indexes for RAG.EntityRelationships
        print("[INFO] Creating indexes on RAG.EntityRelationships...")
        for i, idx_sql in enumerate(CREATE_RELATIONSHIPS_INDEXES, 1):
            try:
                cursor.execute(idx_sql)
                print(f"[INFO]   ✅ Created index {i}/{len(CREATE_RELATIONSHIPS_INDEXES)}")
            except Exception as e:
                print(f"[WARN]   ⚠ Could not create index {i} (may already exist): {e}")

        # Commit changes
        conn.commit()

        # Verify table creation
        print("\n[INFO] Verifying table creation...")
        cursor.execute("SELECT COUNT(*) FROM RAG.Entities")
        entities_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM RAG.EntityRelationships")
        relationships_count = cursor.fetchone()[0]

        print(f"[INFO] ✅ RAG.Entities table verified (current rows: {entities_count})")
        print(f"[INFO] ✅ RAG.EntityRelationships table verified (current rows: {relationships_count})")

        # Close connection
        cursor.close()
        conn.close()

        print("\n[INFO] ===== Knowledge Graph Tables Created Successfully on AWS =====")
        print("[INFO] Tables:")
        print("[INFO]   - RAG.Entities (VECTOR DOUBLE 1024)")
        print("[INFO]   - RAG.EntityRelationships")
        print("[INFO] AWS initialization complete!")

        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to create knowledge graph tables: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create GraphRAG knowledge graph tables on AWS IRIS")
    parser.add_argument(
        '--config',
        default='config/fhir_graphrag_config.aws.yaml',
        help='Path to AWS configuration file'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("AWS IRIS Knowledge Graph Table Creation")
    print("=" * 70)

    success = create_tables_aws(args.config)

    if success:
        print("\n" + "=" * 70)
        print("✅ SUCCESS: AWS knowledge graph tables ready")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Run entity extraction: python3 src/setup/fhir_graphrag_setup.py --config aws --mode=build")
        print("  2. Query the graph: python3 src/query/fhir_graphrag_query.py \"chest pain\" --config aws")
    else:
        print("\n" + "=" * 70)
        print("✗ FAILED: Could not create AWS knowledge graph tables")
        print("=" * 70)

    sys.exit(0 if success else 1)
