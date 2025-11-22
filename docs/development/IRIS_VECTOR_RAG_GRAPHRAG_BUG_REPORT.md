# iris-vector-rag v0.5.4 GraphRAG Pipeline Bug Report

**Date**: December 13, 2025
**Reporter**: AWS GraphRAG deployment testing
**Version**: iris-vector-rag v0.5.4
**Severity**: High (blocks GraphRAG pipeline usage)

---

## Summary

The `GraphRAGPipeline.ingest()` method in iris-vector-rag v0.5.4 fails with an `UnboundLocalError` due to missing `time` module import in the GraphRAG pipeline implementation.

---

## Error Details

### Error Message
```python
UnboundLocalError: cannot access local variable 'time' where it is not associated with a value
```

### Stack Trace
```
File "/opt/homebrew/Caskroom/miniconda/base/lib/python3.12/site-packages/iris_vector_rag/core/base.py", line 145, in ingest
    self.load_documents("", documents=documents, **kwargs)
File "/opt/homebrew/Caskroom/miniconda/base/lib/python3.12/site-packages/iris_vector_rag/pipelines/graphrag.py", line 93, in load_documents
    start_time = time.time()
                 ^^^^
UnboundLocalError: cannot access local variable 'time' where it is not associated with a value
```

### Root Cause
The file `iris_vector_rag/pipelines/graphrag.py` uses `time.time()` at line 93 but does not import the `time` module.

---

## Reproduction Steps

### 1. Setup
```python
import os
os.environ['VECTOR_DIMENSION'] = '1024'
os.environ['IRIS_HOST'] = '3.84.250.46'
os.environ['IRIS_PORT'] = '1972'
os.environ['IRIS_NAMESPACE'] = '%SYS'
os.environ['IRIS_USER'] = '_SYSTEM'
os.environ['IRIS_PASSWORD'] = 'SYS'

from iris_vector_rag.config.manager import ConfigurationManager
from iris_vector_rag.storage.vector_store_iris import IRISVectorStore
from iris_vector_rag.pipelines import GraphRAGPipeline
from iris_vector_rag.core.models import Document
```

### 2. Initialize Pipeline
```python
config = ConfigurationManager(config_path="config/fhir_graphrag_config.aws.yaml")
vector_store = IRISVectorStore(config_manager=config)
pipeline = GraphRAGPipeline(
    config_manager=config,
    vector_store=vector_store
)
```

### 3. Prepare Documents
```python
documents = [
    Document(
        page_content="Clinical note content here",
        id="doc1",
        metadata={'resource_type': 'DocumentReference'}
    )
]
```

### 4. Trigger Error
```python
pipeline.ingest(documents)  # ❌ UnboundLocalError: cannot access local variable 'time'
```

---

## Expected Behavior

The `ingest()` method should:
1. Accept a list of `Document` objects
2. Extract entities from document content
3. Build knowledge graph with entities and relationships
4. Store embeddings in IRIS vector tables
5. Return successfully without errors

---

## Actual Behavior

The `ingest()` method immediately fails with `UnboundLocalError` when attempting to execute `start_time = time.time()` because the `time` module is not imported in `graphrag.py`.

---

## Proposed Fix

### File: `iris_vector_rag/pipelines/graphrag.py`

**Add missing import at the top of the file:**

```python
import time
```

**Before:**
```python
# graphrag.py
from iris_vector_rag.core.base import RAGPipeline
# ... other imports ...
# Missing: import time
```

**After:**
```python
# graphrag.py
import time
from iris_vector_rag.core.base import RAGPipeline
# ... other imports ...
```

---

## Workaround

Until this is fixed in a future release, users can:

### Option 1: Monkey Patch
```python
import time
import iris_vector_rag.pipelines.graphrag as graphrag_module
graphrag_module.time = time
```

### Option 2: Use Alternative Pipelines
```python
# Use BasicRAGPipeline or CRAGPipeline instead
from iris_vector_rag.pipelines import BasicRAGPipeline
pipeline = BasicRAGPipeline(config_manager=config, vector_store=vector_store)
```

### Option 3: Manual Entity Extraction
```python
# Extract entities manually without using GraphRAG pipeline
# (Requires custom implementation)
```

---

## Environment Details

### System
- **OS**: macOS Darwin 24.5.0
- **Python**: 3.12
- **Architecture**: Apple Silicon (ARM64)

### Package Versions
```
iris-vector-rag==0.5.4
intersystems-irispython==5.0.1
sentence-transformers==3.3.1
```

### Database
- **IRIS**: InterSystems IRIS Community Edition (latest)
- **Deployment**: AWS EC2 g5.xlarge (us-east-1)
- **Namespace**: %SYS
- **Schema**: SQLUser

### Configuration
```yaml
# config/fhir_graphrag_config.aws.yaml
database:
  iris:
    host: "3.84.250.46"
    port: 1972
    namespace: "%SYS"

storage:
  vector_dimension: 1024
  distance_metric: "COSINE"
  index_type: "HNSW"

knowledge_graph:
  entities_table: "SQLUser.Entities"
  relationships_table: "SQLUser.EntityRelationships"
```

---

## Impact Assessment

### Severity: **High**
- **Blocks GraphRAG functionality entirely**
- Affects all users attempting to use GraphRAG pipeline
- No graceful degradation or fallback

### Affected Users
- Anyone using `GraphRAGPipeline.ingest()` method
- Cloud deployments requiring GraphRAG features
- Multi-modal search implementations

### Workaround Difficulty
- **Easy** for developers familiar with Python imports
- **Difficult** for users relying on packaged functionality
- Requires code modification or monkey patching

---

## Testing Recommendations

### Unit Test to Prevent Regression
```python
def test_graphrag_pipeline_ingest():
    """Test that GraphRAG pipeline can ingest documents without import errors."""
    from iris_vector_rag.pipelines import GraphRAGPipeline
    from iris_vector_rag.core.models import Document

    # Mock config and vector store
    pipeline = GraphRAGPipeline(config_manager=mock_config, vector_store=mock_store)

    docs = [Document(page_content="test", id="1", metadata={})]

    # Should not raise UnboundLocalError
    try:
        pipeline.ingest(docs)
    except UnboundLocalError as e:
        pytest.fail(f"GraphRAG pipeline missing import: {e}")
```

### Integration Test
```python
def test_graphrag_pipeline_end_to_end():
    """Test full GraphRAG pipeline with real IRIS connection."""
    # Setup real config pointing to test IRIS instance
    config = ConfigurationManager(config_path="test_config.yaml")
    vector_store = IRISVectorStore(config_manager=config)
    pipeline = GraphRAGPipeline(config_manager=config, vector_store=vector_store)

    # Create test documents
    docs = [
        Document(page_content="Patient has chest pain", id="1", metadata={}),
        Document(page_content="Patient prescribed aspirin", id="2", metadata={})
    ]

    # Ingest should complete without errors
    pipeline.ingest(docs)

    # Query should return results
    results = pipeline.query("chest pain", top_k=1)
    assert len(results) > 0
```

---

## Related Issues

### Similar Import Issues to Check
1. Are there other missing imports in `graphrag.py`?
2. Does `HybridGraphRAGPipeline` have the same issue?
3. Are there missing imports in other pipeline implementations?

### Suggested Code Review
- **File**: `iris_vector_rag/pipelines/graphrag.py`
- **Check**: All standard library imports present
- **Verify**: `time`, `datetime`, `os`, `sys`, `json`, etc.

---

## Additional Context

### Use Case
We are deploying a FHIR GraphRAG system on AWS EC2 with:
- 51 DocumentReference resources (clinical notes)
- NVIDIA NIM embeddings (1024-dimensional)
- InterSystems IRIS vector database
- Knowledge graph for medical entity extraction

### Why This Matters
GraphRAG is a key feature differentiator for iris-vector-rag. The pipeline should work out-of-the-box for users following the documentation. This import error creates a poor first-use experience and blocks cloud deployment workflows.

### Documentation Impact
Once fixed, documentation should include:
- End-to-end GraphRAG pipeline example
- Cloud deployment guide (AWS, Azure, GCP)
- Troubleshooting section for common pipeline errors

---

## Verification Steps

### After Fix is Applied

1. **Install fixed version**
   ```bash
   pip install iris-vector-rag>=0.5.5  # or whatever version contains the fix
   ```

2. **Run test script**
   ```python
   from iris_vector_rag.pipelines import GraphRAGPipeline
   from iris_vector_rag.core.models import Document

   # Should import without errors
   import iris_vector_rag.pipelines.graphrag as graphrag
   assert hasattr(graphrag, 'time'), "time module should be imported"
   ```

3. **Test ingest**
   ```python
   pipeline = GraphRAGPipeline(config_manager=config, vector_store=vector_store)
   docs = [Document(page_content="test", id="1", metadata={})]

   # Should complete without UnboundLocalError
   pipeline.ingest(docs)
   print("✅ GraphRAG ingest working!")
   ```

4. **Test query**
   ```python
   results = pipeline.query("test query", top_k=5)
   print(f"✅ GraphRAG query returned {len(results)} results")
   ```

---

## Priority Recommendation

**Priority**: **P0 (Critical)**

**Rationale**:
- Core feature completely broken
- Simple one-line fix
- Blocks user adoption of GraphRAG
- Affects cloud deployment workflows
- Easy to miss in development if not testing GraphRAG path

**Timeline**: Should be fixed in next patch release (v0.5.5)

---

## Contact

For questions about this bug report, please refer to:
- **Repository**: FHIR-AI-Hackathon-Kit AWS deployment
- **Configuration**: `config/fhir_graphrag_config.aws.yaml`
- **Test Script**: `scripts/aws/build-knowledge-graph-aws.py`
- **Full Stack Trace**: See error details section above

---

## Acknowledgments

Thank you to the iris-vector-rag team for creating this valuable framework. This bug report is provided in the spirit of improving the library for the entire community. The overall architecture and API design of iris-vector-rag v0.5.4 is excellent - this is just a minor import oversight that slipped through.

**Positive Feedback**:
- ✅ ConfigurationManager works perfectly
- ✅ IRISVectorStore abstractions are clean
- ✅ Document model is intuitive
- ✅ Pipeline factory pattern is elegant
- ✅ CloudConfiguration API properly reads `storage.vector_dimension`

This bug is easily fixable and doesn't detract from the overall quality of the package.
