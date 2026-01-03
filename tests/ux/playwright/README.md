# Medical GraphRAG UX Verification Suite (Python)

Automated end-to-end verification tests for the Medical GraphRAG Assistant using Playwright and pytest.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install pytest-playwright pytest-html
playwright install chromium
```

### 2. Configure Environment
```bash
export TARGET_URL="http://13.218.19.254:8501"  # EC2 Public IP
export TEST_PASSWORD="your-admin-password"      # Optional
```

### 3. Run Tests
```bash
# Run all tests
pytest tests/ux/playwright/

# Run specific feature group
pytest tests/ux/playwright/test_search.py
pytest tests/ux/playwright/test_memory.py
pytest tests/ux/playwright/test_viz.py
pytest tests/ux/playwright/test_radiology.py
```

## 📊 Test Coverage

### Core Search ([test_search.py](test_search.py))
- UI element presence (sidebar, chat input)
- FHIR document search verification
- Knowledge graph search verification
- Hybrid search verification
- Image search (NV-CLIP) verification
- Entity statistics retrieval
- IRIS result decoding and preview

### Visualizations ([test_viz.py](test_viz.py))
- Plotly chart rendering and interactivity (hover)
- Streamlit-agraph network graph rendering

### Agent Memory ([test_memory.py](test_memory.py))
- Manual memory addition via Sidebar Editor
- Persistence check via "Browse Memories"
- Semantic recall verification in chat

### Radiology ([test_radiology.py](test_radiology.py))
- Patient imaging studies list
- Radiology report retrieval
- Search patients with imaging findings

## 📈 Reporting

- **HTML Report**: `playwright-report/report.html`
- **JUnit XML**: `playwright-report/results.xml`
- **Failures**: Screenshots and videos are saved in `test-results/` on failure.

## 🛠️ Configuration

The suite is configured via `pytest.ini` and `conftest.py`. It uses a **Conditional Login Fixture** to handle applications with or without authentication.
