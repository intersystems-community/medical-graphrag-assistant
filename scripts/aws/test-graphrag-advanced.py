#!/usr/bin/env python3
"""
Advanced GraphRAG query demonstrations showing multi-entity matching,
symptom-condition relationships, and document ranking.

This showcases the full power of the knowledge graph for medical search.
"""

import intersystems_iris.dbapi._DBAPI as iris
from typing import List, Dict, Any, Set
from collections import defaultdict


def connect_aws():
    """Connect to AWS IRIS."""
    return iris.connect(
        hostname='3.84.250.46',
        port=1972,
        namespace='%SYS',
        username='_SYSTEM',
        password='SYS'
    )


def find_entities_fuzzy(conn, keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """Find entities matching any keyword (multi-token support)."""
    cursor = conn.cursor()

    all_entities = []
    seen_ids = set()

    for keyword in keywords:
        query = """
            SELECT EntityID, EntityText, EntityType, Confidence
            FROM SQLUser.Entities
            WHERE LOWER(EntityText) LIKE ?
            ORDER BY Confidence DESC
            LIMIT ?
        """

        cursor.execute(query, (f'%{keyword.lower()}%', limit))

        for entity_id, text, entity_type, confidence in cursor.fetchall():
            if entity_id not in seen_ids:
                seen_ids.add(entity_id)
                all_entities.append({
                    'id': entity_id,
                    'text': text,
                    'type': entity_type,
                    'confidence': float(confidence) if confidence else 0.0,
                    'matched_keyword': keyword
                })

    # Sort by confidence
    all_entities.sort(key=lambda x: x['confidence'], reverse=True)
    cursor.close()
    return all_entities[:limit]


def get_entity_neighbors(conn, entity_id: int) -> Dict[str, Any]:
    """Get all direct neighbors of an entity."""
    cursor = conn.cursor()

    query = """
        SELECT DISTINCT
            CASE
                WHEN r.SourceEntityID = ? THEN r.TargetEntityID
                ELSE r.SourceEntityID
            END as NeighborID,
            CASE
                WHEN r.SourceEntityID = ? THEN e2.EntityText
                ELSE e1.EntityText
            END as NeighborText,
            CASE
                WHEN r.SourceEntityID = ? THEN e2.EntityType
                ELSE e1.EntityType
            END as NeighborType,
            r.RelationshipType
        FROM SQLUser.EntityRelationships r
        JOIN SQLUser.Entities e1 ON r.SourceEntityID = e1.EntityID
        JOIN SQLUser.Entities e2 ON r.TargetEntityID = e2.EntityID
        WHERE r.SourceEntityID = ? OR r.TargetEntityID = ?
    """

    cursor.execute(query, (entity_id, entity_id, entity_id, entity_id, entity_id))

    neighbors = []
    for neighbor_id, text, entity_type, rel_type in cursor.fetchall():
        neighbors.append({
            'id': neighbor_id,
            'text': text,
            'type': entity_type,
            'relationship': rel_type
        })

    cursor.close()
    return neighbors


def find_entity_paths(conn, source_id: int, target_id: int, max_depth: int = 3) -> List[List[Dict]]:
    """Find paths between two entities (breadth-first search)."""
    cursor = conn.cursor()

    # BFS to find paths
    queue = [([source_id], set([source_id]))]
    paths = []

    for depth in range(max_depth):
        new_queue = []

        for path, visited in queue:
            current = path[-1]

            # Get neighbors
            neighbors = get_entity_neighbors(conn, current)

            for neighbor in neighbors:
                neighbor_id = neighbor['id']

                if neighbor_id == target_id:
                    # Found a path!
                    full_path = path + [neighbor_id]
                    paths.append(full_path)
                elif neighbor_id not in visited:
                    new_path = path + [neighbor_id]
                    new_visited = visited | {neighbor_id}
                    new_queue.append((new_path, new_visited))

        if paths:  # Found at least one path
            break

        queue = new_queue

    cursor.close()
    return paths


def rank_documents_by_entities(conn, entity_ids: Set[int]) -> List[Dict[str, Any]]:
    """Rank documents by how many query entities they contain."""
    cursor = conn.cursor()

    if not entity_ids:
        return []

    # Get all documents mentioning these entities
    placeholders = ','.join(['?'] * len(entity_ids))

    query = f"""
        SELECT
            e.ResourceID,
            f.FHIRResourceId,
            COUNT(DISTINCT e.EntityID) as EntityCount
        FROM SQLUser.Entities e
        JOIN SQLUser.FHIRDocuments f ON e.ResourceID = f.FHIRResourceId
        WHERE e.EntityID IN ({placeholders})
        GROUP BY e.ResourceID, f.FHIRResourceId
        ORDER BY EntityCount DESC
    """

    cursor.execute(query, list(entity_ids))

    documents = []
    for resource_id, fhir_id, entity_count in cursor.fetchall():
        documents.append({
            'resource_id': resource_id,
            'fhir_id': fhir_id,
            'entity_count': entity_count,
            'relevance_score': entity_count / len(entity_ids)
        })

    cursor.close()
    return documents


def get_entity_by_id(conn, entity_id: int) -> Dict[str, Any]:
    """Get entity details by ID."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT EntityText, EntityType, Confidence FROM SQLUser.Entities WHERE EntityID = ?",
        (entity_id,)
    )
    result = cursor.fetchone()
    cursor.close()

    if result:
        return {
            'id': entity_id,
            'text': result[0],
            'type': result[1],
            'confidence': float(result[2]) if result[2] else 0.0
        }
    return None


def advanced_query(query_text: str, top_k: int = 5):
    """Execute advanced GraphRAG query with multi-entity matching and path finding."""
    print("="*70)
    print(f"Advanced GraphRAG Query: '{query_text}'")
    print("="*70)

    conn = connect_aws()

    # Step 1: Multi-token entity matching
    keywords = [word.strip() for word in query_text.lower().split() if len(word.strip()) > 2]
    print(f"\n→ Searching for entities matching: {keywords}")

    seed_entities = find_entities_fuzzy(conn, keywords, limit=10)

    if not seed_entities:
        print(f"❌ No entities found matching '{query_text}'")
        conn.close()
        return

    print(f"✅ Found {len(seed_entities)} matching entities:")
    for ent in seed_entities[:5]:
        print(f"   - {ent['text']:30} ({ent['type']:15}) confidence: {ent['confidence']:.2f} [matched: {ent['matched_keyword']}]")

    # Step 2: Get all entities in the query's semantic neighborhood
    all_entity_ids = set()
    entity_network = defaultdict(list)

    print(f"\n→ Expanding entity network...")
    for seed in seed_entities[:3]:  # Use top 3 seeds
        neighbors = get_entity_neighbors(conn, seed['id'])
        all_entity_ids.add(seed['id'])

        for neighbor in neighbors:
            all_entity_ids.add(neighbor['id'])
            entity_network[seed['text']].append(f"{neighbor['text']} ({neighbor['type']})")

    print(f"✅ Network expansion complete:")
    print(f"   - {len(all_entity_ids)} entities in semantic neighborhood")

    # Step 3: Rank documents by entity coverage
    print(f"\n→ Ranking documents by entity relevance...")
    documents = rank_documents_by_entities(conn, all_entity_ids)

    print(f"✅ Retrieved {len(documents)} relevant documents")

    # Step 4: Display results
    print("\n" + "="*70)
    print("Advanced GraphRAG Results")
    print("="*70)

    print(f"\n📄 Top {min(top_k, len(documents))} Documents (ranked by entity coverage):")
    for i, doc in enumerate(documents[:top_k], 1):
        print(f"\n{i}. Document {doc['fhir_id']}")
        print(f"   - Contains {doc['entity_count']} query-related entities")
        print(f"   - Relevance: {doc['relevance_score']:.2%}")

    # Show entity network for top seed
    if seed_entities:
        top_seed = seed_entities[0]
        print(f"\n🔗 Entity Network for '{top_seed['text']}':")
        neighbors = entity_network.get(top_seed['text'], [])
        for i, neighbor in enumerate(neighbors[:5], 1):
            print(f"   {i}. {neighbor}")
        if len(neighbors) > 5:
            print(f"   ... and {len(neighbors) - 5} more")

    # Step 5: If multiple seed entities, show paths between them
    if len(seed_entities) >= 2:
        print(f"\n🛤️  Entity Relationships:")
        entity1 = seed_entities[0]
        entity2 = seed_entities[1]

        print(f"\n   Finding paths: '{entity1['text']}' ↔ '{entity2['text']}'")
        paths = find_entity_paths(conn, entity1['id'], entity2['id'], max_depth=2)

        if paths:
            print(f"   ✅ Found {len(paths)} path(s)")
            # Show first path in detail
            path = paths[0]
            print(f"\n   Shortest path ({len(path) - 1} hop{'s' if len(path) > 2 else ''}):")
            for i, entity_id in enumerate(path):
                entity = get_entity_by_id(conn, entity_id)
                if entity:
                    indent = "   " + "  " * i
                    print(f"{indent}→ {entity['text']} ({entity['type']})")
        else:
            print(f"   ⚠️  No direct path found (entities may be in separate documents)")

    conn.close()

    print("\n" + "="*70)
    print("✅ Advanced GraphRAG Query Complete")
    print("="*70)
    print(f"\nThis query demonstrated:")
    print(f"  ✓ Multi-token entity matching")
    print(f"  ✓ Semantic neighborhood expansion")
    print(f"  ✓ Document ranking by entity coverage")
    print(f"  ✓ Entity relationship path finding")


def main():
    """Test various advanced GraphRAG queries."""

    queries = [
        ("chest pain", 5),
        ("respiratory infection", 3),
        ("fever vomiting", 5),
        ("abdominal discomfort", 3),
    ]

    for query_text, top_k in queries:
        try:
            advanced_query(query_text, top_k=top_k)
            print("\n" + "="*70 + "\n")
        except Exception as e:
            print(f"❌ Query failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
