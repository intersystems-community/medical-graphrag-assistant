#!/usr/bin/env python3
"""
Extract medical entities from migrated FHIR documents on AWS IRIS
and populate SQLUser.Entities and SQLUser.EntityRelationships tables

This script:
1. Reads 51 DocumentReferences from SQLUser.FHIRDocuments on AWS
2. Extracts medical entities (SYMPTOM, CONDITION, MEDICATION, etc.)
3. Generates 1024-dim embeddings for entities using NVIDIA NIM
4. Stores entities and relationships in knowledge graph tables
"""

import os
import sys
import json
import intersystems_iris.dbapi._DBAPI as iris
from typing import List, Dict, Any, Tuple
import requests
import re
from datetime import datetime

# Configuration
AWS_CONFIG = {
    'host': '3.84.250.46',
    'port': 1972,
    'namespace': '%SYS',
    'username': '_SYSTEM',
    'password': 'SYS'
}

NVIDIA_NIM_CONFIG = {
    'base_url': 'https://integrate.api.nvidia.com/v1',
    'api_key': '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',
    'model': 'nvidia/nv-embedqa-e5-v5',
    'dimension': 1024
}

# Medical entity patterns (same as local implementation)
ENTITY_PATTERNS = {
    'SYMPTOM': [
        r'\b(pain|ache|soreness|discomfort|tenderness)\b',
        r'\b(fever|chills|sweating)\b',
        r'\b(nausea|vomiting|diarrhea)\b',
        r'\b(cough|wheeze|dyspnea|shortness of breath|SOB)\b',
        r'\b(fatigue|weakness|malaise)\b',
        r'\b(dizziness|vertigo|lightheadedness)\b',
        r'\b(headache|migraine)\b',
        r'\b(rash|lesion|swelling|edema)\b',
    ],
    'CONDITION': [
        r'\b(hypertension|HTN|high blood pressure)\b',
        r'\b(diabetes|DM|hyperglycemia)\b',
        r'\b(coronary artery disease|CAD|heart disease)\b',
        r'\b(COPD|emphysema|chronic bronchitis)\b',
        r'\b(asthma|reactive airway disease)\b',
        r'\b(arthritis|osteoarthritis|RA)\b',
        r'\b(depression|anxiety|PTSD)\b',
        r'\b(obesity|overweight)\b',
        r'\b(atrial fibrillation|AFib|AF)\b',
        r'\b(CHF|heart failure|congestive heart failure)\b',
    ],
    'MEDICATION': [
        r'\b(aspirin|ASA)\b',
        r'\b(metformin|glucophage)\b',
        r'\b(lisinopril|ACE inhibitor)\b',
        r'\b(atorvastatin|statin|lipitor)\b',
        r'\b(metoprolol|beta blocker)\b',
        r'\b(albuterol|inhaler|bronchodilator)\b',
        r'\b(ibuprofen|advil|NSAID)\b',
        r'\b(warfarin|coumadin|anticoagulant)\b',
    ],
    'PROCEDURE': [
        r'\b(catheterization|cath)\b',
        r'\b(angiography|angiogram)\b',
        r'\b(echocardiogram|echo|TTE)\b',
        r'\b(CT scan|computed tomography)\b',
        r'\b(MRI|magnetic resonance)\b',
        r'\b(X-ray|radiograph)\b',
        r'\b(biopsy|tissue sample)\b',
        r'\b(surgery|surgical procedure|operation)\b',
    ],
    'BODY_PART': [
        r'\b(chest|thorax|thoracic)\b',
        r'\b(heart|cardiac|coronary)\b',
        r'\b(lung|pulmonary|respiratory)\b',
        r'\b(abdomen|abdominal|belly)\b',
        r'\b(head|cranial|cephalic)\b',
        r'\b(arm|leg|limb|extremity)\b',
        r'\b(back|spine|spinal)\b',
        r'\b(neck|cervical)\b',
    ],
    'TEMPORAL': [
        r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD
        r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # MM/DD/YYYY
        r'\b(today|yesterday|last week|last month)\b',
        r'\b(currently|previously|prior to|after|before)\b',
        r'\b(acute|chronic|recent|ongoing)\b',
    ],
}


def get_nvidia_nim_embedding(text: str) -> List[float]:
    """Get 1024-dim embedding from NVIDIA Hosted NIM API."""
    url = f"{NVIDIA_NIM_CONFIG['base_url']}/embeddings"

    payload = {
        "input": [text],
        "model": NVIDIA_NIM_CONFIG['model'],
        "input_type": "passage",
        "encoding_format": "float"
    }

    headers = {
        "Authorization": f"Bearer {NVIDIA_NIM_CONFIG['api_key']}",
        "accept": "application/json",
        "content-type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()

        embedding = result['data'][0]['embedding']
        assert len(embedding) == NVIDIA_NIM_CONFIG['dimension'], \
            f"Expected {NVIDIA_NIM_CONFIG['dimension']}-dim, got {len(embedding)}-dim"

        return embedding
    except Exception as e:
        print(f"⚠️  NVIDIA NIM API error: {e}")
        raise


def extract_entities(text: str) -> List[Tuple[str, str, float]]:
    """Extract medical entities from text using regex patterns."""
    entities = []
    text_lower = text.lower()

    for entity_type, patterns in ENTITY_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity_text = match.group(0)
                # Confidence based on pattern specificity
                confidence = 0.85 if len(entity_text) > 5 else 0.75
                entities.append((entity_text, entity_type, confidence))

    # Deduplicate entities
    seen = set()
    unique_entities = []
    for entity_text, entity_type, confidence in entities:
        key = (entity_text.lower(), entity_type)
        if key not in seen:
            seen.add(key)
            unique_entities.append((entity_text, entity_type, confidence))

    return unique_entities


def extract_relationships(entities: List[Tuple[str, str, float]]) -> List[Tuple[str, str, str, float]]:
    """Extract relationships between entities."""
    relationships = []

    # Simple co-occurrence relationships
    for i, (entity1, type1, conf1) in enumerate(entities):
        for entity2, type2, conf2 in entities[i+1:]:
            if type1 != type2:  # Don't relate entities of same type
                # All co-occurring entities get CO_OCCURS_WITH
                confidence = min(conf1, conf2)
                relationships.append((entity1, entity2, 'CO_OCCURS_WITH', confidence))

    return relationships


def load_fhir_documents() -> List[Dict[str, Any]]:
    """Load FHIR documents from AWS IRIS."""
    print("\n" + "="*70)
    print("Step 1: Load FHIR Documents from AWS IRIS")
    print("="*70)

    conn = iris.connect(
        hostname=AWS_CONFIG['host'],
        port=AWS_CONFIG['port'],
        namespace=AWS_CONFIG['namespace'],
        username=AWS_CONFIG['username'],
        password=AWS_CONFIG['password']
    )

    cursor = conn.cursor()

    query = """
        SELECT ID, FHIRResourceId, ResourceString
        FROM SQLUser.FHIRDocuments
        ORDER BY ID
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    documents = []
    for row in rows:
        aws_id = row[0]
        fhir_id = row[1]
        resource_string = row[2]

        try:
            fhir_json = json.loads(resource_string)

            # Extract text content from base64-encoded data
            text = ""
            if 'content' in fhir_json and len(fhir_json['content']) > 0:
                content = fhir_json['content'][0]
                if 'attachment' in content:
                    attachment = content['attachment']

                    # Decode hex data if present (FHIR stores clinical notes as hex)
                    if 'data' in attachment:
                        try:
                            decoded_bytes = bytes.fromhex(attachment['data'])
                            text = decoded_bytes.decode('utf-8')
                        except Exception as e:
                            print(f"⚠️  Failed to decode hex for {fhir_id}: {e}")
                            text = attachment.get('title', attachment.get('contentType', ''))
                    else:
                        text = attachment.get('title', attachment.get('contentType', ''))

            if not text and 'description' in fhir_json:
                text = fhir_json['description']
            elif not text and 'type' in fhir_json and 'text' in fhir_json['type']:
                text = fhir_json['type']['text']

            if not text:
                text = f"DocumentReference {fhir_id}"

            documents.append({
                'aws_id': aws_id,
                'fhir_id': fhir_id,
                'text': text,
                'fhir_json': fhir_json
            })
        except json.JSONDecodeError:
            print(f"⚠️  Skipping resource {fhir_id}: Invalid JSON")
            continue

    cursor.close()
    conn.close()

    print(f"✅ Loaded {len(documents)} FHIR documents")
    return documents


def create_knowledge_graph(documents: List[Dict[str, Any]]):
    """Extract entities and relationships, store in knowledge graph tables."""
    print("\n" + "="*70)
    print("Step 2: Extract Entities and Build Knowledge Graph")
    print("="*70)

    conn = iris.connect(
        hostname=AWS_CONFIG['host'],
        port=AWS_CONFIG['port'],
        namespace=AWS_CONFIG['namespace'],
        username=AWS_CONFIG['username'],
        password=AWS_CONFIG['password']
    )

    cursor = conn.cursor()

    # Clear existing entities and relationships
    print("\n→ Clearing existing knowledge graph...")
    cursor.execute("DELETE FROM SQLUser.Entities")
    cursor.execute("DELETE FROM SQLUser.EntityRelationships")
    conn.commit()
    print("✅ Knowledge graph cleared")

    # Track unique entities globally with source document
    global_entities = {}  # {entity_text: (entity_type, confidence, embedding, resource_id)}
    all_relationships = []  # (source_key, target_key, rel_type, confidence, resource_id)

    # Extract from each document
    for i, doc in enumerate(documents, 1):
        entities = extract_entities(doc['text'])
        relationships = extract_relationships(entities)

        # Add entities to global collection
        for entity_text, entity_type, confidence in entities:
            key = entity_text.lower()
            if key not in global_entities:
                # Generate embedding for entity
                try:
                    embedding = get_nvidia_nim_embedding(entity_text)
                    global_entities[key] = (entity_text, entity_type, confidence, embedding, doc['fhir_id'])
                except Exception as e:
                    print(f"⚠️  Failed to embed entity '{entity_text}': {e}")
                    continue

        # Add relationships with source document ID
        for source, target, rel_type, confidence in relationships:
            all_relationships.append((source.lower(), target.lower(), rel_type, confidence, doc['fhir_id']))

        if i % 10 == 0:
            print(f"   Processed {i}/{len(documents)} documents...")

    print(f"\n✅ Extracted {len(global_entities)} unique entities")
    print(f"✅ Extracted {len(all_relationships)} relationships")

    # Insert entities
    print("\n→ Storing entities in SQLUser.Entities...")
    entity_insert_sql = """
        INSERT INTO SQLUser.Entities
        (EntityText, EntityType, ResourceID, Confidence, EmbeddingVector, ExtractedAt)
        VALUES (?, ?, ?, ?, TO_VECTOR(?), ?)
    """

    entity_count = 0
    for entity_text, entity_type, confidence, embedding, resource_id in global_entities.values():
        embedding_str = f"[{','.join(map(str, embedding))}]"
        cursor.execute(entity_insert_sql, (
            entity_text,
            entity_type,
            resource_id,
            confidence,
            embedding_str,
            datetime.now()
        ))
        entity_count += 1

        if entity_count % 50 == 0:
            print(f"   Stored {entity_count}/{len(global_entities)} entities...")
            conn.commit()

    conn.commit()
    print(f"✅ Stored {entity_count} entities")

    # Build entity text -> ID mapping
    print("\n→ Building entity ID mapping...")
    entity_id_map = {}
    cursor.execute("SELECT EntityID, EntityText FROM SQLUser.Entities")
    for entity_id, entity_text in cursor.fetchall():
        entity_id_map[entity_text.lower()] = entity_id
    print(f"✅ Mapped {len(entity_id_map)} entities")

    # Insert relationships using entity IDs
    print("\n→ Storing relationships in SQLUser.EntityRelationships...")
    relationship_insert_sql = """
        INSERT INTO SQLUser.EntityRelationships
        (SourceEntityID, TargetEntityID, RelationshipType, ResourceID, Confidence, ExtractedAt)
        VALUES (?, ?, ?, ?, ?, ?)
    """

    rel_count = 0
    skipped_count = 0
    for source, target, rel_type, confidence, resource_id in all_relationships:
        # Get original entity text from global_entities
        source_text = global_entities.get(source, (source,))[0]
        target_text = global_entities.get(target, (target,))[0]

        # Look up entity IDs
        source_id = entity_id_map.get(source_text.lower())
        target_id = entity_id_map.get(target_text.lower())

        if source_id and target_id:
            cursor.execute(relationship_insert_sql, (
                source_id,
                target_id,
                rel_type,
                resource_id,
                confidence,
                datetime.now()
            ))
            rel_count += 1

            if rel_count % 50 == 0:
                print(f"   Stored {rel_count}/{len(all_relationships)} relationships...")
                conn.commit()
        else:
            skipped_count += 1

    conn.commit()
    print(f"✅ Stored {rel_count} relationships")
    if skipped_count > 0:
        print(f"⚠️  Skipped {skipped_count} relationships (entities not found)")

    cursor.close()
    conn.close()


def verify_knowledge_graph():
    """Verify knowledge graph was created successfully."""
    print("\n" + "="*70)
    print("Step 3: Verify Knowledge Graph")
    print("="*70)

    conn = iris.connect(
        hostname=AWS_CONFIG['host'],
        port=AWS_CONFIG['port'],
        namespace=AWS_CONFIG['namespace'],
        username=AWS_CONFIG['username'],
        password=AWS_CONFIG['password']
    )

    cursor = conn.cursor()

    # Count entities by type
    cursor.execute("""
        SELECT EntityType, COUNT(*) as EntityCount
        FROM SQLUser.Entities
        GROUP BY EntityType
        ORDER BY EntityCount DESC
    """)
    entity_counts = cursor.fetchall()

    print("\n✅ Entity counts by type:")
    total_entities = 0
    for entity_type, count in entity_counts:
        print(f"   {entity_type:15} : {count:4} entities")
        total_entities += count

    # Count relationships by type
    cursor.execute("""
        SELECT RelationshipType, COUNT(*) as RelCount
        FROM SQLUser.EntityRelationships
        GROUP BY RelationshipType
        ORDER BY RelCount DESC
    """)
    rel_counts = cursor.fetchall()

    print("\n✅ Relationship counts by type:")
    total_relationships = 0
    for rel_type, count in rel_counts:
        print(f"   {rel_type:20} : {count:4} relationships")
        total_relationships += count

    # Sample entities
    cursor.execute("""
        SELECT TOP 5 EntityText, EntityType, Confidence
        FROM SQLUser.Entities
        ORDER BY Confidence DESC
    """)
    samples = cursor.fetchall()

    print("\n✅ Sample high-confidence entities:")
    for entity_text, entity_type, confidence in samples:
        try:
            conf_val = float(confidence)
            print(f"   {entity_text:30} ({entity_type}) - {conf_val:.2f}")
        except (ValueError, TypeError):
            print(f"   {entity_text:30} ({entity_type}) - {confidence}")

    cursor.close()
    conn.close()

    print("\n" + "="*70)
    print("✅ Knowledge Graph Complete!")
    print("="*70)
    print(f"Total entities: {total_entities}")
    print(f"Total relationships: {total_relationships}")
    print(f"Vector dimension: 1024 (NVIDIA NIM)")


def main():
    """Main entity extraction workflow."""
    print("="*70)
    print("FHIR GraphRAG: Entity Extraction on AWS")
    print("NVIDIA NIM Embeddings (1024-dim)")
    print("="*70)

    try:
        # Step 1: Load FHIR documents
        documents = load_fhir_documents()

        # Step 2: Extract entities and build knowledge graph
        create_knowledge_graph(documents)

        # Step 3: Verify
        verify_knowledge_graph()

        return 0

    except Exception as e:
        print(f"\n❌ Entity extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
