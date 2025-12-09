#!/usr/bin/env python3
"""Load test image with NV-CLIP NIM embedding"""

import sys
sys.path.insert(0, '.')

from src.db.connection import get_connection
from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings

print('Initializing NV-CLIP NIM embedder...')
embedder = NVCLIPEmbeddings()

# Generate embedding for text (we don't have actual images on AWS yet)
print('\nGenerating text embedding for test...')
query = 'chest x-ray pa view'
embedding = embedder.embed_text(query)
print(f'✓ Generated {len(embedding)}-dim embedding')
print(f'Sample values: {embedding[:5]}')

# Insert into database
print('\nInserting into MedicalImageVectors...')
conn = get_connection()
cursor = conn.cursor()

image_id = 'TEST_NIM_001'
patient_id = 'P10000000'
study_type = 'Chest X-ray PA'
image_path = 'test_dicom.png'

embedding_str = '[' + ','.join(map(str, embedding)) + ']'

cursor.execute("""
    INSERT INTO SQLUser.MedicalImageVectors
    (ImageID, PatientID, StudyType, ImagePath, Embedding, CreatedAt, UpdatedAt)
    VALUES (?, ?, ?, ?, TO_VECTOR(?, DOUBLE), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
""", (image_id, patient_id, study_type, image_path, embedding_str))

conn.commit()
print(f'✓ Inserted {image_id}')

# Verify
cursor.execute("SELECT COUNT(*) FROM SQLUser.MedicalImageVectors")
count = cursor.fetchone()[0]
print(f'\n✓ Total images in database: {count}')

cursor.close()
conn.close()
print('\n✅ Test image loaded with NV-CLIP NIM embedding!')
