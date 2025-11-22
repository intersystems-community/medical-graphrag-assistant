#!/usr/bin/env python3
"""
Pure IRIS Vector Memory System - Agent learning with semantic search

Stores agent memories as vector embeddings in IRIS for semantic retrieval:
- User corrections and domain knowledge
- User preferences and feedback
- Query history and successful patterns

100% IRIS - No SQLite, just clean vector search.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add project root to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.db.connection import get_connection


class VectorMemory:
    """Pure IRIS vector-based semantic memory for agent learning."""

    def __init__(self, embedding_model=None):
        """
        Initialize vector memory system.

        Args:
            embedding_model: Optional embedding model (defaults to NVCLIPEmbeddings for text)
        """
        self.embedding_model = embedding_model
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create AgentMemoryVectors table if it doesn't exist."""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'SQLUser' AND TABLE_NAME = 'AgentMemoryVectors'
            """)
            exists = cursor.fetchone()[0] > 0

            if not exists:
                # Create table - pure vector design like MedicalImageVectors
                cursor.execute("""
                    CREATE TABLE SQLUser.AgentMemoryVectors (
                        MemoryID VARCHAR(255) PRIMARY KEY,
                        MemoryType VARCHAR(50) NOT NULL,
                        MemoryText VARCHAR(4000) NOT NULL,
                        Embedding VECTOR(DOUBLE, 1024),
                        Metadata VARCHAR(4000),
                        UseCount INT DEFAULT 1,
                        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        LastUsedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                print("✅ Created AgentMemoryVectors table in IRIS", file=sys.stderr)
        finally:
            cursor.close()
            conn.close()

    def _get_embedding(self, text: str) -> List[float]:
        """
        Get NV-CLIP text embedding.

        Args:
            text: Text to embed

        Returns:
            1024-dim embedding vector
        """
        if self.embedding_model is None:
            # Lazy load NV-CLIP
            try:
                from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings
                self.embedding_model = NVCLIPEmbeddings()
            except Exception as e:
                print(f"Warning: Could not load NV-CLIP: {e}", file=sys.stderr)
                # Return zero vector as fallback
                return [0.0] * 1024

        # Use text embedding (NV-CLIP supports both text and images)
        return self.embedding_model.embed_text(text)

    def remember(self, memory_type: str, memory_text: str, metadata: Dict = None) -> str:
        """
        Store a semantic memory with vector embedding.

        Args:
            memory_type: Type of memory ('correction', 'knowledge', 'preference', 'query', 'feedback')
            memory_text: Text content to remember
            metadata: Optional structured metadata (JSON serialized)

        Returns:
            Memory ID (hash of text)
        """
        import hashlib
        memory_id = hashlib.sha256(memory_text.encode()).hexdigest()[:16]

        # Generate NV-CLIP text embedding
        embedding = self._get_embedding(memory_text)
        embedding_str = ','.join(map(str, embedding))

        # Serialize metadata
        metadata_str = json.dumps(metadata) if metadata else None

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Check if memory already exists
            cursor.execute("""
                SELECT MemoryID FROM SQLUser.AgentMemoryVectors
                WHERE MemoryID = ?
            """, (memory_id,))

            exists = cursor.fetchone() is not None

            if exists:
                # Update existing memory - increment use count
                cursor.execute("""
                    UPDATE SQLUser.AgentMemoryVectors
                    SET UseCount = UseCount + 1,
                        UpdatedAt = CURRENT_TIMESTAMP,
                        LastUsedAt = CURRENT_TIMESTAMP,
                        Metadata = ?
                    WHERE MemoryID = ?
                """, (metadata_str, memory_id))
            else:
                # Insert new memory
                cursor.execute("""
                    INSERT INTO SQLUser.AgentMemoryVectors
                    (MemoryID, MemoryType, MemoryText, Embedding, Metadata, CreatedAt, UpdatedAt, LastUsedAt)
                    VALUES (?, ?, ?, TO_VECTOR(?, DOUBLE), ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (memory_id, memory_type, memory_text, embedding_str, metadata_str))

            conn.commit()
            return memory_id

        finally:
            cursor.close()
            conn.close()

    def recall(self, query: str, memory_type: str = None, top_k: int = 5, min_similarity: float = 0.5) -> List[Dict]:
        """
        Recall memories semantically similar to query using vector search.

        Args:
            query: Search query
            memory_type: Optional filter by memory type
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of memory dictionaries with similarity scores
        """
        # Generate query embedding
        query_embedding = self._get_embedding(query)
        embedding_str = ','.join(map(str, query_embedding))

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Build SQL with optional type filter (same pattern as image search)
            if memory_type:
                sql = """
                    SELECT TOP ?
                        MemoryID, MemoryType, MemoryText, Metadata, UseCount,
                        VECTOR_COSINE(Embedding, TO_VECTOR(?, DOUBLE)) AS Similarity
                    FROM SQLUser.AgentMemoryVectors
                    WHERE MemoryType = ?
                    ORDER BY Similarity DESC
                """
                cursor.execute(sql, (top_k * 2, embedding_str, memory_type))
            else:
                sql = """
                    SELECT TOP ?
                        MemoryID, MemoryType, MemoryText, Metadata, UseCount,
                        VECTOR_COSINE(Embedding, TO_VECTOR(?, DOUBLE)) AS Similarity
                    FROM SQLUser.AgentMemoryVectors
                    ORDER BY Similarity DESC
                """
                cursor.execute(sql, (top_k * 2, embedding_str))

            results = []
            for row in cursor.fetchall():
                memory_id, mtype, text, metadata_str, use_count, similarity = row

                # Handle None similarity (shouldn't happen but be safe)
                if similarity is None:
                    similarity = 0.0

                # Filter by minimum similarity
                if similarity < min_similarity:
                    continue

                # Parse metadata
                metadata = json.loads(metadata_str) if metadata_str else {}

                results.append({
                    'memory_id': memory_id,
                    'memory_type': mtype,
                    'text': text,
                    'metadata': metadata,
                    'use_count': use_count,
                    'similarity': float(similarity)
                })

                if len(results) >= top_k:
                    break

            # Update last used timestamp for retrieved memories
            if results:
                memory_ids = [r['memory_id'] for r in results]
                placeholders = ','.join(['?'] * len(memory_ids))
                cursor.execute(f"""
                    UPDATE SQLUser.AgentMemoryVectors
                    SET LastUsedAt = CURRENT_TIMESTAMP
                    WHERE MemoryID IN ({placeholders})
                """, memory_ids)
                conn.commit()

            return results

        finally:
            cursor.close()
            conn.close()

    def forget(self, memory_id: str = None, memory_type: str = None):
        """
        Remove memories by ID or type.

        Args:
            memory_id: Optional specific memory ID
            memory_type: Optional memory type (if no ID specified)
        """
        conn = get_connection()
        cursor = conn.cursor()

        try:
            if memory_id:
                cursor.execute("DELETE FROM SQLUser.AgentMemoryVectors WHERE MemoryID = ?", (memory_id,))
            elif memory_type:
                cursor.execute("DELETE FROM SQLUser.AgentMemoryVectors WHERE MemoryType = ?", (memory_type,))
            else:
                raise ValueError("Must specify either memory_id or memory_type")

            conn.commit()

        finally:
            cursor.close()
            conn.close()

    def get_stats(self) -> Dict:
        """Get memory system statistics."""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM SQLUser.AgentMemoryVectors")
            total_memories = cursor.fetchone()[0]

            cursor.execute("""
                SELECT MemoryType, COUNT(*) as Cnt
                FROM SQLUser.AgentMemoryVectors
                GROUP BY MemoryType
                ORDER BY Cnt DESC
            """)
            type_breakdown = {mtype: count for mtype, count in cursor.fetchall()}

            cursor.execute("""
                SELECT TOP 5 MemoryText, UseCount
                FROM SQLUser.AgentMemoryVectors
                ORDER BY UseCount DESC
            """)
            most_used = [{'text': text[:100], 'count': count} for text, count in cursor.fetchall()]

            return {
                'total_memories': total_memories,
                'type_breakdown': type_breakdown,
                'most_used_memories': most_used
            }

        finally:
            cursor.close()
            conn.close()

    def get_context_prompt(self, query: str = None, max_memories: int = 5) -> str:
        """
        Generate context prompt from relevant memories.

        Args:
            query: Optional query to find relevant memories (if None, gets most used)
            max_memories: Maximum memories to include

        Returns:
            Formatted context prompt for agent
        """
        if query:
            # Get semantically relevant memories via vector search
            memories = self.recall(query, top_k=max_memories, min_similarity=0.6)
        else:
            # Get most frequently used memories
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT TOP ? MemoryType, MemoryText, Metadata, UseCount
                    FROM SQLUser.AgentMemoryVectors
                    ORDER BY UseCount DESC, LastUsedAt DESC
                """, (max_memories,))

                memories = []
                for mtype, text, metadata_str, use_count in cursor.fetchall():
                    metadata = json.loads(metadata_str) if metadata_str else {}
                    memories.append({
                        'memory_type': mtype,
                        'text': text,
                        'metadata': metadata,
                        'use_count': use_count
                    })
            finally:
                cursor.close()
                conn.close()

        if not memories:
            return ""

        # Format as context prompt
        lines = ["# Agent Memory Context\n"]

        for mem in memories:
            mem_type = mem.get('memory_type', 'unknown')
            text = mem.get('text', '')
            use_count = mem.get('use_count', 0)
            similarity = mem.get('similarity')

            lines.append(f"## {mem_type.title()}")
            lines.append(f"{text}")
            if similarity:
                lines.append(f"*(Relevance: {similarity:.2f}, Used {use_count}x)*")
            else:
                lines.append(f"*(Used {use_count}x)*")
            lines.append("")

        return "\n".join(lines)


# Convenience functions for common operations

def remember_correction(correction_text: str, context: Dict = None) -> str:
    """Remember a user correction with vector embedding."""
    memory = VectorMemory()
    return memory.remember('correction', correction_text, context)

def remember_knowledge(knowledge_text: str, context: Dict = None) -> str:
    """Remember domain knowledge with vector embedding."""
    memory = VectorMemory()
    return memory.remember('knowledge', knowledge_text, context)

def remember_preference(preference_text: str, context: Dict = None) -> str:
    """Remember user preference with vector embedding."""
    memory = VectorMemory()
    return memory.remember('preference', preference_text, context)

def recall_similar(query: str, memory_type: str = None, top_k: int = 5) -> List[Dict]:
    """Recall memories semantically similar to query."""
    memory = VectorMemory()
    return memory.recall(query, memory_type, top_k)


if __name__ == '__main__':
    # Demo/test
    print("🧠 Pure IRIS Vector Memory System Demo\n" + "="*60)

    memory = VectorMemory()

    # Store example memories
    print("\n📝 Storing memories with NV-CLIP embeddings...")

    remember_correction(
        "Pneumonia appears as consolidation (white/opaque areas) on chest X-ray, typically in lung bases",
        context={'source': 'user_feedback', 'date': '2025-01-15'}
    )

    remember_knowledge(
        "Cardiomegaly means enlarged heart, visible as increased cardiac silhouette on frontal chest X-ray",
        context={'source': 'medical_reference'}
    )

    remember_preference(
        "User prefers semantic search over keyword search for medical images",
        context={'confidence': 0.9}
    )

    # Test semantic vector search
    print("\n🔍 Testing semantic vector recall...")

    print("\n1. Query: 'What does pneumonia look like on X-ray?'")
    results = recall_similar("What does pneumonia look like on X-ray?", top_k=3)
    for r in results:
        print(f"   [{r['memory_type']}] Similarity: {r['similarity']:.3f}")
        print(f"   {r['text'][:80]}...")

    print("\n2. Query: 'enlarged heart findings'")
    results = recall_similar("enlarged heart findings", top_k=3)
    for r in results:
        print(f"   [{r['memory_type']}] Similarity: {r['similarity']:.3f}")
        print(f"   {r['text'][:80]}...")

    print("\n3. Query: 'user search preferences'")
    results = recall_similar("user search preferences", top_k=3)
    for r in results:
        print(f"   [{r['memory_type']}] Similarity: {r['similarity']:.3f}")
        print(f"   {r['text'][:80]}...")

    # Stats
    print("\n📊 Memory Statistics:")
    stats = memory.get_stats()
    print(f"   Total memories: {stats['total_memories']}")
    print(f"   By type: {stats['type_breakdown']}")

    # Context prompt
    print("\n📝 Context Prompt for 'chest x-ray findings':")
    context = memory.get_context_prompt("chest x-ray findings", max_memories=2)
    print(context)

    print("\n✅ Demo complete - Pure IRIS vector memory working!")
