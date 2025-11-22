# iris-vector-rag CloudConfiguration API Investigation

**Date**: December 14, 2025
**Goal**: Determine correct configuration keys for CloudConfiguration API in v0.5.4

## CloudConfiguration API - How It Actually Works ✅

### Environment Variable Mapping (Priority 1 - Highest)

**From `manager.py` lines 778-809**:
```python
env_mappings = {
    "IRIS_HOST": ("connection", "host"),
    "IRIS_PORT": ("connection", "port"),
    "IRIS_USERNAME": ("connection", "username"),
    "IRIS_PASSWORD": ("connection", "password"),
    "IRIS_NAMESPACE": ("connection", "namespace"),
    "VECTOR_DIMENSION": ("vector", "vector_dimension"),  # ← THIS IS THE KEY!
    "TABLE_SCHEMA": ("table", "table_schema"),
}
```

**✅ CORRECT environment variable for vector dimension**: `VECTOR_DIMENSION=1024`
**❌ WRONG (what our test used)**: `RAG_EMBEDDING_MODEL__DIMENSION=1024`

### Config File Mapping (Priority 2)

**From `manager.py` lines 753-763**:
```python
# Apply vector config from file
vector_file_config = self.get("storage", {})  # ← Reads from "storage" key!
if isinstance(vector_file_config, dict):
    if "vector_dimension" in vector_file_config:
        vector_config.vector_dimension = int(vector_file_config["vector_dimension"])
        vector_config.source["vector_dimension"] = ConfigSource.CONFIG_FILE
```

**✅ CORRECT config file structure**:
```yaml
storage:
  vector_dimension: 1024
```

**❌ WRONG (what our test used)**:
```yaml
embedding_model:
  dimension: 1024
```

### Defaults (Priority 3 - Lowest)

**From `entities.py` line 165**:
```python
@dataclass
class VectorConfiguration:
    vector_dimension: int = 384  # Default
```

**Default**: 384 dimensions (this is what we were getting!)

## Why Our Test Failed

### Our Test Script Configuration

**File**: `scripts/aws/test-iris-vector-rag-aws.py`

**What we set** (lines 52-55):
```python
'embedding_model': {
    'name': 'sentence-transformers/all-MiniLM-L6-v2',
    'dimension': 1024  # ← CloudConfiguration DOESN'T READ THIS!
},
```

**What we tried to workaround** (lines 369-370):
```python
os.environ['RAG_EMBEDDING_MODEL__NAME'] = 'sentence-transformers/all-MiniLM-L6-v2'
os.environ['RAG_EMBEDDING_MODEL__DIMENSION'] = '1024'  # ← CloudConfiguration DOESN'T READ THIS!
```

### Why It Didn't Work

1. CloudConfiguration reads: `VECTOR_DIMENSION` (simple name)
2. We set: `RAG_EMBEDDING_MODEL__DIMENSION` (RAG_* prefix with double underscore)
3. RAG_ prefix is used by ConfigurationManager's `get()` method for nested keys
4. CloudConfiguration API bypasses that and reads **specific environment variable names**

## The Fix - Two Options

### Option 1: Use Correct Environment Variable (Recommended)

```python
# ✅ CORRECT - This is what CloudConfiguration reads
os.environ['VECTOR_DIMENSION'] = '1024'
```

### Option 2: Use Correct Config File Structure

```yaml
# ✅ CORRECT - CloudConfiguration reads from "storage" key
storage:
  vector_dimension: 1024
  distance_metric: "COSINE"
  index_type: "HNSW"
```

## iris-vector-rag v0.5.4 Assessment

### Is CloudConfiguration API Broken? ❌ NO

**Evidence**:
- ✅ CloudConfiguration correctly reads `VECTOR_DIMENSION` environment variable
- ✅ CloudConfiguration correctly reads `storage.vector_dimension` from config
- ✅ All 21 iris-vector-rag integration tests pass
- ✅ Maintainer verified functionality

### Is Our Test Script Broken? ✅ YES

**Evidence**:
- ❌ Used wrong environment variable name (`RAG_EMBEDDING_MODEL__DIMENSION`)
- ❌ Used wrong config file structure (`embedding_model.dimension`)
- ❌ Tested custom wrapper code instead of iris-vector-rag components
- ❌ Blamed iris-vector-rag for our configuration mistakes

## SchemaManager's Role

### How SchemaManager Gets Dimensions

**From `schema_manager.py` lines 88, 94**:
```python
# SchemaManager queries CloudConfiguration
cloud_config = self.config_manager.get_cloud_config()
self.base_embedding_dimension = cloud_config.vector.vector_dimension
```

**Chain of calls**:
1. SchemaManager calls `config_manager.get_cloud_config()`
2. ConfigurationManager builds CloudConfiguration from:
   - Environment variable `VECTOR_DIMENSION` (priority 1)
   - Config file `storage.vector_dimension` (priority 2)
   - Default 384 (priority 3)
3. Returns `CloudConfiguration` with `vector.vector_dimension` set
4. SchemaManager uses this for all dimension queries

### Why We Got 384

1. Our test set: `RAG_EMBEDDING_MODEL__DIMENSION=1024`
2. CloudConfiguration looks for: `VECTOR_DIMENSION`
3. Not found in environment → checks config file
4. Config has: `embedding_model.dimension: 1024`
5. CloudConfiguration looks for: `storage.vector_dimension`
6. Not found in config → uses default
7. **Result**: 384 (the default)

## Workaround vs Proper Fix

### Our Current Workaround ❌

```python
# This doesn't work for CloudConfiguration API
os.environ['RAG_EMBEDDING_MODEL__DIMENSION'] = '1024'
```

This works for ConfigurationManager's `get("embedding_model:dimension")` but **NOT** for CloudConfiguration API.

### Proper Fix ✅

```python
# Option 1: Simple environment variable
os.environ['VECTOR_DIMENSION'] = '1024'

# Option 2: Proper config structure
config = {
    'storage': {
        'vector_dimension': 1024,
        'distance_metric': 'COSINE',
        'index_type': 'HNSW'
    }
}
```

## Does iris-vector-rag Need Changes? 🤔

### Potential Improvements for iris-vector-rag

**Issue**: Two different configuration systems with different key mappings

1. **ConfigurationManager.get()**: Uses `RAG_*` prefix with `__` for nested keys
   - Example: `RAG_EMBEDDING_MODEL__DIMENSION` → `embedding_model.dimension`

2. **CloudConfiguration API**: Uses specific environment variable names
   - Example: `VECTOR_DIMENSION` → `cloud_config.vector.vector_dimension`

**This creates confusion** because:
- Users might expect consistency between the two systems
- `RAG_` prefix suggests it's part of the standard config system
- CloudConfiguration bypasses ConfigurationManager's nested key system

### Recommendation for iris-vector-rag Team

**Option A: Document the difference** (easier)
- Clearly document that CloudConfiguration uses specific env var names
- Explain why it doesn't use `RAG_*` prefix
- Provide migration guide from old config to CloudConfiguration

**Option B: Unify the systems** (better long-term)
- Make CloudConfiguration honor `RAG_VECTOR__DIMENSION` in addition to `VECTOR_DIMENSION`
- Add mapping layer to support both naming conventions
- Maintain backward compatibility with existing deployments

**Example unified approach**:
```python
# Support both naming conventions
env_mappings = {
    "IRIS_HOST": ("connection", "host"),
    "VECTOR_DIMENSION": ("vector", "vector_dimension"),
    # Also support RAG_ prefix for consistency
    "RAG_VECTOR__DIMENSION": ("vector", "vector_dimension"),
    "RAG_DATABASE__IRIS__HOST": ("connection", "host"),
    # ...
}
```

## Conclusion

### iris-vector-rag v0.5.4 Status ✅

**NO BUGS FOUND** - CloudConfiguration API works correctly:
- ✅ Reads `VECTOR_DIMENSION` environment variable
- ✅ Reads `storage.vector_dimension` from config file
- ✅ Falls back to default 384
- ✅ SchemaManager correctly queries CloudConfiguration
- ✅ All 21 integration tests pass

### Our Test Script Status ❌

**CONFIGURATION ERROR** - Wrong keys used:
- ❌ Used `RAG_EMBEDDING_MODEL__DIMENSION` instead of `VECTOR_DIMENSION`
- ❌ Used `embedding_model.dimension` instead of `storage.vector_dimension`
- ❌ Got default 384 because CloudConfiguration couldn't find our config

### Next Steps

1. ✅ Fix our test script to use `VECTOR_DIMENSION` environment variable
2. ✅ Update config YAML to use `storage.vector_dimension` structure
3. 📝 Document correct CloudConfiguration usage in our project
4. 🤔 Suggest to iris-vector-rag team: Consider unifying the two config systems

The maintainer was 100% correct - this was a test configuration issue, not a bug in iris-vector-rag.
