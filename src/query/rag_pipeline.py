"""
RAG Pipeline for Multi-Modal Medical Query Processing

This module implements the Retrieval-Augmented Generation (RAG) pipeline for
querying clinical notes using vector similarity search and LLM generation.

Main Components:
- Query embedding generation (NVIDIA NIM embeddings)
- Vector similarity search (IRIS database)
- Context assembly from retrieved documents
- LLM response generation (NVIDIA NIM LLM)
- Citation extraction and formatting

Usage:
    from query.rag_pipeline import RAGPipeline

    pipeline = RAGPipeline()
    result = pipeline.process_query(
        query_text="What are the patient's chronic conditions?",
        top_k=10,
        patient_id="patient-123"  # Optional filter
    )

    print(f"Response: {result['response']}")
    print(f"Citations: {result['citations']}")

Performance Target (SC-007): <5 seconds end-to-end query latency
"""

import os
import sys
import logging
import time
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vectorization.embedding_client import NVIDIAEmbeddingsClient
from vectorization.vector_db_client import IRISVectorDBClient


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Main RAG pipeline for medical query processing.

    Coordinates query embedding, vector search, context assembly,
    and LLM generation with citation tracking.
    """

    # Default configuration
    DEFAULT_TOP_K = 10
    DEFAULT_SIMILARITY_THRESHOLD = 0.5
    DEFAULT_MAX_CONTEXT_TOKENS = 4000  # Approximate token budget for context
    DEFAULT_LLM_MAX_TOKENS = 500
    DEFAULT_LLM_TEMPERATURE = 0.7

    def __init__(
        self,
        iris_host: Optional[str] = None,
        iris_port: Optional[int] = None,
        iris_namespace: Optional[str] = None,
        iris_username: Optional[str] = None,
        iris_password: Optional[str] = None,
        llm_endpoint: Optional[str] = None,
        embedding_api_key: Optional[str] = None,
        vector_dimension: int = 1024
    ):
        """
        Initialize RAG pipeline with database and API connections.

        Args:
            iris_host: IRIS database host (default: from env IRIS_HOST or localhost)
            iris_port: IRIS database port (default: from env IRIS_PORT or 1972)
            iris_namespace: IRIS namespace (default: from env IRIS_NAMESPACE or DEMO)
            iris_username: IRIS username (default: from env IRIS_USERNAME or _SYSTEM)
            iris_password: IRIS password (default: from env IRIS_PASSWORD or SYS)
            llm_endpoint: NIM LLM endpoint URL (default: http://localhost:8001)
            embedding_api_key: NVIDIA API key (default: from env NVIDIA_API_KEY)
            vector_dimension: Embedding dimension (default: 1024)
        """
        # IRIS database configuration
        self.iris_host = iris_host or os.getenv("IRIS_HOST", "44.200.206.67")
        self.iris_port = iris_port or int(os.getenv("IRIS_PORT", "1972"))
        self.iris_namespace = iris_namespace or os.getenv("IRIS_NAMESPACE", "USER")
        self.iris_username = iris_username or os.getenv("IRIS_USERNAME", "_SYSTEM")
        self.iris_password = iris_password or os.getenv("IRIS_PASSWORD", "SYS")
        self.vector_dimension = vector_dimension

        # LLM configuration
        self.llm_endpoint = llm_endpoint or os.getenv("LLM_ENDPOINT", "http://44.200.206.67:8001")
        self.llm_completions_url = f"{self.llm_endpoint}/v1/chat/completions"
        self.llm_model = "meta/llama-3.1-8b-instruct"

        # Initialize clients
        logger.info("Initializing NVIDIA NIM embeddings client...")
        self.embedding_client = NVIDIAEmbeddingsClient(api_key=embedding_api_key)

        logger.info("Initializing IRIS vector database client...")
        self.vector_db_client = IRISVectorDBClient(
            host=self.iris_host,
            port=self.iris_port,
            namespace=self.iris_namespace,
            username=self.iris_username,
            password=self.iris_password,
            vector_dimension=self.vector_dimension
        )

        # Connect to IRIS
        self.vector_db_client.connect()
        logger.info(f"✓ Connected to IRIS: {self.iris_host}:{self.iris_port}/{self.iris_namespace}")

    def __del__(self):
        """Cleanup database connection."""
        try:
            if hasattr(self, 'vector_db_client'):
                self.vector_db_client.disconnect()
        except:
            pass

    def generate_query_embedding(self, query_text: str) -> List[float]:
        """
        Generate embedding vector for query text.

        Uses the same NVIDIA NIM embeddings API as the vectorization pipeline
        to ensure query and document embeddings are in the same space.

        Args:
            query_text: Natural language query

        Returns:
            1024-dimensional embedding vector

        Raises:
            RuntimeError: If embedding generation fails
        """
        try:
            logger.info(f"Generating embedding for query: '{query_text[:100]}...'")
            embedding = self.embedding_client.embed(query_text)
            logger.info(f"✓ Generated {len(embedding)}-dimensional embedding")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise RuntimeError(f"Query embedding generation failed: {e}")

    def search_similar_documents(
        self,
        query_vector: List[float],
        top_k: int = DEFAULT_TOP_K,
        patient_id: Optional[str] = None,
        document_type: Optional[str] = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to retrieve
            patient_id: Optional patient ID filter
            document_type: Optional document type filter
            similarity_threshold: Minimum cosine similarity (0-1)

        Returns:
            List of documents with metadata and similarity scores:
            [
                {
                    "resource_id": str,
                    "patient_id": str,
                    "document_type": str,
                    "text_content": str,
                    "similarity": float
                },
                ...
            ]
        """
        logger.info(f"Searching for top-{top_k} similar documents...")
        if patient_id:
            logger.info(f"  Filtering by patient_id: {patient_id}")
        if document_type:
            logger.info(f"  Filtering by document_type: {document_type}")
        logger.info(f"  Similarity threshold: {similarity_threshold}")

        try:
            results = self.vector_db_client.search_similar(
                query_vector=query_vector,
                top_k=top_k,
                patient_id=patient_id,
                document_type=document_type
            )

            # Apply similarity threshold filter
            filtered_results = [
                result for result in results
                if result["similarity"] >= similarity_threshold
            ]

            logger.info(f"✓ Retrieved {len(filtered_results)} documents above threshold")
            return filtered_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise RuntimeError(f"Vector similarity search failed: {e}")

    def filter_and_rank_results(
        self,
        results: List[Dict[str, Any]],
        min_similarity: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Filter and rank search results.

        Applies additional filtering and re-ranking logic:
        - Filters by minimum similarity threshold
        - Re-ranks by document recency if timestamps available
        - Deduplicates similar content

        Args:
            results: Raw search results
            min_similarity: Minimum similarity score

        Returns:
            Filtered and ranked results
        """
        # Filter by minimum similarity
        filtered = [r for r in results if r["similarity"] >= min_similarity]

        # Sort by similarity (already sorted by vector_db_client, but ensure)
        filtered.sort(key=lambda x: x["similarity"], reverse=True)

        logger.info(f"Filtered to {len(filtered)} results (min_similarity={min_similarity})")

        return filtered

    def assemble_context(
        self,
        documents: List[Dict[str, Any]],
        max_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Assemble context from retrieved documents for LLM prompt.

        Concatenates document text with metadata and source identifiers.
        Truncates if total exceeds max_tokens budget.

        Args:
            documents: Retrieved documents with metadata
            max_tokens: Approximate maximum tokens for context

        Returns:
            Tuple of (assembled_context_text, source_documents)
        """
        if not documents:
            return "", []

        context_parts = []
        sources = []

        # Rough token estimation: ~4 characters per token
        chars_per_token = 4
        max_chars = max_tokens * chars_per_token
        current_chars = 0

        for i, doc in enumerate(documents):
            # Format document with metadata
            doc_text = f"""
[Document {i+1}]
Source ID: {doc['resource_id']}
Patient: {doc['patient_id']}
Type: {doc['document_type']}
Similarity: {doc['similarity']:.3f}

Content:
{doc['text_content']}

---
"""

            # Check if adding this document exceeds budget
            if current_chars + len(doc_text) > max_chars:
                logger.warning(f"Context budget exceeded at document {i+1}/{len(documents)}")
                break

            context_parts.append(doc_text)
            sources.append({
                "index": i + 1,
                "resource_id": doc["resource_id"],
                "patient_id": doc["patient_id"],
                "document_type": doc["document_type"],
                "similarity": doc["similarity"]
            })
            current_chars += len(doc_text)

        assembled_context = "\n".join(context_parts)
        logger.info(f"✓ Assembled context from {len(sources)} documents (~{current_chars//chars_per_token} tokens)")

        return assembled_context, sources

    def create_llm_prompt(
        self,
        query_text: str,
        context: str
    ) -> List[Dict[str, str]]:
        """
        Create LLM prompt with system instructions, context, and query.

        Formats a chat completion prompt with:
        - System message instructing to answer only from context
        - User message with retrieved context and query

        Args:
            query_text: User's natural language query
            context: Assembled context from retrieved documents

        Returns:
            Messages array for chat completion API:
            [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."}
            ]
        """
        system_prompt = """You are a helpful medical AI assistant. Answer the user's question based ONLY on the clinical notes provided in the context below.

IMPORTANT INSTRUCTIONS:
- Use only information from the provided clinical notes
- If the context doesn't contain relevant information, say "I don't have enough information to answer this question based on the available clinical notes"
- Cite specific document numbers when referencing information (e.g., "According to Document 1...")
- Be concise and factual
- Do not make up or infer information not present in the context"""

        user_prompt = f"""Context (Retrieved Clinical Notes):

{context}

Question: {query_text}

Please answer the question based on the clinical notes provided above. Cite the document numbers when referencing specific information."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return messages

    def call_llm_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
        temperature: float = DEFAULT_LLM_TEMPERATURE
    ) -> str:
        """
        Call NVIDIA NIM LLM API for response generation.

        Sends chat completion request to NIM LLM service (meta/llama-3.1-8b-instruct)
        running on port 8001.

        Args:
            messages: Chat messages array
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)

        Returns:
            Generated response text

        Raises:
            RuntimeError: If API call fails
        """
        payload = {
            "model": self.llm_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        headers = {}
        if "integrate.api.nvidia.com" in self.llm_endpoint:
            headers["Authorization"] = f"Bearer {self.embedding_client.api_key}"

        try:
            logger.info(f"Calling LLM API at {self.llm_completions_url}...")
            response = requests.post(
                self.llm_completions_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            response_data = response.json()
            generated_text = response_data["choices"][0]["message"]["content"]

            logger.info(f"✓ LLM response generated ({len(generated_text)} chars)")
            return generated_text

        except requests.exceptions.Timeout:
            logger.error("LLM API request timed out")
            raise RuntimeError("LLM API request timed out after 60 seconds")
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to LLM API at {self.llm_completions_url}")
            raise RuntimeError(f"LLM service unavailable at {self.llm_completions_url}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"LLM API returned error: {e}")
            raise RuntimeError(f"LLM API error: {e}")
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected LLM API response format: {e}")
            raise RuntimeError(f"Invalid LLM API response: {e}")

    def extract_citations(
        self,
        response_text: str,
        sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract citations from LLM response.

        Maps LLM response back to source documents by detecting references
        to document numbers (e.g., "Document 1", "Document 2").

        Args:
            response_text: Generated LLM response
            sources: Source documents with metadata

        Returns:
            List of cited sources:
            [
                {
                    "resource_id": str,
                    "patient_id": str,
                    "document_type": str,
                    "similarity": float,
                    "cited_in_response": bool
                },
                ...
            ]
        """
        citations = []

        for source in sources:
            doc_number = source["index"]

            # Check if this document number is mentioned in response
            mentioned = (
                f"Document {doc_number}" in response_text or
                f"document {doc_number}" in response_text or
                f"[{doc_number}]" in response_text
            )

            citations.append({
                "resource_id": source["resource_id"],
                "patient_id": source["patient_id"],
                "document_type": source["document_type"],
                "similarity": source["similarity"],
                "cited_in_response": mentioned
            })

        cited_count = sum(1 for c in citations if c["cited_in_response"])
        logger.info(f"✓ Extracted {cited_count}/{len(citations)} citations mentioned in response")

        return citations

    def handle_no_results(self, query_text: str) -> Dict[str, Any]:
        """
        Handle case when no relevant documents are found.

        Returns explicit "no information found" message instead of
        allowing LLM to hallucinate an answer.

        Args:
            query_text: Original query

        Returns:
            Result dict with no-results message
        """
        logger.warning("No relevant documents found above similarity threshold")

        return {
            "query": query_text,
            "response": "I don't have enough information to answer this question based on the available clinical notes. No relevant documents were found with sufficient similarity to your query.",
            "retrieved_documents": [],
            "citations": [],
            "metadata": {
                "documents_retrieved": 0,
                "documents_used_in_context": 0,
                "processing_time_seconds": 0,
                "timestamp": datetime.now().isoformat()
            }
        }

    def process_query(
        self,
        query_text: str,
        top_k: int = DEFAULT_TOP_K,
        patient_id: Optional[str] = None,
        document_type: Optional[str] = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
        llm_max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
        llm_temperature: float = DEFAULT_LLM_TEMPERATURE
    ) -> Dict[str, Any]:
        """
        Process a complete RAG query from start to finish.

        Main entry point for the RAG pipeline. Coordinates all steps:
        1. Generate query embedding
        2. Search for similar documents
        3. Filter and rank results
        4. Assemble context
        5. Create LLM prompt
        6. Call LLM API
        7. Extract citations

        Args:
            query_text: Natural language query
            top_k: Number of documents to retrieve
            patient_id: Optional patient ID filter
            document_type: Optional document type filter
            similarity_threshold: Minimum similarity score (0-1)
            max_context_tokens: Maximum tokens for context
            llm_max_tokens: Maximum tokens in LLM response
            llm_temperature: LLM temperature parameter

        Returns:
            Complete query result:
            {
                "query": str,
                "response": str,
                "retrieved_documents": List[Dict],
                "citations": List[Dict],
                "metadata": Dict
            }

        Example:
            >>> pipeline = RAGPipeline()
            >>> result = pipeline.process_query(
            ...     query_text="What are the patient's chronic conditions?",
            ...     top_k=10,
            ...     patient_id="patient-123"
            ... )
            >>> print(result["response"])
        """
        start_time = time.time()

        logger.info("="*80)
        logger.info("Starting RAG Query Processing")
        logger.info(f"Query: {query_text}")
        logger.info("="*80)

        try:
            # Step 1: Generate query embedding
            query_vector = self.generate_query_embedding(query_text)

            # Step 2: Search for similar documents
            search_results = self.search_similar_documents(
                query_vector=query_vector,
                top_k=top_k,
                patient_id=patient_id,
                document_type=document_type,
                similarity_threshold=similarity_threshold
            )

            # Step 3: Handle no results case
            if not search_results:
                return self.handle_no_results(query_text)

            # Step 4: Filter and rank results (additional processing)
            filtered_results = self.filter_and_rank_results(
                results=search_results,
                min_similarity=similarity_threshold
            )

            # Step 5: Assemble context
            context, sources = self.assemble_context(
                documents=filtered_results,
                max_tokens=max_context_tokens
            )

            # Step 6: Create LLM prompt
            messages = self.create_llm_prompt(
                query_text=query_text,
                context=context
            )

            # Step 7: Call LLM API
            response_text = self.call_llm_api(
                messages=messages,
                max_tokens=llm_max_tokens,
                temperature=llm_temperature
            )

            # Step 8: Extract citations
            citations = self.extract_citations(
                response_text=response_text,
                sources=sources
            )

            # Calculate processing time
            processing_time = time.time() - start_time

            # Assemble result
            result = {
                "query": query_text,
                "response": response_text,
                "retrieved_documents": filtered_results,
                "citations": citations,
                "metadata": {
                    "documents_retrieved": len(search_results),
                    "documents_used_in_context": len(sources),
                    "processing_time_seconds": round(processing_time, 2),
                    "timestamp": datetime.now().isoformat(),
                    "parameters": {
                        "top_k": top_k,
                        "similarity_threshold": similarity_threshold,
                        "patient_id": patient_id,
                        "document_type": document_type
                    }
                }
            }

            logger.info("="*80)
            logger.info(f"✅ Query processing complete in {processing_time:.2f}s")
            logger.info(f"   Retrieved: {len(search_results)} documents")
            logger.info(f"   Used in context: {len(sources)} documents")
            logger.info(f"   Response length: {len(response_text)} chars")
            logger.info("="*80)

            return result

        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}")
            raise


if __name__ == "__main__":
    """
    Example usage and testing.
    """
    print("RAG Pipeline Module")
    print("=" * 80)
    print()
    print("This module provides the main RAG query processing functionality.")
    print()
    print("Example usage:")
    print()
    print("  from query.rag_pipeline import RAGPipeline")
    print()
    print("  pipeline = RAGPipeline()")
    print("  result = pipeline.process_query(")
    print("      query_text='What medications is the patient taking?',")
    print("      top_k=10,")
    print("      patient_id='patient-123'")
    print("  )")
    print()
    print("  print(f\"Response: {result['response']}\")")
    print("  print(f\"Citations: {len(result['citations'])} sources\")")
    print()
    print("For CLI testing, use: python src/validation/test_rag_query.py")
