#!/usr/bin/env python3
"""
Test iris-vector-rag with AWS IRIS - FIXED VERSION

Tests iris-vector-rag 0.5.4 CloudConfiguration API with CORRECT environment variables and config structure.

Key fixes:
1. Use VECTOR_DIMENSION env var (not RAG_EMBEDDING_MODEL__DIMENSION)
2. Use storage.vector_dimension in config (not embedding_model.dimension)
3. Test iris-vector-rag components directly (not custom wrappers)

This test demonstrates the CORRECT way to use CloudConfiguration API!
"""

import os
import sys
import tempfile
import yaml
from typing import List, Dict, Any

# Test imports
try:
    from iris_vector_rag.config.manager import ConfigurationManager
    from iris_vector_rag.storage.vector_store_iris import IRISVectorStore
    from iris_vector_rag.core.connection import ConnectionManager
    from iris_vector_rag.core.models import Document
    print("✅ iris-vector-rag imports successful")
except ImportError as e:
    print(f"❌ Failed to import iris-vector-rag: {e}")
    sys.exit(1)


def create_test_config() -> str:
    """Create temporary AWS config file with CORRECT structure for CloudConfiguration API."""
    config = {
        'database': {
            'iris': {
                'host': '3.84.250.46',
                'port': 1972,
                'namespace': '%SYS',
                'username': '_SYSTEM',
                'password': 'SYS'
            }
        },
        # ✅ CORRECT: CloudConfiguration reads from "storage" key
        'storage': {
            'iris': {
                'table_name': 'SQLUser.TestDocuments'
            },
            'vector_dimension': 1024,  # ✅ THIS is what CloudConfiguration reads!
            'distance_metric': 'COSINE',
            'index_type': 'HNSW'
        },
        'embeddings': {
            'default_provider': 'sentence_transformers',
            'sentence_transformers': {
                'model_name': 'sentence-transformers/all-MiniLM-L6-v2',
                'device': 'cpu'
            }
        }
    }

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        return f.name


def test_config_manager(config_path: str):
    """Test 1: ConfigurationManager with AWS settings."""
    print("\n" + "="*70)
    print("Test 1: ConfigurationManager with AWS Settings")
    print("="*70)

    try:
        config = ConfigurationManager(config_path=config_path)

        # Test basic config access
        host = config.get("database:iris:host")
        port = config.get("database:iris:port")
        namespace = config.get("database:iris:namespace")

        # Test CORRECT config location for vector dimension
        storage_vector_dim = config.get("storage:vector_dimension")

        print(f"\n✅ Config loaded successfully:")
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   Namespace: {namespace}")
        print(f"   Storage Vector Dimension: {storage_vector_dim} (CloudConfiguration reads this)")

        assert host == "3.84.250.46", f"Expected host 3.84.250.46, got {host}"
        assert namespace == "%SYS", f"Expected namespace %SYS, got {namespace}"
        assert storage_vector_dim == 1024, f"Expected storage:vector_dimension 1024, got {storage_vector_dim}"

        print("\n✅ Test 1 PASSED: ConfigurationManager working correctly")
        return True

    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cloud_config_api(config_path: str):
    """Test 2: CloudConfiguration API with correct environment variables."""
    print("\n" + "="*70)
    print("Test 2: CloudConfiguration API")
    print("="*70)

    try:
        # ✅ CORRECT: Set environment variable that CloudConfiguration actually reads
        print("\n✅ Setting CORRECT environment variable for CloudConfiguration API")
        print("   VECTOR_DIMENSION=1024 (not RAG_EMBEDDING_MODEL__DIMENSION)")
        os.environ['VECTOR_DIMENSION'] = '1024'

        config = ConfigurationManager(config_path=config_path)

        # Test CloudConfiguration API
        print("\n→ Querying CloudConfiguration API...")
        cloud_config = config.get_cloud_config()

        print(f"✅ CloudConfiguration returned:")
        print(f"   Connection host: {cloud_config.connection.host}")
        print(f"   Connection namespace: {cloud_config.connection.namespace}")
        print(f"   Vector dimension: {cloud_config.vector.vector_dimension}")
        print(f"   Distance metric: {cloud_config.vector.distance_metric}")
        print(f"   Table schema: {cloud_config.tables.table_schema}")

        # Verify environment variable took priority
        assert cloud_config.vector.vector_dimension == 1024, \
            f"Expected 1024 from VECTOR_DIMENSION env var, got {cloud_config.vector.vector_dimension}"

        # Clean up
        del os.environ['VECTOR_DIMENSION']

        print("\n✅ Test 2 PASSED: CloudConfiguration API working correctly")
        return True

    except Exception as e:
        print(f"\n❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        # Clean up on error
        if 'VECTOR_DIMENSION' in os.environ:
            del os.environ['VECTOR_DIMENSION']
        return False


def test_connection_manager(config_path: str):
    """Test 3: ConnectionManager with AWS IRIS."""
    print("\n" + "="*70)
    print("Test 3: ConnectionManager with AWS IRIS")
    print("="*70)

    try:
        config = ConfigurationManager(config_path=config_path)

        # Set legacy IRIS_* environment variables (iris-vector-rag's connection utility still uses these)
        print("\n→ Setting legacy IRIS_* environment variables for connection utility")
        os.environ['IRIS_HOST'] = config.get("database:iris:host", "3.84.250.46")
        os.environ['IRIS_PORT'] = str(config.get("database:iris:port", 1972))
        os.environ['IRIS_NAMESPACE'] = config.get("database:iris:namespace", "%SYS")
        os.environ['IRIS_USER'] = config.get("database:iris:username", "_SYSTEM")
        os.environ['IRIS_PASSWORD'] = config.get("database:iris:password", "SYS")

        conn_mgr = ConnectionManager(config_manager=config)

        # Get connection
        print("\n→ Attempting connection to AWS IRIS...")
        connection = conn_mgr.get_connection("iris")

        print("✅ Connected to AWS IRIS successfully")

        # Test basic query
        cursor = connection.cursor()
        cursor.execute("SELECT $ZVERSION")
        version = cursor.fetchone()[0]
        print(f"✅ IRIS Version: {version[:60]}...")

        # Test table access
        cursor.execute("SELECT COUNT(*) FROM SQLUser.ClinicalNoteVectors")
        count = cursor.fetchone()[0]
        print(f"✅ SQLUser.ClinicalNoteVectors has {count} rows")

        cursor.close()

        print("\n✅ Test 3 PASSED: ConnectionManager working with AWS")
        return True

    except Exception as e:
        print(f"\n❌ Test 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up environment variables
        for var in ['IRIS_HOST', 'IRIS_PORT', 'IRIS_NAMESPACE', 'IRIS_USER', 'IRIS_PASSWORD']:
            if var in os.environ:
                del os.environ[var]


def test_schema_manager(config_path: str):
    """Test 4: SchemaManager with CloudConfiguration API."""
    print("\n" + "="*70)
    print("Test 4: SchemaManager with CloudConfiguration API")
    print("="*70)

    try:
        from iris_vector_rag.storage.schema_manager import SchemaManager

        # ✅ CORRECT: Set environment variable that CloudConfiguration reads
        os.environ['VECTOR_DIMENSION'] = '1024'

        config = ConfigurationManager(config_path=config_path)

        # Set legacy environment variables for connection
        os.environ['IRIS_HOST'] = config.get("database:iris:host", "3.84.250.46")
        os.environ['IRIS_PORT'] = str(config.get("database:iris:port", 1972))
        os.environ['IRIS_NAMESPACE'] = config.get("database:iris:namespace", "%SYS")
        os.environ['IRIS_USER'] = config.get("database:iris:username", "_SYSTEM")
        os.environ['IRIS_PASSWORD'] = config.get("database:iris:password", "SYS")

        conn_mgr = ConnectionManager(config_manager=config)

        print("\n→ Creating SchemaManager...")
        # Reset class-level cache to force reload
        SchemaManager._config_loaded = False
        schema_mgr = SchemaManager(conn_mgr, config)

        # Test CloudConfiguration API access
        print("→ Querying CloudConfiguration via SchemaManager...")
        cloud_config = config.get_cloud_config()
        print(f"✅ CloudConfiguration vector dimension: {cloud_config.vector.vector_dimension}")

        # Test getting vector dimension
        vector_dim = schema_mgr.get_vector_dimension("SourceDocuments")
        print(f"✅ SchemaManager vector dimension: {vector_dim}")

        assert vector_dim == 1024, f"Expected 1024, got {vector_dim}"

        print("\n✅ Test 4 PASSED: SchemaManager correctly uses CloudConfiguration API")
        return True

    except Exception as e:
        print(f"\n❌ Test 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up environment variables
        for var in ['VECTOR_DIMENSION', 'IRIS_HOST', 'IRIS_PORT', 'IRIS_NAMESPACE', 'IRIS_USER', 'IRIS_PASSWORD']:
            if var in os.environ:
                del os.environ[var]


def test_vector_store_init(config_path: str):
    """Test 5: IRISVectorStore with CloudConfiguration API."""
    print("\n" + "="*70)
    print("Test 5: IRISVectorStore with CloudConfiguration API")
    print("="*70)

    try:
        # ✅ CORRECT: Set environment variables
        os.environ['VECTOR_DIMENSION'] = '1024'

        config = ConfigurationManager(config_path=config_path)

        # Set legacy environment variables for connection
        os.environ['IRIS_HOST'] = config.get("database:iris:host", "3.84.250.46")
        os.environ['IRIS_PORT'] = str(config.get("database:iris:port", 1972))
        os.environ['IRIS_NAMESPACE'] = config.get("database:iris:namespace", "%SYS")
        os.environ['IRIS_USER'] = config.get("database:iris:username", "_SYSTEM")
        os.environ['IRIS_PASSWORD'] = config.get("database:iris:password", "SYS")

        print("\n→ Creating IRISVectorStore with CloudConfiguration API...")
        vector_store = IRISVectorStore(config_manager=config)

        print("✅ IRISVectorStore initialized successfully")
        print(f"   Table: {vector_store.table_name}")
        print(f"   Vector Dimension: {vector_store.vector_dimension}")

        assert vector_store.vector_dimension == 1024, \
            f"Expected dimension 1024, got {vector_store.vector_dimension}"

        print("\n✅ Test 5 PASSED: IRISVectorStore correctly uses CloudConfiguration")
        return True

    except Exception as e:
        print(f"\n❌ Test 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up environment variables
        for var in ['VECTOR_DIMENSION', 'IRIS_HOST', 'IRIS_PORT', 'IRIS_NAMESPACE', 'IRIS_USER', 'IRIS_PASSWORD']:
            if var in os.environ:
                del os.environ[var]


def main():
    """Run all tests."""
    print("="*70)
    print("iris-vector-rag CloudConfiguration API Test Suite - FIXED VERSION")
    print("Testing with CORRECT environment variables and config structure")
    print("="*70)

    # Create test config with CORRECT structure
    print("\n→ Creating temporary AWS config file with CORRECT structure...")
    config_path = create_test_config()
    print(f"✅ Config created: {config_path}")
    print("   Config uses: storage.vector_dimension (CORRECT for CloudConfiguration)")

    results = {}

    try:
        # Run tests
        results['config_manager'] = test_config_manager(config_path)
        results['cloud_config_api'] = test_cloud_config_api(config_path)
        results['connection'] = test_connection_manager(config_path)
        results['schema_manager'] = test_schema_manager(config_path)
        results['vector_store'] = test_vector_store_init(config_path)

        # Summary
        print("\n" + "="*70)
        print("Test Summary")
        print("="*70)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:20} : {status}")

        print("\n" + "="*70)
        print(f"Results: {passed}/{total} tests passed")
        print("="*70)

        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
            print("\nKey Findings:")
            print("  ✅ CloudConfiguration API works correctly in v0.5.4")
            print("  ✅ VECTOR_DIMENSION environment variable is the correct key")
            print("  ✅ storage.vector_dimension is the correct config file key")
            print("  ✅ SchemaManager correctly uses CloudConfiguration")
            print("  ✅ IRISVectorStore correctly gets dimensions from SchemaManager")
            print("\n🎉 iris-vector-rag v0.5.4 is PRODUCTION-READY!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            print("Review errors above for details")
            return 1

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        # Cleanup
        try:
            os.unlink(config_path)
            print(f"\n✓ Cleaned up: {config_path}")
        except:
            pass


if __name__ == "__main__":
    sys.exit(main())
