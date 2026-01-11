# Data Model: Security Configuration

**Branch**: `011-reset-fhir-security`

## System Configuration Entities

These entities represent the configuration state within InterSystems IRIS `%SYS` namespace.

### User (`Security.Users`)

Represents a user account in the IRIS instance.

| Field | Type | Description |
|-------|------|-------------|
| Name | String | Username (e.g., `_SYSTEM`, `FHIRUser`) |
| Password | String | Hashed password (set via `ChangePassword`) |
| Roles | String | Comma-separated list of roles (e.g., `%DB_FHIR,%HS_FHIR_USER`) |
| Enabled | Boolean | Whether the account is active |

### Web Application (`Security.Applications`)

Represents the CSP application endpoint for FHIR.

| Field | Type | Description |
|-------|------|-------------|
| Name | String | Application path (e.g., `/csp/healthshare/demo/fhir/r4`) |
| AuthenEnabled | Integer | Bitmask of enabled authentication methods |
| Enabled | Boolean | Whether the application is served |

### Authentication Bitmask (Enum)

| Value | Name | Description |
|-------|------|-------------|
| 32 | Password | Standard username/password auth |
| 64 | Kerberos | Kerberos/OS auth |
| 1 | Unauthenticated | Anonymous access (usually disabled for FHIR) |
