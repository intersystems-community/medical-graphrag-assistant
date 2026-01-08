"""
FHIR Document Search Service.
Provides full-text and vector search over clinical notes.
"""

from typing import List, Dict, Any, Optional
from .base import BaseSearchService

class FHIRSearchService(BaseSearchService):
    """Service for searching FHIR clinical documents."""
    
    def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search FHIR documents by text content.
        
        Args:
            query: Search keywords
            limit: Maximum results
            
        Returns:
            List of matching documents with previews
        """
        _, cursor = self.connect()
        
        # Extract keywords for scoring
        keywords = query.lower().split()
        
        # SQL to find documents (parameterized)
        sql = """
            SELECT ResourceID, TextContent
            FROM SQLUser.FHIRDocuments
            WHERE (TextContent %MATCHES(?))
        """
        # Note: Depending on IRIS version/setup, %MATCHES or LIKE might be used.
        # Current MCP server uses manual filtering in Python for text search, 
        # but we'll try a more performant SQL approach if supported.
        # Fallback to fetching and filtering if needed.
        
        # For pragmatic refactor, we'll follow the pattern in fhir_graphrag_mcp_server.py
        # which performs keyword matching on TextContent.
        
        sql = "SELECT FHIRResourceId, TextContent FROM SQLUser.FHIRDocuments"
        cursor.execute(sql)
        
        results = []
        for row in cursor.fetchall():
            doc_id, text_content = row
            if not text_content:
                continue
                
            text_lower = text_content.lower()
            score = sum(text_lower.count(kw) for kw in keywords)
            
            if score > 0:
                results.append({
                    "fhir_id": str(doc_id),
                    "preview": text_content[:200] + "..." if len(text_content) > 200 else text_content,
                    "relevance": score,
                    "full_text": text_content
                })
        
        # Sort by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:limit]

    def get_document_details(self, fhir_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full document details."""
        import json
        _, cursor = self.connect()
        sql = "SELECT FHIRResourceId, ResourceType, ResourceString, TextContent FROM SQLUser.FHIRDocuments WHERE FHIRResourceId = ?"
        cursor.execute(sql, [fhir_id])
        row = cursor.fetchone()
        
        if row:
            fhir_id, resource_type, resource_string, text_content = row
            resource_json = json.loads(resource_string) if resource_string else {}
            
            return {
                "fhir_id": fhir_id,
                "resource_type": resource_type,
                "clinical_note": text_content,
                "metadata": {
                    "id": resource_json.get('id'),
                    "status": resource_json.get('status'),
                    "type": resource_json.get('type', {}).get('coding', [{}])[0].get('display') if resource_json.get('type') else None
                }
            }
        return None
