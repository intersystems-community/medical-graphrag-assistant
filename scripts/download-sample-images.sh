#!/bin/bash
# Download sample MIMIC-CXR DICOM images for testing
# Requires PhysioNet credentials

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGES_DIR="$REPO_ROOT/tests/fixtures/sample_medical_images"

# Check for physionet credentials
if [ -z "$PHYSIONET_USER" ] || [ -z "$PHYSIONET_PASS" ]; then
    echo "Set PHYSIONET_USER and PHYSIONET_PASS environment variables"
    echo "Register at https://physionet.org/ and get MIMIC-CXR access"
    exit 1
fi

mkdir -p "$IMAGES_DIR"

# Sample image IDs from MIMIC-CXR (known good chest X-rays)
# These are example paths - adjust based on actual PhysioNet access
SAMPLE_IMAGES=(
    "p10/p10000032/s50414267/02aa804e-bde0afdd-112c0b34-7bc16630-4e384014.dcm"
    "p10/p10000032/s53189527/2a2277a9-b0ded155-c0de8eb9-c124d10e-82c5caab.dcm"
    "p10/p10000764/s57375967/5a570b6f-2ee6d914-cb5135a9-5e5f9ca4-80f0c40d.dcm"
)

BASE_URL="https://physionet.org/files/mimic-cxr/2.1.0/files"

echo "Downloading sample DICOM images..."
cd "$IMAGES_DIR"

for img_path in "${SAMPLE_IMAGES[@]}"; do
    filename=$(basename "$img_path")
    if [ ! -f "$filename" ]; then
        echo "Downloading $filename..."
        wget --user="$PHYSIONET_USER" --password="$PHYSIONET_PASS" \
            -q -O "$filename" "$BASE_URL/$img_path" || echo "Failed: $img_path"
    else
        echo "Already have $filename"
    fi
done

echo "Downloaded $(ls -1 *.dcm 2>/dev/null | wc -l) DICOM files to $IMAGES_DIR"

# Also sync from S3 if available
if aws s3 ls s3://medical-graphrag-backup/medical-images/ &>/dev/null; then
    echo "Syncing additional images from S3 backup..."
    aws s3 sync s3://medical-graphrag-backup/medical-images/ "$IMAGES_DIR/" --exclude "*" --include "*.dcm"
fi

echo "Done!"
