# Tasks: Reset FHIR Security Configuration

**Phase**: Foundational
**Feature**: Reset FHIR Security Configuration
**Status**: Pending

## Phase 1: Setup

- [x] T001 [P] Create reset script skeleton in `src/setup/reset_fhir_security.py`
- [x] T002 [P] Update CLI entry point in `src/cli/__main__.py` to include `reset-security` command

## Phase 2: Foundational (Blocking)

- [x] T003 Implement `intersystems-irispython` Native SDK connection logic in `src/setup/reset_fhir_security.py`
- [x] T004 Implement namespace switching to `%SYS` in `src/setup/reset_fhir_security.py`

## Phase 3: User Story 1 - Secure FHIR Access (P1)

**Goal**: Ensure automated scripts can authenticate with the FHIR server.

- [x] T005 [US1] Implement user password reset logic in `src/setup/reset_fhir_security.py`
- [x] T006 [US1] Implement CSP application security update logic in `src/setup/reset_fhir_security.py`
- [x] T007 [US1] Implement role assignment logic in `src/setup/reset_fhir_security.py`
- [x] T008 [US1] Add verification step to `src/setup/reset_fhir_security.py` (check metadata endpoint)

## Phase 4: User Story 2 - Automated Security Reset (P2)

**Goal**: Provide a CLI tool for developers to reset environments.

- [x] T009 [US2] Integrate `reset_fhir_security` into `src/cli/__main__.py` as a subcommand
- [x] T010 [US2] Add argument parsing for optional username/password overrides in CLI

## Phase 5: Polish & Cross-Cutting

- [x] T011 Update `src/validation/health_checks.py` to check for 401 errors specifically and suggest reset
- [x] T012 Document usage in `README.md` or `docs/troubleshooting.md`

## Phase 6: E2E Verification

**Goal**: Confirm system satisfies all requirements and is fully working.

- [x] T013 [P] Create E2E verification script `scripts/verify_fhir_reset_e2e.sh`
- [ ] T014 Execute E2E verification on target environment (EC2)
- [ ] T015 Verify successful data population after security reset
- [ ] T016 Final system health check via CLI

## Implementation Strategy

1.  **MVP**: Create the standalone script `src/setup/reset_fhir_security.py` first. This solves the immediate blocker.
2.  **Integration**: Hook it into the CLI for ease of use.
3.  **Verification**: Run the script and verify `populate_full_graphrag_data.py` succeeds.

## Dependencies

- **US1** blocks **US2** (Core logic must exist before CLI exposure)
- **T003/T004** block all US1 tasks.
