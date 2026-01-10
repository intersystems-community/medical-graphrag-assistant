#!/bin/bash
# scripts/verify_fhir_reset_e2e.sh
# End-to-end verification for FHIR security reset.

set -e

echo "=== Starting E2E Verification for FHIR Security Reset ==="

# 1. Run reset-security
echo "[STEP 1] Running reset-security..."
python3 -m src.cli reset-security --username _SYSTEM --password SYS --fhir-app /csp/healthshare/demo/fhir/r4

# 2. Verify FHIR metadata access with requests
echo "[STEP 2] Verifying metadata access via curl..."
# Use default password since we just reset it
status_code=$(curl -s -o /dev/null -w "%{http_code}" -u _SYSTEM:SYS http://localhost:32783/csp/healthshare/demo/fhir/r4/metadata)

if [ "$status_code" -eq 200 ]; then
    echo "✅ FHIR Metadata accessed successfully (HTTP 200)"
else
    echo "❌ FHIR Metadata access failed (HTTP $status_code)"
    exit 1
fi

# 3. Verify Health Check CLI
echo "[STEP 3] Running health-check..."
python3 -m src.cli check-health | grep -A 5 "FHIR Auth"

echo "=== E2E Verification PASSED ==="
