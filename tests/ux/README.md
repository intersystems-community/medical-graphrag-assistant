# UX Verification Suite

This suite provides comprehensive automated tests for the Medical GraphRAG Assistant using Playwright and pytest.

## Prerequisites

- Python 3.11+
- Playwright dependencies: `pip install pytest-playwright pytest-html`
- Browser installation: `playwright install chromium`

## Configuration

Set the following environment variables:

- `TARGET_URL`: The URL of the application (e.g., `http://54.209.84.148:8501`)
- `TEST_PASSWORD`: (Optional) Admin password for the application login.

## Running Tests

### Run all tests
```bash
export TARGET_URL="http://your-ec2-url:8501"
pytest tests/ux/playwright/
```

### Run specific feature
```bash
pytest tests/ux/playwright/test_search.py
```

### Debugging (Headed mode)
```bash
pytest --headed tests/ux/playwright/
```

## Reports

- **HTML Report**: `playwright-report/report.html`
- **JUnit XML**: `playwright-report/results.xml`
- **Screenshots/Videos**: Found in `test-results/` on failure.
