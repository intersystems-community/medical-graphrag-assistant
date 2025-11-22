# Data Model: Enhanced Medical Image Search

**Feature**: 004-medical-image-search-v2  
**Date**: 2025-11-21  
**Status**: Phase 1 Design

This document defines the data entities, database schemas, and validation rules for semantic medical image search with scoring.

---

## Application Layer Entities

### ImageSearchQuery

**Purpose**: Represents a user's search request for medical images

**Schema**:
```python
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ImageSearchQuery:
    query_text: str                    # Natural language query (e.g., "chest X-ray showing pneumonia")
    limit: int = 5                     # Max number of results to return
    min_score: float = 0.0             # Minimum similarity score threshold (0.0-1.0)
    view_positions: Optional[List[str]] = None  # Filter: ['PA', 'AP', 'Lateral', 'LL']
    date_range: Optional[tuple] = None  # Filter: (start_date, end_date) as datetime
    patient_id_pattern: Optional[str] = None  # Filter: SQL LIKE pattern for SubjectID
    
    # Pagination (for P3+)
    page: int = 1                      # Page number (1-indexed)
    page_size: int = 50                # Results per page
```

**Validation Rules**:
- `query_text`: Required, 1-500 characters, non-empty after trim
- `limit`: 1-100 (prevent excessive queries)
- `min_score`: 0.0-1.0 (cosine similarity range)
- `view_positions`: If provided, must be subset of ['PA', 'AP', 'Lateral', 'LL', 'SWIMMERS', 'LATERAL']
- `date_range`: If provided, start_date <= end_date
- `page`: >= 1
- `page_size`: 1-100

**Example**:
```python
query = ImageSearchQuery(
    query_text="bilateral lung infiltrates with pleural effusion",
    limit=10,
    min_score=0.5,
    view_positions=["PA", "AP"]
)
```

---

### ImageSearchResult

**Purpose**: Represents a single image search result with metadata and scoring

**Schema**:
```python
@dataclass
class ImageSearchResult:
    # Core identification
    image_id: str                      # Unique image identifier (DICOM filename)
    study_id: str                      # Study identifier
    subject_id: str                    # Patient identifier (anonymized)
    
    # Metadata
    view_position: Optional[str]       # Radiographic view (PA/AP/Lateral/etc.)
    image_path: str                    # File system path to DICOM/image
    study_date: Optional[datetime]     # When study was performed
    
    # Scoring (P1 feature)
    similarity_score: float            # Cosine similarity (0.0-1.0)
    score_color: str                   # Color code: 'green' | 'yellow' | 'gray'
    confidence_level: str              # Label: 'strong' | 'moderate' | 'weak'
    
    # Clinical context (P2 feature - optional)
    clinical_note: Optional[str] = None        # Associated radiology report
    clinical_note_preview: Optional[str] = None # First 300 chars of note
    
    # System metadata
    search_mode: str = 'semantic'      # 'semantic' | 'keyword' | 'hybrid'
    embedding_model: str = 'nvidia/nvclip'  # Model used for embedding
```

**Validation Rules**:
- `image_id`, `study_id`, `subject_id`: Required, non-empty
- `similarity_score`: 0.0-1.0
- `score_color`: Must be 'green' | 'yellow' | 'gray'
- `confidence_level`: Must be 'strong' | 'moderate' | 'weak'
- `image_path`: Must be valid file path format
- `search_mode`: Must be 'semantic' | 'keyword' | 'hybrid'

**Example**:
```python
result = ImageSearchResult(
    image_id="4b369dbe-417168fa-7e2b5f04-00582488-c50504e7",
    study_id="53819164",
    subject_id="10045779",
    view_position="PA",
    image_path="../mimic-cxr/physionet.org/files/mimic-cxr/2.1.0/files/p10/p10045779/s53819164/4b369dbe.dcm",
    similarity_score=0.87,
    score_color="green",
    confidence_level="strong",
    search_mode="semantic",
    embedding_model="nvidia/nvclip"
)
```

---

### SimilarityScore

**Purpose**: Utility class for score calculations and display logic

**Schema**:
```python
@dataclass
class SimilarityScore:
    value: float                       # Raw cosine similarity (0.0-1.0)
    
    @property
    def color(self) -> str:
        """Get color code based on score thresholds."""
        if self.value >= 0.7:
            return 'green'
        elif self.value >= 0.5:
            return 'yellow'
        else:
            return 'gray'
    
    @property
    def confidence_level(self) -> str:
        """Get human-readable confidence label."""
        if self.value >= 0.7:
            return 'strong'
        elif self.value >= 0.5:
            return 'moderate'
        else:
            return 'weak'
    
    @property
    def hex_color(self) -> str:
        """Get hex color for UI rendering."""
        colors = {
            'green': '#28a745',
            'yellow': '#ffc107',
            'gray': '#6c757d'
        }
        return colors[self.color]
    
    def __str__(self) -> str:
        return f"{self.value:.2f} ({self.confidence_level})"
```

**Score Thresholds** (calibrated from research):
- **Strong** (green): ≥ 0.7
- **Moderate** (yellow): 0.5 - 0.7
- **Weak** (gray): < 0.5

---

### SearchResponse

**Purpose**: Wrapper for complete search API response

**Schema**:
```python
@dataclass
class SearchResponse:
    query: ImageSearchQuery            # Original query
    results: List[ImageSearchResult]   # Matched images
    total_results: int                 # Total matches (before pagination)
    search_mode: str                   # 'semantic' | 'keyword' | 'hybrid'
    execution_time_ms: int             # Query execution time
    cache_hit: bool = False            # Whether embedding was cached
    
    # Error/fallback info
    fallback_reason: Optional[str] = None  # Why fallback used (if search_mode='keyword')
    
    # Statistics
    avg_score: Optional[float] = None  # Average similarity score
    max_score: Optional[float] = None  # Highest similarity score
    min_score: Optional[float] = None  # Lowest similarity score
```

**Example**:
```python
response = SearchResponse(
    query=query,
    results=[result1, result2, result3],
    total_results=127,
    search_mode="semantic",
    execution_time_ms=2456,
    cache_hit=True,
    avg_score=0.72,
    max_score=0.89,
    min_score=0.54
)
```

---

## Database Layer Schemas

### VectorSearch.MIMICCXRImages (Existing Table)

**Purpose**: Stores medical images with vector embeddings for semantic search

**DDL**:
```sql
CREATE TABLE VectorSearch.MIMICCXRImages (
    ImageID VARCHAR(100) PRIMARY KEY,
    SubjectID VARCHAR(20) NOT NULL,
    StudyID VARCHAR(20) NOT NULL,
    DicomID VARCHAR(100),
    ImagePath VARCHAR(1000) NOT NULL,
    ViewPosition VARCHAR(20),
    Vector VECTOR(DOUBLE, 1024) NOT NULL,  -- NV-CLIP embedding
    EmbeddingModel VARCHAR(100) DEFAULT 'nvidia/nvclip',
    Provider VARCHAR(50) DEFAULT 'nvclip',
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_subject (SubjectID),
    INDEX idx_study (StudyID),
    INDEX idx_view (ViewPosition)
)
```

**Notes**:
- `Vector` type is IRIS native vector with optimized VECTOR_COSINE() support
- `ImagePath` is relative path from project root
- `ViewPosition` values: PA, AP, LATERAL, LL, SWIMMERS, etc.

---

### SQLUser.FHIRDocuments (Existing Table)

**Purpose**: Stores FHIR resources including clinical notes

**DDL** (subset relevant to image search):
```sql
CREATE TABLE SQLUser.FHIRDocuments (
    FHIRResourceId VARCHAR(50) PRIMARY KEY,
    ResourceType VARCHAR(50) NOT NULL,
    ResourceString CLOB NOT NULL,  -- JSON with hex-encoded clinical notes
    
    INDEX idx_resource_type (ResourceType)
)
```

**Clinical Note Extraction**:
```python
# Decode hex-encoded clinical note from FHIR JSON
resource_json = json.loads(resource_string)
encoded_data = resource_json['content'][0]['attachment']['data']
clinical_note = bytes.fromhex(encoded_data).decode('utf-8')
```

---

## Service Layer Abstractions

### EmbeddingCache

**Purpose**: In-memory LRU cache for text embeddings

**Interface**:
```python
from functools import lru_cache
from typing import Tuple

class EmbeddingCache:
    """LRU cache for NV-CLIP text embeddings."""
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def get_cached_embedding(query_text: str) -> Tuple[float, ...]:
        """
        Get or compute embedding for query text.
        
        Args:
            query_text: Natural language query
            
        Returns:
            Embedding as tuple (hashable for cache)
        """
        embedder = get_embedder()
        embedding = embedder.embed_text(query_text)
        return tuple(embedding)  # Convert list to tuple for hashing
    
    @staticmethod
    def cache_info():
        """Get cache statistics (hits, misses, size)."""
        return EmbeddingCache.get_cached_embedding.cache_info()
    
    @staticmethod
    def clear_cache():
        """Clear all cached embeddings."""
        EmbeddingCache.get_cached_embedding.cache_clear()
```

**Cache Statistics**:
```python
CacheInfo(hits=342, misses=158, maxsize=1000, currsize=158)
# Hit rate: 68.4%
```

---

### DatabaseConnection

**Purpose**: Environment-aware IRIS database connection manager

**Interface**:
```python
import os
import intersystems_iris.dbapi._DBAPI as iris

class DatabaseConnection:
    """IRIS database connection with environment-based config."""
    
    @staticmethod
    def get_config() -> dict:
        """Get database config from environment variables."""
        return {
            'hostname': os.getenv('IRIS_HOST', '3.84.250.46'),  # Default: AWS prod
            'port': int(os.getenv('IRIS_PORT', 1972)),
            'namespace': os.getenv('IRIS_NAMESPACE', '%SYS'),
            'username': os.getenv('IRIS_USERNAME', '_SYSTEM'),
            'password': os.getenv('IRIS_PASSWORD', 'SYS')
        }
    
    @staticmethod
    def get_connection():
        """Create IRIS database connection."""
        config = DatabaseConnection.get_config()
        return iris.connect(**config)
    
    @staticmethod
    def is_local() -> bool:
        """Check if using local development database."""
        return os.getenv('IRIS_HOST', '').startswith('localhost')
```

**Environment Variables**:
```bash
# Development (.env)
IRIS_HOST=localhost
IRIS_PORT=32782
IRIS_NAMESPACE=DEMO
IRIS_USERNAME=_SYSTEM
IRIS_PASSWORD=ISCDEMO

# Production (AWS - defaults, no .env needed)
# Uses 3.84.250.46:1972/%SYS
```

---

## Validation Logic

### Query Validation

```python
class QueryValidator:
    """Validates ImageSearchQuery parameters."""
    
    @staticmethod
    def validate(query: ImageSearchQuery) -> List[str]:
        """
        Validate query parameters.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Query text
        if not query.query_text or not query.query_text.strip():
            errors.append("query_text is required and cannot be empty")
        elif len(query.query_text) > 500:
            errors.append("query_text must be 500 characters or less")
        
        # Limit
        if query.limit < 1 or query.limit > 100:
            errors.append("limit must be between 1 and 100")
        
        # Min score
        if query.min_score < 0.0 or query.min_score > 1.0:
            errors.append("min_score must be between 0.0 and 1.0")
        
        # View positions
        valid_views = {'PA', 'AP', 'LATERAL', 'LL', 'SWIMMERS'}
        if query.view_positions:
            invalid = set(query.view_positions) - valid_views
            if invalid:
                errors.append(f"Invalid view positions: {invalid}")
        
        # Date range
        if query.date_range:
            start, end = query.date_range
            if start > end:
                errors.append("date_range start must be before end")
        
        # Pagination
        if query.page < 1:
            errors.append("page must be >= 1")
        if query.page_size < 1 or query.page_size > 100:
            errors.append("page_size must be between 1 and 100")
        
        return errors
```

---

## Error Handling

### Exception Types

```python
class ImageSearchError(Exception):
    """Base exception for image search errors."""
    pass

class InvalidQueryError(ImageSearchError):
    """Query validation failed."""
    pass

class EmbeddingServiceError(ImageSearchError):
    """NV-CLIP embedding service unavailable or failed."""
    pass

class DatabaseError(ImageSearchError):
    """IRIS database connection or query failed."""
    pass

class FileNotFoundError(ImageSearchError):
    """Image file path invalid or file missing."""
    pass
```

---

## Performance Considerations

### Expected Latencies

| Operation | Cold Cache | Warm Cache | Notes |
|-----------|-----------|-----------|-------|
| NV-CLIP embed_text() | 500-2000ms | <1ms | API call vs cache |
| IRIS VECTOR_COSINE query | 50-200ms | 30-100ms | Depends on result count |
| FHIR note retrieval | 100-500ms | 50-200ms | Fuzzy matching overhead |
| Total search (semantic) | 600-2200ms | 100-300ms | Target: <10s p95 |
| Total search (keyword) | 20-100ms | 10-50ms | Fallback mode |

### Optimization Strategies

1. **Embedding Cache**: 1000-query LRU cache (68%+ hit rate expected)
2. **Database Indexes**: SubjectID, StudyID, ViewPosition
3. **Result Limiting**: Default 5, max 100 to prevent slow queries
4. **Lazy Loading**: Defer clinical note retrieval to P2 (on-demand)
5. **Pagination**: Avoid loading all results, paginate at 50/page

---

## Migration Path

### From Current Implementation to P1

**Current** (`search_medical_images` tool):
```python
{
    "query": "pneumonia",
    "results_count": 5,
    "images": [
        {
            "image_id": "...",
            "study_id": "...",
            "subject_id": "...",
            "view_position": "PA",
            "image_path": "...",
            "description": "Chest X-ray (PA) for patient ..."
        }
    ]
}
```

**P1 Enhanced** (with scoring):
```python
{
    "query": "pneumonia",
    "results_count": 5,
    "search_mode": "semantic",  # NEW
    "execution_time_ms": 1247,  # NEW
    "cache_hit": true,          # NEW
    "avg_score": 0.74,          # NEW
    "images": [
        {
            "image_id": "...",
            "study_id": "...",
            "subject_id": "...",
            "view_position": "PA",
            "image_path": "...",
            "description": "Chest X-ray (PA) for patient ...",
            "similarity_score": 0.87,      # NEW
            "score_color": "green",        # NEW
            "confidence_level": "strong"   # NEW
        }
    ]
}
```

**Backward Compatibility**: All existing fields preserved, new fields added

---

## Summary

**Entities Defined**: 5 application-layer entities + 2 database schemas + 3 service abstractions

**Key Design Decisions**:
1. Use dataclasses for entity definitions (Python 3.7+)
2. Score thresholds: 0.7 (strong), 0.5 (moderate), <0.5 (weak)
3. LRU cache with 1000-query capacity
4. Environment-based database configuration
5. Graceful fallback to keyword search
6. Backward-compatible response format

**Next Steps**: 
- Create API contracts (JSON schemas)
- Write quickstart guide
- Begin implementation (Phase 2)

---

**Version**: 1.0  
**Status**: Complete  
**Last Updated**: 2025-11-21
