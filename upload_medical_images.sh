#!/bin/bash
# Upload medical images from MIMIC-CXR to AWS instance

set -e

SSH_KEY="$HOME/.ssh/medical-graphrag-key.pem"
AWS_HOST="ubuntu@3.84.250.46"
REMOTE_DIR="~/medical-graphrag/medical_images"

echo "Creating remote directory..."
ssh -i "$SSH_KEY" "$AWS_HOST" "mkdir -p $REMOTE_DIR"

echo "Uploading medical images..."
# Upload 10 actual DICOM files from MIMIC-CXR
cd /Users/tdyar/ws/mimic-cxr/physionet.org/files/mimic-cxr/2.1.0/files/p10

# Select 10 diverse DICOM files
FILES=(
    "p10045779/s53819164/4b369dbe-417168fa-7e2b5f04-00582488-c50504e7.dcm"
    "p10045779/s53819164/32a919a5-177105fa-d113450c-ed8c1c53-fd2ce938.dcm"
    "p10433353/s50527707/48b7ea9c-c1610133-64303c6f-4f6dfe6c-805036e8.dcm"
    "p10433353/s50527707/05ab9148-1a6bb5ef-626e3db3-dd7b0aec-9d1abdb0.dcm"
    "p10179495/s57176651/8640649e-a6a3ae17-6f9c2091-560aef6e-9c1f19c7.dcm"
    "p10179495/s55684258/c83d574a-ee2648b7-6004580c-b4defcb1-f6bbd6a3.dcm"
    "p10444201/s52020223/1c3c26b3-63530c3b-ac088315-0bb93b3c-7c1aaa4f.dcm"
    "p10352385/s58614268/a36d7a92-b9cec968-223c4216-b2cc6ce9-d8943bec.dcm"
    "p10269842/s55419907/0a146a0f-2f0a7735-ff1f4b0e-63ccce6a-4b985c11.dcm"
    "p10269842/s58807489/9918ebd2-a55105d8-c8544298-c3e1794a-9e9896fa.dcm"
)

for file in "${FILES[@]}"; do
    echo "  Uploading $file..."
    scp -i "$SSH_KEY" "$file" "$AWS_HOST:$REMOTE_DIR/" 2>/dev/null
done

echo "✓ Uploaded ${#FILES[@]} medical images"
echo ""
echo "Next steps:"
echo "  1. SSH to AWS: ssh -i $SSH_KEY $AWS_HOST"
echo "  2. Load images: cd ~/medical-graphrag && python load_medical_images.py"
