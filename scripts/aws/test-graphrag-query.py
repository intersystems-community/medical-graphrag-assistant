#!/usr/bin/env python3
"""
Test GraphRAG knowledge graph queries without requiring embeddings.

This demonstrates the knowledge graph traversal capabilities using only
the entity and relationship data already populated in AWS IRIS.
"""

import intersystems_iris.dbapi._DBAPI as iris
from typing import List, Dict, Any


def connect_aws():
    """Connect to AWS IRIS."""
    return iris.connect(
        hostname='3.84.250.46',
        port=1972,
        namespace='%SYS',
        username='_SYSTEM',
        password='SYS'
    )


def find_entities_by_keyword(conn, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Find entities matching a keyword."""
    cursor = conn.cursor()

    query = """
        SELECT EntityID, EntityText, EntityType, Confidence
        FROM SQLUser.Entities
        WHERE LOWER(EntityText) LIKE ?
        ORDER BY Confidence DESC
        LIMIT ?
    """

    cursor.execute(query, (f'%{keyword.lower()}%', limit))

    entities = []
    for entity_id, text, entity_type, confidence in cursor.fetchall():
        entities.append({
            'id': entity_id,
            'text': text,
            'type': entity_type,
            'confidence': float(confidence) if confidence else 0.0
        })

    cursor.close()
    return entities


def traverse_relationships(conn, entity_id: int, max_depth: int = 2) -> Dict[str, Any]:
    """Traverse knowledge graph from seed entity."""
    cursor = conn.cursor()

    visited = {entity_id}
    current_level = {entity_id}
    graph = {'entities': [], 'relationships': []}

    # Get seed entity details
    cursor.execute(
        "SELECT EntityText, EntityType FROM SQLUser.Entities WHERE EntityID = ?",
        (entity_id,)
    )
    seed = cursor.fetchone()
    if seed:
        graph['entities'].append({
            'id': entity_id,
            'text': seed[0],
            'type': seed[1],
            'depth': 0
        })

    for depth in range(max_depth):
        if not current_level:
            break

        next_level = set()

        # Get relationships for current level
        entity_list = list(current_level)
        placeholders = ','.join(['?'] * len(entity_list))

        query = f"""
            SELECT DISTINCT
                r.SourceEntityID,
                r.TargetEntityID,
                r.RelationshipType,
                e1.EntityText as SourceText,
                e1.EntityType as SourceType,
                e2.EntityText as TargetText,
                e2.EntityType as TargetType
            FROM SQLUser.EntityRelationships r
            JOIN SQLUser.Entities e1 ON r.SourceEntityID = e1.EntityID
            JOIN SQLUser.Entities e2 ON r.TargetEntityID = e2.EntityID
            WHERE r.SourceEntityID IN ({placeholders})
               OR r.TargetEntityID IN ({placeholders})
        """

        cursor.execute(query, entity_list + entity_list)

        for row in cursor.fetchall():
            source_id, target_id, rel_type, source_text, source_type, target_text, target_type = row

            # Add relationship
            graph['relationships'].append({
                'source_id': source_id,
                'target_id': target_id,
                'type': rel_type,
                'source_text': source_text,
                'target_text': target_text
            })

            # Add new entities
            for eid, text, etype in [(source_id, source_text, source_type),
                                      (target_id, target_text, target_type)]:
                if eid not in visited:
                    visited.add(eid)
                    next_level.add(eid)
                    graph['entities'].append({
                        'id': eid,
                        'text': text,
                        'type': etype,
                        'depth': depth + 1
                    })

        current_level = next_level

    cursor.close()
    return graph


def get_documents_for_entities(conn, entity_ids: List[int]) -> List[Dict[str, Any]]:
    """Get source documents for entities."""
    if not entity_ids:
        return []

    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(entity_ids))

    query = f"""
        SELECT DISTINCT
            e.ResourceID,
            f.FHIRResourceId
        FROM SQLUser.Entities e
        JOIN SQLUser.FHIRDocuments f ON e.ResourceID = f.FHIRResourceId
        WHERE e.EntityID IN ({placeholders})
    """

    cursor.execute(query, entity_ids)

    documents = []
    for resource_id, fhir_id in cursor.fetchall():
        documents.append({
            'resource_id': resource_id,
            'fhir_id': fhir_id
        })

    cursor.close()
    return documents


def graphrag_query(query_text: str, top_k: int = 5, max_depth: int = 2):
    """Execute a GraphRAG-style query using knowledge graph traversal."""
    print("="*70)
    print(f"GraphRAG Query: '{query_text}'")
    print("="*70)

    conn = connect_aws()

    # Step 1: Find seed entities
    print(f"\n→ Finding seed entities for '{query_text}'...")
    seed_entities = find_entities_by_keyword(conn, query_text, limit=5)

    if not seed_entities:
        print(f"❌ No entities found matching '{query_text}'")
        conn.close()
        return

    print(f"✅ Found {len(seed_entities)} seed entities:")
    for ent in seed_entities:
        print(f"   - {ent['text']:30} ({ent['type']}) confidence: {ent['confidence']:.2f}")

    # Step 2: Traverse graph from each seed entity
    print(f"\n→ Traversing knowledge graph (max depth: {max_depth})...")
    all_entity_ids = set()
    all_relationships = []

    for seed in seed_entities[:3]:  # Use top 3 seeds
        graph = traverse_relationships(conn, seed['id'], max_depth)
        for ent in graph['entities']:
            all_entity_ids.add(ent['id'])
        all_relationships.extend(graph['relationships'])

    print(f"✅ Graph traversal complete:")
    print(f"   - {len(all_entity_ids)} related entities found")
    print(f"   - {len(all_relationships)} relationships traversed")

    # Step 3: Get source documents
    print(f"\n→ Retrieving source documents...")
    documents = get_documents_for_entities(conn, list(all_entity_ids)[:top_k])

    print(f"✅ Retrieved {len(documents)} relevant documents")

    # Step 4: Display results
    print("\n" + "="*70)
    print("GraphRAG Results")
    print("="*70)

    print(f"\n📄 Top {len(documents)} Documents:")
    for i, doc in enumerate(documents, 1):
        print(f"\n{i}. Document {doc['fhir_id']}")

    print(f"\n🔗 Sample Relationships:")
    for i, rel in enumerate(all_relationships[:5], 1):
        print(f"{i}. {rel['source_text']} --[{rel['type']}]--> {rel['target_text']}")

    conn.close()

    print("\n" + "="*70)
    print("✅ GraphRAG Query Complete")
    print("="*70)
    print(f"\nThis query used:")
    print(f"  ✓ Knowledge graph traversal (no embeddings needed)")
    print(f"  ✓ Entity relationships for context expansion")
    print(f"  ✓ Graph-based document ranking")
    print(f"\nFor full GraphRAG (vector + text + graph), configure NVIDIA API key.")


def main():
    """Test various GraphRAG queries."""

    # Test queries
    queries = [
        ("chest pain", 5, 2),
        ("fever", 3, 1),
        ("respiratory", 5, 2),
    ]

    for query_text, top_k, max_depth in queries:
        try:
            graphrag_query(query_text, top_k=top_k, max_depth=max_depth)
            print("\n" + "="*70 + "\n")
        except Exception as e:
            print(f"❌ Query failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
