# AWS GPU Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying a production-grade RAG system on AWS EC2 with GPU acceleration.

**Deployment Time:** ~30 minutes
**Target Instance:** AWS EC2 g5.xlarge (NVIDIA A10G GPU)
**Region:** us-east-1 (configurable)

## Prerequisites

### Required Software
- [ ] AWS CLI configured with credentials
- [ ] SSH key pair for EC2 access
- [ ] NVIDIA NGC API key ([Get one here](https://org.ngc.nvidia.com/setup/api-key))
- [ ] Bash 5.x or later
- [ ] Python 3.10 or later (for local validation scripts)

### Required Access
- [ ] AWS IAM permissions to create EC2 instances
- [ ] AWS IAM permissions to create security groups
- [ ] AWS IAM permissions to create EBS volumes
- [ ] Outbound internet access for package downloads

### Cost Awareness
- **Estimated cost:** $1.006/hour for g5.xlarge instance
- **Storage cost:** ~$40/month for 500GB EBS gp3 volume
- **Total monthly (24/7):** ~$810/month
- **Development (8hrs/day):** ~$270/month

## Quick Start

### 1. Clone and Configure

```bash
# Clone repository
git clone <repository-url>
cd FHIR-AI-Hackathon-Kit

# Copy environment template
cp config/.env.template .env

# Edit .env with your credentials
nano .env
```

**Required environment variables:**
```bash
AWS_REGION=us-east-1
AWS_INSTANCE_TYPE=g5.xlarge
SSH_KEY_NAME=your-key-name
SSH_KEY_PATH=/path/to/your-key.pem
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NGC_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2. Deploy Infrastructure

```bash
# Run the automated deployment script
./scripts/aws/deploy.sh --provision
```

This script will automatically:
1. ✅ Provision EC2 g5.xlarge instance with security groups
2. ✅ Install NVIDIA drivers (driver-535, CUDA 12.2)
3. ✅ Configure Docker with GPU runtime
4. ✅ Deploy InterSystems IRIS vector database
5. ✅ Deploy NVIDIA NIM LLM (meta/llama-3.1-8b-instruct)
6. ✅ Create vector tables with 1024-dim embeddings
7. ✅ Verify all services are running

**Deployment time:** ~10-15 minutes

**For existing instance:**
```bash
# Use existing instance
export INSTANCE_ID=i-xxxxxxxxxxxxx
export PUBLIC_IP=34.xxx.xxx.xxx
./scripts/aws/deploy.sh
```

### 3. Validate Deployment

The deployment includes comprehensive validation to ensure all components are working correctly.

#### Running Validation

**On local/deployed instance:**
```bash
./scripts/aws/validate-deployment.sh
```

**On remote instance via SSH:**
```bash
./scripts/aws/validate-deployment.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>
```

**Using Python health checks:**
```bash
# Run all health checks
python src/validation/health_checks.py

# Run pytest validation suite
pytest src/validation/test_deployment.py -v
```

#### Expected Validation Output

Successful validation should show all checks passing:

```
╔══════════════════════════════════════════════════════════════╗
║ AWS GPU NIM RAG System Validation
╚══════════════════════════════════════════════════════════════╝

→ Checking GPU availability...
✓ GPU detected: NVIDIA A10G
  Memory: 23028 MB
  Driver: 535.xxx.xx
  CUDA: 12.2

→ Checking Docker GPU runtime...
✓ Docker can access GPU

→ Checking IRIS database connectivity...
✓ IRIS container running
→ Checking IRIS database connection (Python)...
✓ IRIS database connection working

→ Checking Vector tables existence...
✓ Vector tables validated

→ Checking NIM LLM service health...
✓ NIM LLM container running
✓ NIM LLM health endpoint responding

→ Checking NIM LLM inference test...
✓ NIM LLM inference working
  Test response: 4

╔══════════════════════════════════════════════════════════════╗
║ Validation Summary
╚══════════════════════════════════════════════════════════════╝

✓ All validation checks passed

System is ready for use!

Next steps:
  1. Vectorize clinical notes: python src/vectorization/vectorize_documents.py
  2. Test vector search: python src/query/test_vector_search.py
  3. Run RAG query: python src/query/rag_query.py --query 'your question'
```

#### Understanding Health Check Results

Each health check validates a specific component:

| Component | What It Checks | Pass Criteria |
|-----------|---------------|---------------|
| **GPU** | nvidia-smi command available, GPU detected | GPU name and driver version returned |
| **GPU Utilization** | Real-time GPU metrics | Utilization %, memory usage, temperature |
| **Docker GPU Runtime** | Docker can access GPU via --gpus flag | Test container can run nvidia-smi |
| **IRIS Connection** | IRIS database accepts connections | SELECT 1 query succeeds |
| **IRIS Tables** | Vector tables exist with correct schema | ClinicalNoteVectors and MedicalImageVectors found |
| **NIM LLM Health** | NIM health endpoint responds | HTTP 200 from /health |
| **NIM LLM Inference** | Model can generate responses | Successful completion for test query |

#### Health Check Details

**Python Health Checks** return structured results:

```python
@dataclass
class HealthCheckResult:
    component: str        # Component name (e.g., "GPU", "IRIS Connection")
    status: str          # "pass" or "fail"
    message: str         # Human-readable status message
    details: Dict        # Additional diagnostic information
```

Example successful result:
```python
HealthCheckResult(
    component="GPU",
    status="pass",
    message="GPU detected: NVIDIA A10G",
    details={
        "gpu_name": "NVIDIA A10G",
        "driver_version": "535.xxx.xx",
        "memory_mb": "23028",
        "cuda_version": "12.2"
    }
)
```

Example failure result:
```python
HealthCheckResult(
    component="IRIS Connection",
    status="fail",
    message="Connection failed: Connection refused",
    details={
        "error_type": "ConnectionError",
        "host": "localhost",
        "port": 1972,
        "suggestion": "Check IRIS container is running: docker ps | grep iris"
    }
)
```

#### Troubleshooting Failed Validation

If validation fails, follow these steps:

**1. GPU Check Fails**

Symptoms:
```
✗ GPU not accessible
  Error: nvidia-smi not found
```

Solutions:
```bash
# Reinstall GPU drivers
./scripts/aws/install-gpu-drivers.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>

# Verify GPU is detected
ssh -i <PATH_TO_KEY> ubuntu@<PUBLIC_IP> nvidia-smi

# If still failing, reboot instance
aws ec2 reboot-instances --instance-ids <INSTANCE_ID>
```

**2. Docker GPU Check Fails**

Symptoms:
```
✗ Docker cannot access GPU
  Error: could not select device driver
```

Solutions:
```bash
# Reinstall Docker GPU runtime
./scripts/aws/setup-docker-gpu.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>

# Manually verify
ssh -i <PATH_TO_KEY> ubuntu@<PUBLIC_IP> \
  'docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi'
```

**3. IRIS Connection Fails**

Symptoms:
```
✗ IRIS container not running
```

Solutions:
```bash
# Check container status
ssh -i <PATH_TO_KEY> ubuntu@<PUBLIC_IP> 'docker ps -a | grep iris'

# Restart IRIS deployment
./scripts/aws/deploy-iris.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY> --force-recreate

# Check logs for errors
ssh -i <PATH_TO_KEY> ubuntu@<PUBLIC_IP> 'docker logs iris-vector-db'
```

**4. Vector Tables Missing**

Symptoms:
```
✗ No vector tables found
  Suggestion: Run: python src/setup/create_text_vector_table.py
```

Solutions:
```bash
# Recreate tables
python src/setup/create_text_vector_table.py

# Or re-run IRIS deployment with schema recreation
./scripts/aws/deploy-iris.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY> --force-recreate
```

**5. NIM LLM Not Responding**

Symptoms:
```
! Health endpoint not available (may be initializing)
! NIM LLM inference not responding (may still be loading model)
```

This is normal during initial deployment. The model download and initialization can take 5-10 minutes.

Wait and retry:
```bash
# Check if model is still downloading
ssh -i <PATH_TO_KEY> ubuntu@<PUBLIC_IP> 'docker logs nim-llm --tail 50'

# Should see progress like:
# "Downloading model... 45%"
# "Loading model into GPU memory..."

# Wait for completion, then re-run validation
./scripts/aws/validate-deployment.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>
```

If stuck for >15 minutes:
```bash
# Restart NIM container
ssh -i <PATH_TO_KEY> ubuntu@<PUBLIC_IP> 'docker restart nim-llm'

# Re-deploy if restart doesn't help
./scripts/aws/deploy-nim-llm.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY> --force-recreate
```

#### Skip Specific Validation Checks

To skip specific components during validation:

```bash
# Skip GPU checks (for testing without GPU)
./scripts/aws/validate-deployment.sh --skip-gpu

# Skip NIM checks (if not deployed yet)
./scripts/aws/validate-deployment.sh --skip-nim

# Multiple skips
./scripts/aws/validate-deployment.sh --skip-gpu --skip-nim
```

#### Automated Testing with Pytest

Run the pytest test suite for comprehensive validation:

```bash
# Run all tests
pytest src/validation/test_deployment.py -v

# Run specific test class
pytest src/validation/test_deployment.py::TestGPU -v

# Run integration tests only
pytest src/validation/test_deployment.py::TestSystemIntegration -v

# Run with detailed output
pytest src/validation/test_deployment.py -v --tb=short

# Run slow tests (comprehensive inference testing)
pytest src/validation/test_deployment.py -v -m slow
```

Expected pytest output:
```
============================== test session starts ===============================
collected 12 items

src/validation/test_deployment.py::TestGPU::test_gpu_detected PASSED        [  8%]
src/validation/test_deployment.py::TestGPU::test_gpu_utilization PASSED     [ 16%]
src/validation/test_deployment.py::TestDocker::test_docker_gpu_access PASSED [ 25%]
src/validation/test_deployment.py::TestIRIS::test_iris_connection PASSED    [ 33%]
src/validation/test_deployment.py::TestIRIS::test_iris_tables_exist PASSED  [ 41%]
src/validation/test_deployment.py::TestNIMLLM::test_nim_llm_health PASSED   [ 50%]
src/validation/test_deployment.py::TestNIMLLM::test_nim_llm_inference PASSED [ 58%]
src/validation/test_deployment.py::TestSystemIntegration::test_all_components_healthy PASSED [ 66%]
src/validation/test_deployment.py::TestSystemIntegration::test_deployment_readiness PASSED [ 75%]
src/validation/test_deployment.py::TestPerformance::test_gpu_utilization_reasonable PASSED [ 83%]

============================== 12 passed in 15.23s ===============================
```

#### Next Steps After Successful Validation

Once all validation checks pass, proceed with:

1. **Load clinical notes data:** See Step 6 below
2. **Vectorize documents:** See Step 6 below
3. **Test vector search:** See Step 7 below
4. **Run RAG queries:** See "Test RAG Query" section

### 4. Test RAG Query

```bash
# Run a sample RAG query
python src/query/test_rag.py \
  --query "What are the patient's chronic conditions?" \
  --patient-id "patient-123"
```

## Detailed Deployment Steps

You can run individual scripts for granular control, or use the automated `./scripts/aws/deploy.sh` script.

### Option A: Automated Deployment

```bash
# Complete deployment in one command
./scripts/aws/deploy.sh --provision

# Or for existing instance
export INSTANCE_ID=i-xxxxxxxxxxxxx
export PUBLIC_IP=34.xxx.xxx.xxx
./scripts/aws/deploy.sh
```

### Option B: Step-by-Step Deployment

### Step 1: Provision EC2 Instance

```bash
./scripts/aws/provision-instance.sh
```

**What this does:**
- Creates security group with required ports:
  - 22 (SSH)
  - 1972 (IRIS SQL)
  - 52773 (IRIS Management Portal)
  - 8001 (NIM LLM API)
- Launches EC2 g5.xlarge instance with Ubuntu 24.04 LTS
- Attaches 500GB gp3 EBS volume
- Configures resource tags for tracking
- Saves instance info to `.instance-info` file

**Expected output:**
```
→ Finding Ubuntu 24.04 LTS AMI in us-east-1...
✓ Found AMI: ami-xxxxxxxxxxxxx
→ Creating security group: fhir-ai-hackathon-sg...
✓ Security group created: sg-xxxxxxxxxxxxx
→ Launching g5.xlarge instance in us-east-1...
✓ Instance launched: i-xxxxxxxxxxxxx
✓ Instance is now running

==========================================
Instance Provisioned Successfully
==========================================
  Instance ID:   i-xxxxxxxxxxxxx
  Instance Type: g5.xlarge
  Public IP:     34.xxx.xxx.xxx
  Region:        us-east-1
  SSH Key:       your-key-name
```

**For remote operations:**
```bash
# Provision from your local machine for remote host
export SSH_KEY_PATH=~/.ssh/your-key.pem
./scripts/aws/provision-instance.sh
```

### Step 2: Install GPU Drivers

```bash
./scripts/aws/install-gpu-drivers.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>
```

**What this does:**
- Installs NVIDIA driver-535 (LTS)
- Installs nvidia-utils-535
- Detects if reboot is required
- Automatically reboots and waits for instance to come back online
- Verifies GPU is accessible

**Expected output:**
```
→ Installing NVIDIA drivers on remote host: 34.xxx.xxx.xxx
→ Updating package list...
→ Installing NVIDIA driver 535 (LTS)...
✓ NVIDIA drivers installed
✓ nvidia-smi is available
! GPU not yet accessible - reboot required

Reboot instance now? (yes/no): yes
→ Rebooting remote host...
→ Waiting 60 seconds for instance to reboot...
→ Waiting for SSH to be available...
✓ Instance is back online
→ Verifying GPU on remote host...
✓ GPU is accessible

==========================================
NVIDIA Driver Installation Complete
==========================================
```

### Step 3: Setup Docker GPU Runtime

```bash
./scripts/aws/setup-docker-gpu.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>
```

**What this does:**
- Installs Docker CE (if not present)
- Installs NVIDIA Container Toolkit
- Configures Docker daemon for GPU runtime
- Restarts Docker service
- Verifies GPU accessibility in containers

**Expected output:**
```
→ Setting up Docker GPU runtime on remote host: 34.xxx.xxx.xxx
→ Checking for Docker...
✓ Docker is already installed
Docker version 27.x.x

→ Installing NVIDIA Container Toolkit...
✓ NVIDIA Container Toolkit installed

→ Configuring Docker for GPU...
→ Restarting Docker...
✓ Docker configured for GPU

→ Verifying GPU accessibility in containers...
✓ GPU is accessible in containers

==========================================
Docker GPU Runtime Setup Complete
==========================================
```

**Validation after reboot:**
```bash
ssh -i your-key.pem ubuntu@<public-ip> nvidia-smi
```

Expected:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.xxx.xx   Driver Version: 535.xxx.xx   CUDA Version: 12.2   |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA A10G         Off  | 00000000:00:1E.0 Off |                    0 |
|  0%   28C    P0    55W / 300W |      0MiB / 23028MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

### Step 4: Deploy IRIS Database

```bash
./scripts/aws/deploy-iris.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>
```

**What this does:**
- Pulls InterSystems IRIS Community Edition 2025.1
- Creates Docker volume for persistent storage
- Starts IRIS container with ports 1972 (SQL) and 52773 (Management)
- Creates DEMO namespace
- Creates vector tables:
  - `ClinicalNoteVectors` with VECTOR(DOUBLE, 1024)
  - `MedicalImageVectors` with VECTOR(DOUBLE, 1024)
- Indexes for efficient patient/document lookups

**Expected output:**
```
→ Deploying InterSystems IRIS...
→ Pulling IRIS image...
✓ Image pulled
→ Creating persistent volume...
✓ Volume created
→ Starting IRIS container...
✓ IRIS container started
→ Waiting for IRIS to initialize (30 seconds)...
✓ IRIS is running

→ Creating namespace and schema...
→ Creating namespace...
✓ Namespace created
→ Creating tables...
✓ Schema created
✓ Tables verified

==========================================
IRIS Vector Database Deployed
==========================================

Connection details:
  Host:      34.xxx.xxx.xxx
  SQL Port:  1972
  Web Port:  52773
  Namespace: DEMO
  Username:  _SYSTEM
  Password:  SYS

Tables created:
  - ClinicalNoteVectors (1024-dim VECTOR)
  - MedicalImageVectors (1024-dim VECTOR)

Management Portal:
  http://34.xxx.xxx.xxx:52773/csp/sys/UtilHome.csp
```

**Testing the connection:**
```bash
# Test with iris Python module
python -c "import iris; \
  conn = iris.connect('34.xxx.xxx.xxx', 1972, 'DEMO', '_SYSTEM', 'SYS'); \
  print('✅ Connected to IRIS')"
```

### Step 5: Deploy NIM LLM

```bash
./scripts/aws/deploy-nim-llm.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>
```

**What this does:**
- Pulls NVIDIA NIM LLM container (meta/llama-3.1-8b-instruct)
- Starts LLM container with GPU allocation
- Downloads model weights (~8GB, first run only)
- Exposes OpenAI-compatible API on port 8001
- Validates service health

**Expected output:**
```
→ Deploying NVIDIA NIM LLM...
  Model: meta/llama-3.1-8b-instruct
✓ NVIDIA API key found

→ Verifying GPU...
✓ GPU accessible

→ Pulling NIM LLM image...
✓ Image pulled

→ Starting NIM LLM container...
✓ NIM LLM container started

→ Waiting for NIM to initialize (checking every 30s)...
→ Still initializing... (30/600s)
→ Still initializing... (60/600s)
✓ NIM is initializing
✓ NIM LLM deployed

==========================================
NVIDIA NIM LLM Deployed
==========================================

Model: meta/llama-3.1-8b-instruct
Endpoint: http://34.xxx.xxx.xxx:8001/v1/chat/completions

Test with curl:
  curl -X POST http://34.xxx.xxx.xxx:8001/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model": "meta/llama-3.1-8b-instruct",
      "messages": [{"role": "user", "content": "What is RAG?"}],
      "max_tokens": 100
    }'
```

**Testing the LLM:**
```bash
# Test chat completion
curl -X POST http://<PUBLIC_IP>:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta/llama-3.1-8b-instruct",
    "messages": [
      {"role": "system", "content": "You are a helpful medical AI assistant."},
      {"role": "user", "content": "Explain hypertension in simple terms."}
    ],
    "max_tokens": 150,
    "temperature": 0.7
  }'
```

### Step 5: Create Vector Tables

```bash
python src/setup/create_text_vector_table.py
```

**What this does:**
- Connects to IRIS database
- Creates `ClinicalNoteVectors` table with VECTOR(DOUBLE, 1024) column
- Creates indices for efficient search
- Validates table schema

**Expected output:**
```
✅ Table created: DEMO.ClinicalNoteVectors
✅ Columns: ResourceID, PatientID, DocumentType, TextContent, Embedding
✅ Vector dimension: 1024
✅ Similarity metric: COSINE
```

### Step 6: Vectorize Clinical Notes

```bash
python src/vectorization/vectorize_documents.py \
  --input synthea_clinical_notes.json \
  --batch-size 50
```

**What this does:**
- Reads clinical notes from JSON file
- Calls NVIDIA embeddings API in batches
- Stores vectors in IRIS database
- Tracks progress with SQLite checkpoint
- Provides ETA and throughput metrics

**Expected output:**
```
📊 Total documents: 50,127
🔄 Processing in batches of 50...
✅ Batch 1/1003 complete (50 docs, 2.3s, 21.7 docs/sec)
✅ Batch 2/1003 complete (50 docs, 2.1s, 23.8 docs/sec)
...
✅ All documents vectorized!
📈 Total time: 42m 15s
📈 Average throughput: 19.8 docs/sec
📈 Total vectors: 50,127
```

### Step 7: Test Vector Search

```bash
python src/query/test_vector_search.py \
  --query "diabetes treatment history" \
  --top-k 10
```

**Expected output:**
```
🔍 Query: "diabetes treatment history"
📊 Found 10 results in 0.23s

Top result:
  Similarity: 0.87
  Patient: patient-456
  Document: Progress Note 2024-01-15
  Content: Patient with type 2 diabetes, currently on metformin 1000mg BID...
```

### Step 8: Vectorize Clinical Notes (Production Pipeline)

Once your infrastructure is validated, you can vectorize clinical notes at scale using the production pipeline:

```bash
python src/vectorization/text_vectorizer.py \
  --input synthea_clinical_notes.json \
  --batch-size 50
```

**What this does:**
- Validates all documents for required fields
- Preprocesses text (whitespace normalization, truncation)
- Generates embeddings in batches (50 docs/batch default)
- Stores vectors in IRIS ClinicalNoteVectors table
- Tracks progress with SQLite checkpoint for resumability
- Logs validation errors to `vectorization_errors.log`

**Expected output:**
```
2025-01-09 14:32:15 - Initializing NVIDIA NIM embeddings client...
2025-01-09 14:32:16 - Initializing IRIS vector database client...
2025-01-09 14:32:17 - ✓ Connected to IRIS: 34.xxx.xxx.xxx:1972/DEMO

Starting vectorization pipeline...
Input file: synthea_clinical_notes.json
Batch size: 50
Resume mode: False

✓ Loaded 50,127 documents
Validating and preprocessing documents...
✓ 50,100 valid documents ready for vectorization

Processing batch 1/1002 (50 documents)
Progress: 1/1002 batches | 50 successful | 0 failed | 21.7 docs/min | ETA: 38.5 min
Processing batch 2/1002 (50 documents)
Progress: 2/1002 batches | 100 successful | 0 failed | 23.1 docs/min | ETA: 36.2 min
...

================================================================================
Vectorization Summary
================================================================================
Total documents:      50,127
Validation errors:    27
Processed:            50,100
Successful:           50,100
Failed:               0
Elapsed time:         2145.3s (35.8 min)
Throughput:           140.1 docs/min
================================================================================

✅ Vectorization complete!
```

**Command-line options:**

```bash
# Resume from checkpoint (skip already processed documents)
python src/vectorization/text_vectorizer.py \
  --input synthea_clinical_notes.json \
  --resume

# Test vector search after vectorization
python src/vectorization/text_vectorizer.py \
  --input synthea_clinical_notes.json \
  --test-search "diabetes medication"

# Adjust batch size for API rate limits
python src/vectorization/text_vectorizer.py \
  --input synthea_clinical_notes.json \
  --batch-size 25

# Custom checkpoint and error log paths
python src/vectorization/text_vectorizer.py \
  --input synthea_clinical_notes.json \
  --checkpoint-db my_state.db \
  --error-log my_errors.log
```

**Performance expectations:**

| Dataset Size | Batch Size | Expected Throughput | Total Time (est.) |
|--------------|------------|---------------------|-------------------|
| 1,000 docs   | 50         | ≥100 docs/min       | ~10 minutes       |
| 10,000 docs  | 50         | ≥100 docs/min       | ~100 minutes      |
| 50,000 docs  | 50         | ≥100 docs/min       | ~500 minutes      |
| 100,000 docs | 50         | ≥100 docs/min       | ~1000 minutes     |

**Note:** Throughput depends on:
- Network latency to NVIDIA API
- NVIDIA API rate limits (60 req/min for free tier)
- IRIS database write performance
- Instance network bandwidth

**Progress tracking:**

The pipeline provides real-time progress updates:
- **Batch X/Y**: Current batch number and total batches
- **Successful**: Number of successfully vectorized documents
- **Failed**: Number of failed documents (check error log)
- **docs/min**: Current throughput rate
- **ETA**: Estimated time remaining

**Resumability:**

The pipeline uses SQLite checkpoint tracking, so you can safely interrupt (Ctrl+C) and resume:

```bash
# Start vectorization
python src/vectorization/text_vectorizer.py --input data.json --batch-size 50

# ... Interrupt with Ctrl+C after processing 5,000 documents ...

# Resume from checkpoint (skips already processed 5,000)
python src/vectorization/text_vectorizer.py --input data.json --resume
```

**Validation errors:**

Documents that fail validation are logged to `vectorization_errors.log` and skipped:

```
================================================================================
Validation Errors - 2025-01-09T14:32:45.123456
================================================================================
Resource ID: doc-broken-123
Error: Missing required field: text_content
--------------------------------------------------------------------------------
Resource ID: doc-empty-456
Error: Empty text_content
--------------------------------------------------------------------------------
```

Common validation failures:
- Missing required fields (resource_id, patient_id, document_type, text_content)
- Empty or whitespace-only text_content
- Invalid JSON structure

**Testing search after vectorization:**

```bash
# Test search with default query
python src/vectorization/text_vectorizer.py \
  --input synthea_clinical_notes.json \
  --test-search

# Test with custom query
python src/vectorization/text_vectorizer.py \
  --input synthea_clinical_notes.json \
  --test-search "hypertension treatment"
```

**Output:**
```
Testing vector search: 'hypertension treatment'

Top 3 results:

1. Similarity: 0.892
   Patient ID: patient-789
   Doc Type: Progress Note
   Content: Patient with essential hypertension on amlodipine 5mg daily...

2. Similarity: 0.856
   Patient ID: patient-123
   Doc Type: History and physical note
   Content: Hypertension managed with lifestyle modifications and ACE inhibitor...

3. Similarity: 0.824
   Patient ID: patient-456
   Doc Type: Encounter note
   Content: Blood pressure elevated, discussed medication compliance...
```

### Step 9: Query Clinical Notes with RAG Pipeline

Once clinical notes are vectorized, you can run natural language queries using the RAG (Retrieval-Augmented Generation) pipeline.

```bash
python src/validation/test_rag_query.py \
  --query "What are the patient's chronic conditions?"
```

**What this does:**
- Generates embedding for your natural language query
- Searches IRIS vector database for semantically similar clinical notes
- Retrieves top-k most relevant documents
- Assembles context from retrieved documents
- Sends context + query to NVIDIA NIM LLM (meta/llama-3.1-8b-instruct)
- Generates natural language response citing source documents
- Extracts and formats citations with similarity scores

**Expected output:**

```
================================================================================
RAG Query Test
================================================================================
Query: "What are the patient's chronic conditions?"
Top-K: 10
Similarity Threshold: 0.5
================================================================================

Response:
--------------------------------------------------------------------------------
Based on the clinical notes, the patient has the following chronic conditions:
1. Type 2 diabetes mellitus (mentioned in Document 1 and Document 3)
2. Essential hypertension (mentioned in Document 2)
3. Hyperlipidemia (mentioned in Document 1)

The patient is currently managing these conditions with:
- Metformin 1000mg BID for diabetes
- Amlodipine 5mg daily for hypertension
- Atorvastatin 20mg daily for hyperlipidemia

================================================================================
Retrieved Documents (3 used in context, 5 total retrieved)
================================================================================

[1] Similarity: 0.87 | Patient: patient-789 | Type: Progress Note
    Resource ID: f1a10b20-dbaa-2a6b-d46f-11223d8ac3f0
    Content: "Patient with type 2 diabetes, currently on metformin..."
    ✓ Cited in response

[2] Similarity: 0.82 | Patient: patient-789 | Type: History and physical
    Resource ID: doc-456-2023-12-10
    Content: "Patient presents with hypertension, well-controlled..."
    ✓ Cited in response

[3] Similarity: 0.79 | Patient: patient-789 | Type: Progress Note
    Resource ID: doc-123-2024-01-05
    Content: "Patient with hyperlipidemia and type 2 diabetes..."
    ✓ Cited in response

Additional 2 documents retrieved but not used in context:
  [4] Similarity: 0.68 | Patient: patient-789 | Type: Encounter note
  [5] Similarity: 0.61 | Patient: patient-789 | Type: Progress Note

================================================================================
Metadata
================================================================================
Processing Time: 3.45 seconds
Documents Retrieved: 5
Documents Used in Context: 3
Citations Found: 3
Performance: ✅ Meets SC-007 target (<5s)
Timestamp: 2025-01-09T15:30:45.123456
================================================================================
```

**Query with patient filter:**

```bash
python src/validation/test_rag_query.py \
  --query "What medications is the patient taking?" \
  --patient-id "patient-789"
```

**Query with document type filter:**

```bash
python src/validation/test_rag_query.py \
  --query "Recent lab results and vital signs" \
  --document-type "Progress Note"
```

**Advanced query parameters:**

```bash
python src/validation/test_rag_query.py \
  --query "Patient's medication history and allergies" \
  --top-k 15 \
  --similarity-threshold 0.6 \
  --max-context-tokens 5000 \
  --llm-max-tokens 1000 \
  --llm-temperature 0.5 \
  --output result.json
```

**Command-line options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--query` | Natural language query (required) | - |
| `--patient-id` | Filter results by patient ID | None |
| `--document-type` | Filter by document type | None |
| `--top-k` | Number of documents to retrieve | 10 |
| `--similarity-threshold` | Minimum similarity score (0-1) | 0.5 |
| `--max-context-tokens` | Max tokens for context | 4000 |
| `--llm-max-tokens` | Max tokens in LLM response | 500 |
| `--llm-temperature` | LLM sampling temperature (0-1) | 0.7 |
| `--output` | Save result to JSON file | None |
| `--show-full-documents` | Show full document text | False |
| `-v, --verbose` | Enable verbose logging | False |

**Performance expectations:**

| Component | Target Latency | Notes |
|-----------|---------------|-------|
| Query embedding | <1s | NVIDIA NIM embeddings API |
| Vector search | <1s | IRIS COSINE similarity search |
| Context retrieval | <0.5s | Database query |
| LLM generation | <3s | NIM LLM (meta/llama-3.1-8b-instruct) |
| **Total (SC-007)** | **<5s** | End-to-end query processing |

**Example queries:**

```bash
# General medical query
python src/validation/test_rag_query.py \
  --query "What are the patient's vital signs trends over time?"

# Specific condition query
python src/validation/test_rag_query.py \
  --query "Has the patient been diagnosed with diabetes?"

# Medication query
python src/validation/test_rag_query.py \
  --query "What dosage of metformin is the patient taking?"

# Treatment history query
python src/validation/test_rag_query.py \
  --query "What treatments have been prescribed for hypertension?"

# Recent activity query
python src/validation/test_rag_query.py \
  --query "What were the findings from the patient's last visit?"
```

**Python API usage:**

You can also use the RAG pipeline directly in Python code:

```python
from query.rag_pipeline import RAGPipeline

# Initialize pipeline
pipeline = RAGPipeline()

# Process query
result = pipeline.process_query(
    query_text="What are the patient's chronic conditions?",
    top_k=10,
    patient_id="patient-789",  # Optional filter
    similarity_threshold=0.5
)

# Access results
print(f"Response: {result['response']}")
print(f"Retrieved: {result['metadata']['documents_retrieved']} documents")
print(f"Processing time: {result['metadata']['processing_time_seconds']}s")

# Iterate through citations
for citation in result['citations']:
    if citation['cited_in_response']:
        print(f"  - {citation['resource_id']} (similarity: {citation['similarity']:.3f})")
```

**Integration testing:**

Run the end-to-end RAG test suite:

```bash
pytest tests/integration/test_end_to_end_rag.py -v
```

Expected output:
```
============================== test session starts ===============================
tests/integration/test_end_to_end_rag.py::TestRAGPipelineBasics::test_pipeline_initialization PASSED
tests/integration/test_end_to_end_rag.py::TestRAGPipelineBasics::test_query_embedding_generation PASSED
tests/integration/test_end_to_end_rag.py::TestRAGQueryProcessing::test_process_simple_query PASSED
tests/integration/test_end_to_end_rag.py::TestRAGQueryProcessing::test_citation_extraction PASSED
tests/integration/test_end_to_end_rag.py::TestPerformance::test_query_latency_meets_sc007 PASSED
...
============================== 15 passed in 45.23s ===============================
```

### Step 10: Deploy NIM Vision Service (Optional - for Image Vectorization)

For multi-modal RAG capabilities with medical images (chest X-rays, CT scans, etc.), deploy the NVIDIA NIM Vision service.

```bash
./scripts/aws/deploy-nim-vision.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>
```

**What this does:**
- Pulls NVIDIA NIM Vision container (nv-clip-vit model)
- Starts Vision service with GPU allocation on port 8002
- Downloads CLIP Vision Transformer model (~2GB, first run only)
- Exposes image embedding API compatible with src/vectorization/image_vectorizer.py
- Validates service health

**Expected output:**
```
╔══════════════════════════════════════════════════════════════╗
║ NVIDIA NIM Vision Deployment                                 ║
╚══════════════════════════════════════════════════════════════╝

→ Checking NVIDIA API key...
✓ NVIDIA API key found

→ Checking GPU availability...
✓ GPU accessible

→ Checking for existing container...

→ Pulling NVIDIA NIM Vision image...
  Image: nvcr.io/nim/nvidia/nv-clip-vit:latest
  This may take several minutes...
✓ Image pulled

→ Starting NVIDIA NIM Vision container...
✓ Container started
  Container name: nim-vision
  Port mapping: 8002:8000

→ Waiting for NIM Vision to initialize...
  This may take 3-5 minutes (model download on first run)
  Still initializing... (30s/300s)
  Still initializing... (60s/300s)
✓ NIM Vision service is healthy

==========================================
NVIDIA NIM Vision Deployed
==========================================

Model: CLIP Vision Transformer
Endpoint: http://34.xxx.xxx.xxx:8002
Health: http://34.xxx.xxx.xxx:8002/health

Container Details:
  Name: nim-vision
  Port: 8002 (external) → 8000 (internal)
  GPU: Enabled
  Shared Memory: 8g

Test with curl:
  curl -X POST http://34.xxx.xxx.xxx:8002/v1/embeddings \
    -H "Content-Type: application/json" \
    -d '{
      "input": "base64_encoded_image_here",
      "model": "nv-clip-vit"
    }'

✅ NIM Vision deployment complete!
```

**Testing the Vision service:**
```bash
# Test health endpoint
curl http://<PUBLIC_IP>:8002/health
# Should return: {"status": "ready"}

# The vision service accepts base64-encoded images
# See image_vectorizer.py for usage examples
```

### Step 11: Vectorize Medical Images (Optional - Multi-Modal RAG)

Once NIM Vision is deployed, vectorize medical images for visual similarity search and multi-modal RAG queries.

**Prerequisites:**
- NIM Vision service running on port 8002
- IRIS MedicalImageVectors table created (automatically handled by image_vectorizer.py)
- Medical images in supported formats (DICOM, PNG, JPG)

#### Using MIMIC-CXR Chest X-Rays

The kit includes integration with the MIMIC-CXR dataset (19,091 DICOM chest X-rays):

```bash
python src/vectorization/image_vectorizer.py \
  --input /path/to/mimic-cxr/files \
  --format dicom \
  --batch-size 10
```

**Expected output:**
```
2025-01-09 19:30:00 - INFO - Initializing components...
2025-01-09 19:30:01 - INFO - NIM Vision client initialized: http://localhost:8002
2025-01-09 19:30:02 - INFO - ✓ Connected to IRIS: localhost:1972/DEMO
2025-01-09 19:30:02 - INFO - Checkpoint database initialized: image_vectorization_state.db

===============================================================================
Medical Image Vectorization Pipeline
===============================================================================
Input directory: /path/to/mimic-cxr/files
Image formats: dicom
Batch size: 10
Resume mode: False
===============================================================================

✓ Discovered 19,091 image files
Validating 19,091 images...
✓ 19,091 valid images, 0 validation errors

Processing 19,091 images in 1,910 batches...

Batch 1/1910: 10 successful, 0 failed | 8.2s | 1.22 imgs/sec | ETA: 4.3 hours
Batch 2/1910: 10 successful, 0 failed | 7.9s | 1.27 imgs/sec | ETA: 4.1 hours
Batch 3/1910: 10 successful, 0 failed | 8.1s | 1.23 imgs/sec | ETA: 4.2 hours
...

================================================================================
Vectorization Summary
================================================================================
Total images discovered:  19,091
Validation errors:        0
Valid images:             19,091
Successfully processed:   19,091
Failed:                   0
Elapsed time:             15,420.5s (4.3 hours)
Throughput:               1.24 images/sec
================================================================================

✅ Performance target met: 1.24 imgs/sec ≥ 0.5 imgs/sec
```

**Performance expectations:**

| Dataset Size | Batch Size | Expected Throughput | Total Time (est.) |
|--------------|------------|---------------------|-------------------|
| 100 images   | 10         | ≥0.5 imgs/sec       | ~3 minutes        |
| 1,000 images | 10         | ≥0.5 imgs/sec       | ~30 minutes       |
| 10,000 images| 10         | ≥0.5 imgs/sec       | ~5 hours          |
| 19,091 images| 10         | ≥0.5 imgs/sec       | ~10 hours         |

**Note:** Performance target SC-005 specifies ≥0.5 images/second (<2 sec/image). Actual throughput depends on:
- GPU model (A10G recommended)
- Network latency to NIM Vision API
- IRIS database write performance
- Image preprocessing complexity (DICOM conversion, normalization, resizing)

#### Command-line Options

```bash
# Resume from checkpoint (skip already processed images)
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --resume

# Process PNG/JPG images
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format png,jpg \
  --batch-size 10

# Test visual similarity search after vectorization
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --test-search /path/to/query-image.dcm

# Custom NIM Vision endpoint
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --vision-url http://34.xxx.xxx.xxx:8002

# Custom checkpoint and error log paths
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --checkpoint-db my_image_state.db \
  --error-log my_image_errors.log
```

#### Visual Similarity Search

After vectorizing images, test visual similarity search:

```bash
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --test-search /path/to/query-image.dcm \
  --top-k 10
```

**Expected output:**
```
================================================================================
Visual Similarity Search Test
================================================================================
Query image: /path/to/query-image.dcm
Top-K: 10

Generating embedding for query image...
✓ Generated 1024-dimensional embedding
Searching for top-10 similar images...
✓ Found 10 results

Similar Images:
--------------------------------------------------------------------------------
[1] Similarity: 0.9234
    Image ID: 4b369dbe-417168fa-7e2b5f04-00582488-c50504e7
    Patient: p10045779
    Study Type: Chest X-Ray
    Path: /path/to/images/p10/p10045779/s53819164/4b369dbe-417168fa-7e2b5f04-00582488-c50504e7.dcm

[2] Similarity: 0.9187
    Image ID: 48b7ea9c-c1610133-64303c6f-4f6dfe6c-805036e8
    Patient: p10433353
    Study Type: Chest X-Ray
    Path: /path/to/images/p10/p10433353/s50527707/48b7ea9c-c1610133-64303c6f-4f6dfe6c-805036e8.dcm

[3] Similarity: 0.9102
    Image ID: 8640649e-a6a3ae17-6f9c2091-560aef6e-9c1f19c7
    Patient: p10179495
    Study Type: Chest X-Ray
    Path: /path/to/images/p10/p10179495/s57176651/8640649e-a6a3ae17-6f9c2091-560aef6e-9c1f19c7.dcm

...

================================================================================
```

#### DICOM Metadata Support

The image vectorizer automatically extracts DICOM metadata:

- **PatientID**: De-identified patient identifier
- **StudyDescription**: Description of imaging study
- **Modality**: Imaging modality (DX, CR, CT, MR, etc.)
- **Rows/Columns**: Image dimensions
- **PixelData**: Raw image array (normalized and preprocessed)

Example DICOM extraction:
```python
from vectorization.image_vectorizer import ImageValidator
from pathlib import Path

validator = ImageValidator(dicom_enabled=True)
is_valid, metadata, error = validator.validate_and_extract(Path("/path/to/image.dcm"))

if is_valid:
    print(f"Patient: {metadata.patient_id}")
    print(f"Study: {metadata.study_type}")
    print(f"Dimensions: {metadata.width}x{metadata.height}")
```

#### Resumability and Error Handling

The image vectorization pipeline supports checkpoint-based resumability:

**Checkpoint tracking:**
- SQLite database stores image processing state (pending, processing, completed, failed)
- Safe interruption with Ctrl+C - resume from where you left off
- Automatic retry of failed images in subsequent runs

**Resume from checkpoint:**
```bash
# Start vectorization
python src/vectorization/image_vectorizer.py --input /path/to/images --format dicom

# ... Interrupt with Ctrl+C after processing 1,000 images ...

# Resume (skips already processed 1,000 images)
python src/vectorization/image_vectorizer.py --input /path/to/images --format dicom --resume
```

**Error logging:**
Validation and processing errors are logged to `image_vectorization_errors.log`:

```
================================================================================
Error - 2025-01-09T19:35:12.345678
================================================================================
Image ID: corrupt-image-001
Error: Validation failed: DICOM file is corrupted or incomplete
--------------------------------------------------------------------------------
Image ID: invalid-dimensions-002
Error: Image dimensions invalid: 0x0
--------------------------------------------------------------------------------
```

Common errors:
- Corrupted DICOM files
- Invalid image dimensions (0x0)
- Unsupported DICOM transfer syntax
- Permission errors reading files

#### Integration Testing

Run integration tests to verify the pipeline:

```bash
pytest tests/integration/test_image_vectorization.py -v
```

**Expected output:**
```
============================== test session starts ===============================
tests/integration/test_image_vectorization.py::TestDICOMValidation::test_dicom_format_detection PASSED
tests/integration/test_image_vectorization.py::TestDICOMValidation::test_dicom_metadata_extraction PASSED
tests/integration/test_image_vectorization.py::TestImagePreprocessing::test_dicom_to_pil_conversion PASSED
tests/integration/test_image_vectorization.py::TestImagePreprocessing::test_image_resizing PASSED
tests/integration/test_image_vectorization.py::TestNIMVisionAPI::test_embedding_generation_mock PASSED
tests/integration/test_image_vectorization.py::TestCheckpointManagement::test_checkpoint_initialization PASSED
tests/integration/test_image_vectorization.py::TestEndToEndPipeline::test_pipeline_initialization PASSED
tests/integration/test_image_vectorization.py::TestPerformanceValidation::test_preprocessing_performance PASSED
============================== 15 passed in 8.23s ===============================
```

## Configuration Options

### Environment Variables

Edit `.env` to customize deployment:

```bash
# AWS Configuration
AWS_REGION=us-east-1              # AWS region
AWS_INSTANCE_TYPE=g5.xlarge       # Instance type
SSH_KEY_NAME=my-key               # SSH key pair name
SSH_KEY_PATH=~/.ssh/my-key.pem    # Path to private key

# NVIDIA API Keys
NVIDIA_API_KEY=nvapi-xxx          # NVIDIA NGC API key
NGC_API_KEY=nvapi-xxx             # Same as NVIDIA_API_KEY

# IRIS Database
IRIS_USERNAME=_SYSTEM             # Database username
IRIS_PASSWORD=ISCDEMO             # Database password
IRIS_HOST=localhost               # Host (localhost for same instance)
IRIS_PORT=1972                    # SQL port
IRIS_NAMESPACE=DEMO               # Namespace for tables

# Optional: Performance Tuning
BATCH_SIZE=50                     # Embedding batch size
EMBEDDING_MODEL=nvidia/nv-embedqa-e5-v5  # Embedding model
LLM_MODEL=meta/llama-3.1-8b-instruct     # LLM model
```

### AWS Configuration

Edit `config/aws-config.yaml` to customize infrastructure:

```yaml
instance:
  type: g5.xlarge          # Change to g5.2xlarge for more GPU memory
  region: us-east-1        # Change region
  availability_zone: us-east-1a

ebs_volume:
  size: 500                # Increase for more data
  type: gp3
  iops: 3000
```

### NIM Configuration

Edit `config/nim-config.yaml` to customize AI services:

```yaml
nim_llm:
  model: meta/llama-3.1-8b-instruct  # Change to larger model
  port: 8001
  shared_memory: 16g                 # Increase for larger models

nim_embeddings:
  batch_size: 50                     # Increase for faster vectorization
  rate_limit:
    requests_per_minute: 60          # Adjust based on API tier
```

## Next Steps

After successful deployment:

1. **Load your own data:** See [docs/data-ingestion.md](data-ingestion.md)
2. **Customize RAG pipeline:** See [docs/rag-customization.md](rag-customization.md)
3. **Monitor performance:** See [docs/monitoring.md](monitoring.md)
4. **Scale the system:** See [docs/scaling.md](scaling.md)

## Support

- **Issues:** Report at [GitHub Issues](https://github.com/your-org/FHIR-AI-Hackathon-Kit/issues)
- **Documentation:** See [docs/](../docs/)
- **Troubleshooting:** See [docs/troubleshooting.md](troubleshooting.md)
