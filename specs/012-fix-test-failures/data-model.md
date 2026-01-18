# Data Model: Test & Operational Tables

This document describes the schema for tables involved in the test failures and operational fixes.

## Table: SQLUser.ClinicalNoteVectors
| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Identity Primary Key |
| ResourceID | VARCHAR(255) | FHIR DocumentReference ID |
| PatientID | VARCHAR(255) | FHIR Patient ID |
| TextContent | VARCHAR(32000) | Extracted text from FHIR |
| Embedding | VECTOR(DOUBLE, 1024) | 1024-dim NV-Embed embedding |

## Table: VectorSearch.PatientImageMapping
| Field | Type | Description |
|-------|------|-------------|
| MIMICSubjectID | VARCHAR(255) | Primary Key (MIMIC ID) |
| FHIRPatientID | VARCHAR(255) | Corresponding FHIR ID |
| FHIRPatientName | VARCHAR(500) | Patient Name |
| MatchConfidence | DOUBLE | Match Score (0-1) |

## Table: SQLUser.AgentMemoryVectors
| Field | Type | Description |
|-------|------|-------------|
| ID | INT | Identity Primary Key |
| MemoryType | VARCHAR(50) | knowledge, feedback, etc. |
| Content | VARCHAR(32000) | Semantic memory text |
| Embedding | VECTOR(DOUBLE, 1024) | Semantic vector |
