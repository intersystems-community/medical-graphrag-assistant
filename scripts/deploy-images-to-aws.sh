#!/bin/bash
# Deploy sample medical images to AWS and ingest them

set -e  # Exit on error

echo "========================================="
echo "Deploy Sample Medical Images to AWS"
echo "========================================="
echo ""

# Configuration
AWS_HOST="ubuntu@3.84.250.46"
SSH_KEY="$HOME/.ssh/medical-graphrag-key.pem"
PROJECT_DIR="medical-graphrag"
SAMPLE_IMAGES_DIR="tests/fixtures/sample_medical_images"

# Step 1: Copy sample images directory to AWS
echo "Step 1: Copying sample images to AWS..."
rsync -avz -e "ssh -i $SSH_KEY" \
  --exclude="._*" \
  --exclude=".DS_Store" \
  "$SAMPLE_IMAGES_DIR/" \
  "$AWS_HOST:~/$PROJECT_DIR/$SAMPLE_IMAGES_DIR/"

echo "✅ Images copied to AWS"
echo ""

# Step 2: Run ingestion on AWS
echo "Step 2: Ingesting images with NV-CLIP embeddings..."
ssh -i "$SSH_KEY" "$AWS_HOST" "cd $PROJECT_DIR && source venv/bin/activate && python ingest_mimic_images.py $SAMPLE_IMAGES_DIR --limit 50"

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "Verification:"
echo "  ssh -i $SSH_KEY $AWS_HOST"
echo "  cd $PROJECT_DIR && source venv/bin/activate"
echo "  python -c \"from src.db.connection import get_connection; conn = get_connection(); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages'); print(f'Total images: {cursor.fetchone()[0]}')\""
echo ""
