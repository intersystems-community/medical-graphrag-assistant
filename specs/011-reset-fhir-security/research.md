# Research: IRIS Security Management via intersystems-irispython

**Date**: 2026-01-10
**Goal**: Determine correct patterns for modifying IRIS security configuration (Users, Applications) programmatically.

## 1. Namespace Access
Administrative classes reside in the `%SYS` namespace. While they can be referenced as `%SYS.Security.Users` from other namespaces in some contexts, switching the process namespace is the most reliable method for administrative scripts.

- **Command**: `iris.system.Process.SetNamespace("%SYS")` (Embedded) or `db_native.classMethodValue("%SYS.Process", "SetNamespace", "%SYS")` (Native SDK).

## 2. Security.Users Management
The `Security.Users` class uses a `Get`/`Modify` pattern for updates.

- **Opening a User**: `Security.Users:Get(name, .properties)`
- **Updating a User**: `Security.Users:Modify(name, .properties)`
- **Direct Password Change**: `Security.Users:ChangePassword(name, password)`

**Implementation Note**: When using the Native SDK (remote connection), the `.properties` parameter (which is `ByRef` in ObjectScript) must be wrapped in `iris.IRISReference({})`.

## 3. Security.Applications Management
Web application security is controlled via bitmasks in the `AuthenEnabled` property.

- **Enable Password Auth**: `current_val | 32`
- **Enable Unauthenticated**: `current_val | 1`

## 4. Code Pattern (Native SDK)
```python
import iris
# ... connection setup ...
db_native = iris.createIRIS(conn)

# Switch to %SYS
db_native.classMethodValue("%SYS.Process", "SetNamespace", "%SYS")

# Modify User
props = iris.IRISReference({})
db_native.classMethodValue("Security.Users", "Get", "_SYSTEM", props)
props.value["Password"] = "NewPassword123"
db_native.classMethodValue("Security.Users", "Modify", "_SYSTEM", props)
```

## Decisions

### D1: Usage of Native SDK
We will use the `intersystems-irispython` Native SDK (`iris.createIRIS(conn)`) pattern as we are connecting remotely (via TCP/IP from within the container or host) rather than Embedded Python (which requires running *inside* the IRIS process memory space). The CLI runs as a separate Python process.

### D2: Credential Handling
The reset script will attempt to connect using:
1. Current known/configured credentials (from `.env`).
2. Default credentials (`_SYSTEM` / `SYS`).
3. If both fail, it cannot proceed (requires manual intervention or interactive `iris session` via `docker exec`).

### D3: Target Namespace
We will explicitly switch context to `%SYS` using `db_native.classMethodValue("%SYS.Process", "SetNamespace", "%SYS")` before attempting any security modifications.
