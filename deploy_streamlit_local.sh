#!/bin/bash
# Deploy Streamlit locally with SSH tunneling to AWS (Option B: Hybrid)

set -e

SSH_KEY="$HOME/.ssh/medical-graphrag-key.pem"
AWS_HOST="ubuntu@3.84.250.46"
LOCAL_PORT=8501

echo "=========================================="
echo "Deploying Streamlit Locally (Hybrid Mode)"
echo "=========================================="

echo ""
echo "[1/3] Creating SSH tunnels to AWS services..."
echo "  - Port 1972: IRIS Database"
echo "  - Port 8002: NV-CLIP NIM"

# Kill any existing SSH tunnels
pkill -f "ssh.*1972.*8002" || true

# Create SSH tunnel in background
ssh -i "$SSH_KEY" \
  -L 1972:localhost:1972 \
  -L 8002:localhost:8002 \
  -N -f \
  "$AWS_HOST"

echo "✓ SSH tunnels established"

echo ""
echo "[2/3] Checking local dependencies..."
pip show streamlit >/dev/null 2>&1 || pip install streamlit plotly pydicom pillow

echo ""
echo "[3/3] Starting Streamlit locally..."
cd mcp-server

# Kill any existing Streamlit
pkill -f "streamlit run" || true

# Start Streamlit
echo "✓ Streamlit starting on http://localhost:${LOCAL_PORT}"
echo ""
echo "=========================================="
echo "✅ Hybrid Deployment Active!"
echo "=========================================="
echo ""
echo "Architecture:"
echo "  Local:  Streamlit UI (port ${LOCAL_PORT})"
echo "  AWS:    IRIS Database (tunneled via port 1972)"
echo "  AWS:    NV-CLIP NIM (tunneled via port 8002)"
echo ""
echo "Access: http://localhost:${LOCAL_PORT}"
echo ""
echo "Press Ctrl+C to stop"
echo ""

streamlit run streamlit_app.py --server.port ${LOCAL_PORT}

# Cleanup on exit
echo ""
echo "Cleaning up SSH tunnels..."
pkill -f "ssh.*1972.*8002" || true
