"""
Knowledge Graph Search Service.
Provides entity-based search and relationship traversal.
"""

from typing import List, Dict, Any
from .base import BaseSearchService

class KGSearchService(BaseSearchService):
    """Service for searching the medical knowledge graph."""
    
    def search_entities(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Search for entities matching query terms.
        
        Args:
            query: Search query
            limit: Maximum entities
            
        Returns:
            Dict containing found entities and related documents
        """
        _, cursor = self.connect()
        keywords = query.lower().split()
        
        # Build parameterized filter for multiple keywords
        entity_clauses = []
        params = []
        for kw in keywords:
            entity_clauses.append("LOWER(EntityText) LIKE ?")
            params.append(f"%{kw}%")
            
        entity_filter = " OR ".join(entity_clauses)
        
        # 1. Find entities
        sql_entities = f"""
            SELECT EntityID, EntityText, EntityType, Confidence, ResourceID
            FROM SQLUser.Entities
            WHERE {entity_filter}
            ORDER BY Confidence DESC
        """
        cursor.execute(sql_entities, params)
        
        entities = []
        doc_ids = set()
        for row in cursor.fetchall():
            eid, text, etype, conf, rid = row
            entities.append({
                "id": eid,
                "text": text,
                "type": etype,
                "confidence": float(conf),
                "resource_id": str(rid)
            })
            if rid:
                doc_ids.add(str(rid))
                
        # 2. Find related documents (previews)
        documents = []
        if doc_ids:
            # IRIS doesn't support list parameters well in all drivers, 
            # so we'll fetch them individually or use a pragmatic JOIN if needed.
            # For simplicity and correctness with IRIS DBAPI:
            for rid in list(doc_ids)[:10]: # Limit to top 10 docs
                cursor.execute("SELECT TextContent FROM SQLUser.FHIRDocuments WHERE ID = ?", [rid])
                doc_row = cursor.fetchone()
                if doc_row:
                    documents.append({
                        "fhir_id": rid,
                        "preview": doc_row[0][:200] + "..." if len(doc_row[0]) > 200 else doc_row[0]
                    })
                    
        return {
            "query": query,
            "entities": entities[:limit],
            "documents": documents
        }

    def get_entity_relationships(self, entity_text: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """Traverse relationships for a given entity."""
        _, cursor = self.connect()
        
        # Find the entity first
        sql_find = "SELECT EntityID FROM SQLUser.Entities WHERE LOWER(EntityText) = ?"
        cursor.execute(sql_find, [entity_text.lower()])
        row = cursor.fetchone()
        if not row:
            return []
            
        entity_id = row[0]
        
        # Find relationships
        sql_rel = """
            SELECT DISTINCT
                e1.EntityText as source,
                e1.EntityType as source_type,
                r.RelationshipType as relation,
                e2.EntityText as target,
                e2.EntityType as target_type,
                r.Confidence
            FROM SQLUser.EntityRelationships r
            JOIN SQLUser.Entities e1 ON r.SourceEntityID = e1.EntityID
            JOIN SQLUser.Entities e2 ON r.TargetEntityID = e2.EntityID
            WHERE r.SourceEntityID = ? OR r.TargetEntityID = ?
            ORDER BY r.Confidence DESC
        """
        cursor.execute(sql_rel, [entity_id, entity_id])
        
        relationships = []
        for row in cursor.fetchall():
            s, st, rel, t, tt, conf = row
            relationships.append({
                "source": s,
                "source_type": st,
                "relationship": rel,
                "target": t,
                "target_type": tt,
                "confidence": float(conf)
            })
            
        return relationships

    def get_statistics(self) -> Dict[str, Any]:
        """Get KG statistics."""
        _, cursor = self.connect()
        
        cursor.execute("SELECT COUNT(*) FROM SQLUser.Entities")
        total_entities = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM SQLUser.EntityRelationships")
        total_rels = cursor.fetchone()[0]
        
        cursor.execute("SELECT EntityType, COUNT(*) as count FROM SQLUser.Entities GROUP BY EntityType")
        distribution = [{"type": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        return {
            "total_entities": total_entities,
            "total_relationships": total_rels,
            "entity_distribution": distribution
        }
