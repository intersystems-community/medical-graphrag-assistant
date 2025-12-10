# Research: Playwright UX Tests

**Date**: 2025-12-10
**Feature**: 002-playwright-ux-tests

## Playwright MCP Server Capabilities

### Decision: Use @playwright/mcp@latest official package

**Rationale**: Official Playwright MCP server provides stable, well-documented tool interface for browser automation via Claude Code.

**Alternatives Considered**:
- Custom Playwright scripts: Requires separate execution environment, more complex CI setup
- Selenium: No MCP integration available
- Puppeteer: Less mature MCP support

### Available Playwright MCP Tools

Based on the Playwright MCP server, the following tools are available:

| Tool | Description | Use Case |
|------|-------------|----------|
| `browser_navigate` | Navigate to URL | Page load tests |
| `browser_click` | Click element by selector | Button interaction tests |
| `browser_type` | Type text into input | Chat input tests |
| `browser_screenshot` | Capture screenshot | Debugging failed tests |
| `browser_snapshot` | Get page accessibility snapshot | Element verification |
| `browser_wait` | Wait for element or timeout | Dynamic content tests |

### Streamlit Element Selectors

**Decision**: Use text-based and role-based selectors for Streamlit apps

**Rationale**: Streamlit generates dynamic class names and IDs. Text selectors are more stable.

**Key Selectors Identified**:

| Element | Selector Strategy | Example |
|---------|-------------------|---------|
| Page title | Text content | `text="Agentic Medical Chat"` |
| Example buttons | Button text | `button:has-text("Common Symptoms")` |
| Chat input | Placeholder/role | `textarea[placeholder*="Ask"]` or role-based |
| Sidebar header | Text content | `text="Available Tools"` |
| Clear button | Button text | `button:has-text("Clear")` |
| Tool list items | Bullet markers | `text="search_fhir_documents"` |

### Timeout Strategy

**Decision**: Use explicit timeouts per operation type

**Rationale**: Different operations have vastly different expected durations.

| Operation | Timeout | Rationale |
|-----------|---------|-----------|
| Page load | 10s | Initial HTTP response + Streamlit hydration |
| Static element | 5s | Already loaded, just locating |
| AI response | 30s | LLM inference + tool execution |
| Chart render | 15s | Data fetch + Plotly rendering |
| Screenshot | 3s | Quick capture operation |

### Test Execution Model

**Decision**: Single Claude Code conversation session

**Rationale**:
- Browser context persists across tests
- Consolidated pass/fail reporting
- Efficient - no repeated browser initialization
- Matches FR-010 requirement

**Test Order** (dependencies):
1. Page load (prerequisite for all)
2. Sidebar verification (static, fast)
3. Example buttons (tests core functionality)
4. Chat input (tests full pipeline)
5. Clear chat (cleanup capability)

## Error Handling Research

### Screenshot on Failure

**Decision**: Capture screenshot immediately when assertion fails

**Rationale**: Screenshots provide visual evidence for debugging without requiring reproduction.

### Failure Reporting Format

```text
TEST FAILED: [Test Name]
- Expected: [expected state]
- Actual: [actual state/error]
- Screenshot: [saved to path]
- Recommendation: [next debug step]
```

## Streamlit Application Analysis

**Target URL**: http://54.209.84.148:8501

**Key UI Elements** (from streamlit_app.py analysis):
- Title: "Agentic Medical Chat" (st.title)
- Sidebar header: "Available Tools" (st.header)
- Example buttons: 6 buttons with labels like "Common Symptoms", "Symptom Chart", "Knowledge Graph"
- Chat input: st.chat_input with placeholder "Ask anything..."
- Clear button: "Clear" in sidebar
- Tool list: 11 MCP tools displayed as bullet points

**Dynamic Content**:
- Chat responses appear in st.chat_message containers
- Charts render via st.plotly_chart (Plotly figures)
- Network graphs via streamlit-agraph (interactive)
- Loading states during LLM processing
