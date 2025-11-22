# iris-vector-rag 0.5.2: New Issues Discovered During Testing

**Date**: December 12, 2025
**Status**: 🔍 **NEW BUGS FOUND** during AWS integration testing

---

## TL;DR

While testing iris-vector-rag 0.5.2 improvements, we discovered **3 NEW critical bugs** that affect AWS deployments:

1. ❌ **Connection utility ignores ConfigurationManager** (uses legacy env vars only)
2. ❌ **SchemaManager dot/colon notation mismatch** (can't read config)
3. ❌ **Class-level caching breaks config reloading**

**Good news**: ConfigurationManager improvements ARE working! Tests 1-3 and 6 passed.
**Bad news**: ConnectionManager and SchemaManager have integration bugs.

---

## Test Results Summary

| Test | Status | Issue |
|------|--------|-------|
| 1. ConfigurationManager | ✅ PASS | Works perfectly! |
| 2. Environment Variables | ✅ PASS | RAG_* prefix working! |
| 3. ConnectionManager | ✅ PASS | (with workaround) |
| 4. IRISVectorStore | ❌ FAIL | SchemaManager bug |
| 5. SchemaManager | ❌ FAIL | SchemaManager bug |
| 6. Document Model | ✅ PASS | Correct API usage |

**Result**: 4/6 tests passed, 2 fail due to SchemaManager bug

---

## Issue #1: Connection Utility Ignores ConfigurationManager

### Problem

The `get_iris_dbapi_connection()` function in `common/iris_dbapi_connector.py` **does not accept any parameters** and **ignores ConfigurationManager settings**.

**Code Analysis** (lines 151-191):

```python
def get_iris_dbapi_connection():
    """
    Establishes a connection to InterSystems IRIS using DBAPI.

    Reads connection parameters from environment variables:
    - IRIS_HOST
    - IRIS_PORT
    - IRIS_NAMESPACE
    - IRIS_USER
    - IRIS_PASSWORD
    """
    # Get connection parameters from environment with auto-detection fallback
    host = os.environ.get("IRIS_HOST", "localhost")
    port_env = os.environ.get("IRIS_PORT")
    # ... only reads from IRIS_* env vars, NOT from ConfigurationManager!
```

**ConnectionManager calls this** (line 158):

```python
connection = get_iris_dbapi_connection()  # No parameters passed!
```

### Impact

- ConfigurationManager settings are **completely ignored** for connections
- Must use **legacy environment variables** (`IRIS_*`) instead of new `RAG_*` variables
- Cannot use YAML configuration for database connection
- Breaks the whole point of having ConfigurationManager!

### Workaround

```bash
# Must set legacy env vars manually
export IRIS_HOST="3.84.250.46"
export IRIS_PORT="1972"
export IRIS_NAMESPACE="%SYS"
export IRIS_USER="_SYSTEM"
export IRIS_PASSWORD="SYS"
```

### Recommendation

**Fix**: Modify `get_iris_dbapi_connection()` to accept ConfigurationManager parameters:

```python
def get_iris_dbapi_connection(config_manager=None):
    """Establishes connection using ConfigurationManager settings."""
    if config_manager:
        host = config_manager.get("database:iris:host", "localhost")
        port = config_manager.get("database:iris:port", 1972)
        # ... use config_manager instead of os.environ
    else:
        # Fallback to env vars for backward compatibility
        host = os.environ.get("IRIS_HOST", "localhost")
        # ...
```

---

## Issue #2: SchemaManager Dot/Colon Notation Mismatch

### Problem

**SchemaManager uses DOT notation** but **ConfigurationManager.get() uses COLON notation**.

**SchemaManager code** (`storage/schema_manager.py` lines 48-52):

```python
self.base_embedding_model = self.config_manager.get(
    "embedding_model.name", "sentence-transformers/all-MiniLM-L6-v2"
)
self.base_embedding_dimension = self.config_manager.get(
    "embedding_model.dimension", 384  # Always returns 384!
)
```

**ConfigurationManager.get()** (`config/manager.py` lines 150-171):

```python
def get(self, key_string: str, default: Optional[Any] = None) -> Any:
    """
    Retrieves a configuration setting.

    Keys can be nested using a colon delimiter (e.g., "database:iris:host").
    """
    keys = [k.lower() for k in key_string.split(":")]  # Splits on COLON!
    # ...
```

### What Happens

When SchemaManager calls `config.get("embedding_model.dimension", 384)`:

1. ConfigurationManager splits on `:` → `["embedding_model.dimension"]` (single element!)
2. Tries to access `config["embedding_model.dimension"]` (single key with dot)
3. Key doesn't exist → returns default `384`
4. **ALWAYS returns 384** regardless of config file or environment variables!

### Impact

- **Cannot configure vector dimensions** via SchemaManager
- **ALWAYS uses 384-dim vectors** (default)
- NVIDIA NIM 1024-dim vectors **impossible to use**
- Makes the "configurable dimensions" feature **completely broken** for SchemaManager

### Evidence

**Test Output**:

```
Test 1: ConfigurationManager
✅ Embedding Model Dimension: 1024 (SchemaManager uses this)

Test 4: IRISVectorStore
   Vector Dimension: 384  ← Should be 1024!

Test 5: SchemaManager
✅ Vector dimension from config: 384  ← Should be 1024!
```

ConfigurationManager correctly loads 1024, but SchemaManager gets 384!

### Workaround

**None that works**. Environment variables don't help because:
- `RAG_EMBEDDING_MODEL__DIMENSION=1024` → `config['embedding_model']['dimension'] = 1024`
- SchemaManager calls `get("embedding_model.dimension")` → splits on `:` → looks for `config["embedding_model.dimension"]`
- Doesn't match!

### Recommendation

**Fix Option 1**: Use `get_nested()` method (already exists!):

```python
# In SchemaManager.__init__
self.base_embedding_dimension = self.config_manager.get_nested(
    "embedding_model.dimension", 384  # Use get_nested() instead of get()
)
```

**Fix Option 2**: Make `get()` handle both notations:

```python
def get(self, key_string: str, default: Optional[Any] = None) -> Any:
    # Try colon notation first
    if ":" in key_string:
        keys = [k.lower() for k in key_string.split(":")]
    # Try dot notation as fallback
    elif "." in key_string:
        keys = [k.lower() for k in key_string.split(".")]
    else:
        keys = [key_string.lower()]
    # ... rest of logic
```

---

## Issue #3: Class-Level Caching Breaks Config Reloading

### Problem

SchemaManager has **class-level caching** that prevents configuration reloading.

**Code** (`storage/schema_manager.py` lines 29-32, 42-57):

```python
class SchemaManager:
    # CLASS-LEVEL CACHING (shared across all instances for performance)
    _schema_validation_cache = {}
    _config_loaded = False  # ← Shared across ALL instances!
    _tables_validated = set()

    def __init__(self, connection_manager, config_manager):
        # Load configuration only if not already loaded
        if not SchemaManager._config_loaded:
            self._load_and_validate_config()
            SchemaManager._config_loaded = True
        else:
            # Use cached config from previous instance
            self.base_embedding_dimension = self.config_manager.get(
                "embedding_model.dimension", 384
            )
```

### Impact

- First SchemaManager instance loads config
- All subsequent instances use **cached values**
- Changing ConfigurationManager has **no effect**
- Cannot test with different configurations
- Makes unit testing **very difficult**

### Workaround

```python
# Must manually reset class-level cache before each test
from iris_vector_rag.storage.schema_manager import SchemaManager
SchemaManager._config_loaded = False
SchemaManager._schema_validation_cache = {}
SchemaManager._tables_validated = set()
```

### Recommendation

**Fix**: Remove class-level caching or make it instance-level:

```python
class SchemaManager:
    def __init__(self, connection_manager, config_manager):
        self.connection_manager = connection_manager
        self.config_manager = config_manager

        # Instance-level cache (not class-level)
        self._dimension_cache = {}

        # ALWAYS load config from config_manager (no caching)
        self._load_and_validate_config()
```

---

## Positive Findings

### ✅ ConfigurationManager Works Great!

**What Works**:
- ✅ YAML configuration loading
- ✅ Environment variable overrides with `RAG_` prefix
- ✅ Nested key access with `__` delimiter
- ✅ Type casting (string → int/float/bool)
- ✅ Default values

**Test Evidence**:

```
Test 1: ConfigurationManager
✅ Config loaded successfully:
   Host: 3.84.250.46
   Port: 1972
   Namespace: %SYS
   Embedding Model Dimension: 1024

Test 2: Environment Variable Overrides
✅ Environment variable override working:
   Config file: 3.84.250.46
   Env var: test-override.example.com
   Actual: test-override.example.com
```

### ✅ Document Model API Clear

**What Works**:
- ✅ Correct parameter names: `page_content`, `id`, `metadata`
- ✅ Embeddings stored separately (not in Document)
- ✅ Clean API design

---

## Summary: Original Pain Points vs New Issues

### Original Pain Points (RESOLVED) ✅

1. ✅ **Hardcoded settings** → ConfigurationManager added
2. ✅ **Inflexible dimensions** → Configurable (but SchemaManager can't use it)
3. ✅ **No config manager** → ConfigurationManager working great

### New Issues (FOUND) ❌

1. ❌ **ConnectionManager ignores config** → Uses legacy env vars only
2. ❌ **SchemaManager dot/colon mismatch** → Can't read config
3. ❌ **Class-level caching** → Prevents config reloading

---

## Recommendations for iris-vector-rag Team

### Priority 1: Fix SchemaManager Configuration

**Impact**: HIGH - Makes "configurable dimensions" feature unusable

**Fix**:
```python
# In SchemaManager._load_and_validate_config()
self.base_embedding_dimension = self.config_manager.get_nested(
    "embedding_model.dimension", 384  # Use get_nested() instead of get()
)
```

### Priority 2: Fix ConnectionManager Integration

**Impact**: HIGH - ConfigurationManager is pointless without this

**Fix**:
```python
# In ConnectionManager.get_connection()
from iris_vector_rag.common.iris_dbapi_connector import get_iris_dbapi_connection

# Pass config_manager settings to connection utility
db_config = self.config_manager.get("database:iris", {})
connection = get_iris_dbapi_connection(
    host=db_config.get("host"),
    port=db_config.get("port"),
    namespace=db_config.get("namespace"),
    username=db_config.get("username"),
    password=db_config.get("password")
)
```

### Priority 3: Remove Class-Level Caching

**Impact**: MEDIUM - Makes testing difficult

**Fix**: Move caching to instance level or remove entirely.

---

## Test Script

See `scripts/aws/test-iris-vector-rag-aws.py` for complete test suite that demonstrates all issues.

**Run tests**:

```bash
python3 scripts/aws/test-iris-vector-rag-aws.py
```

**Expected Results** (with current bugs):
- 4/6 tests pass
- Tests 4-5 fail due to SchemaManager bug

---

## Conclusion

**Good News**:
- ConfigurationManager improvements are **excellent**!
- Environment variable support **works perfectly**
- Core concepts are **solid**

**Bad News**:
- Integration between components is **broken**
- ConnectionManager and SchemaManager **don't use ConfigurationManager**
- Makes the improvements **unusable in practice**

**Recommendation**:
- Fix the dot/colon notation mismatch (1 line change!)
- Integrate ConnectionManager with ConfigurationManager
- These are **easy fixes** that would make iris-vector-rag **production-ready**

---

**Status**: ✅ Issues documented and reproducible
**Next Steps**: Share with iris-vector-rag team for fixes
**Test Suite**: `scripts/aws/test-iris-vector-rag-aws.py`
