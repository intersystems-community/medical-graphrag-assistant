# Memory Search Browse Fix - Empty Query Support

## Issue
Memory search was failing with error: `'<' not supported between instances of 'str' and 'float'` when trying to search. Additionally, empty search strings should allow browsing all memories, but instead showed a warning.

## Root Causes

### 1. Type Comparison Error
**Location**: `src/memory/vector_memory.py:207`

**Problem**: InterSystems IRIS was returning similarity scores as strings instead of floats, causing type error when comparing `similarity < min_similarity`.

**Fix**: Added explicit type conversion with error handling:
```python
# Convert similarity to float (IRIS may return as string)
try:
    similarity = float(similarity) if similarity is not None else 0.0
except (ValueError, TypeError):
    similarity = 0.0
```

### 2. Empty Query Not Supported
**Location**: `src/memory/vector_memory.py:156` (recall method)

**Problem**: Empty search strings triggered warning "Please enter a search query" instead of allowing users to browse all memories.

**Fix**: Added special handling for empty queries - returns all memories sorted by use count and recency:
```python
# Handle empty query - return all memories sorted by use count
if not query or not query.strip():
    # ... SQL query without vector search
    ORDER BY UseCount DESC, UpdatedAt DESC
```

### 3. UI Warning for Empty Search
**Location**: `mcp-server/streamlit_app.py:988-991`

**Problem**: Streamlit UI showed warning and blocked empty searches.

**Fix**:
- Removed the warning check
- Pass empty string to recall() to trigger browse mode
- Updated placeholder text to indicate empty search is supported

## Changes Made

### `src/memory/vector_memory.py`
1. **Lines 169-211**: Added empty query handler that returns all memories sorted by use_count
2. **Lines 246-250**: Added type conversion for similarity scores with try/except

### `mcp-server/streamlit_app.py`
1. **Line 982**: Updated placeholder text: `"e.g., 'pneumonia' or leave empty to browse all"`
2. **Lines 988-991**: Simplified search button logic to allow empty queries

## Features Added

### Browse All Memories
- Click search button with empty query → shows all memories
- Results sorted by use count (most used first)
- Then by last updated timestamp
- Similarity score shows as 1.0 (no vector search performed)

### Semantic Search
- Enter search query → uses NV-CLIP embeddings for semantic similarity
- Results sorted by cosine similarity
- Shows actual similarity scores (0-1)
- Filters by min_similarity threshold (default 0.5)

## Testing

### Test Empty Search (Browse Mode)
```python
from src.memory import VectorMemory

memory = VectorMemory()

# Empty query returns all memories sorted by use count
results = memory.recall("", top_k=10)

for r in results:
    print(f"{r['memory_type']}: {r['text'][:50]}... (used {r['use_count']}x)")
```

### Test Semantic Search
```python
# Search with query uses vector similarity
results = memory.recall("pneumonia", top_k=5)

for r in results:
    print(f"Similarity {r['similarity']:.2f}: {r['text'][:50]}...")
```

## Current Status
- ✅ Streamlit restarted with fixes applied
- ✅ SSH tunnel to AWS NIM active on port 8002
- ✅ Empty search works - browses all memories
- ✅ Semantic search works - uses NV-CLIP embeddings
- ✅ Type errors fixed - handles string/float conversions
- ✅ UI updated with clear placeholder text

## Usage

### Browse All Memories
1. Open http://localhost:8501
2. Expand sidebar "📚 Browse Memories"
3. Leave search box empty
4. Click 🔍 Search
5. See all 5 memories sorted by use count

### Search Memories Semantically
1. Enter search query (e.g., "chest", "pneumonia", "diagnosis")
2. Click 🔍 Search
3. See results ranked by semantic similarity

## Files Modified
- `src/memory/vector_memory.py` - Added empty query handling and type conversion
- `mcp-server/streamlit_app.py` - Removed empty query warning, updated placeholder

## Related Fixes
- See `EMBEDDINGS_FIXED.md` for the original embedding issues
- This fix completes the memory search feature implementation
