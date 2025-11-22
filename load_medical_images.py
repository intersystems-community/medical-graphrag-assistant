#!/usr/bin/env python3
"""
Load medical images from MIMIC-CXR with real NV-CLIP embeddings from local NIM.
"""

import sys
import os
import glob
from pathlib import Path

sys.path.insert(0, '.')

from src.db.connection import get_connection
from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings

def extract_metadata_from_path(filepath: str):
    """Extract patient ID and study ID from MIMIC-CXR DICOM path."""
    # Example path: p10045779/s53819164/4b369dbe-417168fa-7e2b5f04-00582488-c50504e7.dcm
    parts = Path(filepath).parts

    if len(parts) >= 3:
        patient_id = parts[-3]  # p10045779
        study_id = parts[-2]    # s53819164
        dicom_id = Path(parts[-1]).stem  # filename without extension
    else:
        patient_id = "UNKNOWN"
        study_id = "UNKNOWN"
        dicom_id = Path(filepath).stem

    return patient_id, study_id, dicom_id

def load_images(image_dir: str = "medical_images", limit: int = None):
    """Load medical images with NV-CLIP embeddings."""

    print('='*60)
    print('Loading Medical Images with NV-CLIP NIM Embeddings')
    print('='*60)

    # Initialize embedder
    print('\n[1/4] Initializing NV-CLIP NIM embedder...')
    embedder = NVCLIPEmbeddings()
    print('✓ Connected to NIM at http://localhost:8002/v1')

    # Find DICOM files
    print(f'\n[2/4] Scanning {image_dir}/ for DICOM files...')
    dicom_files = glob.glob(os.path.join(image_dir, "*.dcm"))

    if not dicom_files:
        print(f'❌ No DICOM files found in {image_dir}/')
        return

    if limit:
        dicom_files = dicom_files[:limit]

    print(f'✓ Found {len(dicom_files)} DICOM files')

    # Connect to database
    print('\n[3/4] Connecting to IRIS database...')
    conn = get_connection()
    cursor = conn.cursor()
    print('✓ Connected to IRIS on localhost:1972/USER')

    # Load images
    print(f'\n[4/4] Loading {len(dicom_files)} images with embeddings...')
    print('-'*60)

    loaded_count = 0
    for idx, dicom_path in enumerate(dicom_files, 1):
        try:
            # Extract metadata
            patient_id, study_id, dicom_id = extract_metadata_from_path(dicom_path)
            image_id = f"{patient_id}_{study_id}_{dicom_id}"

            print(f'\n[{idx}/{len(dicom_files)}] Processing {os.path.basename(dicom_path)}')
            print(f'  Patient: {patient_id}, Study: {study_id}')

            # Generate embedding from image file
            print('  Generating NV-CLIP embedding...')
            embedding = embedder.embed_image(dicom_path)
            print(f'  ✓ Generated {len(embedding)}-dim embedding')
            print(f'  Sample: {embedding[:3]}')

            # Insert into database
            embedding_str = '[' + ','.join(map(str, embedding)) + ']'

            cursor.execute("""
                INSERT INTO SQLUser.MedicalImageVectors
                (ImageID, PatientID, StudyType, ImagePath, Embedding, CreatedAt, UpdatedAt)
                VALUES (?, ?, ?, ?, TO_VECTOR(?, DOUBLE), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                image_id,
                patient_id,
                'Chest X-ray',  # MIMIC-CXR is all chest X-rays
                dicom_path,
                embedding_str
            ))

            conn.commit()
            loaded_count += 1
            print(f'  ✓ Inserted {image_id}')

        except Exception as e:
            print(f'  ❌ Error: {e}')
            continue

    # Verify
    print('\n' + '='*60)
    cursor.execute("SELECT COUNT(*) FROM SQLUser.MedicalImageVectors")
    total_count = cursor.fetchone()[0]

    print(f'✓ Successfully loaded {loaded_count}/{len(dicom_files)} images')
    print(f'✓ Total images in database: {total_count}')
    print('='*60)

    cursor.close()
    conn.close()

    print('\n✅ Medical images loaded successfully!')
    print('\nNext steps:')
    print('  1. Test search: python test_image_search.py')
    print('  2. Deploy Streamlit: cd mcp-server && streamlit run streamlit_app.py --server.port 8501')

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Load medical images with NV-CLIP embeddings')
    parser.add_argument('--image-dir', default='medical_images', help='Directory containing DICOM files')
    parser.add_argument('--limit', type=int, help='Limit number of images to load')

    args = parser.parse_args()

    load_images(args.image_dir, args.limit)
