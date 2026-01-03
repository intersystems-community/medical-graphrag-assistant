# Data Model: Full UX Verification Tests

## Entities

### TestRun
- **run_id**: UUID (uniquely identifies a full suite execution)
- **timestamp**: ISO8601 (start time)
- **environment**: String ('ec2-prod', 'local-dev', 'ci')
- **target_url**: URL (application endpoint tested)
- **browser**: String ('chromium', 'firefox', 'webkit')
- **status**: Enum ('PASS', 'FAIL', 'ERROR')

### TestCaseResult
- **test_id**: String (maps to FR-XXX in spec)
- **name**: String (e.g., 'Hybrid Search Verification')
- **outcome**: Enum ('PASS', 'FAIL', 'SKIPPED')
- **duration_ms**: Integer
- **error_message**: Text (if failed)
- **screenshot_path**: Path (optional, for failures)
- **trace_path**: Path (optional, for deep inspection)

### FeatureCoverageMap
- **feature_name**: String (e.g., 'FHIR Search')
- **requirement_id**: String (FR-XXX)
- **test_file**: Path (file containing the test)
- **is_implemented**: Boolean

## Validation Rules
- Every `TestCaseResult` must link to a `run_id`.
- `duration_ms` must be non-negative.
- `status` of `TestRun` is 'PASS' only if 100% of non-skipped `TestCaseResult` entries are 'PASS'.

## State Transitions
- **Pending**: Suite initialized, no tests run.
- **Running**: Browser context active, executing cases.
- **Completed**: Browser closed, reports generated.
- **Aborted**: Critical error (e.g., 404 on target URL) prevented suite from completing.
