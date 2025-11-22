# Using iris-devtester for AWS IRIS Deployments

**Status**: Recommended for future deployments
**Priority**: P1 - Would significantly simplify deployment

## Current Approach vs. iris-devtester

### What We Did (Manual Approach)
1. Manually wrote bash scripts for IRIS container deployment
2. Complex ObjectScript heredocs for namespace creation
3. Python scripts with manual iris.connect() calls
4. Manual error handling for authentication issues
5. Custom cleanup and state management

**Time Invested**: ~2 hours troubleshooting authentication, schema creation, and container state

### What iris-devtester Provides
1. **Automatic Container Lifecycle Management**
   - Start/stop/restart IRIS containers
   - Automatic port conflict resolution
   - Password management and reset

2. **Schema Management**
   - Simplified namespace and table creation
   - Built-in fixtures for test data
   - Reproducible schema via DAT files

3. **Testing Utilities**
   - Test isolation (no data pollution)
   - Automatic cleanup even on crashes
   - DBAPI-first performance (3x faster than JDBC)

4. **Error Handling**
   - Automatic recovery from "Password change required" errors
   - Connection retry logic
   - Better error messages

## How to Use iris-devtester for AWS

### Installation
```bash
pip install iris-devtester
# Or from local copy
pip install -e /Users/tdyar/ws/iris-devtester
```

### Basic Usage Pattern

```python
from iris_devtester import IRISContainer

# Create and start IRIS container
# Uses fixed default container name: 'iris_db' (predictable, not random!)
with IRISContainer() as iris:
    # Container is automatically started and ready
    # Check with: docker ps  (will show 'iris_db')
    conn = iris.get_connection()
    cursor = conn.cursor()

    # Create schema
    cursor.execute("CREATE TABLE MyTable (...)")

    # Run tests
    # ...

    # Container automatically stopped and cleaned up
```

**Key Design Feature**: iris-devtester uses a **fixed container name** (`iris_db`) by default, NOT a random name. This makes commands predictable and easy to use:

```bash
# Default container is always 'iris_db'
iris-devtester container up
docker ps  # Shows 'iris_db'

# Status command works without specifying name
iris-devtester container status

# Custom name if needed
iris-devtester container up --name my_custom_iris
```

This design follows **Constitutional Principle #4: Zero Configuration Viable** - the fixed default name makes getting started easy while still allowing customization.

### AWS-Specific Configuration

```python
from iris_devtester import IRISContainer

# Configure for remote AWS deployment
config = {
    'host': '3.84.250.46',
    'port': 1972,
    'namespace': 'DEMO',
    'username': '_SYSTEM',
    'password': 'SYS'
}

# Use iris-devtester's connection management
with IRISContainer.connect_remote(**config) as iris:
    # Automatic retry logic
    # Better error handling
    # Connection pooling
    conn = iris.get_connection()
```

### Schema Setup with iris-devtester

```python
from iris_devtester import IRISContainer, IRISSchema

schema = IRISSchema(
    namespace='DEMO',
    tables=[
        {
            'name': 'ClinicalNoteVectors',
            'columns': [
                ('ResourceID', 'VARCHAR(255) PRIMARY KEY'),
                ('PatientID', 'VARCHAR(255)'),
                ('Embedding', 'VECTOR(DOUBLE, 1024)'),
                # ...
            ],
            'indexes': [
                ('idx_patient', ['PatientID']),
                ('idx_doc_type', ['DocumentType'])
            ]
        }
    ]
)

# Apply schema to IRIS instance
iris.apply_schema(schema)
```

## Benefits for Future AWS Deployments

### 1. Simplified Deployment Scripts
**Before** (120 lines of bash + 150 lines of Python):
- deploy-iris.sh
- setup-iris-schema.py
- test-iris-vectors.py

**After** (30 lines of Python):
```python
from iris_devtester import IRISContainer, deploy_to_aws

config = load_config('aws-config.yaml')
deploy_to_aws(
    instance='3.84.250.46',
    schema='schemas/fhir-vectors.yaml',
    fixtures='fixtures/test-data.dat'
)
```

### 2. Automated Testing
```python
import pytest
from iris_devtester import IRISContainer

@pytest.fixture
def iris_container():
    with IRISContainer() as iris:
        yield iris

def test_vector_similarity(iris_container):
    # Test runs in isolated environment
    # Automatic cleanup after test
    conn = iris_container.get_connection()
    # ...
```

### 3. CI/CD Integration
```yaml
# .github/workflows/test.yml
- name: Run IRIS Integration Tests
  run: |
    pip install iris-devtester
    python -m pytest tests/integration/
    # iris-devtester handles container lifecycle
```

## Migration Plan

### Phase 1: Local Development (Immediate)
- Use iris-devtester for local GraphRAG testing
- Replace manual connection management
- Add automated schema creation

### Phase 2: AWS Deployment (Future)
- Refactor deploy-iris.sh to use iris-devtester
- Add iris-devtester connection pooling
- Implement automated health checks

### Phase 3: CI/CD (Future)
- Add iris-devtester to GitHub Actions
- Automated integration testing
- Performance regression tests

## Lessons Learned

### What Went Well (Manual Approach)
- ✅ Gained deep understanding of IRIS internals
- ✅ Learned about IRIS SQL limitations
- ✅ Documented common pitfalls

### What Could Be Improved
- ❌ Spent 2 hours troubleshooting authentication issues
  → iris-devtester handles password management automatically
- ❌ Manual Docker container lifecycle management
  → iris-devtester provides automatic start/stop/cleanup
- ❌ Complex ObjectScript heredocs
  → iris-devtester provides Python-native schema APIs
- ❌ Custom error handling logic
  → iris-devtester has built-in retry and recovery

## Recommendation

**For Future IRIS Deployments**: Start with iris-devtester

**Estimated Time Savings**: 50-70% reduction in deployment time
- Manual approach: ~2 hours (with troubleshooting)
- iris-devtester approach: ~30 minutes (estimated)

**ROI**: High
- Faster deployments
- More reliable (battle-tested)
- Better error handling
- Easier maintenance

## References

- **iris-devtester Location**: `/Users/tdyar/ws/iris-devtester`
- **Constitution**: `.specify/memory/constitution.md` Section VI
- **Current Deployment Scripts**: `scripts/aws/`
- **AWS Config**: `config/fhir_graphrag_config.aws.yaml`

---

**Note**: This document is based on user feedback after completing Phase 2 of AWS deployment. The manual approach worked successfully but iris-devtester would have been more efficient.
