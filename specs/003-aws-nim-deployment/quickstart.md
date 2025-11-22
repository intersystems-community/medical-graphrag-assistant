# Quick Start: AWS GPU NIM RAG Deployment

**Feature**: 003-aws-nim-deployment
**Estimated Time**: 30 minutes
**Prerequisites**: AWS account, NVIDIA NGC API key, local machine with AWS CLI configured

---

## Prerequisites Checklist

Before starting deployment:

- [ ] AWS account with EC2 permissions
- [ ] AWS CLI v2 installed and configured (`aws configure`)
- [ ] NVIDIA NGC account (https://ngc.nvidia.com)
- [ ] NVIDIA API key (from NGC dashboard)
- [ ] SSH key pair for EC2 access (`.pem` file)
- [ ] Clinical notes dataset (synthea_clinical_notes.json)
- [ ] Git repository cloned locally

---

## Step 1: Configure Environment (2 minutes)

Create configuration file with your credentials:

```bash
# Copy template and edit with your values
cp config/.env.template config/.env

# Edit config/.env with your credentials
nano config/.env
```

Required environment variables:
```bash
AWS_REGION=us-east-1
AWS_INSTANCE_TYPE=g5.xlarge
SSH_KEY_NAME=your-key-name
SSH_KEY_PATH=/path/to/your-key.pem

NVIDIA_API_KEY=nvapi-xxxxx...
NGC_API_KEY=nvapi-xxxxx...  # Usually same as NVIDIA_API_KEY

IRIS_USERNAME=_SYSTEM
IRIS_PASSWORD=ISCDEMO
```

---

## Step 2: Run Main Deployment Script (25 minutes)

Execute the all-in-one deployment automation:

```bash
# Make script executable
chmod +x scripts/aws/deploy.sh

# Run deployment (monitors progress automatically)
./scripts/aws/deploy.sh
```

**What happens automatically**:
1. ✅ Provision g5.xlarge EC2 instance (2 min)
2. ✅ Install NVIDIA drivers + CUDA 12.2 (5 min)
3. ✅ Configure Docker GPU runtime (2 min)
4. ✅ Deploy IRIS vector database (3 min)
5. ✅ Deploy NVIDIA NIM LLM service (10 min - large download)
6. ✅ Run deployment validation tests (3 min)

**Expected Output**:
```
[2025-11-09 12:34:56] Starting deployment...
[2025-11-09 12:36:30] ✅ EC2 instance launched: i-012abe9cf48fdc702
[2025-11-09 12:41:15] ✅ GPU drivers installed: nvidia-driver-535
[2025-11-09 12:43:00] ✅ Docker GPU runtime configured
[2025-11-09 12:46:12] ✅ IRIS database running on port 1972
[2025-11-09 12:56:45] ✅ NIM LLM service ready on port 8001
[2025-11-09 12:59:30] ✅ All validation tests passed

Deployment Summary:
  Instance IP: 34.238.176.10
  GPU: NVIDIA A10G (24GB)
  Services Running: IRIS (1972), NIM-LLM (8001)
  Status: READY

Next steps: Run vectorization pipeline (see Step 3)
```

---

## Step 3: Verify Deployment (1 minute)

Check that all services are healthy:

```bash
# SSH into instance and run health checks
ssh -i $SSH_KEY_PATH ubuntu@<INSTANCE_IP>

# On remote instance:
./fhir-ai-hackathon/scripts/aws/validate-deployment.sh
```

**Expected Output**:
```
Running deployment validation...

✅ GPU Check: NVIDIA A10G detected (Driver 535.274.02)
✅ Docker GPU: nvidia-smi accessible in containers
✅ IRIS Database: Connection successful (port 1972)
✅ IRIS Tables: ClinicalNoteVectors table exists
✅ NIM LLM Service: Health check passed (port 8001)
✅ NIM LLM Inference: Test query successful (2.3s response time)

All validation checks passed! System ready for vectorization.
```

---

## Step 4: Vectorize Clinical Notes (30-50 minutes)

Process your clinical documents dataset:

```bash
# On remote instance (via SSH)
cd ~/fhir-ai-hackathon

# Copy your data file (if not already present)
# From local machine:
scp -i $SSH_KEY_PATH synthea_clinical_notes.json ubuntu@<INSTANCE_IP>:~/fhir-ai-hackathon/

# On remote instance: Run vectorization
python3 src/vectorization/text_vectorizer.py \
  --input synthea_clinical_notes.json \
  --batch-size 50 \
  --resume  # Enables resumable processing
```

**Progress Output**:
```
Vectorization Pipeline Starting...
Total documents: 50,569
Batch size: 50
Resume mode: ENABLED

Processing batch 1/1012... [=====>    ] 50/50 docs (2.1s)
Processing batch 2/1012... [=====>    ] 50/50 docs (2.0s)
...
Processing batch 1012/1012... [=====>    ] 19/50 docs (0.8s)

Vectorization Complete!
  Total documents: 50,569
  Successfully processed: 50,565 (99.99%)
  Failed: 4 (see vectorization_errors.log)
  Total time: 42 minutes
  Throughput: 120 docs/min
```

---

## Step 5: Test RAG Query (30 seconds)

Verify end-to-end RAG functionality:

```bash
# On remote instance
python3 src/validation/test_rag_query.py \
  --query "What are the common symptoms of diabetes?"
```

**Expected Output**:
```
Running RAG Query Test...

Query: "What are the common symptoms of diabetes?"

Retrieved Documents (top 3):
  1. [Patient: patient-456, Score: 0.89]
     "Patient presents with polyuria, polydipsia, and unexplained weight loss..."

  2. [Patient: patient-123, Score: 0.85]
     "History of frequent urination, excessive thirst, and fatigue..."

  3. [Patient: patient-789, Score: 0.82]
     "Chief complaint: increased hunger and blurred vision..."

Generated Response (NIM LLM):
"Based on the retrieved clinical notes, common symptoms of diabetes include:
- Polyuria (frequent urination)
- Polydipsia (excessive thirst)
- Unexplained weight loss
- Fatigue
- Increased hunger
- Blurred vision

Sources: Patient records patient-456, patient-123, patient-789"

Query completed in 4.2 seconds.
✅ RAG query test PASSED
```

---

## Common Issues & Solutions

### Issue: "Permission denied" when running deploy.sh
```bash
# Solution: Make script executable
chmod +x scripts/aws/deploy.sh
```

###  Issue: "NVIDIA driver not loading" after reboot
```bash
# Solution: System reboot required after driver install
sudo reboot

# Wait 2 minutes, then re-SSH and verify
nvidia-smi
```

### Issue: "NIM LLM container failed to start"
```bash
# Check NGC API key is set
echo $NVIDIA_API_KEY

# View container logs
docker logs nim-llm

# Common fix: Restart container with correct API key
docker rm -f nim-llm
# Re-run deploy-nim-llm.sh script
```

### Issue: "Out of GPU memory during vectorization"
```bash
# Solution: Reduce batch size
python3 src/vectorization/text_vectorizer.py \
  --batch-size 25  # Reduced from default 50
```

---

## Next Steps

After successful deployment and vectorization:

1. **Add Medical Images**: Run image vectorization pipeline
   ```bash
   python3 src/vectorization/image_vectorizer.py --input /path/to/mimic-cxr
   ```

2. **Build RAG Application**: Integrate with your application using IRIS and NIM APIs

3. **Monitor System**: Set up CloudWatch alarms for GPU utilization and service health

4. **Scale Up**: For production, consider g5.2xlarge or multi-instance deployment

---

## Cost Estimate

**Hourly Costs** (us-east-1):
- g5.xlarge instance: $1.006/hour
- EBS gp3 storage (500GB): $0.08/month (~$0.00011/hour)
- Data transfer: Negligible for testing

**Monthly Cost** (24/7 operation):
- Instance: ~$730/month
- Storage: ~$80/month
- **Total**: ~$810/month

**Cost Savings**:
- Stop instance when not in use: $0/hour (only pay for EBS)
- Use Spot Instances: ~60-70% discount on instance cost

---

## Support & Documentation

- Full deployment guide: `docs/deployment-guide.md`
- Troubleshooting: `docs/troubleshooting.md`
- Architecture: `docs/architecture.md`
- NVIDIA NIM docs: https://docs.nvidia.com/nim/
- IRIS Vector Search: https://docs.intersystems.com/irislatest/csp/docbook/Doc.View.cls?KEY=GSQL_vecsearch
