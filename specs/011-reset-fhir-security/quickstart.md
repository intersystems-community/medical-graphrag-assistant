# Quickstart: Reset FHIR Security Configuration

**Goal**: Resolve "401 Unauthorized" errors by resetting IRIS security settings.

## 1. Prerequisites

- IRIS container running (`docker ps` shows healthy)
- Python environment active (`source venv/bin/activate`)
- SSH/Executive access to the container (usually via `docker exec`)

## 2. Reset Procedure

We provide a utility script to reset the security configuration to a known good state.

```bash
# 1. Run the reset script (connects via Native SDK)
# Note: You may need to provide superuser credentials if defaults fail
python src/setup/reset_fhir_security.py --username _SYSTEM --password SYS

# 2. Verify the fix via CLI health check
python -m src.cli check-health
```

## 3. Manual Reset (Fallback)

If the script fails to connect, execute this inside the container:

```bash
docker exec -it iris-fhir iris session IRIS
```

Inside the IRIS shell:

```objectscript
zn "%SYS"
// Reset password
do ##class(Security.Users).ChangePassword("_SYSTEM", "SYS")
// Enable password auth for FHIR
set props("AuthenEnabled") = 32
do ##class(Security.Applications).Modify("/csp/healthshare/demo/fhir/r4", .props)
halt
```

## 4. Verification

Use `curl` to verify access:

```bash
curl -v -u _SYSTEM:SYS http://localhost:32783/csp/healthshare/demo/fhir/r4/metadata
```

Expected output: `HTTP/1.1 200 OK`
