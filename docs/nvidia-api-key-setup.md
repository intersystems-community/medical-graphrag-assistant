# NVIDIA API Key Setup Guide

## Step 1: Get Your NVIDIA API Key

### Navigate to NVIDIA Build
Go to: **https://build.nvidia.com**

### Create/Login to NVIDIA Account
1. Click "Sign In" (top right)
2. Create an NVIDIA account or login with existing credentials
3. You may need to verify your email

### Generate API Key
1. Once logged in, look for "API Keys" or "Get API Key" section
2. Click "Generate API Key" or "Create New API Key"
3. Copy the key - it will look like: `nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
4. **IMPORTANT**: Save this key securely - you won't be able to see it again

## Step 2: Set Up API Key in Your Environment

### Option A: Environment Variable (Recommended)
```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, or ~/.bash_profile)
export NVIDIA_API_KEY="nvapi-your-key-here"

# Reload your shell
source ~/.zshrc  # or ~/.bashrc
```

### Option B: .env File
```bash
# Create .env file in project root
cd /Users/tdyar/ws/FHIR-AI-Hackathon-Kit
echo 'NVIDIA_API_KEY="nvapi-your-key-here"' > .env

# Add .env to .gitignore
echo ".env" >> .gitignore
```

### Option C: Temporary (for testing)
```bash
# Set for current terminal session only
export NVIDIA_API_KEY="nvapi-your-key-here"
```

## Step 3: Test Your API Key

### Test with curl
```bash
curl https://integrate.api.nvidia.com/v1/embeddings \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "What are the symptoms of hypertension?",
    "model": "nvidia/nv-embedqa-e5-v5",
    "input_type": "query"
  }'
```

### Expected Response
You should see a JSON response with embeddings:
```json
{
  "object": "list",
  "data": [
    {
      "index": 0,
      "embedding": [0.123, -0.456, 0.789, ...],
      "object": "embedding"
    }
  ],
  "model": "nvidia/nv-embedqa-e5-v5",
  "usage": {
    "prompt_tokens": 8,
    "total_tokens": 8
  }
}
```

### Test with Python
```python
import os

# Load API key
api_key = os.environ.get('NVIDIA_API_KEY')
if api_key:
    print(f"✅ API key loaded: {api_key[:10]}...")
else:
    print("❌ API key not found!")
```

## Step 4: Install Required Package

```bash
pip install langchain-nvidia-ai-endpoints
```

## Step 5: Test NIM Embeddings

```python
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
import os

# Initialize embeddings
embeddings = NVIDIAEmbeddings(
    model="nvidia/nv-embedqa-e5-v5",
    api_key=os.environ.get('NVIDIA_API_KEY')
)

# Test embedding
test_query = "chest pain and shortness of breath"
vector = embeddings.embed_query(test_query)

print(f"✅ Embedding generated!")
print(f"Dimensions: {len(vector)}")
print(f"First 5 values: {vector[:5]}")
```

Expected output:
```
✅ Embedding generated!
Dimensions: 1024
First 5 values: [0.123, -0.456, 0.789, -0.234, 0.567]
```

## Troubleshooting

### Error: "Unauthorized" or "Invalid API Key"
- Double-check your API key is correct
- Make sure there are no extra spaces or quotes
- Verify the key is active on build.nvidia.com

### Error: "API key not found"
- Check environment variable: `echo $NVIDIA_API_KEY`
- Reload shell after setting: `source ~/.zshrc`
- Try restarting your terminal

### Error: "Model not found"
- Check model name is exactly: `nvidia/nv-embedqa-e5-v5`
- Visit build.nvidia.com to see available models

### Rate Limits
- Free tier has rate limits
- Check build.nvidia.com for current limits
- Consider upgrading for production use

## Available NIM Embedding Models

### For FHIR Text Embeddings (Recommended)
- **nvidia/nv-embedqa-e5-v5**: 1024-dim, Q&A optimized
- **nvidia/nv-embedqa-mistral-7b-v2**: 4096-dim, complex medical text

### Model Selection Guide
- **Clinical notes, symptoms, short queries**: Use NV-EmbedQA-E5-v5 (1024-dim)
- **Long radiology reports, complex documents**: Use NV-EmbedQA-Mistral7B-v2 (4096-dim)

## Security Best Practices

1. **Never commit API keys to git**
   - Use .env file and add to .gitignore
   - Use environment variables

2. **Rotate keys periodically**
   - Generate new keys every 90 days
   - Revoke old keys on build.nvidia.com

3. **Use separate keys for dev/prod**
   - Development: One key for testing
   - Production: Separate key with monitoring

## Next Steps

Once your API key is working:
1. ✅ Proceed with NIM text embeddings integration
2. Create vector table for 1024-dimensional embeddings
3. Re-vectorize existing DocumentReference resources
4. Test query performance vs. SentenceTransformer baseline

## Resources

- NVIDIA Build: https://build.nvidia.com
- NIM Documentation: https://docs.nvidia.com/nim/
- LangChain Integration: https://python.langchain.com/docs/integrations/text_embedding/nvidia_ai_endpoints
