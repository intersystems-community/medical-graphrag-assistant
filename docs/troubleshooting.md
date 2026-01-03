# Troubleshooting Guide

This guide covers common issues and their solutions for the AWS GPU deployment.

## Quick Diagnostic Commands

Run these commands to quickly diagnose issues:

```bash
# Check all services status
ssh -i <key> ubuntu@<ip> docker ps

# View deployment script logs
./scripts/aws/deploy.sh 2>&1 | tee deployment.log

# Verify GPU accessibility
ssh -i <key> ubuntu@<ip> nvidia-smi

# Check IRIS database
ssh -i <key> ubuntu@<ip> docker logs iris-vector-db

# Check NIM LLM
ssh -i <key> ubuntu@<ip> docker logs nim-llm
```

## Automated Deployment Script Issues

### Deploy.sh orchestration failures

#### Deployment stops at GPU driver installation
**Symptoms:**
- Script completes driver installation but hangs at reboot
- SSH connection lost during deployment

**Cause:** Instance rebooting for driver activation

**Solution:**
```bash
# The script should handle this automatically, but if it hangs:
# 1. Wait 2-3 minutes for instance to reboot
# 2. Run remaining steps manually:

# Resume from Docker setup:
./scripts/aws/setup-docker-gpu.sh --remote <PUBLIC_IP> --ssh-key <SSH_KEY>
./scripts/aws/deploy-iris.sh --remote <PUBLIC_IP> --ssh-key <SSH_KEY>
./scripts/aws/deploy-nim-llm.sh --remote <PUBLIC_IP> --ssh-key <SSH_KEY>
```

#### Provision-instance.sh fails with existing resources
**Symptoms:**
- Error: "Security group already exists"
- Error: "Instance with tag already exists"

**Cause:** Previous deployment left resources behind

**Solution:**
```bash
# Use existing instance instead of provisioning new one:
export INSTANCE_ID=i-xxxxxxxxxxxxx
export PUBLIC_IP=34.xxx.xxx.xxx
./scripts/aws/deploy.sh

# Or force new instance creation:
# First, terminate old instance via AWS console
# Then run provision with --force:
./scripts/aws/provision-instance.sh --force
```

#### Deploy.sh missing environment variables
**Symptoms:**
- Error: "SSH_KEY_NAME environment variable is required"
- Error: "NVIDIA_API_KEY not found"

**Cause:** .env file not loaded or incomplete

**Solution:**
```bash
# Ensure .env file exists and is complete:
cat .env

# Should contain:
# AWS_REGION=us-east-1
# SSH_KEY_NAME=your-key-name
# SSH_KEY_PATH=/path/to/key.pem
# NVIDIA_API_KEY=nvapi-xxxxx

# Load environment variables:
source .env

# Verify:
env | grep -E "(AWS_REGION|SSH_KEY|NVIDIA_API_KEY)"

# Then re-run deployment:
./scripts/aws/deploy.sh
```

### Install-gpu-drivers.sh issues

#### Docker not accessible after driver installation
**Symptoms:**
- Error: "Docker: Error response from daemon: could not select device driver"
- nvidia-smi works but Docker can't access GPU

**Cause:** Docker daemon not restarted after toolkit installation

**Solution:**
```bash
# SSH into instance
ssh -i <key> ubuntu@<ip>

# Manually restart Docker
sudo systemctl restart docker

# Verify GPU access in Docker:
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

#### GPU drivers install but nvidia-smi fails after reboot
**Symptoms:**
- Driver installation succeeds
- After reboot: nvidia-smi: command not found

**Cause:** Driver package installed but not properly configured

**Solution:**
```bash
# Reinstall driver package
./scripts/aws/install-gpu-drivers.sh --remote <PUBLIC_IP> --ssh-key <SSH_KEY>

# Or manually via SSH:
ssh -i <key> ubuntu@<ip>
sudo apt-get remove --purge nvidia-* -y
sudo apt-get install -y nvidia-driver-535 nvidia-utils-535
sudo reboot
```

### Deploy-iris.sh issues

#### IRIS container starts but namespace creation fails
**Symptoms:**
- Container running but DEMO namespace not created
- Error: "Namespace creation failed"

**Cause:** ObjectScript execution timing issue

**Solution:**
```bash
# Manually create namespace via IRIS terminal:
ssh -i <key> ubuntu@<ip>

docker exec -it iris-vector-db iris session IRIS -U%SYS
# Enter password when prompted: SYS

# Then in IRIS terminal:
Set namespace = "DEMO"
Set properties("Globals") = "DEMO"
Set properties("Library") = "IRISLIB"
Set properties("Routines") = "DEMO"
Set sc = ##class(Config.Namespaces).Create(namespace, .properties)

# Or re-run deployment with schema skip initially:
./scripts/aws/deploy-iris.sh --remote <PUBLIC_IP> --ssh-key <SSH_KEY> --skip-schema
# Then run table creation separately
```

#### Vector tables not created
**Symptoms:**
- IRIS running but queries fail: "Table does not exist"

**Cause:** SQL execution failed silently

**Solution:**
```bash
# Check if tables exist:
ssh -i <key> ubuntu@<ip>
docker exec -i iris-vector-db iris sql IRIS -UDEMO << EOF
SYS
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='DEMO';
EOF

# If missing, recreate manually:
python src/setup/create_text_vector_table.py

# Or re-run deploy-iris.sh with --force-recreate:
./scripts/aws/deploy-iris.sh --remote <PUBLIC_IP> --ssh-key <SSH_KEY> --force-recreate
```

### Deploy-nim-llm.sh issues

#### NIM container pulls but won't start
**Symptoms:**
- docker pull succeeds
- Container immediately exits (docker ps shows nothing)

**Cause:** Missing NGC API key or GPU not accessible

**Solution:**
```bash
# Verify API key is set:
ssh -i <key> ubuntu@<ip>
echo $NVIDIA_API_KEY  # Should show nvapi-xxxxx

# Check logs for specific error:
docker logs nim-llm

# Common fixes:
# 1. API key not in environment:
docker run -d \
  --name nim-llm \
  --gpus all \
  -p 8001:8000 \
  -e NGC_API_KEY=<your-key> \
  --shm-size=16g \
  nvcr.io/nim/meta/llama-3.1-8b-instruct:latest

# 2. GPU not accessible:
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

#### NIM model download appears stuck
**Symptoms:**
- Container running but logs show: "Downloading... 0%"
- Stays at 0% for >10 minutes

**Cause:** Slow network or download resume failure

**Solution:**
```bash
# Check actual download progress (model is ~8GB):
ssh -i <key> ubuntu@<ip>
docker exec nim-llm du -sh /opt/nim/.cache

# If genuinely stuck, restart container:
docker restart nim-llm

# Monitor download:
docker logs -f nim-llm

# If repeatedly fails, check network:
wget --output-document=/dev/null http://speedtest.tele2.net/100MB.zip
# Should show >50MB/s for reasonable download time
```

## Common Issues

### 1. EC2 Instance Issues

#### Instance won't launch
**Symptoms:**
- `provision.sh` fails with capacity error
- Error: "Insufficient capacity"

**Cause:** g5.xlarge instances may not be available in the selected AZ

**Solution:**
```bash
# Try a different availability zone
# Edit config/aws-config.yaml:
availability_zone: us-east-1b  # Change from us-east-1a

# Or try a different region
# Edit .env:
AWS_REGION=us-west-2
```

**Alternative:** Wait and retry, or use a different instance type (g5.2xlarge)

#### SSH connection refused
**Symptoms:**
- `ssh: connect to host <ip> port 22: Connection refused`

**Cause:** Security group not configured or instance still booting

**Solution:**
```bash
# Check security group rules
aws ec2 describe-security-groups --group-ids <sg-id>

# Verify your IP is allowed
# Edit config/aws-config.yaml to add your IP:
ingress_rules:
  - port: 22
    cidr: YOUR.IP.ADDRESS.HERE/32  # Replace with your IP
```

#### Instance running but no GPU detected
**Symptoms:**
- `nvidia-smi` command not found
- No GPU visible

**Cause:** Drivers not installed or instance needs reboot

**Solution:**
```bash
# Re-run GPU setup
./scripts/aws/setup-gpu.sh

# Manually reboot
aws ec2 reboot-instances --instance-ids <instance-id>

# Wait 2 minutes, then verify
ssh -i <key> ubuntu@<ip> nvidia-smi
```

### 2. NVIDIA Driver Issues

#### APT source corruption
**Symptoms:**
- Error: "Type '<!doctype' is not known on line 1"
- `nvidia-container-toolkit` installation fails

**Cause:** APT source list contains HTML instead of repository list

**Solution:**
```bash
# SSH into instance
ssh -i <key> ubuntu@<ip>

# Remove corrupted source
sudo rm /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Re-add correct source
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Update and install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
```

#### Driver version mismatch
**Symptoms:**
- `nvidia-smi` shows wrong driver version
- Docker can't access GPU

**Cause:** Multiple driver versions installed

**Solution:**
```bash
# Remove all NVIDIA packages
sudo apt-get remove --purge nvidia-* -y
sudo apt-get autoremove -y

# Reinstall driver-535
sudo apt-get install -y nvidia-driver-535 nvidia-utils-535

# Reboot
sudo reboot
```

#### CUDA version mismatch
**Symptoms:**
- NIM containers fail to start
- Error: "CUDA version not supported"

**Cause:** Driver provides different CUDA version than expected

**Solution:**
```bash
# Check CUDA version
nvidia-smi | grep "CUDA Version"

# Should show 12.2 or higher
# If lower, upgrade driver:
sudo apt-get install -y nvidia-driver-535
sudo reboot
```

### 3. IRIS Database Issues

#### IRIS container won't start
**Symptoms:**
- `docker ps` doesn't show iris-fhir
- Container exits immediately

**Cause:** Port conflict or volume permission issues

**Solution:**
```bash
# Check for port conflicts
sudo lsof -i :1972
sudo lsof -i :52773

# Kill conflicting processes if any
sudo kill <PID>

# Check volume permissions
ls -la iris-data/
sudo chown -R 51773:51773 iris-data/

# Restart container
docker restart iris-fhir
```

#### Can't connect to IRIS database
**Symptoms:**
- Connection timeout
- Error: "Connection refused"

**Cause:** Container not fully initialized or firewall blocking

**Solution:**
```bash
# Wait for health check
docker logs iris-fhir --tail 50

# Should see: "Database ready"

# Check if port is open
nc -zv localhost 1972

# If not, check Docker networking
docker network inspect bridge
```

#### Vector table creation fails
**Symptoms:**
- Error: "VECTOR type not supported"
- Error: "Invalid column type"

**Cause:** Using older IRIS version without vector support

**Solution:**
```bash
# Check IRIS version
docker exec iris-fhir iris session IRIS -U%SYS <<< "write \$zv"

# Should be 2025.1 or later
# If not, pull correct image:
docker pull intersystemsdc/iris-community:2025.1
docker stop iris-fhir
docker rm iris-fhir

# Re-run deployment
./scripts/aws/deploy-iris.sh
```

### 4. NIM Service Issues

#### NIM LLM container fails to start
**Symptoms:**
- Container exits with code 137 (out of memory)
- Error: "Cannot allocate memory"

**Cause:** Insufficient GPU memory for model

**Solution:**
```bash
# Check GPU memory
nvidia-smi

# If <16GB available, try smaller model or adjust profile:
docker run -d \
  --name nim-llm \
  --gpus all \
  -e NIM_MODEL_PROFILE=fp16  # Use fp16 instead of auto
  -p 8001:8000 \
  --shm-size=16g \
  nvcr.io/nim/meta/llama-3.1-8b-instruct:latest

# Or use g5.2xlarge instance (48GB GPU memory)
```

#### NIM LLM model download timeout
**Symptoms:**
- Container running but model not loading
- Logs show: "Downloading model... 0%"

**Cause:** Slow network or large model

**Solution:**
```bash
# Check download progress
docker logs nim-llm --follow

# Model is ~16GB, may take 10-30 minutes
# Verify network speed:
wget --output-document=/dev/null http://speedtest.tele2.net/10MB.zip

# If download stalls, restart container:
docker restart nim-llm
```

#### NVIDIA API key invalid
**Symptoms:**
- Error: "Invalid API key"
- Error: "Authentication failed"

**Cause:** Wrong API key format or expired key

**Solution:**
```bash
# Verify API key format (should start with "nvapi-")
echo $NVIDIA_API_KEY

# Test API key directly:
curl -H "Authorization: Bearer $NVIDIA_API_KEY" \
  https://api.nvcf.nvidia.com/v2/nvcf/pexec/status

# Generate new key at: https://org.ngc.nvidia.com/setup/api-key

# Update .env and reload
nano .env
docker restart nim-llm
```

#### Embeddings API rate limited
**Symptoms:**
- Error: "Rate limit exceeded"
- Vectorization slows down dramatically

**Cause:** Exceeding free tier rate limits (60 req/min)

**Solution:**
```bash
# Reduce batch size in config/nim-config.yaml:
nim_embeddings:
  batch_size: 25  # Reduce from 50
  rate_limit:
    requests_per_minute: 30  # Reduce from 60

# Or upgrade to paid tier for higher limits
# Or use local embedding model instead
```

### 5. Vectorization Issues

#### Vectorization fails with connection error
**Symptoms:**
- Error: "Connection to IRIS failed"
- Error: "Embeddings API unavailable"

**Cause:** Services not healthy or wrong endpoints

**Solution:**
```bash
# Verify IRIS connection
python -c "
import irispython
conn = irispython.connect('localhost', 1972, 'DEMO', '_SYSTEM', 'ISCDEMO')
print('✅ IRIS connection OK')
"

# Verify embeddings API
curl http://localhost:8000/health

# Check endpoints in .env
cat .env | grep -E '(IRIS_HOST|IRIS_PORT)'
```

#### Vectorization extremely slow
**Symptoms:**
- <5 docs/sec throughput
- ETA shows hours for completion

**Cause:** Rate limiting, small batches, or network latency

**Solution:**
```bash
# Increase batch size (if not rate limited):
python src/vectorization/vectorize_documents.py \
  --batch-size 100  # Increase from 50

# Use parallel processing:
python src/vectorization/vectorize_documents.py \
  --workers 4

# Check network latency to API:
ping api.nvcf.nvidia.com
```

#### Duplicate vectors inserted
**Symptoms:**
- Error: "Duplicate primary key"
- Same documents vectorized multiple times

**Cause:** Checkpoint file corrupted

**Solution:**
```bash
# Check checkpoint status
sqlite3 vectorization_state.db "SELECT COUNT(*) FROM processed_documents;"

# If corrupted, remove and restart:
rm vectorization_state.db

# Resume from specific offset:
python src/vectorization/vectorize_documents.py \
  --resume-from 1000  # Skip first 1000 docs
```

### 6. Vector Search Issues

#### Search returns no results
**Symptoms:**
- All queries return empty results
- Similarity scores all 0

**Cause:** No vectors in database or wrong query format

**Solution:**
```bash
# Verify vectors exist
python -c "
import irispython
conn = irispython.connect('localhost', 1972, 'DEMO', '_SYSTEM', 'ISCDEMO')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM DEMO.ClinicalNoteVectors')
print(f'Total vectors: {cursor.fetchone()[0]}')
"

# Test with known query:
python src/query/test_vector_search.py \
  --query "test" \
  --top-k 10
```

#### Search returns irrelevant results
**Symptoms:**
- Low similarity scores (<0.3)
- Results don't match query semantically

**Cause:** Wrong similarity metric or embedding model mismatch

**Solution:**
```bash
# Verify similarity metric in table definition
# Should be COSINE for embeddings

# Verify using same embedding model for query and documents
# Check config/nim-config.yaml:
nim_embeddings:
  model: nvidia/nv-embedqa-e5-v5  # Must match model used for vectorization
```

#### Search timeout
**Symptoms:**
- Queries take >10 seconds
- Error: "Query timeout"

**Cause:** Missing index or scanning all vectors

**Solution:**
```bash
# Create index on Embedding column
# Note: IRIS Community Edition has limited indexing options
# For production, upgrade to IRIS Standard Edition with HNSW index support
```

### 7. RAG Query Issues

#### LLM generates irrelevant responses
**Symptoms:**
- Response doesn't use retrieved context
- Generic answers instead of specific

**Cause:** Poor prompt engineering or context not passed correctly

**Solution:**
```bash
# Check RAG prompt template in src/query/rag_query.py
# Ensure context is properly formatted:
"""
System: You are a medical assistant. Use ONLY the following clinical notes to answer.

Context:
{retrieved_notes}

User: {query}
"""

# Debug by printing prompt before sending to LLM
```

#### LLM response slow
**Symptoms:**
- >30s response time
- Timeout errors

**Cause:** Model still loading or insufficient GPU memory

**Solution:**
```bash
# Check LLM container status
docker logs nim-llm --tail 50

# Should see "Model loaded and ready"

# Check GPU memory usage
nvidia-smi

# If GPU memory full, reduce context size:
python src/query/rag_query.py \
  --top-k 5  # Reduce from 10
  --max-context-tokens 2000  # Limit context
```

### 8. Clinical Note Vectorization Issues

#### Vectorization fails to start

**Symptoms:**
- Error: "NVIDIA API key required"
- Error: "IRIS connection failed"
- Script exits immediately

**Cause:** Missing credentials or services not running

**Solution:**
```bash
# Check NVIDIA API key is set
echo $NVIDIA_API_KEY  # Should show nvapi-xxxxx

# If not set, add to .env
nano .env
# Add: NVIDIA_API_KEY=nvapi-xxxxx

# Reload environment
source .env

# Verify IRIS is running
docker ps | grep iris
docker logs iris-vector-db --tail 20

# Test IRIS connection
python -c "import iris; conn = iris.connect('localhost', 1972, 'DEMO', '_SYSTEM', 'SYS'); print('✅ Connected')"

# Re-run vectorization
python src/vectorization/text_vectorizer.py --input your_data.json
```

#### Vectorization extremely slow (<10 docs/min)

**Symptoms:**
- Throughput far below 100 docs/min target
- ETA shows hours for small datasets
- Progress updates very slow

**Cause:** API rate limiting, small batches, or network issues

**Solution:**
```bash
# Check current batch size (should be 50+ for production)
# Increase batch size if using smaller value
python src/vectorization/text_vectorizer.py \
  --input data.json \
  --batch-size 50  # Up to 100 if API allows

# Check network latency to NVIDIA API
ping api.nvcf.nvidia.com

# If latency >100ms, consider:
# - Using closer AWS region
# - Checking for network throttling
# - Contacting NVIDIA about API performance

# Monitor API rate limits in logs
# Look for "Rate limit exceeded" messages
# Free tier: 60 req/min (1 req/sec)
# Paid tier: Higher limits available
```

#### Validation errors for all documents

**Symptoms:**
- All documents fail validation
- Error: "Missing required field: text_content"
- No successful vectorizations

**Cause:** Input JSON format mismatch

**Solution:**
```bash
# Check input file format
python -c "
import json
with open('your_data.json', 'r') as f:
    data = json.load(f)
    print(f'Type: {type(data)}')
    print(f'Count: {len(data)}')
    if isinstance(data, list) and len(data) > 0:
        print(f'Sample keys: {list(data[0].keys())}')
"

# Expected format:
# Type: <class 'list'>
# Count: 1234
# Sample keys: ['resource_id', 'patient_id', 'document_type', 'text_content']

# If keys don't match, transform data:
python -c "
import json

with open('your_data.json', 'r') as f:
    data = json.load(f)

# Transform to expected format
transformed = []
for item in data:
    transformed.append({
        'resource_id': item['id'],  # Adjust field names as needed
        'patient_id': item['patientId'],
        'document_type': item['type'],
        'text_content': item['text'],
        'source_bundle': item.get('source', '')
    })

with open('transformed_data.json', 'w') as f:
    json.dump(transformed, f)

print(f'✅ Transformed {len(transformed)} documents')
"

# Retry with transformed data
python src/vectorization/text_vectorizer.py --input transformed_data.json
```

#### Checkpoint corruption / resumeability broken

**Symptoms:**
- Resume mode processes documents again
- Error: "database is locked"
- Duplicate primary key errors

**Cause:** Checkpoint database corrupted or locked

**Solution:**
```bash
# Check checkpoint database status
sqlite3 vectorization_state.db "SELECT Status, COUNT(*) FROM VectorizationState GROUP BY Status;"

# If showing unexpected states or locked:

# Option 1: Reset failed documents only
python -c "
import sqlite3
conn = sqlite3.connect('vectorization_state.db')
cursor = conn.cursor()
cursor.execute(\"UPDATE VectorizationState SET Status='pending' WHERE Status='failed'\")
conn.commit()
print(f'✅ Reset {cursor.rowcount} failed documents')
conn.close()
"

# Option 2: Clear checkpoint entirely and restart
rm vectorization_state.db
python src/vectorization/text_vectorizer.py --input data.json

# Option 3: Use new checkpoint database
python src/vectorization/text_vectorizer.py \
  --input data.json \
  --checkpoint-db fresh_state.db
```

#### GPU memory exhaustion during vectorization

**Symptoms:**
- Error: "CUDA out of memory"
- Embeddings API fails intermittently
- Container restarts during processing

**Cause:** Batch size too large for GPU memory

**Solution:**
```bash
# Reduce batch size
python src/vectorization/text_vectorizer.py \
  --input data.json \
  --batch-size 25  # Reduce from 50

# Check GPU memory usage
nvidia-smi

# If using local NIM embeddings (not Cloud API):
# - Ensure no other GPU processes running
# - Consider g5.2xlarge (48GB) instead of g5.xlarge (24GB)

# For Cloud API (recommended), GPU memory not a factor
```

#### IRIS vector insertion errors

**Symptoms:**
- Error: "Vector dimension mismatch"
- Error: "Duplicate primary key"
- Successful embeddings but failed DB inserts

**Cause:** Vector dimension or ID conflicts

**Solution:**
```bash
# Check vector dimension in IRIS table
python -c "
import iris
conn = iris.connect('localhost', 1972, 'DEMO', '_SYSTEM', 'SYS')
cursor = conn.cursor()
cursor.execute(\"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='ClinicalNoteVectors'\")
if cursor.fetchone():
    print('✅ Table exists')
else:
    print('❌ Table missing - run: python src/setup/create_text_vector_table.py')
conn.close()
"

# For dimension mismatch:
# NV-EmbedQA-E5-V5 produces 1024-dim vectors
# Table must be created with VECTOR(DOUBLE, 1024)

# Recreate table with correct dimension
python src/setup/create_text_vector_table.py

# For duplicate key errors:
# Check if documents were already vectorized
python -c "
import iris
conn = iris.connect('localhost', 1972, 'DEMO', '_SYSTEM', 'SYS')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM DEMO.ClinicalNoteVectors')
print(f'Vectors in DB: {cursor.fetchone()[0]:,}')
conn.close()
"

# If duplicates exist, use resume mode to skip them
python src/vectorization/text_vectorizer.py --input data.json --resume
```

#### Progress appears stuck

**Symptoms:**
- No progress updates for >5 minutes
- Script appears frozen
- No error messages

**Cause:** Large batch embedding or slow API

**Solution:**
```bash
# Script is likely waiting for API response
# NVIDIA API can take 30-60s for large batches

# Check if process is still alive
ps aux | grep text_vectorizer

# Monitor network activity
# On macOS:
nettop -m tcp

# On Linux:
sudo netstat -tunap | grep python

# If truly stuck (>5 min no activity):
# 1. Interrupt with Ctrl+C
# 2. Resume from checkpoint
python src/vectorization/text_vectorizer.py --input data.json --resume

# Reduce batch size to get more frequent updates
python src/vectorization/text_vectorizer.py \
  --input data.json \
  --batch-size 25 \
  --resume
```

## Performance Optimization

### Vectorization Performance

**Target:** ≥100 docs/min

**If slower:**
1. Increase batch size: `--batch-size 100`
2. Check NVIDIA API rate limits (60 req/min free tier)
3. Reduce network latency (use AWS EC2 in us-east-1)
4. Ensure IRIS database not overloaded

**Throughput troubleshooting:**
```bash
# Test embedding API latency
time python -c "
from src.vectorization.embedding_client import NVIDIAEmbeddingsClient
client = NVIDIAEmbeddingsClient()
texts = ['test'] * 50
embeddings = client.embed_batch(texts)
print(f'Generated {len(embeddings)} embeddings')
"

# Should complete in <5 seconds for 50 texts
# If slower, check network or API status

# Test IRIS insert performance
time python -c "
from src.vectorization.vector_db_client import IRISVectorDBClient
import random
client = IRISVectorDBClient()
client.connect()
embedding = [random.random() for _ in range(1024)]
for i in range(50):
    client.insert_vector(
        resource_id=f'test-{i}',
        patient_id='test-patient',
        document_type='Test',
        text_content='Test content',
        embedding=embedding,
        embedding_model='test'
    )
print('✅ Inserted 50 vectors')
client.disconnect()
"

# Should complete in <2 seconds for 50 inserts
# If slower, check IRIS performance
```

### Vector Search Performance

**Target:** <1s for 100K vectors

**If slower:**
1. Ensure using COSINE similarity (not EUCLIDEAN)
2. Limit result set: `--top-k 10`
3. Use IRIS query optimization
4. Consider IRIS Standard Edition with HNSW index

### RAG Query Performance

**Target:** <5s end-to-end

**Breakdown:**
- Vector search: <1s
- Context retrieval: <0.5s
- LLM generation: <3s

**If slower:**
1. Optimize vector search (see above)
2. Reduce context size
3. Use faster LLM profile (fp16)
4. Cache frequent queries

### 9. RAG Query Issues

#### Slow query response (>5 seconds)

**Symptoms:**
- Query processing exceeds SC-007 target (<5s)
- User experience degraded
- Timeout errors

**Cause:** One or more pipeline components running slowly

**Solution:**

```bash
# Diagnose which component is slow by adding verbose logging
python src/validation/test_rag_query.py \
  --query "test query" \
  --verbose

# Check GPU utilization during query
nvidia-smi dmon -c 10

# If GPU utilization is low (<70%), investigate:
# 1. Check NIM LLM container logs
docker logs nim-llm --tail 50

# 2. Check if LLM model is fully loaded
curl http://localhost:8001/health

# If vector search is slow:
# - Check number of documents in database
python -c "
from vectorization.vector_db_client import IRISVectorDBClient
client = IRISVectorDBClient()
client.connect()
stats = client.get_vector_stats()
print(f'Total vectors: {stats}')
client.disconnect()
"

# Optimize query parameters
python src/validation/test_rag_query.py \
  --query "test query" \
  --top-k 5 \  # Reduce from 10
  --max-context-tokens 2000 \  # Reduce from 4000
  --llm-max-tokens 300  # Reduce from 500
```

Performance breakdown targets:
- Query embedding: <1s (NVIDIA API latency)
- Vector search: <1s (IRIS query)
- Context assembly: <0.5s (string concatenation)
- LLM generation: <3s (NIM LLM inference)

#### No results returned / "No information found" message

**Symptoms:**
- All queries return "no information found"
- Retrieved documents count is 0
- Similarity scores all below threshold

**Cause:** Similarity threshold too high or no vectorized documents

**Solution:**

```bash
# Check if documents are vectorized
python -c "
from vectorization.vector_db_client import IRISVectorDBClient
client = IRISVectorDBClient()
client.connect()
cursor = client.connection.cursor()
cursor.execute('SELECT COUNT(*) FROM DEMO.ClinicalNoteVectors')
count = cursor.fetchone()[0]
print(f'Total vectorized documents: {count}')
client.disconnect()
"

# If count is 0, vectorize documents first:
python src/vectorization/text_vectorizer.py \
  --input synthea_clinical_notes.json

# If documents exist, lower similarity threshold:
python src/validation/test_rag_query.py \
  --query "your query" \
  --similarity-threshold 0.3  # Lower from default 0.5

# Test with very low threshold to see what's being retrieved:
python src/validation/test_rag_query.py \
  --query "your query" \
  --similarity-threshold 0.0 \
  --show-full-documents
```

#### Irrelevant results returned

**Symptoms:**
- Retrieved documents don't match query semantically
- Low similarity scores (<0.5)
- LLM response doesn't address question

**Cause:** Poor embedding quality or wrong similarity metric

**Solution:**

```bash
# Verify using same embedding model for query and documents
# Both should use NVIDIA NV-EmbedQA-E5-V5

# Check embedding model configuration
python -c "
from vectorization.embedding_client import NVIDIAEmbeddingsClient
client = NVIDIAEmbeddingsClient()
print(f'Model: {client.model}')
print(f'Dimension: {client.get_embedding_dimension()}')
"

# Should output:
# Model: nvidia/nv-embedqa-e5-v5
# Dimension: 1024

# Test with more specific query
python src/validation/test_rag_query.py \
  --query "What specific medications for diabetes?" \
  --top-k 15  # Retrieve more documents

# Add patient or document type filters for precision
python src/validation/test_rag_query.py \
  --query "medication dosages" \
  --patient-id "patient-123" \
  --document-type "Progress Note"

# Adjust similarity threshold
python src/validation/test_rag_query.py \
  --query "your query" \
  --similarity-threshold 0.6  # Increase for higher precision
```

#### LLM generates response but doesn't cite sources

**Symptoms:**
- Response generated successfully
- No citations marked as "cited_in_response"
- LLM not referencing document numbers

**Cause:** LLM prompt not emphasizing citation requirement or model temperature too high

**Solution:**

```bash
# Reduce LLM temperature for more deterministic citations
python src/validation/test_rag_query.py \
  --query "your query" \
  --llm-temperature 0.3  # Lower from default 0.7

# The system prompt already instructs citing documents
# Check if retrieved documents are relevant enough

# Verify citation extraction logic by checking response text
python src/validation/test_rag_query.py \
  --query "patient conditions" \
  --output result.json \
  --verbose

# Check result.json for response text and citations array
```

#### LLM connection errors

**Symptoms:**
- Error: "LLM service unavailable"
- Error: "Connection refused" on port 8001
- Timeout errors

**Cause:** NIM LLM service not running or still initializing

**Solution:**

```bash
# Check if NIM LLM container is running
docker ps | grep nim-llm

# If not running, check why it stopped
docker logs nim-llm --tail 100

# Verify health endpoint
curl http://localhost:8001/health
# Should return: {"status": "ready"}

# If model still downloading, wait and monitor
docker logs -f nim-llm
# Look for "Model loaded successfully" message

# Restart NIM LLM if necessary
docker restart nim-llm

# Wait 2-3 minutes for model to load into GPU memory
sleep 180

# Test again
curl http://localhost:8001/health
```

#### Embedding API errors during query

**Symptoms:**
- Error: "Failed to generate query embedding"
- NVIDIA API connection errors
- API rate limit errors

**Cause:** NVIDIA API key invalid or rate limits exceeded

**Solution:**

```bash
# Verify API key is set
echo $NVIDIA_API_KEY
# Should show: nvapi-xxxxx

# Test API key directly
curl -H "Authorization: Bearer $NVIDIA_API_KEY" \
  https://api.nvcf.nvidia.com/v2/nvcf/pexec/status

# If rate limited, queries use same rate limits as vectorization
# Free tier: 60 requests/minute
# Queries use 1 request per query (for query embedding)

# Generate new API key if needed:
# Visit: https://org.ngc.nvidia.com/setup/api-key

# Update .env and reload
export NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### Empty or generic LLM responses

**Symptoms:**
- LLM generates generic answers not based on context
- Response doesn't use retrieved clinical notes
- Hallucinated information

**Cause:** Context not passed correctly or LLM ignoring instructions

**Solution:**

```bash
# Verify documents are being retrieved
python src/validation/test_rag_query.py \
  --query "your query" \
  --verbose

# Check if "Documents Used in Context" is > 0

# Increase context size if documents are too short
python src/validation/test_rag_query.py \
  --query "your query" \
  --max-context-tokens 6000  # Increase from 4000

# Lower temperature for more faithful responses
python src/validation/test_rag_query.py \
  --query "your query" \
  --llm-temperature 0.1  # Very low for strict adherence

# Retrieve more documents for richer context
python src/validation/test_rag_query.py \
  --query "your query" \
  --top-k 20 \
  --similarity-threshold 0.4
```

#### Integration test failures

**Symptoms:**
- pytest tests/integration/test_end_to_end_rag.py fails
- SC-007 performance test failures
- Citation extraction test failures

**Cause:** System components not properly configured or database empty

**Solution:**

```bash
# Ensure all services are running
docker ps

# Should show:
# - iris-vector-db (ports 1972, 52773)
# - nim-llm (port 8001)

# Ensure database has vectorized documents
python -c "
from vectorization.vector_db_client import IRISVectorDBClient
client = IRISVectorDBClient()
client.connect()
cursor = client.connection.cursor()
cursor.execute('SELECT COUNT(*) FROM DEMO.ClinicalNoteVectors')
count = cursor.fetchone()[0]
print(f'Vectorized documents: {count}')
client.disconnect()
"

# If count is 0, vectorize test data
python src/vectorization/text_vectorizer.py \
  --input tests/fixtures/sample_clinical_notes.json

# Run tests with verbose output
pytest tests/integration/test_end_to_end_rag.py -v -s

# Run specific failing test
pytest tests/integration/test_end_to_end_rag.py::TestPerformance::test_query_latency_meets_sc007 -v

# If SC-007 performance test fails:
# - Check GPU is being utilized (nvidia-smi)
# - Ensure no other processes using GPU
# - Verify NIM LLM is using GPU (check container logs)
```

### 10. Image Vectorization Issues

#### NIM Vision deployment failures

**Symptoms:**
- deploy-nim-vision.sh script fails
- Container exits immediately after start
- Error: "Container not found" or "unhealthy"
- Health check never succeeds

**Cause:** NVIDIA API key missing, GPU not accessible, or insufficient resources

**Solution:**

```bash
# Verify NVIDIA API key is set
echo $NVIDIA_API_KEY
# Should show: nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# If not set, add to .env
nano .env
# Add: NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Reload environment
source .env

# Verify GPU is accessible
nvidia-smi
# Should show NVIDIA A10G with available memory

# Check GPU is accessible in Docker
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

# Redeploy NIM Vision with force recreate
./scripts/aws/deploy-nim-vision.sh --force-recreate

# Monitor deployment logs
docker logs -f nim-vision

# Verify health after 3-5 minutes
curl http://localhost:8002/health
# Should return: {"status": "ready"}
```

**Check container resource usage:**
```bash
# Ensure sufficient GPU memory (requires ~2-4GB)
nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits

# Should show >4000 MB available

# If insufficient, stop other GPU containers
docker stop nim-llm  # Frees ~8GB
docker start nim-llm  # Restart after NIM Vision is up
```

**Manual container restart:**
```bash
# Stop and remove old container
docker stop nim-vision || true
docker rm nim-vision || true

# Start fresh
docker run -d \
  --name nim-vision \
  --gpus all \
  --restart unless-stopped \
  -p 8002:8000 \
  -e NGC_API_KEY=$NVIDIA_API_KEY \
  -e NIM_MODEL_PROFILE=auto \
  --shm-size=8g \
  nvcr.io/nim/nvidia/nv-clip-vit:latest

# Wait for initialization
sleep 180

# Verify health
curl http://localhost:8002/health
```

#### DICOM validation errors

**Symptoms:**
- All DICOM files fail validation
- Error: "DICOM file is corrupted or incomplete"
- Error: "pydicom not available"
- Image validation returns "Validation failed: ..."

**Cause:** pydicom not installed, corrupted DICOM files, or unsupported transfer syntax

**Solution:**

```bash
# Ensure pydicom is installed
pip install pydicom

# Test DICOM reading
python -c "
import pydicom
from pathlib import Path

dcm_file = Path('tests/fixtures/sample_medical_images').glob('*.dcm')
first_dcm = next(dcm_file)
ds = pydicom.dcmread(first_dcm)
print(f'✅ Patient: {ds.PatientID}')
print(f'✅ Dimensions: {ds.Rows}x{ds.Columns}')
print(f'✅ Modality: {ds.Modality}')
"

# If reading fails, check file integrity
python -c "
import pydicom
from pathlib import Path

dcm_files = list(Path('path/to/images').glob('*.dcm'))
print(f'Found {len(dcm_files)} DICOM files')

corrupted = []
for dcm_file in dcm_files:
    try:
        ds = pydicom.dcmread(dcm_file)
        # Try to access pixel data
        _ = ds.pixel_array
    except Exception as e:
        corrupted.append((dcm_file.name, str(e)))

if corrupted:
    print(f'\\n❌ {len(corrupted)} corrupted files:')
    for name, error in corrupted[:10]:  # Show first 10
        print(f'  - {name}: {error}')
else:
    print('✅ All DICOM files valid')
"
```

**Handle unsupported transfer syntax:**
```bash
# Install GDCM for additional codec support
pip install pydicom[gdcm]

# Or use Pillow with JPEG 2000 support
pip install Pillow pillow-jpls
```

**Skip corrupted files:**
```bash
# The pipeline automatically skips corrupted files and logs errors
# Check error log for details
cat image_vectorization_errors.log
```

#### Image preprocessing failures

**Symptoms:**
- Error: "Preprocessing failed: Image validation failed"
- Error: "cannot identify image file"
- Error: "Image dimensions invalid: 0x0"
- Preprocessing takes >5 seconds per image

**Cause:** Invalid image format, missing dependencies, or oversized images

**Solution:**

```bash
# Ensure Pillow is installed with all codecs
pip install Pillow

# Test image preprocessing
python -c "
from PIL import Image
from pathlib import Path

# Test loading DICOM
import pydicom
dcm_path = Path('path/to/test.dcm')
ds = pydicom.dcmread(dcm_path)
pixel_array = ds.pixel_array

# Normalize to 0-255
pixel_array = pixel_array - pixel_array.min()
pixel_array = pixel_array / pixel_array.max() * 255
pixel_array = pixel_array.astype('uint8')

# Convert to PIL
image = Image.fromarray(pixel_array)
print(f'✅ Image size: {image.size}')
print(f'✅ Image mode: {image.mode}')

# Test resizing
image_resized = image.resize((224, 224), Image.Resampling.LANCZOS)
print(f'✅ Resized to: {image_resized.size}')
"
```

**Optimize for large images:**
```bash
# If preprocessing is slow due to large DICOM files (>10MB)
# The pipeline automatically resizes to 224x224, but loading can be slow

# Check image sizes
find path/to/images -name "*.dcm" -exec du -h {} \; | sort -hr | head -20

# For very large files (>50MB), consider:
# 1. Pre-downsampling DICOM files
# 2. Increasing batch processing timeout
# 3. Processing in smaller batches
```

**Handle grayscale vs RGB conversion:**
```bash
# Pipeline converts all images to RGB mode
# Test conversion
python -c "
from PIL import Image

# Grayscale image
img = Image.open('grayscale.png')
print(f'Original mode: {img.mode}')

# Convert to RGB
img_rgb = img.convert('RGB')
print(f'Converted mode: {img_rgb.mode}')
print(f'✅ Conversion successful')
"
```

#### Embedding generation failures

**Symptoms:**
- Error: "NIM Vision request timed out"
- Error: "Could not connect to NIM Vision"
- Error: "Invalid NIM Vision response format"
- Batch embedding fails for all images in batch

**Cause:** NIM Vision service not running, wrong endpoint, or network issues

**Solution:**

```bash
# Verify NIM Vision is running
docker ps | grep nim-vision

# If not running, check why
docker logs nim-vision --tail 100

# Test NIM Vision health endpoint
curl http://localhost:8002/health
# Should return: {"status": "ready"}

# Test embedding generation manually
python -c "
import requests
import base64
from PIL import Image
from io import BytesIO

# Load test image
img = Image.new('RGB', (224, 224), color='red')
buffered = BytesIO()
img.save(buffered, format='PNG')
img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

# Test API
response = requests.post(
    'http://localhost:8002/v1/embeddings',
    json={'input': img_b64, 'model': 'nv-clip-vit'},
    timeout=60
)

print(f'Status: {response.status_code}')
data = response.json()
print(f'✅ Embedding dimension: {len(data[\"data\"][0][\"embedding\"])}')
"

# If embedding test fails, restart NIM Vision
docker restart nim-vision
sleep 180

# Check custom endpoint if using remote deployment
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --vision-url http://34.xxx.xxx.xxx:8002
```

**Timeout issues:**
```bash
# If timeouts occur frequently, increase timeout in code
# Edit src/vectorization/image_vectorizer.py
# Change: timeout=60 to timeout=120 in NIMVisionClient.__init__

# Or use smaller batch sizes to reduce per-request load
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --batch-size 5  # Reduce from 10
```

**Network connectivity issues:**
```bash
# Test network connectivity to NIM Vision
curl -v http://localhost:8002/health

# If using remote instance, ensure port 8002 is accessible
# Check security group rules:
aws ec2 describe-security-groups --group-ids sg-xxxxx

# Add ingress rule if missing:
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 8002 \
  --cidr 0.0.0.0/0
```

#### Performance below target (SC-005: <0.5 images/sec)

**Symptoms:**
- Throughput <0.5 images/second (>2 sec/image)
- ETA shows many hours for small datasets
- Pipeline progress very slow
- GPU utilization low (<50%)

**Cause:** Network latency, small batches, slow disk I/O, or GPU not being used

**Solution:**

```bash
# Check current throughput in pipeline output
# Look for: "X.XX imgs/sec" in batch processing logs

# Increase batch size for better GPU utilization
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --batch-size 20  # Increase from default 10

# Verify GPU is being used by NIM Vision
nvidia-smi

# Should show GPU utilization >70% during processing
# If low, check NIM Vision logs:
docker logs nim-vision --tail 50

# Profile preprocessing performance
python -c "
import time
from pathlib import Path
from vectorization.image_vectorizer import ImagePreprocessor

preprocessor = ImagePreprocessor()
test_images = list(Path('path/to/images').glob('*.dcm'))[:20]

start = time.time()
for img_path in test_images:
    preprocessor.preprocess(img_path)
elapsed = time.time() - start

throughput = len(test_images) / elapsed
print(f'Preprocessing throughput: {throughput:.2f} imgs/sec')
# Should be >10 imgs/sec for DICOM
"

# If preprocessing is slow:
# - Check disk I/O: iostat -x 1
# - Use SSD storage for image files
# - Reduce image resolution in preprocessing (already 224x224)

# Check network latency to NIM Vision API
# (Not applicable for local deployment on same instance)
```

**GPU memory issues:**
```bash
# Check GPU memory usage during vectorization
watch -n 2 'nvidia-smi --query-gpu=memory.used,memory.total --format=csv'

# If GPU memory full:
# 1. Reduce NIM Vision batch size (decrease --batch-size)
# 2. Stop other GPU containers temporarily
# 3. Ensure no memory leaks (restart nim-vision periodically)

# Restart NIM Vision to free GPU memory
docker restart nim-vision
sleep 180
```

**Optimize for large datasets:**
```bash
# For datasets >10,000 images, use resumability
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --batch-size 15 \
  --resume \
  --checkpoint-db large_dataset_state.db

# Process in parallel if multiple GPUs available
# (Advanced: requires custom script to split dataset)
```

#### Checkpoint corruption / resume failures

**Symptoms:**
- Resume mode processes images again
- Error: "database is locked"
- Error: "no such table: ImageVectorizationState"
- Duplicate image ID errors in IRIS

**Cause:** Checkpoint database corrupted, locked, or schema mismatch

**Solution:**

```bash
# Check checkpoint database status
sqlite3 image_vectorization_state.db "SELECT Status, COUNT(*) FROM ImageVectorizationState GROUP BY Status;"

# Expected output:
# pending|X
# processing|0
# completed|Y
# failed|Z

# If table doesn't exist or schema error:
rm image_vectorization_state.db
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom  # Will create fresh checkpoint

# If database is locked:
# 1. Kill any running image_vectorizer.py processes
ps aux | grep image_vectorizer
kill <PID>

# 2. Check for open connections
lsof image_vectorization_state.db

# 3. Reset locked state
sqlite3 image_vectorization_state.db "UPDATE ImageVectorizationState SET Status='pending' WHERE Status='processing';"

# Resume from checkpoint
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --resume
```

**Reset failed images only:**
```bash
# Mark all failed images as pending for retry
python -c "
import sqlite3
conn = sqlite3.connect('image_vectorization_state.db')
cursor = conn.cursor()
cursor.execute('UPDATE ImageVectorizationState SET Status=\"pending\" WHERE Status=\"failed\"')
conn.commit()
print(f'✅ Reset {cursor.rowcount} failed images to pending')
conn.close()
"

# Resume to retry failed images
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --resume
```

**Use separate checkpoint for different runs:**
```bash
# Avoid conflicts by using unique checkpoint databases
python src/vectorization/image_vectorizer.py \
  --input /path/to/mimic-cxr \
  --format dicom \
  --checkpoint-db mimic_cxr_state.db

python src/vectorization/image_vectorizer.py \
  --input /path/to/other-images \
  --format png \
  --checkpoint-db other_images_state.db
```

#### Visual similarity search returns no results

**Symptoms:**
- Search returns empty list
- All similarity scores are 0 or very low (<0.1)
- Query embedding generation succeeds but search fails
- No error messages, just empty results

**Cause:** No images vectorized, wrong table, or embedding dimension mismatch

**Solution:**

```bash
# Check if images are vectorized in database
python -c "
from vectorization.vector_db_client import IRISVectorDBClient
client = IRISVectorDBClient()
client.connect()
cursor = client.connection.cursor()
cursor.execute('SELECT COUNT(*) FROM DEMO.MedicalImageVectors')
count = cursor.fetchone()[0]
print(f'Total vectorized images: {count}')
client.disconnect()
"

# If count is 0, vectorize images first:
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --batch-size 10

# Verify table schema
python -c "
from vectorization.vector_db_client import IRISVectorDBClient
client = IRISVectorDBClient()
client.connect()
cursor = client.connection.cursor()
cursor.execute('''
    SELECT COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME='MedicalImageVectors' AND TABLE_SCHEMA='DEMO'
''')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')
client.disconnect()
"

# Should show Embedding as VECTOR type

# Test search with known query image
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --test-search /path/to/query-image.dcm \
  --top-k 10

# Expected output: List of similar images with similarity scores
```

**Test with sample data:**
```bash
# Use test fixtures for validation
python src/vectorization/image_vectorizer.py \
  --input tests/fixtures/sample_medical_images \
  --format dicom \
  --batch-size 10

# Then test search
python src/vectorization/image_vectorizer.py \
  --input tests/fixtures/sample_medical_images \
  --format dicom \
  --test-search tests/fixtures/sample_medical_images/030fc0af-f26c3b88-6e03c1ab-5dae4289-1f25be42.dcm

# Should find similar images from the sample set
```

**Lower similarity threshold for debugging:**
```bash
# Check what's actually in the database
python -c "
from vectorization.vector_db_client import IRISVectorDBClient
import random

client = IRISVectorDBClient()
client.connect()

# Generate random query vector (for testing)
query_vector = [random.random() for _ in range(1024)]

# Search with very low threshold
results = client.search_similar_images(
    query_vector=query_vector,
    top_k=10
)

print(f'Found {len(results)} results')
for i, result in enumerate(results[:3], 1):
    print(f'{i}. {result[\"image_id\"]} - similarity: {result[\"similarity\"]:.4f}')

client.disconnect()
"
```

**Verify embedding dimensions match:**
```bash
# Check NIM Vision embedding dimension
curl -X POST http://localhost:8002/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": "test", "model": "nv-clip-vit"}' | \
  python -c "import sys, json; data = json.load(sys.stdin); print(f'Dimension: {len(data[\"data\"][0][\"embedding\"])}')"

# Should output: Dimension: 1024

# Check IRIS table vector dimension
python -c "
from vectorization.vector_db_client import IRISVectorDBClient
client = IRISVectorDBClient()
print(f'Expected dimension: {client.vector_dimension}')
# Should output: Expected dimension: 1024
"
```

#### IRIS image vector insertion errors

**Symptoms:**
- Error: "Vector dimension mismatch"
- Error: "Table MedicalImageVectors does not exist"
- Successful embeddings but failed DB inserts
- Error: "Duplicate primary key"

**Cause:** Table not created, wrong schema, or duplicate image IDs

**Solution:**

```bash
# Verify MedicalImageVectors table exists
python -c "
from vectorization.vector_db_client import IRISVectorDBClient
client = IRISVectorDBClient()
client.connect()
cursor = client.connection.cursor()
cursor.execute('''
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_NAME='MedicalImageVectors' AND TABLE_SCHEMA='DEMO'
''')
exists = cursor.fetchone()[0]
print(f'Table exists: {exists == 1}')
client.disconnect()
"

# If table doesn't exist, create it
python -c "
from vectorization.vector_db_client import IRISVectorDBClient
client = IRISVectorDBClient()
client.connect()
cursor = client.connection.cursor()

cursor.execute('''
    CREATE TABLE DEMO.MedicalImageVectors (
        ImageID VARCHAR(255) PRIMARY KEY,
        PatientID VARCHAR(255) NOT NULL,
        StudyType VARCHAR(255) NOT NULL,
        ImagePath VARCHAR(1000) NOT NULL,
        Embedding VECTOR(DOUBLE, 1024) NOT NULL,
        RelatedReportID VARCHAR(255),
        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('CREATE INDEX idx_image_patient ON DEMO.MedicalImageVectors(PatientID)')
cursor.execute('CREATE INDEX idx_study_type ON DEMO.MedicalImageVectors(StudyType)')

client.connection.commit()
print('✅ Table created')
client.disconnect()
"

# For duplicate key errors, check existing images
python -c "
from vectorization.vector_db_client import IRISVectorDBClient
client = IRISVectorDBClient()
client.connect()
cursor = client.connection.cursor()
cursor.execute('SELECT ImageID FROM DEMO.MedicalImageVectors LIMIT 10')
existing_ids = [row[0] for row in cursor.fetchall()]
print(f'Sample existing IDs: {existing_ids[:5]}')
client.disconnect()
"

# Use resume mode to skip already processed images
python src/vectorization/image_vectorizer.py \
  --input /path/to/images \
  --format dicom \
  --resume
```

#### Integration test failures

**Symptoms:**
- pytest tests/integration/test_image_vectorization.py fails
- DICOM validation tests fail
- Performance tests fail (SC-005)
- Mock tests pass but integration fails

**Cause:** Missing test fixtures, dependencies not installed, or services not running

**Solution:**

```bash
# Ensure test fixtures exist
ls -la tests/fixtures/sample_medical_images/*.dcm
# Should show 50 DICOM files

# If missing, create symlinks to MIMIC-CXR dataset
cd tests/fixtures/sample_medical_images
# Follow README.md instructions to create symlinks

# Install test dependencies
pip install pytest pillow pydicom

# Run tests with verbose output
pytest tests/integration/test_image_vectorization.py -v -s

# Run specific test class
pytest tests/integration/test_image_vectorization.py::TestDICOMValidation -v

# Run performance tests
pytest tests/integration/test_image_vectorization.py::TestPerformanceValidation -v -m slow

# If tests fail due to NIM Vision not running:
# - Use mocked tests (default behavior)
# - Or start NIM Vision for integration testing

# Check test output for specific failures
pytest tests/integration/test_image_vectorization.py -v --tb=short
```

**Debug specific test:**
```bash
# Run single test with debugging
pytest tests/integration/test_image_vectorization.py::TestDICOMValidation::test_dicom_metadata_extraction -vv -s

# Add print statements to see what's failing
python -c "
from pathlib import Path
from vectorization.image_vectorizer import ImageValidator

validator = ImageValidator(dicom_enabled=True)
sample_dcm = list(Path('tests/fixtures/sample_medical_images').glob('*.dcm'))[0]

is_valid, metadata, error = validator.validate_and_extract(sample_dcm)
print(f'Valid: {is_valid}')
print(f'Metadata: {metadata.to_dict() if metadata else None}')
print(f'Error: {error}')
"
```

## Health Monitoring & Diagnostics

The deployment includes comprehensive health monitoring tools to validate system components and diagnose issues.

### Automated Health Checks

#### Running Health Checks

**System Health CLI (recommended):**
```bash
# Verify system health and schema integrity
python -m src.cli check-health --smoke-test

# Attempt to auto-fix environment issues (missing tables, etc.)
python -m src.cli fix-environment
```

**Quick validation script:**
```bash
# Validate all components
./scripts/aws/validate-deployment.sh

# Validate remote instance
./scripts/aws/validate-deployment.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>

# Skip specific checks
./scripts/aws/validate-deployment.sh --skip-nim --skip-iris
```

**Python health check module:**
```bash
# Run all health checks and see detailed results
python src/validation/health_checks.py

# Use specific check functions
python -c "
from src.validation.health_checks import gpu_check, iris_connection_check
print(gpu_check())
print(iris_connection_check())
"
```

**Pytest automated testing:**
```bash
# Run full test suite
pytest src/validation/test_deployment.py -v

# Run specific component tests
pytest src/validation/test_deployment.py::TestGPU -v
pytest src/validation/test_deployment.py::TestIRIS -v
```

### Understanding Health Check Output

Each health check returns structured diagnostic information:

**Passing check example:**
```
✓ GPU detected: NVIDIA A10G
  Memory: 23028 MB
  Driver: 535.xxx.xx
  CUDA: 12.2
```

**Failing check example:**
```
✗ GPU not accessible
  Error: nvidia-smi not found
  Suggestion: Run: ./scripts/aws/install-gpu-drivers.sh
```

**Warning example:**
```
! Health endpoint not available (may be initializing)
  NIM may still be loading - check: docker logs nim-llm
```

### Common Health Check Failures

#### GPU Not Detected

**Symptoms:**
- Health check shows: `✗ GPU not accessible`
- nvidia-smi command not found
- Error: "No devices were found"

**Diagnostic steps:**
```bash
# 1. Check if nvidia-smi is installed
which nvidia-smi

# 2. Try running nvidia-smi manually
nvidia-smi

# 3. Check kernel module
lsmod | grep nvidia

# 4. Check driver package
dpkg -l | grep nvidia-driver
```

**Solutions:**

Option 1: Reinstall GPU drivers
```bash
./scripts/aws/install-gpu-drivers.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>
```

Option 2: Manual driver installation
```bash
ssh -i <PATH_TO_KEY> ubuntu@<PUBLIC_IP>

# Remove existing drivers
sudo apt-get remove --purge nvidia-* -y

# Install driver-535
sudo apt-get update
sudo apt-get install -y nvidia-driver-535 nvidia-utils-535

# Reboot required
sudo reboot
```

Option 3: Verify instance type
```bash
# Ensure you're using g5.xlarge (not t3.xlarge or similar)
aws ec2 describe-instances --instance-ids <INSTANCE_ID> \
  --query 'Reservations[0].Instances[0].InstanceType' --output text

# Should output: g5.xlarge
```

**Expected result after fix:**
```bash
nvidia-smi
# Should show:
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 535.xxx.xx   Driver Version: 535.xxx.xx   CUDA Version: 12.2   |
# |   0  NVIDIA A10G         Off  | 00000000:00:1E.0 Off |                    0 |
# +-----------------------------------------------------------------------------+
```

#### Docker Cannot Access GPU

**Symptoms:**
- Health check shows: `✗ Docker cannot access GPU`
- Error: "could not select device driver"
- Error: "unknown or invalid runtime name: nvidia"

**Diagnostic steps:**
```bash
# 1. Check Docker is installed
docker --version

# 2. Check nvidia-container-toolkit is installed
dpkg -l | grep nvidia-container-toolkit

# 3. Check Docker daemon configuration
cat /etc/docker/daemon.json

# 4. Try manual GPU test
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

**Solutions:**

Option 1: Reinstall Docker GPU runtime
```bash
./scripts/aws/setup-docker-gpu.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>
```

Option 2: Manual configuration
```bash
ssh -i <PATH_TO_KEY> ubuntu@<PUBLIC_IP>

# Install nvidia-container-toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Test
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

**Expected result after fix:**
```bash
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
# Should show NVIDIA A10G GPU details inside container
```

#### IRIS Database Connection Refused

**Symptoms:**
- Health check shows: `✗ IRIS container not running`
- Error: "Connection refused" on port 1972
- Python iris.connect() fails with timeout

**Diagnostic steps:**
```bash
# 1. Check if container exists
docker ps -a | grep iris

# 2. Check container status
docker inspect iris-vector-db --format '{{.State.Status}}'

# 3. Check container logs
docker logs iris-vector-db --tail 50

# 4. Check port binding
docker port iris-vector-db

# 5. Check if port is listening
netstat -tlnp | grep 1972
```

**Solutions:**

Option 1: Restart IRIS container
```bash
docker restart iris-vector-db

# Wait 30 seconds for initialization
sleep 30

# Verify it's running
docker ps | grep iris-vector-db
```

Option 2: Redeploy IRIS
```bash
./scripts/aws/deploy-iris.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY> --force-recreate
```

Option 3: Manual container start
```bash
ssh -i <PATH_TO_KEY> ubuntu@<PUBLIC_IP>

# Stop and remove old container
docker stop iris-vector-db || true
docker rm iris-vector-db || true

# Create volume if needed
docker volume create iris-data

# Start fresh container
docker run -d \
  --name iris-vector-db \
  -p 1972:1972 \
  -p 52773:52773 \
  -v iris-data:/usr/irissys/data \
  -e IRIS_USERNAME=_SYSTEM \
  -e IRIS_PASSWORD=SYS \
  intersystemsdc/iris-community:2025.1
```

**Check for port conflicts:**
```bash
# See what's using port 1972
sudo lsof -i :1972

# If another process is using it, kill it
sudo kill <PID>
```

**Expected result after fix:**
```bash
python -c "import iris; conn = iris.connect('localhost', 1972, 'DEMO', '_SYSTEM', 'SYS'); print('✅ Connected')"
# Should output: ✅ Connected
```

#### Vector Tables Not Found

**Symptoms:**
- Health check shows: `✗ No vector tables found`
- SQL queries fail: "Table does not exist"
- Vectorization fails with schema errors

**Diagnostic steps:**
```bash
# 1. Connect to IRIS and check tables
python -c "
import iris
conn = iris.connect('localhost', 1972, 'DEMO', '_SYSTEM', 'SYS')
cursor = conn.cursor()
cursor.execute('SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=\\'DEMO\\'')
print('Tables:', [row[0] for row in cursor.fetchall()])
"

# 2. Check namespace exists
docker exec iris-vector-db iris sql IRIS -UDEMO << EOF
SYS
SELECT COUNT(*) AS namespace_exists FROM %Library.EnsPortal_Config_Namespaces WHERE Name='DEMO';
EOF
```

**Solutions:**

Option 1: Create tables using Python script
```bash
python src/setup/create_text_vector_table.py
```

Option 2: Redeploy IRIS with schema recreation
```bash
./scripts/aws/deploy-iris.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY> --force-recreate
```

Option 3: Manual table creation via IRIS SQL
```bash
docker exec -i iris-vector-db iris sql IRIS -UDEMO << 'EOF'
SYS

CREATE TABLE ClinicalNoteVectors (
    ResourceID VARCHAR(255) PRIMARY KEY,
    PatientID VARCHAR(255),
    DocumentType VARCHAR(100),
    TextContent VARCHAR(65535),
    Embedding VECTOR(DOUBLE, 1024)
);

CREATE INDEX idx_patient ON ClinicalNoteVectors(PatientID);
CREATE INDEX idx_doc_type ON ClinicalNoteVectors(DocumentType);

CREATE TABLE MedicalImageVectors (
    ImageID VARCHAR(255) PRIMARY KEY,
    PatientID VARCHAR(255),
    StudyType VARCHAR(100),
    ImagePath VARCHAR(1000),
    Embedding VECTOR(DOUBLE, 1024)
);

CREATE INDEX idx_image_patient ON MedicalImageVectors(PatientID);
CREATE INDEX idx_study_type ON MedicalImageVectors(StudyType);
EOF
```

**Expected result after fix:**
```bash
python -c "
import iris
conn = iris.connect('localhost', 1972, 'DEMO', '_SYSTEM', 'SYS')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=\\'DEMO\\' AND TABLE_NAME IN (\\'ClinicalNoteVectors\\', \\'MedicalImageVectors\\')')
print(f'Tables found: {cursor.fetchone()[0]}')  # Should print: Tables found: 2
"
```

#### NIM LLM Service Not Responding

**Symptoms:**
- Health check shows: `✗ NIM LLM container not running`
- Health endpoint returns 404 or timeout
- Inference requests fail with connection errors

**Diagnostic steps:**
```bash
# 1. Check container status
docker ps -a | grep nim-llm

# 2. Check recent logs
docker logs nim-llm --tail 100

# 3. Check if model is downloading
docker logs nim-llm | grep -i "download"

# 4. Test health endpoint manually
curl http://localhost:8001/health

# 5. Check GPU memory usage (model requires ~8GB)
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

**Solutions:**

Option 1: Wait for model initialization (first deployment only)
```bash
# Model download can take 5-10 minutes
# Monitor progress:
docker logs -f nim-llm

# Look for messages like:
# "Downloading model... 45%"
# "Model loaded successfully"
```

Option 2: Restart container
```bash
docker restart nim-llm

# Wait 2 minutes
sleep 120

# Check health
curl http://localhost:8001/health
```

Option 3: Verify API key
```bash
# Check API key is set
echo $NVIDIA_API_KEY

# Should start with "nvapi-"
# If not set:
export NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Restart container with correct key
docker stop nim-llm
docker rm nim-llm

./scripts/aws/deploy-nim-llm.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY>
```

Option 4: Check GPU memory availability
```bash
# NIM LLM requires ~8GB GPU memory
nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits

# If less than 8000 MB free, stop other GPU containers:
docker stop nim-embeddings  # Frees ~2GB
docker stop iris-vector-db  # If using GPU features
```

Option 5: Redeploy with force recreate
```bash
./scripts/aws/deploy-nim-llm.sh --remote <PUBLIC_IP> --ssh-key <PATH_TO_KEY> --force-recreate
```

**Expected result after fix:**
```bash
# Health endpoint should respond
curl http://localhost:8001/health
# {"status": "ready"}

# Inference should work
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta/llama-3.1-8b-instruct",
    "messages": [{"role": "user", "content": "Hi"}],
    "max_tokens": 10
  }'
# Should return JSON with generated text
```

### Continuous Health Monitoring

#### Set Up Automated Health Checks

Create a cron job to run health checks periodically:

```bash
# Add to crontab (every 5 minutes)
crontab -e

# Add this line:
*/5 * * * * /path/to/FHIR-AI-Hackathon-Kit/scripts/aws/validate-deployment.sh > /var/log/health-check.log 2>&1
```

#### Monitor GPU Utilization

Track GPU usage over time:

```bash
# Watch GPU stats in real-time (updates every 2 seconds)
watch -n 2 nvidia-smi

# Log GPU stats to file
nvidia-smi --query-gpu=timestamp,name,utilization.gpu,memory.used,memory.total,temperature.gpu \
  --format=csv -l 60 > gpu-metrics.csv &

# View GPU utilization graph (requires nvidia-smi dmon)
nvidia-smi dmon -s pucvmet -c 100
```

#### Monitor Service Health with Python

Create a monitoring script:

```python
#!/usr/bin/env python3
"""
Continuous health monitoring script.
Runs health checks every N seconds and logs results.
"""
import time
import json
from datetime import datetime
from src.validation.health_checks import run_all_checks

def monitor(interval_seconds=300):
    """Run health checks every interval_seconds."""
    while True:
        timestamp = datetime.now().isoformat()
        results = run_all_checks()

        # Log results
        for result in results:
            status_emoji = "✓" if result.status == "pass" else "✗"
            print(f"{timestamp} {status_emoji} {result.component}: {result.message}")

            if result.status == "fail":
                print(f"  Details: {result.details}")

        # Save to JSON log
        with open('health-monitor.log', 'a') as f:
            log_entry = {
                "timestamp": timestamp,
                "results": [r.to_dict() for r in results]
            }
            f.write(json.dumps(log_entry) + "\n")

        time.sleep(interval_seconds)

if __name__ == "__main__":
    print("Starting health monitor (Ctrl+C to stop)...")
    monitor(interval_seconds=300)  # Every 5 minutes
```

Run in background:
```bash
python scripts/monitor_health.py > health-monitor.out 2>&1 &
```

#### Alert on Health Check Failures

Send email alerts when checks fail:

```bash
# Install mail utilities
sudo apt-get install -y mailutils

# Add to health monitoring script
./scripts/aws/validate-deployment.sh || \
  echo "Health check failed on $(hostname)" | \
  mail -s "AWS RAG System Alert" your-email@example.com
```

## Monitoring

### Service Health Checks

```bash
# Check all services
docker ps

# Expected containers:
# - iris-fhir (ports 1972, 52773)
# - nim-llm (port 8001)

# Check GPU usage
nvidia-smi --loop=1

# Check IRIS database size
du -sh iris-data/
```

### Log Locations

```bash
# Docker container logs
docker logs iris-fhir
docker logs nim-llm

# System logs
journalctl -u docker
```

### Disk Space

```bash
# Check disk usage
df -h

# If running low:
# - Clean up old Docker images
docker system prune -a

# - Compress old logs
sudo journalctl --vacuum-time=7d
```

## Getting Help

### Collect Diagnostic Information

```bash
# Run diagnostics script
./scripts/aws/collect-diagnostics.sh > diagnostics.txt

# This collects:
# - System information
# - Docker status
# - Service logs
# - Configuration files
# - Resource usage
```

### Report an Issue

When reporting issues, include:
1. Output of `collect-diagnostics.sh`
2. Error message and stack trace
3. Steps to reproduce
4. AWS region and instance type
5. IRIS and NIM versions

**Where to report:**
- GitHub Issues: https://github.com/your-org/FHIR-AI-Hackathon-Kit/issues
- Community Forum: [Link]
- Email: support@your-org.com
