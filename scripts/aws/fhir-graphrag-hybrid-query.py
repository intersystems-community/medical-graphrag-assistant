#!/usr/bin/env python3
"""
Hybrid FHIR + GraphRAG Query System

Uses LLM to generate structured FHIR queries from natural language,
executes them against the FHIR repository, and integrates results
with GraphRAG knowledge graph traversal.

Architecture:
1. Natural language query → LLM → Structured FHIR query
2. Execute FHIR query against HSFHIR_X0001_R.Rsrc (native FHIR storage)
3. Execute GraphRAG entity search
4. Fusion: Combine and rank results from both sources
"""

import intersystems_iris.dbapi._DBAPI as iris
from typing import List, Dict, Any, Set, Optional
import json
import os
import requests
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


def get_nvidia_api_key():
    """Get NVIDIA API key from environment or file."""
    # Try environment variable first
    api_key = os.getenv('NVIDIA_API_KEY')

    if not api_key:
        # Try reading from file
        key_file = os.path.expanduser('~/.nvidia_api_key')
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                api_key = f.read().strip()

    return api_key


def generate_fhir_query_with_llm(natural_query: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Use NVIDIA NIM LLM to generate structured FHIR query from natural language.

    Returns:
        {
            'resource_type': 'DocumentReference',
            'filters': {
                'status': 'current',
                'type': 'clinical-note',
                'content_search': 'chest pain'
            },
            'explanation': 'Searching for current clinical notes mentioning chest pain'
        }
    """
    if not api_key:
        # Fallback to rule-based query generation
        return generate_fhir_query_rule_based(natural_query)

    # Use NVIDIA NIM to generate structured query
    prompt = f"""You are a FHIR query expert. Convert this natural language query into a structured FHIR search.

Natural Query: "{natural_query}"

Available FHIR Resources:
- DocumentReference: Clinical notes, reports, documents
- Patient: Patient demographics
- Observation: Lab results, vital signs, clinical observations
- Condition: Diagnoses, problems
- Medication: Medication orders and administrations

Generate a JSON response with:
{{
  "resource_type": "DocumentReference",
  "filters": {{
    "content_search": "relevant search terms",
    "status": "current",
    "date_range": {{"start": "2024-01-01", "end": "2024-12-31"}} (if date mentioned)
  }},
  "explanation": "Brief explanation of the query strategy"
}}

Respond ONLY with valid JSON, no markdown formatting."""

    try:
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nvidia/llama-3.1-nemotron-70b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 500
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()

            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]

            return json.loads(content)
        else:
            print(f"⚠️  LLM API error: {response.status_code}, falling back to rule-based")
            return generate_fhir_query_rule_based(natural_query)

    except Exception as e:
        print(f"⚠️  LLM generation failed: {e}, falling back to rule-based")
        return generate_fhir_query_rule_based(natural_query)


def generate_fhir_query_rule_based(natural_query: str) -> Dict[str, Any]:
    """Fallback rule-based FHIR query generation."""
    query_lower = natural_query.lower()

    # Detect resource type
    resource_type = "DocumentReference"  # Default to clinical notes

    if any(word in query_lower for word in ['lab', 'test', 'result', 'observation']):
        resource_type = "Observation"
    elif any(word in query_lower for word in ['diagnosis', 'condition', 'disease']):
        resource_type = "Condition"
    elif any(word in query_lower for word in ['medication', 'drug', 'prescription']):
        resource_type = "Medication"
    elif any(word in query_lower for word in ['patient', 'demographic']):
        resource_type = "Patient"

    return {
        'resource_type': resource_type,
        'filters': {
            'content_search': natural_query,
            'status': 'current'
        },
        'explanation': f'Rule-based: Searching {resource_type} resources for "{natural_query}"'
    }


def execute_fhir_query(conn, fhir_query: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Execute structured FHIR query against migrated FHIR documents.

    Queries SQLUser.FHIRDocuments table which contains DocumentReference resources.
    """
    cursor = conn.cursor()

    resource_type = fhir_query['resource_type']
    filters = fhir_query.get('filters', {})
    content_search = filters.get('content_search', '')

    # Build SQL query
    # SQLUser.FHIRDocuments contains: FHIRResourceId, ResourceType, ResourceString (JSON)

    if resource_type == "DocumentReference":
        # Search clinical notes in DocumentReference resources
        # Decode hex-encoded clinical notes for text search
        sql = """
            SELECT TOP ?
                FHIRResourceId,
                ResourceType,
                ResourceString
            FROM SQLUser.FHIRDocuments
            WHERE ResourceType = 'DocumentReference'
        """

        cursor.execute(sql, (limit * 3,))  # Get more, will filter in Python

        search_terms = content_search.lower().split()

        results = []
        for fhir_id, resource_type, resource_string in cursor.fetchall():
            try:
                # Parse FHIR JSON
                resource_json = json.loads(resource_string)

                # Extract and decode clinical note
                clinical_note = None
                if 'content' in resource_json:
                    try:
                        encoded_data = resource_json['content'][0]['attachment']['data']
                        clinical_note = bytes.fromhex(encoded_data).decode('utf-8')
                    except:
                        pass

                # Filter by search terms
                if clinical_note and search_terms:
                    clinical_note_lower = clinical_note.lower()
                    # Check if any search term appears in clinical note
                    if any(term in clinical_note_lower for term in search_terms):
                        results.append({
                            'fhir_id': fhir_id,
                            'resource_type': resource_type,
                            'resource_json': resource_json,
                            'clinical_note': clinical_note[:500],  # Preview
                            'source': 'fhir_repository'
                        })

                        if len(results) >= limit:
                            break
                elif not search_terms:
                    # No search terms, return all
                    results.append({
                        'fhir_id': fhir_id,
                        'resource_type': resource_type,
                        'resource_json': resource_json,
                        'clinical_note': clinical_note[:500] if clinical_note else None,
                        'source': 'fhir_repository'
                    })

                    if len(results) >= limit:
                        break

            except (json.JSONDecodeError, KeyError) as e:
                pass

        cursor.close()
        return results

    else:
        # For other resource types, just query the table
        sql = """
            SELECT TOP ?
                FHIRResourceId,
                ResourceType,
                ResourceString
            FROM SQLUser.FHIRDocuments
            WHERE ResourceType = ?
        """
        cursor.execute(sql, (limit, resource_type))

        results = []
        for fhir_id, resource_type, resource_string in cursor.fetchall():
            try:
                resource_json = json.loads(resource_string)
                results.append({
                    'fhir_id': fhir_id,
                    'resource_type': resource_type,
                    'resource_json': resource_json,
                    'clinical_note': None,
                    'source': 'fhir_repository'
                })
            except json.JSONDecodeError:
                pass

        cursor.close()
        return results


def find_entities_fuzzy(conn, keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """Find entities in knowledge graph matching keywords."""
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

    all_entities.sort(key=lambda x: x['confidence'], reverse=True)
    cursor.close()
    return all_entities[:limit]


def get_documents_for_entities(conn, entity_ids: Set[int]) -> List[Dict[str, Any]]:
    """Get FHIR documents referenced by knowledge graph entities."""
    if not entity_ids:
        return []

    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(entity_ids))

    query = f"""
        SELECT DISTINCT
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
            'source': 'knowledge_graph'
        })

    cursor.close()
    return documents


def fuse_results(fhir_results: List[Dict], graphrag_results: List[Dict]) -> List[Dict[str, Any]]:
    """
    Fuse results from FHIR repository and GraphRAG knowledge graph.

    Uses Reciprocal Rank Fusion (RRF) to combine rankings.
    """
    k = 60  # RRF constant

    # Build score map
    score_map = defaultdict(lambda: {'fhir_rank': None, 'graph_rank': None, 'sources': set()})

    # Add FHIR results
    for rank, result in enumerate(fhir_results, 1):
        key = result.get('resource_key') or result.get('fhir_id')
        if key:
            score_map[key]['fhir_rank'] = rank
            score_map[key]['fhir_result'] = result
            score_map[key]['sources'].add('fhir_repository')

    # Add GraphRAG results
    for rank, result in enumerate(graphrag_results, 1):
        key = result['fhir_id']
        score_map[key]['graph_rank'] = rank
        score_map[key]['graph_result'] = result
        score_map[key]['sources'].add('knowledge_graph')

    # Calculate RRF scores
    fused = []
    for key, data in score_map.items():
        rrf_score = 0.0

        if data['fhir_rank']:
            rrf_score += 1.0 / (k + data['fhir_rank'])

        if data['graph_rank']:
            rrf_score += 1.0 / (k + data['graph_rank'])

        # Combine result data
        result = {
            'key': key,
            'rrf_score': rrf_score,
            'sources': list(data['sources']),
            'fhir_rank': data['fhir_rank'],
            'graph_rank': data['graph_rank']
        }

        # Add result details
        if 'fhir_result' in data:
            result.update(data['fhir_result'])
        if 'graph_result' in data:
            result['entity_count'] = data['graph_result'].get('entity_count')

        fused.append(result)

    # Sort by RRF score
    fused.sort(key=lambda x: x['rrf_score'], reverse=True)

    return fused


def hybrid_query(natural_query: str, top_k: int = 5, use_llm: bool = True):
    """
    Execute hybrid FHIR + GraphRAG query.

    Steps:
    1. Generate structured FHIR query (with LLM or rules)
    2. Execute FHIR repository search
    3. Execute GraphRAG entity search
    4. Fuse and rank results
    """
    print("="*70)
    print(f"Hybrid FHIR + GraphRAG Query: '{natural_query}'")
    print("="*70)

    conn = connect_aws()
    api_key = get_nvidia_api_key() if use_llm else None

    # Step 1: Generate FHIR query
    print(f"\n→ Generating structured FHIR query...")
    if use_llm and api_key:
        print(f"   Using NVIDIA NIM LLM (llama-3.1-nemotron-70b-instruct)")
    else:
        print(f"   Using rule-based query generation")

    fhir_query = generate_fhir_query_with_llm(natural_query, api_key)

    print(f"✅ FHIR Query Generated:")
    print(f"   - Resource Type: {fhir_query['resource_type']}")
    print(f"   - Search Terms: {fhir_query['filters'].get('content_search')}")
    print(f"   - Strategy: {fhir_query['explanation']}")

    # Step 2: Execute FHIR repository search
    print(f"\n→ Searching FHIR repository (SQLUser.FHIRDocuments)...")
    fhir_results = execute_fhir_query(conn, fhir_query, limit=top_k * 2)
    print(f"✅ Found {len(fhir_results)} FHIR resources")

    # Step 3: Execute GraphRAG entity search
    print(f"\n→ Searching knowledge graph entities...")
    keywords = [w.strip() for w in natural_query.lower().split() if len(w.strip()) > 2]
    seed_entities = find_entities_fuzzy(conn, keywords, limit=5)

    print(f"✅ Found {len(seed_entities)} matching entities:")
    for ent in seed_entities[:3]:
        print(f"   - {ent['text']:25} ({ent['type']:15}) confidence: {ent['confidence']:.2f}")

    # Get documents for entities
    entity_ids = {e['id'] for e in seed_entities}
    graphrag_results = get_documents_for_entities(conn, entity_ids)
    print(f"✅ Found {len(graphrag_results)} documents via knowledge graph")

    # Step 4: Fuse results
    print(f"\n→ Fusing results with Reciprocal Rank Fusion...")
    fused_results = fuse_results(fhir_results, graphrag_results)
    print(f"✅ Generated unified ranking of {len(fused_results)} unique documents")

    # Display results
    print("\n" + "="*70)
    print("Hybrid Search Results (FHIR + GraphRAG)")
    print("="*70)

    for i, result in enumerate(fused_results[:top_k], 1):
        print(f"\n{i}. Document: {result.get('fhir_id') or result.get('resource_key')}")
        print(f"   RRF Score: {result['rrf_score']:.4f}")
        print(f"   Sources: {', '.join(result['sources'])}")

        if result.get('fhir_rank'):
            print(f"   FHIR Rank: #{result['fhir_rank']}")
        if result.get('graph_rank'):
            print(f"   Graph Rank: #{result['graph_rank']} ({result.get('entity_count', 0)} entities)")

        # Show clinical note preview if available
        if result.get('clinical_note'):
            preview = result['clinical_note'][:150].replace('\n', ' ')
            print(f"   Preview: {preview}...")

    conn.close()

    print("\n" + "="*70)
    print("✅ Hybrid Query Complete")
    print("="*70)
    print(f"\nQuery combined:")
    print(f"  ✓ Direct FHIR repository search (native storage)")
    print(f"  ✓ Knowledge graph entity matching")
    print(f"  ✓ Reciprocal Rank Fusion for unified ranking")
    if use_llm and api_key:
        print(f"  ✓ LLM-generated FHIR query strategy")


def main():
    """Test hybrid FHIR + GraphRAG queries."""

    # Check for NVIDIA API key
    api_key = get_nvidia_api_key()
    use_llm = api_key is not None

    if not use_llm:
        print("⚠️  NVIDIA_API_KEY not found, using rule-based query generation")
        print("   Set NVIDIA_API_KEY environment variable for LLM-powered queries\n")
    else:
        print(f"✅ NVIDIA API key found, using LLM for query generation\n")

    queries = [
        ("chest pain and breathing difficulty", 5),
        ("fever and vomiting", 3),
        ("respiratory infection", 5),
        ("abdominal discomfort", 3),
    ]

    for query_text, top_k in queries:
        try:
            hybrid_query(query_text, top_k=top_k, use_llm=use_llm)
            print("\n" + "="*70 + "\n")
        except Exception as e:
            print(f"❌ Query failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
