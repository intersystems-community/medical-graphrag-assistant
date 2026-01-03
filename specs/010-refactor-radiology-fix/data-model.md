# Data Model Verification: Radiology Fix

This feature does not add new tables but requires verification of the following existing IRIS schema:

| Table Name | Schema | Required Columns |
|------------|--------|------------------|
| `FHIRDocuments` | `SQLUser` | `ID`, `ResourceID`, `TextContent`, `Embedding` |
| `Entities` | `SQLUser` | `ID`, `EntityText`, `EntityType` |
| `EntityRelationships`| `SQLUser` | `ID`, `SourceEntityID`, `TargetEntityID` |
| `MIMICCXRImages` | `VectorSearch`| `ID`, `DicomID`, `Embedding` |

## Validation Rules
1. `SQLUser.FHIRDocuments` MUST exist for radiology document retrieval.
2. `VectorSearch.MIMICCXRImages` MUST exist for image similarity search.
3. Tables must be accessible by the configured `IRIS_USERNAME`.
