# OpenAI → NIM Migration Strategy

## Strategy Overview

**Phase 1: Development with OpenAI** (Now - 1 week)
- Fast iteration and testing
- Cheap ($0.0001/1K tokens)
- Validate architecture works
- Build and test all features

**Phase 2: Production Demo with NIM** (Week 2)
- Deploy NIM on AWS EC2 with GPU
- Swap embeddings backend (minimal code changes)
- Demonstrate private, on-premise capability
- Stress testing with self-hosted NIM

**Phase 3: Cost Optimization** (Ongoing)
- Auto start/stop EC2 when not in use
- Save ~$500/month vs 24/7 operation
- Keep OpenAI for dev, NIM for demos

---

## Architecture: Pluggable Embeddings

### Abstract Interface (Swap Providers Easily)

```python
# src/embeddings/base_embeddings.py

from abc import ABC, abstractmethod
from typing import List

class BaseEmbeddings(ABC):
    """Abstract base class for embeddings providers."""

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension."""
        pass

    @property
    @abstractmethod
    def provider(self) -> str:
        """Provider name (openai, nim, etc)."""
        pass
```

---

## Implementation 1: OpenAI (Development)

### OpenAI Embeddings Adapter

```python
# src/embeddings/openai_embeddings.py

from openai import OpenAI
import os
from typing import List
from .base_embeddings import BaseEmbeddings

class OpenAIEmbeddings(BaseEmbeddings):
    """OpenAI embeddings adapter."""

    def __init__(self, model: str = "text-embedding-3-large"):
        """
        Initialize OpenAI embeddings.

        Args:
            model: OpenAI embedding model
                - text-embedding-3-small (1536-dim, $0.00002/1K tokens)
                - text-embedding-3-large (3072-dim, $0.00013/1K tokens)
        """
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=api_key)
        self.model_name = model

        # Dimension based on model
        self._dimension = 3072 if "large" in model else 1536

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        response = self.client.embeddings.create(
            input=text,
            model=self.model_name
        )
        return response.data[0].embedding

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents (batch)."""
        response = self.client.embeddings.create(
            input=texts,
            model=self.model_name
        )
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def provider(self) -> str:
        return "openai"
```

### Setup Instructions

```bash
# Install OpenAI SDK
pip install openai

# Set API key
export OPENAI_API_KEY="sk-..."

# Test
python -c "
from src.embeddings.openai_embeddings import OpenAIEmbeddings
embedder = OpenAIEmbeddings(model='text-embedding-3-large')
vector = embedder.embed_query('chest pain and shortness of breath')
print(f'✅ OpenAI embeddings: {len(vector)} dimensions')
"
```

### Cost
- **text-embedding-3-large**: $0.00013 per 1K tokens
- **51 documents × 100 tokens avg**: 5,100 tokens = $0.0007 (~$0.001)
- **10K documents × 100 tokens avg**: 1M tokens = $0.13
- **Queries (1K/day × 30 days)**: 30K tokens = $0.004/month

**Total for development: ~$1-5/month**

---

## Implementation 2: NIM (Production Demo)

### NIM Embeddings Adapter

```python
# src/embeddings/nim_embeddings.py

import requests
import os
from typing import List
from .base_embeddings import BaseEmbeddings

class NIMEmbeddings(BaseEmbeddings):
    """Self-hosted NIM embeddings adapter."""

    def __init__(self,
                 endpoint: str = "http://localhost:8000/v1/embeddings",
                 model: str = "nvidia/nv-embedqa-e5-v5"):
        """
        Initialize NIM embeddings.

        Args:
            endpoint: NIM inference endpoint URL
            model: NIM model name (for metadata)
        """
        self.endpoint = endpoint
        self.model_name = model

        # Test connection
        self._test_connection()

    def _test_connection(self):
        """Test NIM endpoint is reachable."""
        try:
            response = requests.get(
                self.endpoint.replace('/v1/embeddings', '/health'),
                timeout=5
            )
            if response.status_code != 200:
                raise ConnectionError(f"NIM health check failed: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Cannot reach NIM endpoint {self.endpoint}: {e}")

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        response = requests.post(
            self.endpoint,
            json={
                "input": text,
                "model": self.model_name,
                "input_type": "query"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents (batch)."""
        response = requests.post(
            self.endpoint,
            json={
                "input": texts,
                "model": self.model_name,
                "input_type": "passage"
            },
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()["data"]
        return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]

    @property
    def dimension(self) -> int:
        # NV-EmbedQA-E5-v5 is 1024-dim
        return 1024

    @property
    def provider(self) -> str:
        return "nim"
```

---

## Factory Pattern (Easy Switching)

```python
# src/embeddings/embeddings_factory.py

import os
from typing import Optional
from .base_embeddings import BaseEmbeddings
from .openai_embeddings import OpenAIEmbeddings
from .nim_embeddings import NIMEmbeddings

class EmbeddingsFactory:
    """Factory for creating embeddings providers."""

    @staticmethod
    def create(provider: Optional[str] = None) -> BaseEmbeddings:
        """
        Create embeddings provider.

        Args:
            provider: 'openai', 'nim', or None (auto-detect)

        Returns:
            BaseEmbeddings instance

        Environment Variables:
            EMBEDDINGS_PROVIDER: 'openai' or 'nim'
            OPENAI_API_KEY: Required for OpenAI
            NIM_ENDPOINT: Required for NIM (default: http://localhost:8000/v1/embeddings)
        """
        # Auto-detect from environment
        if provider is None:
            provider = os.environ.get('EMBEDDINGS_PROVIDER', 'openai')

        if provider == 'openai':
            return OpenAIEmbeddings(model='text-embedding-3-large')

        elif provider == 'nim':
            endpoint = os.environ.get('NIM_ENDPOINT', 'http://localhost:8000/v1/embeddings')
            return NIMEmbeddings(endpoint=endpoint)

        else:
            raise ValueError(f"Unknown provider: {provider}")
```

### Usage in Application

```python
# src/setup/vectorize_documents.py

from src.embeddings.embeddings_factory import EmbeddingsFactory
import iris
import json

def vectorize_all_documents():
    """Vectorize all DocumentReference resources."""

    # Create embeddings provider (auto-detect from env)
    embedder = EmbeddingsFactory.create()
    print(f"Using embeddings provider: {embedder.provider}")
    print(f"Embedding dimension: {embedder.dimension}")

    # Connect to IRIS
    conn = iris.connect('localhost', 32782, 'DEMO', '_SYSTEM', 'ISCDEMO')
    cursor = conn.cursor()

    # Get all DocumentReference resources
    cursor.execute("""
        SELECT ID, ResourceString
        FROM HSFHIR_X0001_R.Rsrc
        WHERE ResourceType = 'DocumentReference'
        AND (Deleted = 0 OR Deleted IS NULL)
    """)

    documents = cursor.fetchall()
    print(f"Found {len(documents)} DocumentReference resources")

    for resource_id, resource_string in documents:
        # Parse FHIR JSON and decode clinical note
        fhir_data = json.loads(resource_string)
        try:
            hex_data = fhir_data['content'][0]['attachment']['data']
            clinical_note = bytes.fromhex(hex_data).decode('utf-8', errors='replace')
        except:
            print(f"  Skipping resource {resource_id}: No clinical note")
            continue

        # Generate embedding
        print(f"  Vectorizing resource {resource_id}...")
        vector = embedder.embed_query(clinical_note)

        # Insert into database
        cursor.execute("""
            INSERT INTO VectorSearch.FHIRTextVectors
            (ResourceID, ResourceType, TextContent, Vector, EmbeddingModel, Provider)
            VALUES (?, ?, ?, TO_VECTOR(?), ?, ?)
        """, (
            resource_id,
            'DocumentReference',
            clinical_note,
            str(vector),
            embedder.model_name if hasattr(embedder, 'model_name') else 'unknown',
            embedder.provider
        ))

    conn.commit()
    cursor.close()
    conn.close()

    print(f"✅ Vectorized {len(documents)} documents with {embedder.provider}")

if __name__ == '__main__':
    vectorize_all_documents()
```

---

## Switching Between Providers

### Development Mode (OpenAI)
```bash
export EMBEDDINGS_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."

python src/setup/vectorize_documents.py
```

### Production Demo (NIM)
```bash
export EMBEDDINGS_PROVIDER="nim"
export NIM_ENDPOINT="http://ec2-xx-xx-xx-xx.compute.amazonaws.com:8000/v1/embeddings"

python src/setup/vectorize_documents.py
```

### Auto-Detection
If `EMBEDDINGS_PROVIDER` not set, defaults to OpenAI for development.

---

## AWS EC2 Setup for NIM

### Launch EC2 Instance

```bash
# Launch g5.xlarge with GPU
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \  # Deep Learning AMI
  --instance-type g5.xlarge \
  --key-name your-key \
  --security-group-ids sg-xxx \
  --subnet-id subnet-xxx \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=nim-embeddings}]'
```

### Install NIM Container

```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@ec2-xx-xx-xx-xx.compute.amazonaws.com

# Install NVIDIA Container Toolkit (if not pre-installed)
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Pull NIM container (requires NGC API key)
export NGC_API_KEY="your-ngc-key"
docker login nvcr.io --username '$oauthtoken' --password $NGC_API_KEY

# Pull NIM text embedding model
docker pull nvcr.io/nim/nvidia/nv-embedqa-e5-v5:latest

# Run NIM container
docker run -d \
  --gpus all \
  --name nim-embeddings \
  -p 8000:8000 \
  -e NGC_API_KEY=$NGC_API_KEY \
  nvcr.io/nim/nvidia/nv-embedqa-e5-v5:latest

# Test
curl http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What are the symptoms of hypertension?",
    "model": "nvidia/nv-embedqa-e5-v5"
  }'
```

---

## Cost Control: Auto Start/Stop EC2

### Start Script
```bash
#!/bin/bash
# scripts/aws/start-nim-ec2.sh

INSTANCE_ID="i-xxxxxxxxxxxx"

echo "Starting NIM EC2 instance..."
aws ec2 start-instances --instance-ids $INSTANCE_ID

echo "Waiting for instance to start..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "✅ NIM instance started: http://$PUBLIC_IP:8000"
echo "Set environment variable:"
echo "export NIM_ENDPOINT=\"http://$PUBLIC_IP:8000/v1/embeddings\""
```

### Stop Script
```bash
#!/bin/bash
# scripts/aws/stop-nim-ec2.sh

INSTANCE_ID="i-xxxxxxxxxxxx"

echo "Stopping NIM EC2 instance..."
aws ec2 stop-instances --instance-ids $INSTANCE_ID

echo "Waiting for instance to stop..."
aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID

echo "✅ NIM instance stopped (saving ~$24/day)"
```

### Usage
```bash
# Morning: Start for demo/testing
./scripts/aws/start-nim-ec2.sh
export NIM_ENDPOINT="http://ec2-xx-xx-xx-xx.amazonaws.com:8000/v1/embeddings"
export EMBEDDINGS_PROVIDER="nim"

# Test
python src/query/fhir_graphrag_query.py "chest pain" --top-k 5

# Evening: Stop to save money
./scripts/aws/stop-nim-ec2.sh
```

---

## Cost Comparison

### Development (OpenAI)
- 51 documents vectorized: $0.001
- 1K queries/month: $0.13
- **Total: ~$1-5/month**

### Production Demo (NIM on EC2)
- g5.xlarge: $1.006/hour
- 8 hours/day × 20 days = 160 hours/month
- **Total: ~$160/month** (vs $720 if running 24/7)

### Cost Savings
- Auto start/stop: **Save $560/month** (78% reduction)
- Use OpenAI for dev: **Save another $155/month**
- **Combined savings: $715/month**

---

## Migration Checklist

### Phase 1: OpenAI Development (Week 1)
- [ ] Install OpenAI SDK: `pip install openai`
- [ ] Set OPENAI_API_KEY
- [ ] Implement OpenAIEmbeddings class
- [ ] Implement EmbeddingsFactory
- [ ] Create VectorSearch.FHIRTextVectors table (3072-dim for OpenAI)
- [ ] Vectorize 51 DocumentReferences
- [ ] Test query functionality
- [ ] Develop all features with OpenAI

### Phase 2: NIM Production Setup (Week 2)
- [ ] Launch AWS EC2 g5.xlarge
- [ ] Install NIM container
- [ ] Test NIM endpoint
- [ ] Implement NIMEmbeddings class
- [ ] Test provider switching (OpenAI → NIM)
- [ ] Re-vectorize with NIM (1024-dim)
- [ ] Performance benchmark
- [ ] Create start/stop scripts

### Phase 3: Demo Preparation
- [ ] Script for starting EC2 before demo
- [ ] Verify NIM endpoint accessible
- [ ] Switch EMBEDDINGS_PROVIDER to "nim"
- [ ] Test full demo flow
- [ ] Stop EC2 after demo

---

## Summary

**Development**: OpenAI ($1-5/month, fast iteration)
**Production Demo**: Self-hosted NIM on EC2 ($160/month with auto-stop)
**Code**: Same interface, swap with environment variable

**Result**: Best of both worlds - cheap development + production-ready demo! 🚀
