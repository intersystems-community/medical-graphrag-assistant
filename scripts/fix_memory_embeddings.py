#!/usr/bin/env python3
"""
Fix Memory Embeddings - Re-embed existing memories with real NV-CLIP vectors

This script re-generates embeddings for all memories that have mock/zero embeddings.
Requires NVCLIP_BASE_URL to be set to a working NV-CLIP endpoint.
"""

import sys
import os

# Add parent directory to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.db.connection import get_connection
from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings

def fix_memory_embeddings():
    """Re-embed memories with real NV-CLIP vectors."""

    print("=" * 60)
    print("Fix Memory Embeddings with NV-CLIP")
    print("=" * 60)
    print()

    # Initialize NV-CLIP
    try:
        embedder = NVCLIPEmbeddings()
        print(f"✅ NV-CLIP initialized")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize NV-CLIP: {e}")
        print()
        print("Make sure NVCLIP_BASE_URL is set:")
        print("  export NVCLIP_BASE_URL=http://localhost:8002/v1")
        return 1

    # Connect to database
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get all memories
        cursor.execute("""
            SELECT MemoryID, MemoryText,
                   VECTOR_DOT_PRODUCT(Embedding, Embedding) as magnitude
            FROM SQLUser.AgentMemoryVectors
        """)

        memories = cursor.fetchall()
        total = len(memories)

        if total == 0:
            print("No memories found in database.")
            return 0

        print(f"Found {total} memories")
        print()

        # Count how many need fixing
        needs_fix = sum(1 for mem in memories if mem[2] == 0.0)

        print(f"Memories with mock embeddings (zeros): {needs_fix}")
        print(f"Memories with real embeddings: {total - needs_fix}")
        print()

        if needs_fix == 0:
            print("✅ All memories already have real embeddings!")
            return 0

        # Fix memories
        print(f"Re-embedding {needs_fix} memories...")
        print()

        fixed = 0
        errors = 0

        for memory_id, memory_text, magnitude in memories:
            if magnitude > 0:
                continue  # Skip memories that already have real embeddings

            try:
                # Generate real embedding
                embedding = embedder.embed_text(memory_text)

                # Verify it's real
                import numpy as np
                vec = np.array(embedding)
                new_magnitude = np.dot(vec, vec)

                if new_magnitude == 0:
                    print(f"  ❌ {memory_id[:8]}: Still got zeros")
                    errors += 1
                    continue

                # Update in database
                cursor.execute("""
                    UPDATE SQLUser.AgentMemoryVectors
                    SET Embedding = TO_VECTOR(?)
                    WHERE MemoryID = ?
                """, (str(embedding), memory_id))

                conn.commit()

                fixed += 1
                print(f"  ✅ {memory_id[:8]}: Fixed (magnitude {new_magnitude:.4f})")

            except Exception as e:
                print(f"  ❌ {memory_id[:8]}: Error - {e}")
                errors += 1

        print()
        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"Total memories: {total}")
        print(f"Fixed: {fixed}")
        print(f"Errors: {errors}")
        print(f"Already had real embeddings: {total - needs_fix}")
        print()

        if fixed > 0:
            print("✅ Memory search should now work!")

        return 0

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    sys.exit(fix_memory_embeddings())
