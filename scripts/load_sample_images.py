#!/usr/bin/env python3
"""
Load sample medical images into IRIS database for testing.

This script:
1. Reads DICOM files from test fixtures
2. Generates NV-CLIP embeddings (or mock embeddings if NV-CLIP unavailable)
3. Stores image metadata and vectors in MedicalImageVectors table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path
import json

from src.db.connection import get_connection

# Try to import DICOM and image processing
try:
    import pydicom
    from PIL import Image
    import numpy as np
    DICOM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: {e}")
    DICOM_AVAILABLE = False

# Try to import NV-CLIP
try:
    from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings
    NVCLIP_AVAILABLE = True
except ImportError as e:
    print(f"Warning: NV-CLIP not available: {e}")
    NVCLIP_AVAILABLE = False


def process_dicom(dicom_path):
    """Extract image from DICOM file."""
    if not DICOM_AVAILABLE:
        return None

    try:
        dcm = pydicom.dcmread(dicom_path)

        # Get pixel array
        pixel_array = dcm.pixel_array

        # Normalize to 0-255
        if pixel_array.max() > 0:
            pixel_array = ((pixel_array - pixel_array.min()) /
                          (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)

        # Convert to PIL Image
        image = Image.fromarray(pixel_array)

        # Convert to RGB if grayscale
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Resize to reasonable size (224x224 is common for vision models)
        image = image.resize((224, 224))

        return image
    except Exception as e:
        print(f"Error processing DICOM {dicom_path}: {e}")
        return None


def generate_embedding(image, embedder):
    """Generate embedding for image."""
    if embedder and image:
        try:
            # NV-CLIP expects PIL Image
            embedding = embedder.embed_image(image)
            return embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")

    # Return mock embedding if NV-CLIP unavailable
    print("Using mock embedding (NV-CLIP not available)")
    return [0.1] * 1024  # 1024-dimensional mock embedding (matches table schema)


def load_images(limit=10):
    """Load sample images into database."""
    fixtures_dir = Path("tests/fixtures/sample_medical_images")

    if not fixtures_dir.exists():
        print(f"Error: {fixtures_dir} not found")
        return

    # Get DICOM files
    dicom_files = list(fixtures_dir.glob("*.dcm"))[:limit]

    if not dicom_files:
        print("No DICOM files found")
        return

    print(f"Found {len(dicom_files)} DICOM files")

    # Initialize embedder if available
    embedder = None
    if NVCLIP_AVAILABLE:
        try:
            embedder = NVCLIPEmbeddings()
            print("✓ NV-CLIP embedder initialized")
        except Exception as e:
            print(f"Could not initialize NV-CLIP: {e}")

    # Connect to database
    conn = get_connection()
    cursor = conn.cursor()

    print(f"\nLoading {len(dicom_files)} images into database...")

    loaded = 0
    for i, dicom_file in enumerate(dicom_files, 1):
        image_id = dicom_file.stem  # Use filename without extension

        # Check if already loaded
        cursor.execute(
            "SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages WHERE ImageID = ?",
            (image_id,)
        )
        if cursor.fetchone()[0] > 0:
            print(f"  {i}/{len(dicom_files)}: {image_id} - already exists, skipping")
            continue

        # Process DICOM
        image = process_dicom(dicom_file) if DICOM_AVAILABLE else None

        if image is None and not DICOM_AVAILABLE:
            pass
        elif image is None:
            print(f"  {i}/{len(dicom_files)}: {image_id} - could not process, skipping")
            continue

        # Generate embedding
        embedding = generate_embedding(image, embedder)

        # Store in database
        try:
            # Convert embedding to VECTOR format: "[0.1,0.2,0.3,...]"
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"

            cursor.execute("""
                INSERT INTO VectorSearch.MIMICCXRImages
                (ImageID, PatientID, StudyType, ImagePath, Embedding, CreatedAt, UpdatedAt)
                VALUES (?, ?, ?, ?, TO_VECTOR(?, DOUBLE), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                image_id,
                "P10000000",  # Mock patient ID
                "Chest X-ray",
                str(dicom_file),
                embedding_str
            ))

            conn.commit()
            loaded += 1
            print(f"  {i}/{len(dicom_files)}: {image_id} - ✓ loaded")
        except Exception as e:
            print(f"  {i}/{len(dicom_files)}: {image_id} - error: {e}")
            conn.rollback()

    cursor.close()
    conn.close()

    print(f"\nDone! Loaded {loaded} images")
    print(f"\nVerify with:")
    print(f"  python check_image_tables.py")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Load sample medical images")
    parser.add_argument("--limit", type=int, default=10, help="Number of images to load")
    args = parser.parse_args()

    load_images(limit=args.limit)
