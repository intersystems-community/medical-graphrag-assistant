#!/bin/bash
# Deploy Streamlit on AWS (Option A: Everything on AWS)

set -e

SSH_KEY="$HOME/.ssh/medical-graphrag-key.pem"
AWS_HOST="ubuntu@3.84.250.46"
AWS_IP="3.84.250.46"

echo "=========================================="
echo "Deploying Streamlit on AWS"
echo "=========================================="

echo ""
echo "[1/3] Uploading Streamlit app and dependencies..."
scp -i "$SSH_KEY" -r mcp-server "$AWS_HOST:~/medical-graphrag/"

echo ""
echo "[2/3] Installing Streamlit dependencies on AWS..."
ssh -i "$SSH_KEY" "$AWS_HOST" << 'EOF'
cd ~/medical-graphrag
source venv/bin/activate
pip install streamlit plotly pydicom pillow
EOF

echo ""
echo "[3/3] Starting Streamlit on AWS..."
ssh -i "$SSH_KEY" "$AWS_HOST" << 'EOF'
cd ~/medical-graphrag/mcp-server
source ../venv/bin/activate

# Kill any existing Streamlit process
pkill -f "streamlit run" || true

# Start Streamlit in background
nohup streamlit run streamlit_app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  > ../streamlit.log 2>&1 &

echo "✓ Streamlit started in background"
echo "Logs: ~/medical-graphrag/streamlit.log"
EOF

echo ""
echo "=========================================="
echo "✅ Streamlit Deployed on AWS!"
echo "=========================================="
echo ""
echo "Access at: http://${AWS_IP}:8501"
echo ""
echo "⚠️  IMPORTANT: Configure AWS Security Group"
echo "   1. Go to AWS Console → EC2 → Security Groups"
echo "   2. Find security group for instance i-0432eba10b98c4949"
echo "   3. Add inbound rule:"
echo "      - Type: Custom TCP"
echo "      - Port: 8501"
echo "      - Source: 0.0.0.0/0 (or your IP for security)"
echo ""
echo "Logs: ssh -i $SSH_KEY $AWS_HOST 'tail -f ~/medical-graphrag/streamlit.log'"
echo "Stop: ssh -i $SSH_KEY $AWS_HOST 'pkill -f streamlit'"
