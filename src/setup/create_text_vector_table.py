"""
Create VectorSearch.FHIRTextVectors table.

This table stores clinical note embeddings from both OpenAI (3072-dim)
and NIM (1024-dim) providers.
"""

import iris
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_text_vector_table():
    """
    Create VectorSearch.FHIRTextVectors table.

    Table supports both OpenAI (3072-dim) and NIM (1024-dim) vectors
    by storing provider metadata and using max dimension.
    """
    # Connect to IRIS
    conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
    cursor = conn.cursor()

    try:
        # Drop table if exists (for clean re-creation)
        logger.info("Dropping existing table if exists...")
        cursor.execute("DROP TABLE IF EXISTS VectorSearch.FHIRTextVectors")

        # Create table with support for both provider dimensions
        logger.info("Creating VectorSearch.FHIRTextVectors table...")
        cursor.execute("""
            CREATE TABLE VectorSearch.FHIRTextVectors (
                ResourceID VARCHAR(255) NOT NULL,
                ResourceType VARCHAR(50) NOT NULL,
                TextContent VARCHAR(MAX),
                Vector VECTOR(DOUBLE, 3072),
                EmbeddingModel VARCHAR(100),
                Provider VARCHAR(20),
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ResourceID, Provider)
            )
        """)

        # Create index for fast provider filtering
        logger.info("Creating index on Provider column...")
        cursor.execute("""
            CREATE INDEX idx_provider
            ON VectorSearch.FHIRTextVectors(Provider)
        """)

        # Create index on ResourceType for filtering
        logger.info("Creating index on ResourceType column...")
        cursor.execute("""
            CREATE INDEX idx_resource_type
            ON VectorSearch.FHIRTextVectors(ResourceType)
        """)

        conn.commit()
        logger.info("✅ Table created successfully!")

        # Verify table creation
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'FHIRTextVectors'
            AND TABLE_SCHEMA = 'VectorSearch'
        """)
        count = cursor.fetchone()[0]

        if count == 1:
            logger.info("✅ Table verified in INFORMATION_SCHEMA")
        else:
            logger.warning("⚠️ Table not found in INFORMATION_SCHEMA")

        # Show table structure
        logger.info("\nTable structure:")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'FHIRTextVectors'
            AND TABLE_SCHEMA = 'VectorSearch'
            ORDER BY ORDINAL_POSITION
        """)

        for column_name, data_type in cursor.fetchall():
            logger.info(f"  {column_name:20} {data_type}")

    except Exception as e:
        logger.error(f"❌ Error creating table: {e}")
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("Creating VectorSearch.FHIRTextVectors Table")
    print("=" * 60)
    print()

    create_text_vector_table()

    print()
    print("=" * 60)
    print("Table Creation Complete")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Set EMBEDDINGS_PROVIDER environment variable")
    print("     - export EMBEDDINGS_PROVIDER='openai'  # for development")
    print("     - export EMBEDDINGS_PROVIDER='nim'     # for production")
    print()
    print("  2. Set provider-specific credentials")
    print("     - export OPENAI_API_KEY='sk-...'  # if using OpenAI")
    print("     - export NIM_ENDPOINT='http://...'  # if using NIM")
    print()
    print("  3. Run vectorization script")
    print("     - python src/setup/vectorize_documents.py")
