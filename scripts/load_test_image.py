#!/usr/bin/env python3
"""Load a single test image into MedicalImageVectors"""

import sys
sys.path.insert(0, '.')

from src.db.connection import get_connection
from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings

print('=== Loading test image ===')

# Initialize embedder
try:
    embedder = NVCLIPEmbeddings()
    print('✓ NV-CLIP embedder initialized')
except Exception as e:
    print(f'✗ NV-CLIP failed: {e}')
    print('Using mock embeddings')
    embedder = None

# Generate embedding (for text query, not image)
test_query = 'chest x-ray'
if embedder:
    try:
        embedding = embedder.embed_text(test_query)
        print(f'✓ Generated {len(embedding)}-dim embedding')
    except Exception as e:
        print(f'✗ Embedding failed: {e}')
        embedding = [0.1] * 1024
else:
    embedding = [0.1] * 1024

# Insert into database
conn = get_connection()
cursor = conn.cursor()

image_id = 'TEST001'
patient_id = 'P10000000'
study_type = 'Chest X-ray PA'
image_path = 'test_dicom.png'

embedding_str = '[' + ','.join(map(str, embedding)) + ']'

try:
    cursor.execute("""
        INSERT INTO SQLUser.MedicalImageVectors
        (ImageID, PatientID, StudyType, ImagePath, Embedding, CreatedAt, UpdatedAt)
        VALUES (?, ?, ?, ?, TO_VECTOR(?, DOUBLE), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (image_id, patient_id, study_type, image_path, embedding_str))
    
    conn.commit()
    print(f'✓ Inserted test image: {image_id}')
    
except Exception as e:
    print(f'✗ Insert failed: {e}')
    conn.rollback()

# Verify
cursor.execute('SELECT COUNT(*) FROM SQLUser.MedicalImageVectors')
count = cursor.fetchone()[0]
print(f'\n✅ Total images in database: {count}')

cursor.close()
conn.close()
