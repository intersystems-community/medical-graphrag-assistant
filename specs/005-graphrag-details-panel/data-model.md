# Data Model: GraphRAG Details Panel Enhancement

**Feature**: 005-graphrag-details-panel
**Date**: 2025-12-10

## Overview

This feature introduces UI-layer data structures for displaying GraphRAG information in the details panel. No database schema changes required - all data is derived from existing MCP tool results.

## Entities

### DisplayEntity

Represents a medical entity extracted from GraphRAG results for display purposes.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | string | Unique identifier | Required, UUID or hash |
| name | string | Entity display name | Required, max 200 chars |
| type | EntityType | Category of entity | Required, enum value |
| score | float | Relevance/frequency score | 0.0 to 1.0 |
| sources | List[SourceReference] | Document references | Optional, max 10 |
| context | string | Surrounding text context | Optional, max 500 chars |

### EntityType (Enum)

| Value | Description |
|-------|-------------|
| SYMPTOM | Patient-reported or observed symptom |
| CONDITION | Diagnosed medical condition |
| MEDICATION | Drug or pharmaceutical |
| PROCEDURE | Medical procedure or intervention |
| ANATOMY | Body part or anatomical structure |
| LAB_RESULT | Laboratory test result |
| VITAL_SIGN | Vital sign measurement |
| OTHER | Unclassified entity |

### DisplayRelationship

Represents a connection between two entities.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | string | Unique identifier | Required |
| source_id | string | Source entity ID | Required, FK to DisplayEntity |
| target_id | string | Target entity ID | Required, FK to DisplayEntity |
| relationship_type | string | Type of relationship | Required, e.g., "causes", "treats" |
| strength | float | Relationship confidence | 0.0 to 1.0 |

### SourceReference

Reference to source document for an entity.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| document_id | string | FHIR document ID | Required |
| document_type | string | Type of document | e.g., "ClinicalNote", "DiagnosticReport" |
| excerpt | string | Relevant text excerpt | Max 200 chars |

### ToolExecution

Record of a tool invocation during the response generation.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| id | string | Unique identifier | Required |
| tool_name | string | MCP tool name | Required |
| start_time | datetime | When tool started | Required |
| duration_ms | int | Execution time in milliseconds | Required, >= 0 |
| status | ExecutionStatus | Success/failure state | Required |
| parameters | dict | Input parameters | Optional, sanitized |
| result_summary | string | Brief result description | Max 200 chars |
| error_message | string | Error details if failed | Optional |

### ExecutionStatus (Enum)

| Value | Description |
|-------|-------------|
| SUCCESS | Tool completed successfully |
| FAILED | Tool encountered an error |
| TIMEOUT | Tool exceeded time limit |
| SKIPPED | Tool was not executed |

### DetailsPanel

Aggregate structure containing all details panel data.

| Field | Type | Description |
|-------|------|-------------|
| entities | List[DisplayEntity] | All discovered entities |
| relationships | List[DisplayRelationship] | Entity relationships |
| tool_executions | List[ToolExecution] | Tool call timeline |
| total_entity_count | int | Total entities before truncation |
| is_truncated | bool | Whether entity list was limited |
| query_text | string | Original user query |
| response_time_ms | int | Total response generation time |

## State Transitions

### Entity Selection State

```
[No Selection] -> (click entity) -> [Entity Selected]
[Entity Selected] -> (click same) -> [No Selection]
[Entity Selected] -> (click different) -> [Entity Selected (new)]
[Entity Selected] -> (collapse section) -> [No Selection]
```

### Section Collapse State

```
[All Expanded] -> (click Entities header) -> [Entities Collapsed]
[Entities Collapsed] -> (click Entities header) -> [Entities Expanded]
```

Each section (Entities, Graph, Tools) maintains independent collapse state in session.

## Validation Rules

1. **Entity Names**: Must not be empty; HTML entities escaped for display
2. **Scores**: Must be in range [0.0, 1.0]; displayed as percentage
3. **Relationships**: source_id and target_id must reference existing entities
4. **Tool Executions**: Must be ordered by start_time ascending
5. **Truncation**: If total_entity_count > 50, is_truncated = true

## Data Flow

```
MCP Tool Results (JSON)
        │
        ▼
┌─────────────────────┐
│ parse_tool_results()│
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│   DetailsPanel      │
│   (in-memory)       │
└─────────────────────┘
        │
        ├──────────────────┬──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Entity List   │  │ Relationship  │  │ Tool Timeline │
│ Component     │  │ Graph         │  │ Component     │
└───────────────┘  └───────────────┘  └───────────────┘
```

## Session State Keys

| Key | Type | Purpose |
|-----|------|---------|
| `details_selected_entity` | string | Currently selected entity ID |
| `details_entities_expanded` | bool | Entities section state |
| `details_graph_expanded` | bool | Graph section state |
| `details_tools_expanded` | bool | Tools section state |
| `details_show_all_entities` | bool | Whether to show full entity list |
