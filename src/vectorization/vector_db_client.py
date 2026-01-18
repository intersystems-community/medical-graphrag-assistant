"""
IRIS Vector Database Client

Provides a Python wrapper for InterSystems IRIS vector database operations.
Supports connection management, vector insertion, and similarity search using
IRIS native VECTOR(DOUBLE, n) type with COSINE similarity.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IRISVectorDBClient:
    """
    Client for InterSystems IRIS vector database operations.

    Handles connection management, table creation, vector insertion,
    and similarity search using IRIS native VECTOR type.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1972,
        namespace: str = "DEMO",
        username: str = "_SYSTEM",
        password: str = "SYS",
        vector_dimension: int = 1024
    ):
        """
        Initialize IRIS database client.
        """
        self.host = host
        self.port = port
        self.namespace = namespace
        self.username = username
        self.password = password
        self.vector_dimension = vector_dimension

        self.connection = None
        self.cursor = None

        logger.info(f"Initialized IRIS client: {host}:{port}/{namespace}")

    def connect(self) -> None:
        """
        Establish connection to IRIS database using the centralized DatabaseConnection.
        """
        try:
            from src.db.connection import DatabaseConnection
            
            self.connection = DatabaseConnection.get_connection(
                hostname=self.host,
                port=self.port,
                namespace=self.namespace,
                username=self.username,
                password=self.password
            )

            self.cursor = self.connection.cursor()
            if self.cursor is None:
                raise ConnectionError("Failed to create database cursor")
                
            logger.info(f"✓ Connected to IRIS: {self.host}:{self.port}/{self.namespace}")

        except Exception as e:
            logger.error(f"✗ Failed to connect to IRIS: {e}")
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            logger.info("✓ Disconnected from IRIS")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def _get_full_table_name(self, table_name: str) -> str:
        """
        Get fully qualified table name.
        If table_name contains a dot, assume it is already qualified.
        Otherwise, default to SQLUser schema (IRIS default).
        """
        if "." in table_name:
            return table_name
        return f"SQLUser.{table_name}"

    def create_clinical_note_vectors_table(
        self,
        table_name: str = "ClinicalNoteVectors",
        drop_if_exists: bool = False
    ) -> None:
        """
        Create the ClinicalNoteVectors table with VECTOR column.
        """
        if not self.connection:
            self.connect()
        assert self.cursor is not None

        full_table_name = self._get_full_table_name(table_name)

        try:
            # Drop table if requested
            if drop_if_exists:
                drop_sql = f"DROP TABLE IF EXISTS {full_table_name}"
                self.cursor.execute(drop_sql)
                logger.info(f"✓ Dropped existing table: {full_table_name}")

            # Create table with VECTOR column
            create_sql = f"""
            CREATE TABLE {full_table_name} (
                ResourceID VARCHAR(255) PRIMARY KEY,
                PatientID VARCHAR(255) NOT NULL,
                DocumentType VARCHAR(255) NOT NULL,
                TextContent VARCHAR(32000),
                SourceBundle VARCHAR(500),
                Embedding VECTOR(DOUBLE, {self.vector_dimension}) NOT NULL,
                EmbeddingModel VARCHAR(100) NOT NULL,
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """

            self.cursor.execute(create_sql)
            self.connection.commit()

            logger.info(f"✓ Created table: {full_table_name}")
            logger.info(f"  Vector dimension: {self.vector_dimension}")
            logger.info(f"  Similarity metric: COSINE")

        except Exception as e:
            logger.error(f"✗ Failed to create table: {e}")
            raise

    def insert_vector(
        self,
        resource_id: str,
        patient_id: str,
        document_type: str,
        text_content: str,
        embedding: List[float],
        embedding_model: str,
        source_bundle: Optional[str] = None,
        table_name: str = "ClinicalNoteVectors"
    ) -> None:
        """
        Insert a single vector into the database.
        """
        if not self.connection:
            self.connect()
        assert self.cursor is not None

        # Validate vector dimension
        if len(embedding) != self.vector_dimension:
            raise ValueError(
                f"Vector dimension mismatch: expected {self.vector_dimension}, "
                f"got {len(embedding)}"
            )

        full_table_name = self._get_full_table_name(table_name)

        # Convert vector to VECTOR literal format
        vector_str = "[" + ",".join(map(str, embedding)) + "]"

        try:
            insert_sql = f"""
            INSERT INTO {full_table_name} (
                ResourceID,
                PatientID,
                DocumentType,
                TextContent,
                SourceBundle,
                Embedding,
                EmbeddingModel
            ) VALUES (?, ?, ?, ?, ?, TO_VECTOR(?, DOUBLE), ?)
            """

            self.cursor.execute(
                insert_sql,
                (
                    resource_id,
                    patient_id,
                    document_type,
                    text_content,
                    source_bundle,
                    vector_str,
                    embedding_model
                )
            )

            self.connection.commit()

        except Exception as e:
            logger.error(f"✗ Failed to insert vector for {resource_id}: {e}")
            raise

    def insert_vectors_batch(
        self,
        vectors: List[Dict[str, Any]],
        table_name: str = "ClinicalNoteVectors"
    ) -> Tuple[int, int]:
        """
        Insert multiple vectors in a batch.
        """
        if not self.connection:
            self.connect()
        assert self.cursor is not None

        success_count = 0
        failed_count = 0

        for vector_data in vectors:
            try:
                self.insert_vector(
                    resource_id=vector_data["resource_id"],
                    patient_id=vector_data["patient_id"],
                    document_type=vector_data["document_type"],
                    text_content=vector_data["text_content"],
                    embedding=vector_data["embedding"],
                    embedding_model=vector_data["embedding_model"],
                    source_bundle=vector_data.get("source_bundle"),
                    table_name=table_name
                )
                success_count += 1

            except Exception as e:
                logger.warning(f"Failed to insert {vector_data.get('resource_id')}: {e}")
                failed_count += 1

        logger.info(f"✓ Batch insert: {success_count} successful, {failed_count} failed")
        return success_count, failed_count

    def search_similar(
        self,
        query_vector: List[float],
        top_k: int = 10,
        patient_id: Optional[str] = None,
        document_type: Optional[str] = None,
        table_name: str = "ClinicalNoteVectors"
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors using COSINE similarity.
        """
        if not self.connection:
            self.connect()
        assert self.cursor is not None

        # Validate vector dimension
        if len(query_vector) != self.vector_dimension:
            raise ValueError(
                f"Query vector dimension mismatch: expected {self.vector_dimension}, "
                f"got {len(query_vector)}"
            )

        full_table_name = self._get_full_table_name(table_name)

        # Convert query vector to VECTOR literal
        vector_str = "[" + ",".join(map(str, query_vector)) + "]"

        # Build query with optional filters
        where_clauses = []
        params = []

        if patient_id:
            where_clauses.append("PatientID = ?")
            params.append(patient_id)

        if document_type:
            where_clauses.append("DocumentType = ?")
            params.append(document_type)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # VECTOR_COSINE returns similarity (0-1, higher is better)
        search_sql = f"""
        SELECT TOP {top_k}
            ResourceID,
            PatientID,
            DocumentType,
            TextContent,
            SourceBundle,
            VECTOR_COSINE(Embedding, TO_VECTOR('{vector_str}', DOUBLE)) AS Similarity
        FROM {full_table_name}
        {where_sql}
        ORDER BY Similarity DESC
        """

        try:
            if params:
                self.cursor.execute(search_sql, params)
            else:
                self.cursor.execute(search_sql)

            results = []
            for row in self.cursor.fetchall():
                results.append({
                    "resource_id": row[0],
                    "patient_id": row[1],
                    "document_type": row[2],
                    "text_content": row[3],
                    "source_bundle": row[4],
                    "similarity": float(row[5])
                })

            logger.info(f"✓ Found {len(results)} similar vectors (top {top_k})")
            return results

        except Exception as e:
            logger.error(f"✗ Vector search failed: {e}")
            raise

    def count_vectors(self, table_name: str = "ClinicalNoteVectors") -> int:
        """
        Count total vectors in table.
        """
        if not self.connection:
            self.connect()
        assert self.cursor is not None

        full_table_name = self._get_full_table_name(table_name)

        count_sql = f"SELECT COUNT(*) FROM {full_table_name}"

        try:
            self.cursor.execute(count_sql)
            count = self.cursor.fetchone()[0]
            return int(count)

        except Exception as e:
            logger.error(f"✗ Count failed: {e}")
            raise

    def get_vector_stats(
        self,
        table_name: str = "ClinicalNoteVectors"
    ) -> Dict[str, Any]:
        """
        Get statistics about vectors in table.
        """
        if not self.connection:
            self.connect()
        assert self.cursor is not None

        full_table_name = self._get_full_table_name(table_name)

        try:
            # Total vectors
            total = self.count_vectors(table_name)

            # Unique patients
            self.cursor.execute(
                f"SELECT COUNT(DISTINCT PatientID) FROM {full_table_name}"
            )
            unique_patients = int(self.cursor.fetchone()[0])

            # Document type breakdown
            self.cursor.execute(f"""
                SELECT DocumentType, COUNT(*) as count
                FROM {full_table_name}
                GROUP BY DocumentType
                ORDER BY count DESC
            """)

            doc_type_counts = {}
            for row in self.cursor.fetchall():
                doc_type_counts[row[0]] = int(row[1])

            stats = {
                "total_vectors": total,
                "unique_patients": unique_patients,
                "unique_document_types": len(doc_type_counts),
                "document_type_counts": doc_type_counts
            }

            logger.info(f"✓ Vector stats: {total} vectors, {unique_patients} patients")
            return stats

        except Exception as e:
            logger.error(f"✗ Stats query failed: {e}")
            raise

    def insert_image_vector(
        self,
        image_id: str,
        patient_id: str,
        study_type: str,
        image_path: str,
        embedding: List[float],
        related_report_id: Optional[str] = None,
        table_name: str = "MedicalImageVectors"
    ) -> None:
        """
        Insert an image vector into the database.
        """
        if not self.connection:
            self.connect()
        assert self.cursor is not None

        # Validate vector dimension
        if len(embedding) != self.vector_dimension:
            raise ValueError(
                f"Vector dimension mismatch: expected {self.vector_dimension}, "
                f"got {len(embedding)}"
            )

        full_table_name = self._get_full_table_name(table_name)

        # Convert vector to VECTOR literal format
        # IRIS expects: TO_VECTOR('[0.1,0.2,0.3,...]', DOUBLE)
        vector_str = "[" + ",".join(map(str, embedding)) + "]"

        try:
            insert_sql = f"""
            INSERT INTO {full_table_name} (
                ImageID,
                PatientID,
                StudyType,
                ImagePath,
                Embedding,
                RelatedReportID
            ) VALUES (?, ?, ?, ?, TO_VECTOR(?, DOUBLE), ?)
            """

            self.cursor.execute(
                insert_sql,
                (
                    image_id,
                    patient_id,
                    study_type,
                    image_path,
                    vector_str,
                    related_report_id
                )
            )

            self.connection.commit()

        except Exception as e:
            logger.error(f"✗ Failed to insert image vector for {image_id}: {e}")
            raise

    def search_similar_images(
        self,
        query_vector: List[float],
        top_k: int = 10,
        patient_id: Optional[str] = None,
        study_type: Optional[str] = None,
        table_name: str = "MedicalImageVectors"
    ) -> List[Dict[str, Any]]:
        """
        Search for similar images using COSINE similarity.
        """
        if not self.connection:
            self.connect()
        assert self.cursor is not None

        # Validate vector dimension
        if len(query_vector) != self.vector_dimension:
            raise ValueError(
                f"Query vector dimension mismatch: expected {self.vector_dimension}, "
                f"got {len(query_vector)}"
            )

        full_table_name = self._get_full_table_name(table_name)

        # Convert query vector to VECTOR literal
        vector_str = "[" + ",".join(map(str, query_vector)) + "]"

        # Build query with optional filters
        where_clauses = []
        params = []

        if patient_id:
            where_clauses.append("PatientID = ?")
            params.append(patient_id)

        if study_type:
            where_clauses.append("StudyType = ?")
            params.append(study_type)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # VECTOR_COSINE returns similarity (0-1, higher is better)
        search_sql = f"""
        SELECT TOP {top_k}
            ImageID,
            PatientID,
            StudyType,
            ImagePath,
            RelatedReportID,
            VECTOR_COSINE(Embedding, TO_VECTOR('{vector_str}', DOUBLE)) AS Similarity
        FROM {full_table_name}
        {where_sql}
        ORDER BY Similarity DESC
        """

        try:
            if params:
                self.cursor.execute(search_sql, params)
            else:
                self.cursor.execute(search_sql)

            results = []
            for row in self.cursor.fetchall():
                results.append({
                    "image_id": row[0],
                    "patient_id": row[1],
                    "study_type": row[2],
                    "image_path": row[3],
                    "related_report_id": row[4],
                    "similarity": float(row[5])
                })

            logger.info(f"✓ Found {len(results)} similar images (top {top_k})")
            return results

        except Exception as e:
            logger.error(f"✗ Image vector search failed: {e}")
            raise


# Example usage
if __name__ == "__main__":
    # Example: Connect and query
    client = IRISVectorDBClient()

    with client:
        # Get stats
        try:
            stats = client.get_vector_stats()
            print(f"\\nVector Database Stats:")
            print(f"  Total vectors: {stats['total_vectors']:,}")
            print(f"  Unique patients: {stats['unique_patients']:,}")
            print(f"  Document types: {stats['unique_document_types']}")

            for doc_type, count in stats['document_type_counts'].items():
                print(f"    - {doc_type}: {count:,}")
        except Exception as e:
            print(f"Error getting stats: {e}")
