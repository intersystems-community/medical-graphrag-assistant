"""
Create VectorSearch.FHIRTextVectors table.

This table stores clinical note embeddings from both OpenAI (3072-dim)
and NIM (1024-dim) providers.
"""

import logging
from src.db.connection import DatabaseConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_text_vector_table():
    """
    Ensure all required text and document tables exist.
    Creates:
    - VectorSearch.FHIRTextVectors (for embeddings)
    - SQLUser.FHIRDocuments (for raw document storage and search)
    """
    conn = DatabaseConnection.get_connection()
    cursor = conn.cursor()

    try:
        logger.info("Verifying VectorSearch.FHIRTextVectors table...")
        cursor.execute("DROP TABLE IF EXISTS VectorSearch.FHIRTextVectors")
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

        logger.info("Verifying SQLUser.FHIRDocuments table...")
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'FHIRDocuments'
            AND TABLE_SCHEMA = 'SQLUser'
        """)
        if cursor.fetchone()[0] == 0:
            logger.info("Creating SQLUser.FHIRDocuments table...")
            cursor.execute("""
                CREATE TABLE SQLUser.FHIRDocuments (
                    ID INTEGER IDENTITY PRIMARY KEY,
                    FHIRResourceId VARCHAR(255),
                    ResourceString CLOB,
                    ResourceType VARCHAR(50),
                    TextContent VARCHAR(MAX),
                    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            cursor.execute("""
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'FHIRDocuments'
                AND TABLE_SCHEMA = 'SQLUser'
                AND COLUMN_NAME = 'TextContent'
            """)
            if cursor.fetchone()[0] == 0:
                logger.info("Adding TextContent column to SQLUser.FHIRDocuments...")
                cursor.execute("ALTER TABLE SQLUser.FHIRDocuments ADD COLUMN TextContent VARCHAR(MAX)")

        conn.commit()
        logger.info("✅ All tables verified successfully!")

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
