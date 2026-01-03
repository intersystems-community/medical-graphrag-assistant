"""
Hybrid Search Service.
Combines FHIR text search and KG search using Reciprocal Rank Fusion (RRF).
"""

from typing import Dict, Any
from .base import BaseSearchService
from .fhir_search import FHIRSearchService
from .kg_search import KGSearchService

class HybridSearchService(BaseSearchService):
    """Service for combined multi-modal search."""
    
    def __init__(self, config_path: str = "config/fhir_graphrag_config.yaml"):
        super().__init__(config_path)
        self.fhir_service = FHIRSearchService(config_path)
        self.kg_service = KGSearchService(config_path)
        self.rrf_k = 60  # Standard RRF constant

    def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Execute hybrid search with RRF fusion.
        
        Args:
            query: Natural language query
            top_k: Number of final results
            
        Returns:
            Dict containing fused results and breakdown
        """
        # 1. Execute sub-searches
        fhir_results = self.fhir_service.search_documents(query, limit=30)
        kg_data = self.kg_service.search_entities(query, limit=10)
        kg_results = kg_data.get("entities", [])
        
        # 2. Map resource_id to RRF score
        rrf_scores = {}
        document_meta = {}
        
        # Process FHIR text results
        for rank, result in enumerate(fhir_results, start=1):
            fhir_id = result["fhir_id"]
            score = 1.0 / (self.rrf_k + rank)
            
            if fhir_id not in rrf_scores:
                rrf_scores[fhir_id] = {"fhir": 0.0, "kg": 0.0, "total": 0.0}
                document_meta[fhir_id] = {
                    "preview": result["preview"],
                    "sources": ["fhir"]
                }
            
            rrf_scores[fhir_id]["fhir"] = score
            rrf_scores[fhir_id]["total"] += score

        # Process KG entity results (entities are linked to resources)
        # Note: multiple entities can point to same resource
        seen_kg_resources = set()
        for rank, entity in enumerate(kg_results, start=1):
            fhir_id = entity["resource_id"]
            if not fhir_id or fhir_id == "None":
                continue
                
            score = 1.0 / (self.rrf_k + rank)
            
            if fhir_id not in rrf_scores:
                rrf_scores[fhir_id] = {"fhir": 0.0, "kg": 0.0, "total": 0.0}
                document_meta[fhir_id] = {
                    "preview": entity.get("preview", "No preview available"),
                    "sources": ["kg"]
                }
            elif "kg" not in document_meta[fhir_id]["sources"]:
                document_meta[fhir_id]["sources"].append("kg")
                
            if fhir_id not in seen_kg_resources:
                rrf_scores[fhir_id]["kg"] = score
                rrf_scores[fhir_id]["total"] += score
                seen_kg_resources.add(fhir_id)

        # 3. Sort by total RRF score
        fused_results = []
        for fhir_id, scores in sorted(rrf_scores.items(), key=lambda x: x[1]["total"], reverse=True)[:top_k]:
            meta = document_meta[fhir_id]
            fused_results.append({
                "fhir_id": fhir_id,
                "rrf_score": scores["total"],
                "fhir_score": scores["fhir"],
                "kg_score": scores["kg"],
                "sources": meta["sources"],
                "preview": meta["preview"]
            })
            
        return {
            "query": query,
            "results_count": len(fused_results),
            "top_documents": fused_results,
            "entities_found": len(kg_results)
        }

    def close(self):
        """Close all sub-services."""
        self.fhir_service.close()
        self.kg_service.close()
        super().close()
