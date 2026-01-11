# Specification: Reset FHIR Security Configuration

**Feature Branch**: `011-reset-fhir-security`  
**Created**: 2026-01-10  
**Status**: Draft  
**Input**: User description: "To fully resolve the FHIR 401 errors, a deeper reset of the IRIS FHIR server's security configuration would be required"

## User Scenarios & Testing

### User Story 1 - Secure FHIR Access (Priority: P1)

System administrators and automated scripts need reliable, authenticated access to the FHIR server to populate data and perform queries.

**Why this priority**: Without basic access, the core application features (search, graphrag) cannot function. This is a blocker.

**Independent Test**: Can be tested by running a curl command with credentials against the metadata endpoint.

**Acceptance Scenarios**:

1. **Given** the FHIR server is running, **When** a request is made to `/fhir/r4/metadata` with valid credentials, **Then** the server returns HTTP 200 and the CapabilityStatement.
2. **Given** the FHIR server is running, **When** a request is made with INVALID credentials, **Then** the server returns HTTP 401.
3. **Given** the reset script has run, **When** the `populate_full_graphrag_data.py` script executes, **Then** it completes without any 401 errors.

---

### User Story 2 - Automated Security Reset (Priority: P2)

Developers need a tool to reset security configurations to a known good state when environments drift or break.

**Why this priority**: Reduces debugging time and ensures consistent environments across dev/test/prod.

**Independent Test**: Running the reset tool updates passwords and permissions correctly.

**Acceptance Scenarios**:

1. **Given** a misconfigured environment (wrong password), **When** `fix-environment` (or equivalent) is run, **Then** the password is reset to the expected value.
2. **Given** a fresh environment, **When** the reset tool runs, **Then** it reports success and makes no destructive changes to data.

---

### Edge Cases

- What happens if the IRIS container is not running? (Script should fail gracefully with clear error).
- What happens if the `_SYSTEM` account is locked? (Script should attempt to unlock it).

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a mechanism to reset the FHIR superuser password to a standard value (e.g., `SYS`).
- **FR-002**: System MUST configure the CSP application for the FHIR endpoint to allow Password authentication.
- **FR-003**: System MUST assign necessary roles (`%DB_FHIR`, `%HS_FHIR_USER`) to the service user.
- **FR-004**: The data population script MUST handle authentication retry or failure gracefully, reporting specific config issues.
- **FR-005**: System MUST validate connectivity immediately after configuration changes.

### Key Entities

- **FHIRUser**: The IRIS user account used for API access.
- **FHIRService**: The interoperability service handling FHIR requests.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of valid requests to `/fhir/r4/metadata` return HTTP 200 after reset.
- **SC-002**: Data population script runs to completion with 0 authentication errors.
- **SC-003**: Security reset operation completes in under 30 seconds.
