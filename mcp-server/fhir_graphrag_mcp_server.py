#!/usr/bin/env python3
"""
FHIR + GraphRAG MCP Server

Model Context Protocol (MCP) server exposing FHIR repository search,
GraphRAG knowledge graph queries, and medical data visualization tools
for AI-powered medical chat applications.

Tools provided:
- search_fhir_documents: Full-text search of FHIR DocumentReference resources
- search_knowledge_graph: Entity-based search through medical knowledge graph
- hybrid_search: Combined FHIR + GraphRAG search with RRF fusion
- get_entity_relationships: Traverse knowledge graph from seed entities
- get_document_details: Retrieve full FHIR document with decoded clinical notes
- get_entity_statistics: Knowledge graph statistics and entity distribution
- plot_entity_distribution: Generate entity type distribution chart data
- plot_patient_timeline: Generate patient encounter timeline chart data
- plot_symptom_frequency: Generate symptom frequency bar chart data
- plot_entity_network: Generate entity relationship network graph data
"""

import sys
import os

# Add project root to path to find src (MUST be first in path)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import json
import time  # For execution time tracking
from typing import Any, Dict, List, Optional
from datetime import datetime

# Import MCP modules
from mcp.server import Server
from mcp.types import Resource, Tool,TextContent, ImageContent, EmbeddedResource
from mcp.server.stdio import stdio_server

# Import async tools
import asyncio

# Import NetworkX for force-directed graph layouts
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("Warning: networkx not available, graph layouts will use random positions", file=sys.stderr)

# Import boto3 for AWS Bedrock
try:
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    print("Warning: boto3 not available, AWS Bedrock will not be used", file=sys.stderr)

# Add src to path for imports
# This line is now redundant due to the 'parent_dir' block above, but keeping it for now as it wasn't explicitly removed.
# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
try:
    from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings
except ImportError:
    print("Warning: Could not import NVCLIPEmbeddings. Image search will be limited.", file=sys.stderr)
    NVCLIPEmbeddings = None

# MCP SDK
# This block is now replaced by the explicit MCP imports above.
# try:
#     from mcp.server import Server
#     from mcp.types import Tool, TextContent, ImageContent
#     import mcp.server.stdio
# except ImportError:
#     print("Error: MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)
#     sys.exit(1)


# Import database connection module
from src.db.connection import get_connection

# Import search modules for scoring and caching
from src.search.scoring import get_score_color, get_confidence_level
from src.search.cache import get_cached_embedding, cache_info

# Import memory system
from src.memory import VectorMemory


# Initialize MCP server
server = Server("fhir-graphrag-server")

# Initialize NV-CLIP embedder (lazy load or global)
embedder = None

def get_embedder():
    """Get or initialize NV-CLIP embedder."""
    global embedder
    if embedder is None and NVCLIPEmbeddings:
        try:
            embedder = NVCLIPEmbeddings()
        except Exception as e:
            print(f"Warning: Failed to initialize NV-CLIP: {e}", file=sys.stderr)
    return embedder

# Initialize vector memory system
vector_memory = None

def get_memory():
    """Get or initialize vector memory system."""
    global vector_memory
    if vector_memory is None:
        vector_memory = VectorMemory(embedding_model=get_embedder())
    return vector_memory


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="search_fhir_documents",
            description="Search FHIR DocumentReference resources by text content. "
                       "Decodes hex-encoded clinical notes and performs full-text search. "
                       "Returns matching documents with clinical note previews.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query terms (e.g., 'chest pain', 'fever vomiting')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_knowledge_graph",
            description="Search medical knowledge graph for entities matching query terms. "
                       "Returns entities with types (SYMPTOM, CONDITION, MEDICATION, etc.) "
                       "and confidence scores, plus documents containing those entities.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Medical entity search terms (e.g., 'respiratory', 'abdominal pain')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of entities to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="hybrid_search",
            description="Combined FHIR + GraphRAG search using Reciprocal Rank Fusion. "
                       "Searches both FHIR document text and knowledge graph entities, "
                       "then fuses results for optimal ranking. Best for complex medical queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Medical search query (e.g., 'chest pain and difficulty breathing')"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top results to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_entity_relationships",
            description="Traverse knowledge graph relationships from seed entities. "
                       "Performs multi-hop graph traversal to find related entities and "
                       "discovers semantic connections between medical concepts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_text": {
                        "type": "string",
                        "description": "Starting entity text (e.g., 'fever', 'respiratory')"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum traversal depth (1-3 hops)",
                        "default": 2
                    }
                },
                "required": ["entity_text"]
            }
        ),
        Tool(
            name="get_document_details",
            description="Retrieve full details of a FHIR DocumentReference resource. "
                       "Decodes hex-encoded clinical notes and returns complete document "
                       "with metadata and full text content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "fhir_id": {
                        "type": "string",
                        "description": "FHIR resource ID (e.g., '1474', '2079')"
                    }
                },
                "required": ["fhir_id"]
            }
        ),
        Tool(
            name="get_entity_statistics",
            description="Get knowledge graph statistics including entity counts by type, "
                       "relationship counts, and high-confidence entities. Useful for "
                       "understanding the scope and quality of the knowledge graph.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="plot_entity_distribution",
            description="Generate interactive pie/bar chart data showing distribution of entity types "
                       "(SYMPTOM, CONDITION, MEDICATION, etc.). Returns Plotly-compatible chart data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "description": "Chart type: 'pie' or 'bar'",
                        "default": "pie"
                    }
                }
            }
        ),
        Tool(
            name="plot_patient_timeline",
            description="Generate timeline visualization showing patient encounters over time. "
                       "Returns Plotly-compatible timeline chart data with dates and event counts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "granularity": {
                        "type": "string",
                        "description": "Time granularity: 'day', 'week', 'month'",
                        "default": "month"
                    }
                }
            }
        ),
        Tool(
            name="plot_symptom_frequency",
            description="Generate bar chart showing most frequent symptoms in the knowledge graph. "
                       "Returns top N symptoms with their occurrence counts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top symptoms to show",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="plot_entity_network",
            description="Generate network graph data showing entity relationships for visualization. "
                       "Returns nodes and edges in format compatible with network visualization libraries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Filter by entity type (SYMPTOM, CONDITION, etc.) or 'all'",
                        "default": "all"
                    },
                    "max_nodes": {
                        "type": "integer",
                        "description": "Maximum number of nodes to include",
                        "default": 50
                    }
                }
            }
        ),
        Tool(
            name="visualize_graphrag_results",
            description="Visualize GraphRAG search results showing the query, entities found, and their relationships. "
                       "Performs a knowledge graph search and returns visualization data showing how entities connect to the query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Medical search query to visualize (e.g., 'diabetes symptoms', 'chest pain treatment')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of entities to include in visualization",
                        "default": 10
                    }
                },
                "required": ["query"]
            }

        ),
        Tool(
            name="search_medical_images",
            description="Search for medical images (X-rays) using text query or metadata. "
                       "Uses NV-CLIP for semantic search (e.g., 'pneumonia', 'lateral view') "
                       "to find relevant chest X-rays from MIMIC-CXR dataset.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'chest X-ray of pneumonia', 'enlarged heart')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of images to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="remember_information",
            description="Store information in agent memory with semantic embedding. "
                       "Use this to remember user corrections, preferences, domain knowledge, or feedback. "
                       "IMPORTANT: When storing corrections about tool usage, ALWAYS include the specific tool name "
                       "(e.g., 'plot_entity_network' not just 'graph'). Rephrase vague user requests to be explicit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_type": {
                        "type": "string",
                        "description": "Type of memory: 'correction', 'knowledge', 'preference', 'feedback'",
                        "enum": ["correction", "knowledge", "preference", "feedback"]
                    },
                    "text": {
                        "type": "string",
                        "description": "Information to remember. For corrections, include SPECIFIC TOOL NAMES. "
                                      "Example: 'For knowledge graph queries, use plot_entity_network (network visualization) "
                                      "instead of plot_entity_distribution (bar chart)'"
                    },
                    "context": {
                        "type": "object",
                        "description": "Optional context metadata (JSON)",
                        "default": {}
                    }
                },
                "required": ["memory_type", "text"]
            }
        ),
        Tool(
            name="recall_information",
            description="Recall memories semantically similar to a query. "
                       "Returns relevant past corrections, knowledge, preferences with similarity scores.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'pneumonia appearance', 'user preferences')"
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Optional filter by type: 'correction', 'knowledge', 'preference', 'feedback'",
                        "enum": ["correction", "knowledge", "preference", "feedback", "all"],
                        "default": "all"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of memories to return",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_memory_stats",
            description="Get agent memory statistics including counts by type and most used memories.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_encounter_imaging",
            description="Retrieve imaging studies associated with a specific patient encounter. "
                       "Useful for viewing all radiology performed during a hospital visit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "encounter_id": {
                        "type": "string",
                        "description": "FHIR Encounter resource ID (e.g., 'enc-123' or 'Encounter/enc-123')"
                    },
                    "include_reports": {
                        "type": "boolean",
                        "description": "Whether to include associated DiagnosticReport resources",
                        "default": True
                    }
                },
                "required": ["encounter_id"]
            }
        ),
        Tool(
            name="get_patient_imaging_studies",
            description="Retrieve all ImagingStudy resources for a given patient. "
                       "Returns study dates, modalities, and associated report references.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "FHIR Patient resource ID (e.g., 'p10002428')"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Optional start date filter (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Optional end date filter (YYYY-MM-DD)"
                    },
                    "modality": {
                        "type": "string",
                        "description": "Filter by modality (CR, DX, CT, MR, US, NM, PT)"
                    }
                },
                "required": ["patient_id"]
            }
        ),
        Tool(
            name="get_imaging_study_details",
            description="Retrieve detailed information for a specific ImagingStudy resource, "
                       "including series and instance metadata and linked MIMIC-CXR images.",
            inputSchema={
                "type": "object",
                "properties": {
                    "study_id": {
                        "type": "string",
                        "description": "ImagingStudy resource ID (e.g., 'study-s50414267') or MIMIC study ID"
                    }
                },
                "required": ["study_id"]
            }
        ),
        Tool(
            name="get_radiology_reports",
            description="Retrieve DiagnosticReport resources for radiology studies. "
                       "Returns clinical findings, impressions, and full report text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "study_id": {
                        "type": "string",
                        "description": "ImagingStudy resource ID to find associated reports"
                    },
                    "patient_id": {
                        "type": "string",
                        "description": "Patient ID to find all radiology reports for a patient"
                    },
                    "include_full_text": {
                        "type": "boolean",
                        "description": "Include full report text (base64 decoded)",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="search_patients_with_imaging",
            description="Search for patients who have imaging studies. "
                       "Filter by modality, date range, or clinical findings text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "modality": {
                        "type": "string",
                        "description": "Filter by modality (CR, DX, CT, MR, US)"
                    },
                    "finding_text": {
                        "type": "string",
                        "description": "Search report conclusions (e.g., 'pneumonia')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum patients to return",
                        "default": 20
                    }
                }
            }
        ),
        Tool(
            name="list_radiology_queries",
            description="List available pre-defined radiology query templates. "
                       "Returns a catalog of supported FHIR queries for radiology data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category: patient, study, report, encounter, or all",
                        "default": "all"
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool invocations."""

    # Tools that use FHIR REST only (no IRIS DB connection required)
    FHIR_REST_ONLY_TOOLS = {
        "get_patient_imaging_studies",
        "get_imaging_study_details",
        "get_radiology_reports",
        "search_patients_with_imaging",
        "get_encounter_imaging",
        "list_radiology_queries"
    }

    try:
        # Only get IRIS connection for tools that need it
        conn = None
        cursor = None
        if name not in FHIR_REST_ONLY_TOOLS:
            conn = get_connection()
            cursor = conn.cursor()

        if name == "search_fhir_documents":
            query = arguments["query"]
            limit = arguments.get("limit", 10)

            # Query FHIR documents
            sql = """
                SELECT TOP ?
                    FHIRResourceId,
                    ResourceType,
                    ResourceString
                FROM SQLUser.FHIRDocuments
                WHERE ResourceType = 'DocumentReference'
            """

            cursor.execute(sql, (limit * 3,))

            search_terms = query.lower().split()
            results = []

            for fhir_id, resource_type, resource_string in cursor.fetchall():
                try:
                    resource_json = json.loads(resource_string)

                    # Decode clinical note
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
                        if any(term in clinical_note_lower for term in search_terms):
                            results.append({
                                'fhir_id': fhir_id,
                                'preview': clinical_note[:300],
                                'relevance': 'matches: ' + ', '.join([t for t in search_terms if t in clinical_note_lower])
                            })

                            if len(results) >= limit:
                                break
                except:
                    pass

            cursor.close()
            conn.close()

            return [TextContent(
                type="text",
                text=json.dumps({
                    "query": query,
                    "results_count": len(results),
                    "documents": results
                }, indent=2)
            )]

        elif name == "search_knowledge_graph":
            query = arguments["query"]
            limit = arguments.get("limit", 5)

            keywords = [w.strip() for w in query.lower().split() if len(w.strip()) > 2]
            all_entities = []
            seen_ids = set()

            for keyword in keywords:
                sql = """
                    SELECT EntityID, EntityText, EntityType, Confidence
                    FROM SQLUser.Entities
                    WHERE LOWER(EntityText) LIKE ?
                    ORDER BY Confidence DESC
                    LIMIT ?
                """

                cursor.execute(sql, (f'%{keyword}%', 10))

                for entity_id, text, entity_type, confidence in cursor.fetchall():
                    if entity_id not in seen_ids:
                        seen_ids.add(entity_id)
                        all_entities.append({
                            'id': entity_id,
                            'text': text,
                            'type': entity_type,
                            'confidence': float(confidence) if confidence else 0.0,
                            'matched_keyword': keyword,
                            'source': 'direct_match'  # Mark as direct query match
                        })

            all_entities.sort(key=lambda x: x['confidence'], reverse=True)
            top_entities = all_entities[:limit]

            documents = []
            relationships = []

            # Get documents and relationships for these entities
            if top_entities:
                entity_ids = [e['id'] for e in top_entities]
                placeholders = ','.join(['?'] * len(entity_ids))

                # Get documents containing these entities
                doc_sql = f"""
                    SELECT DISTINCT e.ResourceID, f.FHIRResourceId,
                           COUNT(DISTINCT e.EntityID) as EntityCount
                    FROM SQLUser.Entities e
                    JOIN SQLUser.FHIRDocuments f ON e.ResourceID = f.FHIRResourceId
                    WHERE e.EntityID IN ({placeholders})
                    GROUP BY e.ResourceID, f.FHIRResourceId
                    ORDER BY EntityCount DESC
                """

                cursor.execute(doc_sql, entity_ids)
                for resource_id, fhir_id, entity_count in cursor.fetchall():
                    documents.append({
                        'fhir_id': fhir_id,
                        'entity_count': entity_count
                    })

                # Get relationships between found entities from EntityRelationships table
                # Enhanced query: also fetch entity types for related entities
                rel_sql = f"""
                    SELECT r.SourceEntityID, r.TargetEntityID, r.RelationshipType,
                           e1.EntityText as SourceText, e1.EntityType as SourceType, e1.Confidence as SourceConf,
                           e2.EntityText as TargetText, e2.EntityType as TargetType, e2.Confidence as TargetConf
                    FROM SQLUser.EntityRelationshipsr
                    JOIN SQLUser.Entities e1 ON r.SourceEntityID = e1.EntityID
                    JOIN SQLUser.Entities e2 ON r.TargetEntityID = e2.EntityID
                    WHERE r.SourceEntityID IN ({placeholders})
                    OR r.TargetEntityID IN ({placeholders})
                """
                cursor.execute(rel_sql, entity_ids + entity_ids)
                seen_rels = set()

                # Track entities extracted from relationships (for complete entity list)
                related_entities = []

                for row in cursor.fetchall():
                    src_id, tgt_id, rel_type, src_text, src_type, src_conf, tgt_text, tgt_type, tgt_conf = row

                    # Deduplicate relationships
                    rel_key = f"{min(src_id, tgt_id)}_{max(src_id, tgt_id)}"
                    if rel_key not in seen_rels:
                        seen_rels.add(rel_key)
                        relationships.append({
                            'source_id': src_id,
                            'target_id': tgt_id,
                            'source_text': src_text,
                            'target_text': tgt_text,
                            'type': rel_type or 'related'
                        })

                    # ENHANCEMENT: Extract complete entity objects from relationships
                    # This ensures all related entities are returned with full metadata
                    if src_id not in seen_ids:
                        seen_ids.add(src_id)
                        related_entities.append({
                            'id': src_id,
                            'text': src_text,
                            'type': src_type,
                            'confidence': float(src_conf) if src_conf else 0.4,
                            'source': 'relationship'  # Mark as discovered via relationship
                        })

                    if tgt_id not in seen_ids:
                        seen_ids.add(tgt_id)
                        related_entities.append({
                            'id': tgt_id,
                            'text': tgt_text,
                            'type': tgt_type,
                            'confidence': float(tgt_conf) if tgt_conf else 0.4,
                            'source': 'relationship'  # Mark as discovered via relationship
                        })

                # Combine direct matches with related entities
                # Direct matches first (higher relevance), then related entities
                all_result_entities = top_entities + related_entities

            else:
                all_result_entities = top_entities

            cursor.close()
            conn.close()

            return [TextContent(
                type="text",
                text=json.dumps({
                    "query": query,
                    "entities_found": len(all_result_entities),
                    "direct_matches": len(top_entities),
                    "related_entities": len(all_result_entities) - len(top_entities),
                    "entities": all_result_entities,
                    "relationships_found": len(relationships),
                    "relationships": relationships,
                    "documents_found": len(documents),
                    "documents": documents
                }, indent=2)
            )]

        elif name == "hybrid_search":
            query = arguments["query"]
            top_k = arguments.get("top_k", 5)

            # Execute FHIR search (text matching)
            fhir_sql = """
                SELECT TOP ?
                    FHIRResourceId,
                    ResourceType,
                    ResourceString
                FROM SQLUser.FHIRDocuments
                WHERE ResourceType = 'DocumentReference'
            """

            cursor.execute(fhir_sql, (top_k * 3,))
            search_terms = query.lower().split()
            fhir_results = []

            for fhir_id, resource_type, resource_string in cursor.fetchall():
                try:
                    resource_json = json.loads(resource_string)
                    clinical_note = None
                    if 'content' in resource_json:
                        try:
                            encoded_data = resource_json['content'][0]['attachment']['data']
                            clinical_note = bytes.fromhex(encoded_data).decode('utf-8')
                        except:
                            pass

                    if clinical_note and search_terms:
                        clinical_note_lower = clinical_note.lower()
                        if any(term in clinical_note_lower for term in search_terms):
                            fhir_results.append({'fhir_id': fhir_id})
                            if len(fhir_results) >= top_k * 2:
                                break
                except:
                    pass

            # Execute GraphRAG search (entity matching)
            keywords = [w.strip() for w in query.lower().split() if len(w.strip()) > 2]
            all_entity_ids = set()

            for keyword in keywords[:3]:  # Limit to 3 keywords
                entity_sql = """
                    SELECT EntityID FROM SQLUser.Entities
                    WHERE LOWER(EntityText) LIKE ?
                    LIMIT 5
                """
                cursor.execute(entity_sql, (f'%{keyword}%',))
                for row in cursor.fetchall():
                    all_entity_ids.add(row[0])

            graphrag_results = []
            if all_entity_ids:
                entity_list = list(all_entity_ids)
                placeholders = ','.join(['?'] * len(entity_list))
                doc_sql = f"""
                    SELECT DISTINCT f.FHIRResourceId
                    FROM SQLUser.Entities e
                    JOIN SQLUser.FHIRDocuments f ON e.ResourceID = f.FHIRResourceId
                    WHERE e.EntityID IN ({placeholders})
                """
                cursor.execute(doc_sql, entity_list)
                graphrag_results = [{'fhir_id': row[0]} for row in cursor.fetchall()]

            # RRF fusion
            k = 60
            score_map = {}

            for rank, doc in enumerate(fhir_results, 1):
                fhir_id = doc['fhir_id']
                if fhir_id not in score_map:
                    score_map[fhir_id] = {'fhir_rank': None, 'graph_rank': None}
                score_map[fhir_id]['fhir_rank'] = rank

            for rank, doc in enumerate(graphrag_results, 1):
                fhir_id = doc['fhir_id']
                if fhir_id not in score_map:
                    score_map[fhir_id] = {'fhir_rank': None, 'graph_rank': None}
                score_map[fhir_id]['graph_rank'] = rank

            fused = []
            for fhir_id, data in score_map.items():
                rrf_score = 0.0
                if data['fhir_rank']:
                    rrf_score += 1.0 / (k + data['fhir_rank'])
                if data['graph_rank']:
                    rrf_score += 1.0 / (k + data['graph_rank'])

                sources = []
                if data['fhir_rank']:
                    sources.append('fhir')
                if data['graph_rank']:
                    sources.append('graphrag')

                fused.append({
                    'fhir_id': fhir_id,
                    'rrf_score': rrf_score,
                    'sources': sources
                })

            fused.sort(key=lambda x: x['rrf_score'], reverse=True)

            cursor.close()
            conn.close()

            return [TextContent(
                type="text",
                text=json.dumps({
                    "query": query,
                    "fhir_results": len(fhir_results),
                    "graphrag_results": len(graphrag_results),
                    "fused_results": len(fused),
                    "top_documents": fused[:top_k]
                }, indent=2)
            )]

        elif name == "get_entity_relationships":
            entity_text = arguments["entity_text"]
            max_depth = arguments.get("max_depth", 2)

            # Find entity
            sql = """
                SELECT EntityID, EntityText, EntityType, Confidence
                FROM SQLUser.Entities
                WHERE LOWER(EntityText) LIKE ?
                ORDER BY Confidence DESC
                LIMIT 1
            """

            cursor.execute(sql, (f'%{entity_text.lower()}%',))
            result = cursor.fetchone()

            if not result:
                cursor.close()
                conn.close()
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Entity '{entity_text}' not found"})
                )]

            entity_id, text, entity_type, confidence = result

            # Traverse relationships
            visited = {entity_id}
            current_level = {entity_id}
            graph = {'entities': [{'id': entity_id, 'text': text, 'type': entity_type, 'depth': 0}],
                     'relationships': []}

            for depth in range(max_depth):
                if not current_level:
                    break

                next_level = set()
                entity_list = list(current_level)
                placeholders = ','.join(['?'] * len(entity_list))

                rel_sql = f"""
                    SELECT DISTINCT
                        r.SourceEntityID, r.TargetEntityID, r.RelationshipType,
                        e1.EntityText as SourceText, e1.EntityType as SourceType,
                        e2.EntityText as TargetText, e2.EntityType as TargetType
                    FROM SQLUser.EntityRelationshipsr
                    JOIN SQLUser.Entities e1 ON r.SourceEntityID = e1.EntityID
                    JOIN SQLUser.Entities e2 ON r.TargetEntityID = e2.EntityID
                    WHERE r.SourceEntityID IN ({placeholders})
                       OR r.TargetEntityID IN ({placeholders})
                """

                cursor.execute(rel_sql, entity_list + entity_list)

                for row in cursor.fetchall():
                    source_id, target_id, rel_type, source_text, source_type, target_text, target_type = row

                    graph['relationships'].append({
                        'source': source_text,
                        'target': target_text,
                        'type': rel_type
                    })

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
            conn.close()

            return [TextContent(
                type="text",
                text=json.dumps({
                    "seed_entity": entity_text,
                    "entities_found": len(graph['entities']),
                    "relationships_found": len(graph['relationships']),
                    "graph": graph
                }, indent=2)
            )]

        elif name == "get_document_details":
            fhir_id = arguments["fhir_id"]

            sql = """
                SELECT FHIRResourceId, ResourceType, ResourceString
                FROM SQLUser.FHIRDocuments
                WHERE FHIRResourceId = ?
            """

            cursor.execute(sql, (fhir_id,))
            result = cursor.fetchone()

            if not result:
                cursor.close()
                conn.close()
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Document '{fhir_id}' not found"})
                )]

            _, resource_type, resource_string = result
            resource_json = json.loads(resource_string)

            # Decode clinical note
            clinical_note = None
            if 'content' in resource_json:
                try:
                    encoded_data = resource_json['content'][0]['attachment']['data']
                    clinical_note = bytes.fromhex(encoded_data).decode('utf-8')
                except:
                    pass

            cursor.close()
            conn.close()

            return [TextContent(
                type="text",
                text=json.dumps({
                    "fhir_id": fhir_id,
                    "resource_type": resource_type,
                    "clinical_note": clinical_note,
                    "metadata": {
                        "id": resource_json.get('id'),
                        "status": resource_json.get('status'),
                        "type": resource_json.get('type', {}).get('coding', [{}])[0].get('display') if resource_json.get('type') else None
                    }
                }, indent=2)
            )]

        elif name == "get_entity_statistics":
            # Entity count by type
            stats_sql = """
                SELECT EntityType, COUNT(*) as EntityCount
                FROM SQLUser.Entities
                GROUP BY EntityType
                ORDER BY EntityCount DESC
            """

            cursor.execute(stats_sql)
            entity_stats = []
            for entity_type, count in cursor.fetchall():
                entity_stats.append({'type': entity_type, 'count': count})

            # Total counts
            cursor.execute("SELECT COUNT(*) FROM SQLUser.Entities")
            total_entities = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM SQLUser.Relationship")
            total_relationships = cursor.fetchone()[0]

            # High confidence entities
            cursor.execute("""
                SELECT TOP 10 EntityText, EntityType, Confidence
                FROM SQLUser.Entities
                ORDER BY Confidence DESC
            """)

            high_confidence = []
            for text, entity_type, confidence in cursor.fetchall():
                high_confidence.append({
                    'text': text,
                    'type': entity_type,
                    'confidence': float(confidence) if confidence else 0.0
                })

            cursor.close()
            conn.close()

            return [TextContent(
                type="text",
                text=json.dumps({
                    "total_entities": total_entities,
                    "total_relationships": total_relationships,
                    "entity_distribution": entity_stats,
                    "high_confidence_entities": high_confidence
                }, indent=2)
            )]

        elif name == "plot_entity_distribution":
            chart_type = arguments.get("chart_type", "pie")

            # Get entity type distribution
            cursor.execute("""
                SELECT EntityType, COUNT(*) as EntityCount
                FROM SQLUser.Entities
                GROUP BY EntityType
                ORDER BY EntityCount DESC
            """)

            labels = []
            values = []
            for entity_type, count in cursor.fetchall():
                labels.append(entity_type)
                values.append(count)

            cursor.close()
            conn.close()

            # Return Plotly-compatible data
            chart_data = {
                "chart_type": chart_type,
                "data": {
                    "labels": labels,
                    "values": values
                },
                "layout": {
                    "title": "Medical Entity Type Distribution",
                    "xaxis_title": "Entity Type" if chart_type == "bar" else None,
                    "yaxis_title": "Count" if chart_type == "bar" else None
                }
            }

            return [TextContent(
                type="text",
                text=json.dumps(chart_data, indent=2)
            )]

        elif name == "plot_patient_timeline":
            granularity = arguments.get("granularity", "month")

            # Get temporal entities (dates)
            cursor.execute("""
                SELECT EntityText, COUNT(*) as Frequency
                FROM SQLUser.Entities
                WHERE EntityType = 'TEMPORAL'
                GROUP BY EntityText
                ORDER BY EntityText
            """)

            dates = []
            counts = []
            for date_text, count in cursor.fetchall():
                # Try to parse date (handle various formats)
                try:
                    if len(date_text) == 10 and '-' in date_text:  # YYYY-MM-DD
                        dates.append(date_text)
                        counts.append(count)
                except:
                    pass

            cursor.close()
            conn.close()

            chart_data = {
                "chart_type": "timeline",
                "data": {
                    "dates": dates,
                    "counts": counts
                },
                "layout": {
                    "title": "Patient Encounters Timeline",
                    "xaxis_title": "Date",
                    "yaxis_title": "Event Count"
                }
            }

            return [TextContent(
                type="text",
                text=json.dumps(chart_data, indent=2)
            )]

        elif name == "plot_symptom_frequency":
            top_n = arguments.get("top_n", 10)

            # Get symptom frequencies
            cursor.execute(f"""
                SELECT TOP {top_n}
                    e.EntityText,
                    COUNT(DISTINCT er.RelationshipID) as Frequency
                FROM SQLUser.Entities e
                LEFT JOIN SQLUser.EntityRelationshipser
                    ON e.EntityID = er.SourceEntityID OR e.EntityID = er.TargetEntityID
                WHERE e.EntityType = 'SYMPTOM'
                GROUP BY e.EntityText
                ORDER BY Frequency DESC
            """)

            symptoms = []
            frequencies = []
            for text, freq in cursor.fetchall():
                symptoms.append(text)
                frequencies.append(freq)

            cursor.close()
            conn.close()

            # Return Plotly-compatible data
            chart_data = {
                "chart_type": "bar",
                "data": {
                    "symptoms": symptoms,
                    "frequencies": frequencies
                },
                "layout": {
                    "title": f"Top {top_n} Most Frequent Symptoms",
                    "xaxis_title": "Symptom",
                    "yaxis_title": "Frequency"
                }
            }

            return [TextContent(
                type="text",
                text=json.dumps(chart_data, indent=2)
            )]

        elif name == "plot_entity_network":
            entity_type = arguments.get("entity_type", "all")
            max_nodes = arguments.get("max_nodes", 50)

            # Get top entities and their relationships
            cursor.execute(f"""
                SELECT TOP {max_nodes} EntityID, EntityText, EntityType
                FROM SQLUser.Entities
                {'WHERE EntityType = ?' if entity_type != 'all' else ''}
                ORDER BY Confidence DESC
            """, (entity_type,) if entity_type != 'all' else ())

            nodes = []
            node_ids = set()
            id_to_idx = {}
            for idx, (eid, text, etype) in enumerate(cursor.fetchall()):
                nodes.append({
                    "id": eid,
                    "name": text,
                    "type": etype,
                    "x": 0, "y": 0
                })
                node_ids.add(eid)
                id_to_idx[eid] = idx

            # Get relationships between these nodes
            edges = []
            if node_ids:
                placeholders = ','.join(['?'] * len(node_ids))
                cursor.execute(f"""
                    SELECT SourceEntityID, TargetEntityID, RelationshipType
                    FROM SQLUser.Relationship
                    WHERE SourceEntityID IN ({placeholders})
                    AND TargetEntityID IN ({placeholders})
                """, list(node_ids) + list(node_ids))

                for source, target, rel_type in cursor.fetchall():
                    if source in id_to_idx and target in id_to_idx:
                        edges.append({
                            "source": id_to_idx[source],
                            "target": id_to_idx[target],
                            "type": rel_type
                        })

            cursor.close()
            conn.close()

            # Apply force-directed layout using NetworkX
            if NETWORKX_AVAILABLE and nodes:
                G = nx.Graph()
                for i, node in enumerate(nodes):
                    G.add_node(i)
                for edge in edges:
                    G.add_edge(edge["source"], edge["target"])

                # Use spring layout (force-directed)
                pos = nx.spring_layout(G, k=2.0, iterations=50, seed=42)

                # Scale positions to reasonable range and update nodes
                for i, node in enumerate(nodes):
                    if i in pos:
                        node["x"] = float(pos[i][0]) * 100
                        node["y"] = float(pos[i][1]) * 100

            # Assign colors by entity type
            type_colors = {
                "SYMPTOM": "#ff6b6b",
                "CONDITION": "#4ecdc4",
                "MEDICATION": "#45b7d1",
                "PROCEDURE": "#96ceb4",
                "ANATOMY": "#ffeaa7",
                "OBSERVATION": "#dfe6e9",
            }
            for node in nodes:
                node["color"] = type_colors.get(node["type"], "#b2bec3")

            return [TextContent(
                type="text",
                text=json.dumps({
                    "chart_type": "network",
                    "data": {
                        "nodes": nodes,
                        "edges": edges
                    }
                }, indent=2)
            )]

        elif name == "visualize_graphrag_results":
            query = arguments["query"]
            limit = arguments.get("limit", 10)

            # 1. Find entities matching query
            keywords = [w.strip() for w in query.lower().split() if len(w.strip()) > 2]
            matched_entities = []

            for keyword in keywords:
                cursor.execute("""
                    SELECT EntityID, EntityText, EntityType
                    FROM SQLUser.Entities
                    WHERE LOWER(EntityText) LIKE ?
                    ORDER BY Confidence DESC
                    LIMIT 5
                """, (f'%{keyword}%',))
                for row in cursor.fetchall():
                    matched_entities.append(row)

            # 2. Find related entities (1 hop)
            nodes = []
            edges = []
            node_ids = set()
            id_to_idx = {}

            # Add query node at center
            nodes.append({
                "id": -1,
                "name": query,
                "type": "QUERY",
                "color": "#e74c3c",
                "x": 0, "y": 0
            })
            id_to_idx[-1] = 0

            # Entity type colors
            type_colors = {
                "SYMPTOM": "#ff6b6b",
                "CONDITION": "#4ecdc4",
                "MEDICATION": "#45b7d1",
                "PROCEDURE": "#96ceb4",
                "ANATOMY": "#ffeaa7",
                "OBSERVATION": "#dfe6e9",
            }

            # Add matched entities
            for eid, text, etype in matched_entities[:limit]:
                if eid not in node_ids:
                    idx = len(nodes)
                    nodes.append({
                        "id": eid,
                        "name": text,
                        "type": etype,
                        "color": type_colors.get(etype, "#b2bec3"),
                        "x": 0, "y": 0
                    })
                    node_ids.add(eid)
                    id_to_idx[eid] = idx
                    # Edge from query to entity
                    edges.append({
                        "source": 0,  # Query is index 0
                        "target": idx,
                        "type": "MATCHES"
                    })

            # Add relationships between found entities
            if node_ids:
                placeholders = ','.join(['?'] * len(node_ids))
                cursor.execute(f"""
                    SELECT SourceEntityID, TargetEntityID, RelationshipType
                    FROM SQLUser.Relationship
                    WHERE SourceEntityID IN ({placeholders})
                    AND TargetEntityID IN ({placeholders})
                """, list(node_ids) + list(node_ids))

                for source, target, rel_type in cursor.fetchall():
                    if source in id_to_idx and target in id_to_idx:
                        edges.append({
                            "source": id_to_idx[source],
                            "target": id_to_idx[target],
                            "type": rel_type
                        })

            cursor.close()
            conn.close()

            # Apply force-directed layout using NetworkX
            if NETWORKX_AVAILABLE and len(nodes) > 1:
                G = nx.Graph()
                for i in range(len(nodes)):
                    G.add_node(i)
                for edge in edges:
                    G.add_edge(edge["source"], edge["target"])

                # Use spring layout with query node at center
                pos = nx.spring_layout(G, k=2.0, iterations=50, seed=42, center=(0, 0))

                # Scale positions and update nodes
                for i, node in enumerate(nodes):
                    if i in pos:
                        node["x"] = float(pos[i][0]) * 100
                        node["y"] = float(pos[i][1]) * 100

            return [TextContent(
                type="text",
                text=json.dumps({
                    "chart_type": "network",
                    "query": query,
                    "entities_found": len(matched_entities),
                    "data": {
                        "nodes": nodes,
                        "edges": edges
                    }
                }, indent=2)
            )]

        elif name == "search_medical_images":
            query = arguments["query"]
            limit = arguments.get("limit", 5)
            min_score = arguments.get("min_score", 0.0)  # New: score threshold filter

            emb = get_embedder()
            results = []
            search_mode = "keyword"  # Default to keyword search
            cache_hit = False
            fallback_reason = None
            start_time = time.time()

            if emb:
                try:
                    # Semantic search with NV-CLIP (using cached embeddings)
                    query_vector_tuple = get_cached_embedding(query)
                    query_vector = list(query_vector_tuple)  # Convert tuple back to list
                    vector_str = ','.join(map(str, query_vector))
                    
                    # Check if this was a cache hit
                    info = cache_info()
                    cache_hit = info.hits > 0
                    
                    search_mode = "semantic"

                    # Updated SQL: Include similarity score and patient info via LEFT JOIN (T013-T016)
                    sql = f"""
                        SELECT TOP ?
                            i.ImageID, i.StudyID, i.SubjectID, i.ViewPosition, i.ImagePath,
                            VECTOR_COSINE(i.Vector, TO_VECTOR(?, double)) AS Similarity,
                            m.FHIRPatientID, m.FHIRPatientName
                        FROM VectorSearch.MIMICCXRImages i
                        LEFT JOIN VectorSearch.PatientImageMapping m
                            ON i.SubjectID = m.MIMICSubjectID
                        ORDER BY Similarity DESC
                    """
                    cursor.execute(sql, (limit, vector_str))
                except Exception as e:
                    # Enhanced error handling (T018)
                    print(f"Error in vector search: {e}", file=sys.stderr)
                    fallback_reason = f"NV-CLIP search failed: {str(e)}"
                    search_mode = "keyword"
                    # Fallback to keyword search
                    emb = None
            else:
                # No embedder available
                fallback_reason = "NV-CLIP embedder not available"

            if not emb:
                # Keyword search fallback
                keywords = query.lower().split()
                conditions = []
                params = []
                for kw in keywords:
                    conditions.append("(LOWER(ViewPosition) LIKE ? OR LOWER(ImageID) LIKE ?)")
                    params.extend([f'%{kw}%', f'%{kw}%'])

                where_clause = " OR ".join(conditions) if conditions else "1=1"
                
                sql = f"""
                    SELECT TOP ?
                        ImageID, StudyID, SubjectID, ViewPosition, ImagePath
                    FROM VectorSearch.MIMICCXRImages
                    WHERE {where_clause}
                """
                cursor.execute(sql, [limit] + params)

            # Process results with scoring metadata and patient info (T014-T016)
            scores = []
            for row in cursor.fetchall():
                if search_mode == "semantic":
                    # Semantic search returns 8 columns (including similarity + patient info)
                    image_id, study_id, subject_id, view_pos, image_path, similarity, fhir_patient_id, fhir_patient_name = row
                    similarity_score = float(similarity) if similarity is not None else 0.0

                    # Filter by min_score if specified
                    if similarity_score < min_score:
                        continue

                    scores.append(similarity_score)

                    # Build patient display name - use linked name or show as unlinked (T016)
                    if fhir_patient_name:
                        patient_display = fhir_patient_name
                        patient_linked = True
                    else:
                        patient_display = f"Unlinked - Source ID: {subject_id}"
                        patient_linked = False

                    results.append({
                        "image_id": image_id,
                        "study_id": study_id,
                        "subject_id": subject_id,
                        "view_position": view_pos,
                        "image_path": image_path,
                        "similarity_score": similarity_score,
                        "score_color": get_score_color(similarity_score),
                        "confidence_level": get_confidence_level(similarity_score),
                        "description": f"Chest X-ray ({view_pos}) - {patient_display}",
                        "embedding_model": "nvidia/nvclip",
                        # Patient info fields (T014)
                        "patient_name": fhir_patient_name,
                        "fhir_patient_id": fhir_patient_id,
                        "patient_linked": patient_linked,
                        "patient_display": patient_display
                    })
                else:
                    # Keyword search returns 5 columns (no similarity, no patient info yet)
                    image_id, study_id, subject_id, view_pos, image_path = row
                    results.append({
                        "image_id": image_id,
                        "study_id": study_id,
                        "subject_id": subject_id,
                        "view_position": view_pos,
                        "image_path": image_path,
                        "description": f"Chest X-ray ({view_pos}) - Unlinked - Source ID: {subject_id}",
                        "patient_linked": False,
                        "patient_display": f"Unlinked - Source ID: {subject_id}"
                    })

            cursor.close()
            conn.close()
            
            # Calculate execution time and statistics
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Build response with enhanced metadata
            response = {
                "query": query,
                "results_count": len(results),
                "total_results": len(results),  # TODO: Get actual total from COUNT query
                "search_mode": search_mode,
                "execution_time_ms": execution_time_ms,
                "images": results
            }
            
            # Add semantic search statistics
            if search_mode == "semantic" and scores:
                response["cache_hit"] = cache_hit
                response["avg_score"] = sum(scores) / len(scores) if scores else None
                response["max_score"] = max(scores) if scores else None
                response["min_score"] = min(scores) if scores else None
            
            # Add fallback reason if applicable
            if fallback_reason:
                response["fallback_reason"] = fallback_reason

            return [TextContent(
                type="text",
                text=json.dumps(response, indent=2)
            )]

        elif name == "remember_information":
            memory_type = arguments["memory_type"]
            text = arguments["text"]
            context = arguments.get("context", {})

            # Store in vector memory
            memory = get_memory()
            memory_id = memory.remember(memory_type, text, context)

            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "memory_id": memory_id,
                    "memory_type": memory_type,
                    "text": text,
                    "message": f"Stored {memory_type} memory with semantic embedding"
                }, indent=2)
            )]

        elif name == "recall_information":
            query = arguments["query"]
            memory_type = arguments.get("memory_type", "all")
            top_k = arguments.get("top_k", 5)

            # Search vector memory
            memory = get_memory()
            if memory_type == "all":
                memory_type = None

            memories = memory.recall(query, memory_type, top_k)

            return [TextContent(
                type="text",
                text=json.dumps({
                    "query": query,
                    "memories_found": len(memories),
                    "memories": memories
                }, indent=2)
            )]

        elif name == "get_memory_stats":
            memory = get_memory()
            stats = memory.get_stats()

            return [TextContent(
                type="text",
                text=json.dumps(stats, indent=2)
            )]

        elif name == "get_encounter_imaging":
            encounter_id = arguments["encounter_id"]
            include_reports = arguments.get("include_reports", True)

            # Strip 'Encounter/' prefix if present
            if encounter_id.startswith("Encounter/"):
                encounter_id = encounter_id[len("Encounter/"):]

            # Import the FHIR radiology adapter
            from src.adapters.fhir_radiology_adapter import FHIRRadiologyAdapter

            adapter = FHIRRadiologyAdapter()

            # Get the encounter details first
            encounter_url = f"{adapter.fhir_base_url}/Encounter/{encounter_id}"
            encounter_response = adapter.session.get(encounter_url)

            encounter_data = None
            if encounter_response.status_code == 200:
                encounter_resource = encounter_response.json()
                encounter_data = {
                    "id": encounter_resource.get("id"),
                    "status": encounter_resource.get("status"),
                    "class": encounter_resource.get("class", {}).get("display", "unknown"),
                    "period": {
                        "start": encounter_resource.get("period", {}).get("start"),
                        "end": encounter_resource.get("period", {}).get("end")
                    },
                    "patient_ref": encounter_resource.get("subject", {}).get("reference")
                }

            # Get imaging studies for this encounter
            imaging_studies = adapter.get_encounter_imaging(encounter_id)

            # Format studies for output per contract
            formatted_studies = []
            for study in imaging_studies:
                study_entry = {
                    "id": study.get("id"),
                    "study_id": None,
                    "status": study.get("status"),
                    "started": study.get("started"),
                    "modality": None,
                    "number_of_instances": study.get("numberOfInstances", 0)
                }

                # Extract MIMIC study ID from identifiers
                for identifier in study.get("identifier", []):
                    if identifier.get("system") == "urn:mimic-cxr:study":
                        study_entry["study_id"] = identifier.get("value")

                # Extract modality
                modalities = study.get("modality", [])
                if modalities:
                    study_entry["modality"] = modalities[0].get("code", "unknown")

                # Include report if requested
                if include_reports:
                    # Look up DiagnosticReport referencing this ImagingStudy
                    report_url = f"{adapter.fhir_base_url}/DiagnosticReport"
                    report_params = {
                        "imaging-study": f"ImagingStudy/{study.get('id')}"
                    }
                    report_response = adapter.session.get(report_url, params=report_params)

                    if report_response.status_code == 200:
                        report_bundle = report_response.json()
                        report_entries = report_bundle.get("entry", [])
                        if report_entries:
                            report_resource = report_entries[0].get("resource", {})
                            study_entry["report"] = {
                                "id": report_resource.get("id"),
                                "conclusion": report_resource.get("conclusion"),
                                "status": report_resource.get("status")
                            }

                formatted_studies.append(study_entry)

            return [TextContent(
                type="text",
                text=json.dumps({
                    "encounter": encounter_data,
                    "imaging_studies": formatted_studies,
                    "total_studies": len(formatted_studies)
                }, indent=2)
            )]

        elif name == "get_patient_imaging_studies":
            patient_id = arguments["patient_id"]
            date_from = arguments.get("date_from")
            date_to = arguments.get("date_to")
            modality = arguments.get("modality")

            # Import the FHIR radiology adapter
            from src.adapters.fhir_radiology_adapter import FHIRRadiologyAdapter

            adapter = FHIRRadiologyAdapter()

            # Build FHIR search URL with parameters
            search_url = f"{adapter.fhir_base_url}/ImagingStudy"
            params = {"subject": f"Patient/{patient_id}"}

            if date_from:
                params["started"] = f"ge{date_from}"
            if date_to:
                if "started" in params:
                    # Can't have two started params, use _filter or adjust
                    pass  # FHIR servers handle date ranges differently
                else:
                    params["started"] = f"le{date_to}"
            if modality:
                params["modality"] = modality

            response = adapter.session.get(search_url, params=params)

            studies = []
            if response.status_code == 200:
                bundle = response.json()
                for entry in bundle.get("entry", []):
                    resource = entry.get("resource", {})
                    study_entry = {
                        "id": resource.get("id"),
                        "status": resource.get("status"),
                        "started": resource.get("started"),
                        "modality": None,
                        "description": resource.get("description"),
                        "number_of_series": resource.get("numberOfSeries", 0),
                        "number_of_instances": resource.get("numberOfInstances", 0)
                    }

                    # Extract modality
                    modalities = resource.get("modality", [])
                    if modalities:
                        study_entry["modality"] = modalities[0].get("code")

                    # Extract study ID from identifiers
                    for identifier in resource.get("identifier", []):
                        if identifier.get("system") == "urn:mimic-cxr:study":
                            study_entry["mimic_study_id"] = identifier.get("value")

                    studies.append(study_entry)

            return [TextContent(
                type="text",
                text=json.dumps({
                    "patient_id": patient_id,
                    "studies": studies,
                    "total_count": len(studies)
                }, indent=2)
            )]

        elif name == "get_imaging_study_details":
            study_id = arguments["study_id"]

            # Import the FHIR radiology adapter
            from src.adapters.fhir_radiology_adapter import FHIRRadiologyAdapter

            adapter = FHIRRadiologyAdapter()

            # Try to get by FHIR ID first
            study_url = f"{adapter.fhir_base_url}/ImagingStudy/{study_id}"
            response = adapter.session.get(study_url)

            study_data = None
            if response.status_code == 200:
                study_data = response.json()
            else:
                # Try searching by MIMIC study ID
                search_url = f"{adapter.fhir_base_url}/ImagingStudy"
                params = {"identifier": f"urn:mimic-cxr:study|{study_id}"}
                response = adapter.session.get(search_url, params=params)
                if response.status_code == 200:
                    bundle = response.json()
                    entries = bundle.get("entry", [])
                    if entries:
                        study_data = entries[0].get("resource")

            if not study_data:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"ImagingStudy '{study_id}' not found"})
                )]

            # Format study details
            result = {
                "id": study_data.get("id"),
                "status": study_data.get("status"),
                "started": study_data.get("started"),
                "description": study_data.get("description"),
                "modality": None,
                "patient_reference": study_data.get("subject", {}).get("reference"),
                "encounter_reference": study_data.get("encounter", {}).get("reference"),
                "number_of_series": study_data.get("numberOfSeries", 0),
                "number_of_instances": study_data.get("numberOfInstances", 0),
                "series": [],
                "linked_images": []
            }

            # Extract modality
            modalities = study_data.get("modality", [])
            if modalities:
                result["modality"] = modalities[0].get("code")

            # Extract MIMIC study ID
            mimic_study_id = None
            for identifier in study_data.get("identifier", []):
                if identifier.get("system") == "urn:mimic-cxr:study":
                    mimic_study_id = identifier.get("value")
                    result["mimic_study_id"] = mimic_study_id

            # Extract series information
            for series in study_data.get("series", []):
                series_entry = {
                    "uid": series.get("uid"),
                    "number": series.get("number"),
                    "modality": series.get("modality", {}).get("code"),
                    "description": series.get("description"),
                    "number_of_instances": series.get("numberOfInstances", 0),
                    "instances": []
                }

                for instance in series.get("instance", []):
                    series_entry["instances"].append({
                        "uid": instance.get("uid"),
                        "sop_class": instance.get("sopClass", {}).get("code"),
                        "number": instance.get("number")
                    })

                result["series"].append(series_entry)

            # Get linked MIMIC-CXR images from database
            if mimic_study_id:
                try:
                    sql = """
                        SELECT ImageID, SubjectID, ViewPosition, ImagePath
                        FROM VectorSearch.MIMICCXRImages
                        WHERE StudyID = ?
                    """
                    cursor.execute(sql, (mimic_study_id,))
                    for row in cursor.fetchall():
                        result["linked_images"].append({
                            "image_id": row[0],
                            "subject_id": row[1],
                            "view_position": row[2],
                            "image_path": row[3]
                        })
                except Exception as e:
                    result["linked_images_error"] = str(e)

            cursor.close()
            conn.close()

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "get_radiology_reports":
            study_id = arguments.get("study_id")
            patient_id = arguments.get("patient_id")
            include_full_text = arguments.get("include_full_text", True)

            if not study_id and not patient_id:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "Either study_id or patient_id is required"})
                )]

            # Import the FHIR radiology adapter
            from src.adapters.fhir_radiology_adapter import FHIRRadiologyAdapter

            adapter = FHIRRadiologyAdapter()

            # Build search parameters
            search_url = f"{adapter.fhir_base_url}/DiagnosticReport"
            params = {"category": "RAD"}  # Radiology category

            if study_id:
                params["imaging-study"] = f"ImagingStudy/{study_id}"
            if patient_id:
                params["subject"] = f"Patient/{patient_id}"

            response = adapter.session.get(search_url, params=params)

            reports = []
            if response.status_code == 200:
                bundle = response.json()
                for entry in bundle.get("entry", []):
                    resource = entry.get("resource", {})

                    report_entry = {
                        "id": resource.get("id"),
                        "status": resource.get("status"),
                        "issued": resource.get("issued"),
                        "conclusion": resource.get("conclusion"),
                        "imaging_study_references": []
                    }

                    # Extract imaging study references
                    for study_ref in resource.get("imagingStudy", []):
                        report_entry["imaging_study_references"].append(
                            study_ref.get("reference")
                        )

                    # Extract full text if requested
                    if include_full_text:
                        for content in resource.get("presentedForm", []):
                            if content.get("contentType") == "text/plain":
                                data = content.get("data")
                                if data:
                                    import base64
                                    try:
                                        report_entry["full_text"] = base64.b64decode(data).decode("utf-8")
                                    except Exception:
                                        report_entry["full_text"] = data

                    reports.append(report_entry)

            return [TextContent(
                type="text",
                text=json.dumps({
                    "study_id": study_id,
                    "patient_id": patient_id,
                    "reports": reports,
                    "total_count": len(reports)
                }, indent=2)
            )]

        elif name == "search_patients_with_imaging":
            modality = arguments.get("modality")
            finding_text = arguments.get("finding_text")
            limit = arguments.get("limit", 20)

            # Import the FHIR radiology adapter
            from src.adapters.fhir_radiology_adapter import FHIRRadiologyAdapter

            adapter = FHIRRadiologyAdapter()

            # Strategy: Search ImagingStudy resources and extract unique patients
            search_url = f"{adapter.fhir_base_url}/ImagingStudy"
            params = {"_count": limit * 3}  # Fetch more to get unique patients

            if modality:
                params["modality"] = modality

            response = adapter.session.get(search_url, params=params)

            patients = {}  # patient_id -> patient_data
            if response.status_code == 200:
                bundle = response.json()
                for entry in bundle.get("entry", []):
                    resource = entry.get("resource", {})
                    patient_ref = resource.get("subject", {}).get("reference", "")

                    if patient_ref and patient_ref not in patients:
                        # Extract patient ID
                        patient_id = patient_ref.replace("Patient/", "")

                        # Get patient details
                        patient_url = f"{adapter.fhir_base_url}/Patient/{patient_id}"
                        patient_response = adapter.session.get(patient_url)

                        if patient_response.status_code == 200:
                            patient_data = patient_response.json()
                            patient_name = "Unknown"
                            names = patient_data.get("name", [])
                            if names:
                                name = names[0]
                                parts = name.get("given", []) + [name.get("family", "")]
                                patient_name = " ".join(p for p in parts if p)

                            patients[patient_ref] = {
                                "id": patient_id,
                                "name": patient_name,
                                "birth_date": patient_data.get("birthDate"),
                                "gender": patient_data.get("gender"),
                                "study_count": 0
                            }

                        if len(patients) >= limit:
                            break

                    # Increment study count
                    if patient_ref in patients:
                        patients[patient_ref]["study_count"] += 1

            # If finding_text specified, filter by DiagnosticReport conclusions
            if finding_text and patients:
                filtered_patients = {}
                for patient_ref, patient_data in patients.items():
                    # Search reports for this patient
                    report_url = f"{adapter.fhir_base_url}/DiagnosticReport"
                    report_params = {
                        "subject": patient_ref,
                        "category": "RAD"
                    }
                    report_response = adapter.session.get(report_url, params=report_params)

                    if report_response.status_code == 200:
                        report_bundle = report_response.json()
                        for report_entry in report_bundle.get("entry", []):
                            report = report_entry.get("resource", {})
                            conclusion = report.get("conclusion", "").lower()
                            if finding_text.lower() in conclusion:
                                filtered_patients[patient_ref] = patient_data
                                break

                patients = filtered_patients

            return [TextContent(
                type="text",
                text=json.dumps({
                    "modality": modality,
                    "finding_text": finding_text,
                    "patients": list(patients.values())[:limit],
                    "total_count": len(patients)
                }, indent=2)
            )]

        elif name == "list_radiology_queries":
            category = arguments.get("category", "all")

            # Define available query templates
            query_catalog = {
                "patient": [
                    {
                        "name": "get_patient_imaging_studies",
                        "description": "Retrieve all imaging studies for a patient",
                        "parameters": ["patient_id", "date_from?", "date_to?", "modality?"],
                        "example": "get_patient_imaging_studies(patient_id='p10002428')"
                    }
                ],
                "study": [
                    {
                        "name": "get_imaging_study_details",
                        "description": "Get detailed information for a specific imaging study",
                        "parameters": ["study_id"],
                        "example": "get_imaging_study_details(study_id='study-s50414267')"
                    },
                    {
                        "name": "search_medical_images",
                        "description": "Semantic search for medical images using NV-CLIP",
                        "parameters": ["query", "limit?"],
                        "example": "search_medical_images(query='pneumonia chest x-ray')"
                    }
                ],
                "report": [
                    {
                        "name": "get_radiology_reports",
                        "description": "Retrieve diagnostic reports for studies or patients",
                        "parameters": ["study_id?", "patient_id?", "include_full_text?"],
                        "example": "get_radiology_reports(patient_id='p10002428')"
                    }
                ],
                "encounter": [
                    {
                        "name": "get_encounter_imaging",
                        "description": "Get imaging studies for a specific encounter",
                        "parameters": ["encounter_id", "include_reports?"],
                        "example": "get_encounter_imaging(encounter_id='enc-123')"
                    }
                ]
            }

            # Filter by category
            if category == "all":
                result = query_catalog
            elif category in query_catalog:
                result = {category: query_catalog[category]}
            else:
                result = {"error": f"Unknown category '{category}'. Valid: patient, study, report, encounter, all"}

            return [TextContent(
                type="text",
                text=json.dumps({
                    "category": category,
                    "queries": result,
                    "total_queries": sum(len(v) for v in query_catalog.values()) if category == "all" else len(result.get(category, []))
                }, indent=2)
            )]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        import traceback
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        )]



async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
