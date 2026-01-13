# Repository Transfer Notes: Medical GraphRAG Assistant

This repository is being transferred to the `intersystems-community` organization. This document outlines the current state, known gaps, and essential operational knowledge.

## 🏛️ System Architecture

The project implements an agentic clinical chat interface powered by **InterSystems IRIS**, **NVIDIA NIM**, and **Model Context Protocol (MCP)**.

- **Core Node**: Handles FHIR storage (IRIS), LLM synthesis (NIM Llama 3.1), and GraphRAG services.
- **Vision Node**: (Distributed mode) Dedicated instance for medical image embeddings (NV-CLIP).
- **Search**: Hybrid approach combining FHIR Document search (SQL), Knowledge Graph traversal (GraphRAG), and Multimodal search (NV-CLIP).

## 🛠️ Essential Setup (AWS)

1.  **IAM Roles**: The Core node requires the `EC2-SSM-InstanceProfileRole` with `AmazonBedrockFullAccess` (if using Bedrock fallback).
2.  **API Keys**: An NVIDIA NGC API key is required for NIM model downloads and the NVIDIA Cloud API fallback.
3.  **Environment**: Always use `python 3.11+` and `intersystems-irispython`. The `iris-devtester` package is used for automated environment fixes.

## ⚠️ Known Gaps & Tech Debt

1.  **FHIR Authentication**: The production IRIS environment occasionally requires a security reset to resolve 401 errors. Use `python -m src.cli reset-security` to fix this.
2.  **Entity Extraction**: Currently using a rule-based/regex approach. Moving to LLM-based extraction is planned for higher accuracy.
3.  **Image Data**: Licensed MIMIC-CXR images have been purged from history. Use `scripts/download-test-images.sh` to fetch public alternatives for testing.
4.  **Path Scrubbing**: All `/Users/tdyar/` references have been replaced with relative paths or placeholders. Verify any new documentation for absolute paths.

## 🚀 Future Roadmap

- Integrate **LLM-based medical entity extraction**.
- Expand the knowledge graph with specialized clinical ontologies.
- Implement **EHR-integrated UI** via FHIR Smart-on-FHIR.

---
*Transferred on: 2026-01-13*
