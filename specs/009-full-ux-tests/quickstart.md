# Quickstart: Full UX Verification Tests

## Setup

1. **Install dependencies**:
   ```bash
   pip install pytest-playwright
   playwright install chromium
   ```

2. **Configure environment**:
   ```bash
   export TARGET_URL="http://54.209.84.148:8501"  # EC2 Public URL
   export TEST_PASSWORD="your-admin-password"     # Optional
   ```

## Running Tests

### Full Suite
```bash
pytest tests/ux/playwright/
```

### Specific Feature (e.g., Memory)
```bash
pytest tests/ux/playwright/test_memory.py
```

### With Headed Browser (Debugging)
```bash
pytest --headed tests/ux/playwright/
```

## Viewing Reports

- **HTML Report**: Open `playwright-report/index.html` after a run.
- **JSON Output**: Parse `test-results.json` for automated status checks.
