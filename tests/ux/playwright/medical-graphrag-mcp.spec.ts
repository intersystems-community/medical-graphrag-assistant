/**
 * Medical GraphRAG Assistant UX Test Suite
 *
 * IMPORTANT: These tests are designed to be executed via the Playwright MCP server
 * as per the project constitution (Principle VI).
 *
 * Execution: Use Claude Code with Playwright MCP connected to run these tests.
 * The test definitions below map to MCP tool calls.
 *
 * Target: http://54.209.84.148:8501
 */

/**
 * Test Suite Structure for Playwright MCP Execution
 *
 * Each test case maps to a sequence of Playwright MCP tool calls:
 * - browser_navigate: Navigate to URL
 * - browser_snapshot: Capture page state for assertions
 * - browser_click: Click elements
 * - browser_type: Type into inputs
 * - browser_wait_for: Wait for elements/text
 */

export const TEST_CONFIG = {
  baseUrl: 'http://54.209.84.148:8501',
  timeouts: {
    pageLoad: 10000,
    aiResponse: 30000,
    elementVisible: 5000,
  }
};

/**
 * Test Case Definitions
 * Format: { id, name, description, steps[], assertions[] }
 */
export const TEST_CASES = {
  // ============================================================================
  // User Story 1: Application Accessibility (TC-001 to TC-004)
  // ============================================================================

  'TC-001': {
    id: 'TC-001',
    name: 'Page Load Verification',
    description: 'Verify the application loads successfully',
    mcpSteps: [
      { tool: 'browser_navigate', params: { url: 'http://54.209.84.148:8501' } },
      { tool: 'browser_wait_for', params: { time: 3 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'contains_text', value: 'Agentic Medical Chat' }
    ]
  },

  'TC-002': {
    id: 'TC-002',
    name: 'Title Verification',
    description: 'Verify page title contains "Agentic Medical Chat"',
    mcpSteps: [
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'contains_text', value: 'Agentic Medical Chat' }
    ]
  },

  'TC-003': {
    id: 'TC-003',
    name: 'Sidebar Visible',
    description: 'Verify sidebar with "Available Tools" header is visible',
    mcpSteps: [
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'contains_text', value: 'Available Tools' }
    ]
  },

  'TC-004': {
    id: 'TC-004',
    name: 'Chat Input Present',
    description: 'Verify chat input area exists and is functional',
    mcpSteps: [
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'element_visible', selector: 'textarea', description: 'chat input' }
    ]
  },

  // ============================================================================
  // User Story 2: Example Button Interactions (TC-005 to TC-007)
  // ============================================================================

  'TC-005': {
    id: 'TC-005',
    name: 'Common Symptoms Button',
    description: 'Verify "Common Symptoms" button triggers AI response',
    mcpSteps: [
      { tool: 'browser_snapshot', params: {} },
      { tool: 'browser_click', params: { element: 'Common Symptoms button', ref: 'button:Common Symptoms' } },
      { tool: 'browser_wait_for', params: { time: 30 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'response_received', description: 'AI response with medical content' }
    ]
  },

  'TC-006': {
    id: 'TC-006',
    name: 'Symptom Chart Button',
    description: 'Verify "Symptom Chart" button renders visualization',
    mcpSteps: [
      { tool: 'browser_click', params: { element: 'Symptom Chart button', ref: 'button:Symptom Chart' } },
      { tool: 'browser_wait_for', params: { time: 30 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'element_visible', description: 'chart visualization' }
    ]
  },

  'TC-007': {
    id: 'TC-007',
    name: 'Knowledge Graph Button',
    description: 'Verify "Knowledge Graph" button renders network graph',
    mcpSteps: [
      { tool: 'browser_click', params: { element: 'Knowledge Graph button', ref: 'button:Knowledge Graph' } },
      { tool: 'browser_wait_for', params: { time: 30 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'element_visible', description: 'network graph visualization' }
    ]
  },

  // ============================================================================
  // User Story 3: Manual Chat Input (TC-008)
  // ============================================================================

  'TC-008': {
    id: 'TC-008',
    name: 'Manual Chat Input',
    description: 'Verify manual text input produces AI response',
    mcpSteps: [
      { tool: 'browser_snapshot', params: {} },
      { tool: 'browser_type', params: {
        element: 'chat input',
        ref: 'textarea',
        text: 'What are common symptoms?',
        submit: true
      }},
      { tool: 'browser_wait_for', params: { time: 30 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'response_received', description: 'AI response with symptom information' }
    ]
  },

  // ============================================================================
  // User Story 4: Tool List Verification (TC-009)
  // ============================================================================

  'TC-009': {
    id: 'TC-009',
    name: 'Tool List Verification',
    description: 'Verify sidebar displays expected MCP tools',
    mcpSteps: [
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'contains_text', value: 'search_fhir_documents' },
      { type: 'contains_text', value: 'hybrid_search' },
      { type: 'contains_text', value: 'plot_entity_network' }
    ]
  },

  // ============================================================================
  // User Story 5: Clear Chat (TC-010)
  // ============================================================================

  'TC-010': {
    id: 'TC-010',
    name: 'Clear Chat',
    description: 'Verify Clear button resets conversation',
    mcpSteps: [
      { tool: 'browser_click', params: { element: 'Clear button', ref: 'button:Clear' } },
      { tool: 'browser_wait_for', params: { time: 2 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'chat_cleared', description: 'no previous messages visible' }
    ]
  },

  // ============================================================================
  // Feature 005: GraphRAG Details Panel (TC-011 to TC-015)
  // ============================================================================

  'TC-011': {
    id: 'TC-011',
    name: 'Details Expander Visible',
    description: 'Verify "Show Execution Details" expander appears after query response',
    prerequisite: 'TC-005',
    mcpSteps: [
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'contains_text', value: 'Show Execution Details' }
    ]
  },

  'TC-012': {
    id: 'TC-012',
    name: 'Entity Section Visible',
    description: 'Verify entity section appears when details panel is expanded',
    prerequisite: 'TC-011',
    mcpSteps: [
      { tool: 'browser_click', params: { element: 'Show Execution Details expander', ref: 'text:Show Execution Details' } },
      { tool: 'browser_wait_for', params: { time: 2 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'contains_text', value: 'Entities Found' }
    ]
  },

  'TC-013': {
    id: 'TC-013',
    name: 'Graph Section Visible',
    description: 'Verify relationship graph section appears in details panel',
    prerequisite: 'TC-012',
    mcpSteps: [
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'contains_text', value: 'Entity Relationships' }
    ]
  },

  'TC-014': {
    id: 'TC-014',
    name: 'Tool Execution Section Visible',
    description: 'Verify tool execution timeline appears in details panel',
    prerequisite: 'TC-012',
    mcpSteps: [
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'contains_text', value: 'Tool Execution' }
    ]
  },

  'TC-015': {
    id: 'TC-015',
    name: 'Sub-Sections Collapsible',
    description: 'Verify each sub-section can be independently collapsed',
    prerequisite: 'TC-012',
    mcpSteps: [
      { tool: 'browser_click', params: { element: 'Entities Found expander', ref: 'text:Entities Found' } },
      { tool: 'browser_wait_for', params: { time: 1 } },
      { tool: 'browser_snapshot', params: {} },
      { tool: 'browser_click', params: { element: 'Entities Found expander', ref: 'text:Entities Found' } },
      { tool: 'browser_wait_for', params: { time: 1 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'toggle_works', description: 'section collapses and expands' }
    ]
  },

  // ============================================================================
  // Feature 007: FHIR Radiology Integration (TC-016 to TC-021)
  // ============================================================================

  'TC-016': {
    id: 'TC-016',
    name: 'Radiology Tools Listed in Sidebar',
    description: 'Verify radiology MCP tools appear in Available Tools sidebar',
    mcpSteps: [
      { tool: 'browser_navigate', params: { url: 'http://54.209.84.148:8501' } },
      { tool: 'browser_wait_for', params: { time: 3 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'contains_text', value: 'get_patient_imaging_studies' },
      { type: 'contains_text', value: 'get_radiology_reports' }
    ]
  },

  'TC-017': {
    id: 'TC-017',
    name: 'Radiology Query via Chat',
    description: 'Verify radiology query produces AI response with imaging data',
    mcpSteps: [
      { tool: 'browser_snapshot', params: {} },
      { tool: 'browser_type', params: {
        element: 'chat input',
        ref: 'textarea',
        text: 'Show me available radiology queries',
        submit: true
      }},
      { tool: 'browser_wait_for', params: { time: 30 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'response_received', description: 'AI response with radiology query information' },
      { type: 'contains_text', value: 'patient' }
    ]
  },

  'TC-018': {
    id: 'TC-018',
    name: 'Medical Image Search Query',
    description: 'Verify medical image search returns chest X-ray results',
    mcpSteps: [
      { tool: 'browser_click', params: { element: 'Clear button', ref: 'button:Clear' } },
      { tool: 'browser_wait_for', params: { time: 2 } },
      { tool: 'browser_type', params: {
        element: 'chat input',
        ref: 'textarea',
        text: 'Search for chest X-rays showing pneumonia',
        submit: true
      }},
      { tool: 'browser_wait_for', params: { time: 30 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'response_received', description: 'AI response with image search results' }
    ]
  },

  'TC-019': {
    id: 'TC-019',
    name: 'Patient Imaging Studies Query',
    description: 'Verify get_patient_imaging_studies tool can be invoked via chat',
    mcpSteps: [
      { tool: 'browser_click', params: { element: 'Clear button', ref: 'button:Clear' } },
      { tool: 'browser_wait_for', params: { time: 2 } },
      { tool: 'browser_type', params: {
        element: 'chat input',
        ref: 'textarea',
        text: 'Find patients who have imaging studies',
        submit: true
      }},
      { tool: 'browser_wait_for', params: { time: 30 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'response_received', description: 'AI response with patient imaging information' }
    ]
  },

  'TC-020': {
    id: 'TC-020',
    name: 'Radiology Tool Execution Details',
    description: 'Verify execution details show radiology tool was used',
    prerequisite: 'TC-017',
    mcpSteps: [
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'contains_text', value: 'Show Execution Details' }
    ]
  },

  'TC-021': {
    id: 'TC-021',
    name: 'Radiology Tool in Execution Timeline',
    description: 'Verify radiology tool appears in execution timeline after query',
    prerequisite: 'TC-020',
    mcpSteps: [
      { tool: 'browser_click', params: { element: 'Show Execution Details expander', ref: 'text:Show Execution Details' } },
      { tool: 'browser_wait_for', params: { time: 2 } },
      { tool: 'browser_snapshot', params: {} }
    ],
    assertions: [
      { type: 'contains_text', value: 'Tool Execution' }
    ]
  }
};

/**
 * Test Execution Prompt for Claude Code with Playwright MCP
 *
 * Copy this prompt to execute the full test suite:
 */
export const EXECUTION_PROMPT = `
Run UX tests for Medical GraphRAG Assistant at http://54.209.84.148:8501

Execute these tests in order, stopping on first failure (fail-fast):

## Core Application Tests (TC-001 to TC-010)

1. [TC-001] Navigate to URL, verify page loads with "Agentic Medical Chat" visible
2. [TC-002] Verify page title contains "Agentic Medical Chat"
3. [TC-003] Verify sidebar is visible with "Available Tools" header
4. [TC-004] Verify chat input area (textarea) is present
5. [TC-005] Click "Common Symptoms" button, wait 30s for AI response
6. [TC-006] Click "Symptom Chart" button, verify chart appears (30s timeout)
7. [TC-007] Click "Knowledge Graph" button, verify network graph appears (30s timeout)
8. [TC-008] Type "What are common symptoms?" in chat, verify response (30s timeout)
9. [TC-009] Verify sidebar contains: search_fhir_documents, hybrid_search, plot_entity_network
10. [TC-010] Click "Clear" button, verify chat history cleared

## Feature 005: Details Panel Tests (TC-011 to TC-015)

11. [TC-011] After response from TC-005, verify "Show Execution Details" expander visible
12. [TC-012] Click "Show Execution Details", verify "Entities Found" section visible
13. [TC-013] Verify "Entity Relationships" section visible in details
14. [TC-014] Verify "Tool Execution" section visible with tools used
15. [TC-015] Click "Entities Found" header to collapse, click again to expand - verify toggle works

## Feature 007: FHIR Radiology Integration Tests (TC-016 to TC-021)

16. [TC-016] Navigate to URL, verify sidebar contains "get_patient_imaging_studies" and "get_radiology_reports"
17. [TC-017] Type "Show me available radiology queries" in chat, verify response with "patient"
18. [TC-018] Clear chat, type "Search for chest X-rays showing pneumonia", verify AI response
19. [TC-019] Clear chat, type "Find patients who have imaging studies", verify AI response
20. [TC-020] After radiology query, verify "Show Execution Details" expander visible
21. [TC-021] Click "Show Execution Details", verify "Tool Execution" section visible

For each test:
- Use browser_navigate, browser_snapshot, browser_click, browser_type, browser_wait_for
- Report PASS/FAIL status with timing
- On failure: capture screenshot via browser_take_screenshot, report error, STOP execution

At end: Report summary (X/21 passed, total time)
`;
