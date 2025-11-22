#!/usr/bin/env python3
"""
RAG Query Testing CLI Tool

Interactive command-line tool for testing the RAG pipeline with natural
language queries against vectorized clinical notes.

Usage:
    python src/validation/test_rag_query.py --query "What medications is the patient taking?"

    python src/validation/test_rag_query.py \\
        --query "What are the patient's chronic conditions?" \\
        --patient-id "patient-123" \\
        --top-k 10

    python src/validation/test_rag_query.py \\
        --query "Recent lab results" \\
        --patient-id "patient-456" \\
        --document-type "Progress Note"

Performance Target (SC-007): <5 seconds end-to-end query latency

Example Output:
    ================================================================================
    RAG Query Test
    ================================================================================
    Query: "What are the patient's chronic conditions?"
    Patient Filter: patient-123
    Top-K: 10
    Similarity Threshold: 0.5
    ================================================================================

    Response:
    ----------
    Based on the clinical notes, the patient has the following chronic conditions:
    1. Type 2 diabetes mellitus (mentioned in Document 1 and Document 3)
    2. Essential hypertension (mentioned in Document 2)
    3. Hyperlipidemia (mentioned in Document 1)

    ================================================================================
    Retrieved Documents (3 used in context, 5 total retrieved)
    ================================================================================

    [1] Similarity: 0.87 | Patient: patient-123 | Type: Progress Note
        Resource ID: doc-456-2024-01-15
        Content: "Patient with type 2 diabetes, currently on metformin..."
        ✓ Cited in response

    [2] Similarity: 0.82 | Patient: patient-123 | Type: History and physical
        Resource ID: doc-789-2023-12-10
        Content: "Patient presents with hypertension, well-controlled..."
        ✓ Cited in response

    ...

    ================================================================================
    Metadata
    ================================================================================
    Processing Time: 3.45 seconds
    Documents Retrieved: 5
    Documents Used in Context: 3
    Citations Found: 2
    Timestamp: 2025-01-09T15:30:45.123456
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from query.rag_pipeline import RAGPipeline


def format_response_output(result: Dict[str, Any], show_full_documents: bool = False) -> str:
    """
    Format RAG query result for console output.

    Args:
        result: RAG pipeline result dictionary
        show_full_documents: Whether to show full document text (can be long)

    Returns:
        Formatted string for display
    """
    output_lines = []

    # Header
    output_lines.append("=" * 80)
    output_lines.append("RAG Query Test")
    output_lines.append("=" * 80)
    output_lines.append(f"Query: \"{result['query']}\"")

    # Query parameters
    params = result['metadata']['parameters']
    if params.get('patient_id'):
        output_lines.append(f"Patient Filter: {params['patient_id']}")
    if params.get('document_type'):
        output_lines.append(f"Document Type Filter: {params['document_type']}")
    output_lines.append(f"Top-K: {params['top_k']}")
    output_lines.append(f"Similarity Threshold: {params['similarity_threshold']}")
    output_lines.append("=" * 80)
    output_lines.append("")

    # Response
    output_lines.append("Response:")
    output_lines.append("-" * 80)
    output_lines.append(result['response'])
    output_lines.append("")

    # Retrieved Documents
    retrieved_docs = result['retrieved_documents']
    citations = result['citations']
    docs_used = result['metadata']['documents_used_in_context']

    output_lines.append("=" * 80)
    output_lines.append(f"Retrieved Documents ({docs_used} used in context, {len(retrieved_docs)} total retrieved)")
    output_lines.append("=" * 80)
    output_lines.append("")

    if not retrieved_docs:
        output_lines.append("No documents retrieved above similarity threshold.")
    else:
        for i, (doc, citation) in enumerate(zip(retrieved_docs[:docs_used], citations[:docs_used])):
            # Document header
            cited_marker = "✓ Cited in response" if citation['cited_in_response'] else "  Not cited"
            output_lines.append(
                f"[{i+1}] Similarity: {doc['similarity']:.3f} | "
                f"Patient: {doc['patient_id']} | "
                f"Type: {doc['document_type']}"
            )
            output_lines.append(f"    Resource ID: {doc['resource_id']}")

            # Content preview or full
            if show_full_documents:
                output_lines.append(f"    Content:")
                # Indent each line of content
                for line in doc['text_content'].split('\n'):
                    output_lines.append(f"      {line}")
            else:
                # Show preview (first 200 chars)
                preview = doc['text_content'][:200].replace('\n', ' ')
                if len(doc['text_content']) > 200:
                    preview += "..."
                output_lines.append(f"    Content: \"{preview}\"")

            output_lines.append(f"    {cited_marker}")
            output_lines.append("")

    # Show additional retrieved documents not used in context
    if len(retrieved_docs) > docs_used:
        output_lines.append(f"Additional {len(retrieved_docs) - docs_used} documents retrieved but not used in context:")
        for i in range(docs_used, len(retrieved_docs)):
            doc = retrieved_docs[i]
            output_lines.append(
                f"  [{i+1}] Similarity: {doc['similarity']:.3f} | "
                f"Patient: {doc['patient_id']} | "
                f"Type: {doc['document_type']}"
            )
        output_lines.append("")

    # Metadata
    output_lines.append("=" * 80)
    output_lines.append("Metadata")
    output_lines.append("=" * 80)
    output_lines.append(f"Processing Time: {result['metadata']['processing_time_seconds']} seconds")
    output_lines.append(f"Documents Retrieved: {result['metadata']['documents_retrieved']}")
    output_lines.append(f"Documents Used in Context: {result['metadata']['documents_used_in_context']}")

    cited_count = sum(1 for c in citations if c['cited_in_response'])
    output_lines.append(f"Citations Found: {cited_count}")
    output_lines.append(f"Timestamp: {result['metadata']['timestamp']}")

    # Performance assessment
    processing_time = result['metadata']['processing_time_seconds']
    if processing_time < 5.0:
        performance_status = "✅ Meets SC-007 target (<5s)"
    else:
        performance_status = "⚠️  Exceeds SC-007 target (<5s)"
    output_lines.append(f"Performance: {performance_status}")

    output_lines.append("=" * 80)

    return "\n".join(output_lines)


def save_result_json(result: Dict[str, Any], output_file: str):
    """
    Save RAG query result to JSON file.

    Args:
        result: RAG pipeline result dictionary
        output_file: Path to output JSON file
    """
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"✓ Result saved to: {output_file}")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Test RAG query pipeline with natural language queries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic query
  python src/validation/test_rag_query.py --query "What medications is the patient taking?"

  # Query with patient filter
  python src/validation/test_rag_query.py \\
      --query "What are the patient's chronic conditions?" \\
      --patient-id "patient-123"

  # Query with document type filter
  python src/validation/test_rag_query.py \\
      --query "Recent lab results" \\
      --document-type "Progress Note"

  # Save result to JSON
  python src/validation/test_rag_query.py \\
      --query "Medication history" \\
      --output result.json

  # Show full document text
  python src/validation/test_rag_query.py \\
      --query "Diabetes treatment" \\
      --show-full-documents

Environment Variables:
  IRIS_HOST           IRIS database host (default: localhost)
  IRIS_PORT           IRIS database port (default: 1972)
  IRIS_NAMESPACE      IRIS namespace (default: DEMO)
  IRIS_USERNAME       IRIS username (default: _SYSTEM)
  IRIS_PASSWORD       IRIS password (default: SYS)
  NVIDIA_API_KEY      NVIDIA API key for embeddings

Performance Target:
  SC-007: End-to-end query latency <5 seconds
        """
    )

    # Required arguments
    parser.add_argument(
        "--query",
        required=True,
        help="Natural language query to process"
    )

    # Optional filters
    parser.add_argument(
        "--patient-id",
        help="Filter results by patient ID"
    )
    parser.add_argument(
        "--document-type",
        help="Filter results by document type (e.g., 'Progress Note')"
    )

    # Retrieval parameters
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of documents to retrieve (default: 10)"
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.5,
        help="Minimum similarity score 0-1 (default: 0.5)"
    )

    # LLM parameters
    parser.add_argument(
        "--max-context-tokens",
        type=int,
        default=4000,
        help="Maximum tokens for context (default: 4000)"
    )
    parser.add_argument(
        "--llm-max-tokens",
        type=int,
        default=500,
        help="Maximum tokens in LLM response (default: 500)"
    )
    parser.add_argument(
        "--llm-temperature",
        type=float,
        default=0.7,
        help="LLM sampling temperature 0-1 (default: 0.7)"
    )

    # Database connection (optional overrides)
    parser.add_argument(
        "--iris-host",
        help="IRIS database host (default: from env or localhost)"
    )
    parser.add_argument(
        "--iris-port",
        type=int,
        help="IRIS database port (default: from env or 1972)"
    )
    parser.add_argument(
        "--iris-namespace",
        help="IRIS namespace (default: from env or DEMO)"
    )
    parser.add_argument(
        "--iris-username",
        help="IRIS username (default: from env or _SYSTEM)"
    )
    parser.add_argument(
        "--iris-password",
        help="IRIS password (default: from env or SYS)"
    )

    # LLM endpoint
    parser.add_argument(
        "--llm-endpoint",
        default="http://localhost:8001",
        help="NIM LLM endpoint URL (default: http://localhost:8001)"
    )

    # Output options
    parser.add_argument(
        "--output",
        help="Save result to JSON file"
    )
    parser.add_argument(
        "--show-full-documents",
        action="store_true",
        help="Show full document text instead of preview"
    )

    # Verbose mode
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


def main():
    """Main entry point for RAG query testing."""
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Initialize RAG pipeline
        print("Initializing RAG pipeline...")
        pipeline = RAGPipeline(
            iris_host=args.iris_host,
            iris_port=args.iris_port,
            iris_namespace=args.iris_namespace,
            iris_username=args.iris_username,
            iris_password=args.iris_password,
            llm_endpoint=args.llm_endpoint
        )
        print("✓ RAG pipeline initialized")
        print()

        # Process query
        result = pipeline.process_query(
            query_text=args.query,
            top_k=args.top_k,
            patient_id=args.patient_id,
            document_type=args.document_type,
            similarity_threshold=args.similarity_threshold,
            max_context_tokens=args.max_context_tokens,
            llm_max_tokens=args.llm_max_tokens,
            llm_temperature=args.llm_temperature
        )

        # Format and display output
        print()
        formatted_output = format_response_output(
            result,
            show_full_documents=args.show_full_documents
        )
        print(formatted_output)

        # Save to file if requested
        if args.output:
            save_result_json(result, args.output)

        # Exit with success
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nQuery cancelled by user.")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
