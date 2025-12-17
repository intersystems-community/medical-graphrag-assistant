# Feature Specification: GraphRAG Details Panel Enhancement

**Feature Branch**: `005-graphrag-details-panel`
**Created**: 2025-12-10
**Status**: Draft
**Input**: User description: "Add GraphRAG info to details dropdown panel, such as entities found, rendering of graph using same force-directed rendering for the main results, etc"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Entities Found in Query Results (Priority: P1)

As a medical researcher reviewing AI-generated responses, I want to see the specific entities (symptoms, conditions, medications, etc.) that were discovered during the GraphRAG search so I can understand what data informed the response.

**Why this priority**: This is the core value proposition - users need transparency into what entities the system found to trust and verify the AI's reasoning. Without this, users cannot validate results.

**Independent Test**: Can be fully tested by submitting any medical query and expanding the details dropdown to verify entity information is displayed.

**Acceptance Scenarios**:

1. **Given** a completed AI response with GraphRAG results, **When** the user expands the "Show Execution Details" dropdown, **Then** a list of all entities found during the search is displayed with their types (symptom, condition, medication, etc.)
2. **Given** the details panel is expanded, **When** the user views the entities list, **Then** each entity shows its name, type, and frequency/relevance score
3. **Given** a query that returns no entities, **When** the user expands the details panel, **Then** a message indicates "No entities found" rather than an empty section

---

### User Story 2 - View Interactive Entity Relationship Graph (Priority: P2)

As a medical researcher, I want to see a force-directed graph visualization of the entities and their relationships within the details panel so I can understand how the discovered information connects.

**Why this priority**: Visual relationship mapping provides deeper insight than a list alone, but requires entities to be displayed first (P1). This enhances understanding of complex medical relationships.

**Independent Test**: Can be fully tested by submitting a query that returns multiple related entities and verifying the graph renders with draggable nodes and visible connections.

**Acceptance Scenarios**:

1. **Given** a completed response with multiple related entities, **When** the user expands the details panel, **Then** a force-directed graph displays showing entities as nodes and relationships as edges
2. **Given** the graph is displayed, **When** the user drags a node, **Then** the graph layout dynamically adjusts (same interaction as main results graph)
3. **Given** the graph is displayed, **When** the user scrolls within the graph area, **Then** the graph zooms in/out appropriately
4. **Given** a query with fewer than 2 related entities, **When** the user expands details, **Then** the graph section is hidden (not enough data to visualize relationships)

---

### User Story 3 - View Tool Execution Summary (Priority: P3)

As a user reviewing AI responses, I want to see a summary of which tools were called, in what order, and how long each took so I can understand the system's reasoning process.

**Why this priority**: Provides execution transparency but is supplementary to the entity/graph information. Useful for debugging and understanding system behavior.

**Independent Test**: Can be fully tested by submitting any query and verifying the tool execution timeline appears in the details panel.

**Acceptance Scenarios**:

1. **Given** a completed AI response, **When** the user expands the details panel, **Then** a list of tools executed is shown in chronological order
2. **Given** the tool list is displayed, **When** the user views a tool entry, **Then** they see the tool name, execution duration, and success/failure status
3. **Given** a tool failed during execution, **When** the user views details, **Then** the failed tool is visually distinguished (different styling) with error context

---

### Edge Cases

- What happens when the GraphRAG search times out before returning entities? Display partial results with a timeout indicator.
- How does the system handle extremely large entity counts (100+ entities)? Limit display to top 50 most relevant with "Show more" option.
- What happens when the graph has circular relationships? The force-directed layout handles cycles naturally through physics simulation.
- How does the panel behave on mobile/small screens? Graph collapses to a simplified list view on screens narrower than 768px.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display all entities discovered during GraphRAG search within the details dropdown panel
- **FR-002**: System MUST categorize entities by type (symptom, condition, medication, procedure, anatomy, etc.)
- **FR-003**: System MUST show entity relevance/frequency scores alongside each entity name
- **FR-004**: System MUST render an interactive force-directed graph showing entity relationships when 2+ related entities exist
- **FR-005**: System MUST use the same force-directed graph rendering approach as the main results area for visual consistency
- **FR-006**: Graph nodes MUST be draggable with dynamic layout adjustment
- **FR-007**: Graph MUST support zoom via scroll and pan via click-drag on background
- **FR-008**: System MUST display tool execution sequence with timing information
- **FR-009**: System MUST visually distinguish failed tool executions from successful ones
- **FR-010**: System MUST gracefully handle empty results (no entities found) with appropriate messaging
- **FR-011**: System MUST limit entity display to top 50 most relevant when count exceeds 50, with option to expand
- **FR-012**: Details panel MUST maintain collapsed/expanded state within a session
- **FR-013**: Clicking an entity (in list or graph) MUST display a tooltip showing entity details including source documents and contextual information
- **FR-014**: Details panel MUST organize content into collapsible sub-sections (Entities, Graph, Tools), all expanded by default
- **FR-015**: Each sub-section MUST be independently collapsible/expandable by the user

### Key Entities

- **Entity**: A medical concept extracted from GraphRAG (name, type, relevance score, source document references)
- **Relationship**: A connection between two entities (source entity, target entity, relationship type, strength)
- **Tool Execution**: A record of tool invocation (tool name, start time, duration, status, parameters, result summary)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view entity information within 1 second of expanding the details panel
- **SC-002**: Force-directed graph renders and becomes interactive within 2 seconds for graphs with up to 50 nodes
- **SC-003**: 90% of users can identify at least 3 entities that informed a response within 30 seconds of viewing details
- **SC-004**: Graph interaction (drag, zoom, pan) responds within 100ms for smooth user experience
- **SC-005**: Tool execution summary displays complete timeline for 100% of queries that use tools

## Clarifications

### Session 2025-12-10

- Q: What happens when a user clicks on an entity in the list or graph? → A: Click shows tooltip with entity details (sources, context)
- Q: How should sections (entities, graph, tools) be organized in the details panel? → A: Collapsible sub-sections, all visible/expanded by default

## Assumptions

- The existing "Show Execution Details" dropdown provides the container for this enhancement
- GraphRAG already returns entity and relationship data that can be surfaced in the UI
- The force-directed graph component used in main results is reusable for the details panel
- Users are familiar with the existing details dropdown interaction pattern
- Entity type classification is already performed by the GraphRAG system

## Out of Scope

- Editing or filtering entities from the details panel
- Exporting entity/graph data to external formats
- Comparing entities across multiple queries
- Real-time entity updates during streaming responses (entities shown after completion only)
