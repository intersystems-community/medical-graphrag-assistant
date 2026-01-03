# Research: Full UX Verification Tests

## Phase 0: Outline & Research Findings

This document consolidates research and architectural decisions for the comprehensive UX verification suite.

### 1. Robust Streamlit Testing Patterns
- **Decision**: Use `data-testid` based locators combined with "stStatusWidget" monitoring.
- **Rationale**: Streamlit's reactive rendering causes frequent element detachment. Monitoring the status widget ensures the app has finished processing before assertions are made.
- **Alternatives considered**: Fixed timeouts (rejected as fragile/slow), text-based locators (rejected due to medical terminology variability).

### 2. Remote Authentication Strategy
- **Decision**: Conditional Login Fixture with `TEST_PASSWORD` environment variable.
- **Rationale**: Enables the same suite to run against open development environments and secured production EC2 instances. It uses a "find-and-login" strategy that degrades gracefully if auth is not enabled.
- **Alternatives considered**: Hardcoded credentials (rejected for security), dedicated test user DB (rejected as out of scope for UX-only tests).

### 3. Visualization Verification (Plotly & Agraph)
- **Decision**: Assert existence of SVG trace containers for Plotly and frame-based inspection for `streamlit-agraph`.
- **Rationale**: These elements render complex canvases or SVGs that standard text locators cannot see. Targeted CSS selectors (`.js-plotly-plot`, `[data-testid="agraph"]`) are required.
- **Alternatives considered**: Screenshot comparison (rejected due to font/rendering differences on EC2), direct JS execution (kept as a fallback).

### 4. Structured Reporting
- **Decision**: Multi-reporter setup (HTML + JSON + JUnit).
- **Rationale**: HTML provides visual traces for human debugging; JSON/JUnit allows for automated pass/fail parsing in CI/CD pipelines (e.g., AWS CodePipeline).
- **Alternatives considered**: Console output only (rejected as non-persistent).

### 5. EC2 Connectivity & Connectivity
- **Decision**: Target the application directly via public URL; internal service health (IRIS/NIM) verified via UI state.
- **Rationale**: The UX suite should simulate a real user. Managing SSH tunnels within the test runner adds unnecessary complexity.
- **Alternatives considered**: Run runner *on* the EC2 instance (rejected as it doesn't test public reachability).

## Resolution of Technical Context Unknowns

| Unknown | Resolution |
|---------|------------|
| Auth Pattern | Conditional login via `TEST_PASSWORD` |
| Connectivity | Direct URL targeting via `TARGET_URL` |
| Reporting | JSON/JUnit + HTML |
| Viz Testing | CSS selector tracing for SVG elements |
