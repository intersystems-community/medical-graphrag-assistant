#!/usr/bin/env python3
"""
Ingest MIMIC-CXR Images into IRIS (VectorSearch.MIMICCXRImages)

Loads DICOM chest X-rays with NV-CLIP embeddings for semantic search.
Supports both local testing (mock embeddings) and production (real NV-CLIP).
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional, List, Dict

# Add project root to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.db.connection import get_connection

# Try to import NV-CLIP embeddings
try:
    from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings
    NVCLIP_AVAILABLE = True
except ImportError:
    NVCLIP_AVAILABLE = False
    print("Warning: NV-CLIP not available, will use mock embeddings", file=sys.stderr)


def get_embedder():
    """Get NV-CLIP embedder or None if unavailable."""
    if not NVCLIP_AVAILABLE:
        return None

    try:
        return NVCLIPEmbeddings()
    except Exception as e:
        print(f"Warning: Could not initialize NV-CLIP: {e}", file=sys.stderr)
        return None


def find_dicom_files(base_path: str, limit: Optional[int] = None) -> List[Path]:
    """
    Find DICOM files in MIMIC-CXR directory structure.

    MIMIC-CXR structure:
      files/pXX/pXXXXXXXX/sXXXXXXXX/*.dcm

    Args:
        base_path: Root path to MIMIC-CXR files
        limit: Optional limit on number of files to return

    Returns:
        List of Path objects to DICOM files
    """
    base = Path(base_path)
    if not base.exists():
        raise FileNotFoundError(f"MIMIC-CXR path not found: {base_path}")

    print(f"📂 Scanning for DICOM files in {base_path}...")

    dicom_files = []
    for dcm_file in base.rglob("*.dcm"):
        dicom_files.append(dcm_file)
        if limit and len(dicom_files) >= limit:
            break

    print(f"Found {len(dicom_files)} DICOM files")
    return dicom_files


def extract_metadata_from_path(dcm_path: Path) -> Dict:
    """
    Extract patient, study, and image IDs from MIMIC-CXR file path.

    Path format: .../pXX/pXXXXXXXX/sXXXXXXXX/IMAGE_ID.dcm

    Args:
        dcm_path: Path to DICOM file

    Returns:
        Dictionary with subject_id, study_id, image_id
    """
    parts = dcm_path.parts

    # Find patient folder (pXXXXXXXX)
    patient_folder = None
    study_folder = None
    for i, part in enumerate(parts):
        if part.startswith('p') and len(part) == 9:  # pXXXXXXXX
            patient_folder = part
            # Study folder is next level down
            if i + 1 < len(parts) and parts[i + 1].startswith('s'):
                study_folder = parts[i + 1]
            break

    image_id = dcm_path.stem  # filename without .dcm

    return {
        'subject_id': patient_folder if patient_folder else 'unknown',
        'study_id': study_folder if study_folder else 'unknown',
        'image_id': image_id,
        'file_path': str(dcm_path)
    }


def load_dicom_metadata(dcm_path: Path) -> Optional[Dict]:
    """
    Load DICOM metadata including view position.

    Args:
        dcm_path: Path to DICOM file

    Returns:
        Dictionary with DICOM metadata, or None if unable to read
    """
    try:
        import pydicom
        dcm = pydicom.dcmread(str(dcm_path), stop_before_pixels=True)

        return {
            'view_position': getattr(dcm, 'ViewPosition', 'UNKNOWN'),
            'modality': getattr(dcm, 'Modality', 'CR'),
            'patient_id': getattr(dcm, 'PatientID', 'unknown'),
            'study_date': getattr(dcm, 'StudyDate', 'unknown'),
            'series_description': getattr(dcm, 'SeriesDescription', '')
        }
    except Exception as e:
        print(f"Warning: Could not read DICOM metadata from {dcm_path}: {e}", file=sys.stderr)
        return None


def ingest_image(cursor, conn, dcm_path: Path, embedder, dry_run: bool = False) -> bool:
    """
    Ingest a single DICOM image into IRIS.

    Args:
        cursor: IRIS database cursor
        conn: IRIS database connection
        dcm_path: Path to DICOM file
        embedder: NV-CLIP embedder (or None for mock)
        dry_run: If True, don't actually insert

    Returns:
        True if successful, False otherwise
    """
    # Extract path-based metadata
    path_meta = extract_metadata_from_path(dcm_path)
    image_id = path_meta['image_id']

    # Check if already exists
    cursor.execute("""
        SELECT ImageID FROM VectorSearch.MIMICCXRImages
        WHERE ImageID = ?
    """, (image_id,))

    if cursor.fetchone():
        return True  # Already exists, skip

    # Load DICOM metadata
    dicom_meta = load_dicom_metadata(dcm_path)
    view_position = dicom_meta['view_position'] if dicom_meta else 'UNKNOWN'

    # Generate embedding
    if embedder:
        try:
            # Use view position as text for embedding
            text = f"Chest X-ray {view_position} view"
            embedding = embedder.embed_text(text)
        except Exception as e:
            print(f"Warning: Embedding failed for {image_id}: {e}", file=sys.stderr)
            embedding = [0.0] * 1024
    else:
        # Mock embedding
        embedding = [0.0] * 1024

    # Prepare metadata JSON
    metadata = {
        'path_metadata': path_meta,
        'dicom_metadata': dicom_meta if dicom_meta else {},
        'embedding_source': 'nvclip' if embedder else 'mock'
    }
    metadata_str = json.dumps(metadata)

    if dry_run:
        print(f"[DRY RUN] Would insert: {image_id} ({view_position})")
        return True

    # Insert into database
    try:
        embedding_str = ','.join(map(str, embedding))

        cursor.execute("""
            INSERT INTO VectorSearch.MIMICCXRImages
            (ImageID, StudyID, SubjectID, ViewPosition, ImagePath, Vector, Metadata)
            VALUES (?, ?, ?, ?, ?, TO_VECTOR(?, DOUBLE), ?)
        """, (
            image_id,
            path_meta['study_id'],
            path_meta['subject_id'],
            view_position,
            path_meta['file_path'],
            embedding_str,
            metadata_str
        ))

        conn.commit()
        return True

    except Exception as e:
        print(f"Error inserting {image_id}: {e}", file=sys.stderr)
        conn.rollback()
        return False


def ingest_mimic_images(
    mimic_path: str,
    limit: Optional[int] = None,
    dry_run: bool = False,
    batch_size: int = 100
):
    """
    Ingest MIMIC-CXR images into IRIS.

    Args:
        mimic_path: Path to MIMIC-CXR files directory
        limit: Optional limit on number of images
        dry_run: If True, don't actually insert
        batch_size: Commit after this many inserts
    """
    print("="*60)
    print("MIMIC-CXR Image Ingestion")
    print("="*60)
    print(f"MIMIC path: {mimic_path}")
    print(f"Limit: {limit if limit else 'None (all files)'}")
    print(f"Dry run: {dry_run}")
    print()

    # Initialize embedder
    embedder = get_embedder()
    if embedder:
        print("✅ NV-CLIP embedder initialized")
    else:
        print("⚠️  Using mock embeddings (NV-CLIP not available)")
    print()

    # Find DICOM files
    dicom_files = find_dicom_files(mimic_path, limit)
    if not dicom_files:
        print("❌ No DICOM files found")
        return

    # Connect to database
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Process files
        print(f"Loading {len(dicom_files)} images into database...")
        print()

        success_count = 0
        skip_count = 0
        error_count = 0
        start_time = time.time()

        for i, dcm_path in enumerate(dicom_files, 1):
            try:
                # Check if exists first
                path_meta = extract_metadata_from_path(dcm_path)
                cursor.execute("""
                    SELECT ImageID FROM VectorSearch.MIMICCXRImages
                    WHERE ImageID = ?
                """, (path_meta['image_id'],))

                if cursor.fetchone():
                    skip_count += 1
                    if i % 100 == 0:
                        print(f"  {i}/{len(dicom_files)}: Skipped {skip_count}, Added {success_count}, Errors {error_count}")
                    continue

                success = ingest_image(cursor, conn, dcm_path, embedder, dry_run)

                if success:
                    success_count += 1
                else:
                    error_count += 1

                # Progress update
                if i % 100 == 0 or i == len(dicom_files):
                    elapsed = time.time() - start_time
                    rate = i / elapsed if elapsed > 0 else 0
                    print(f"  {i}/{len(dicom_files)}: Skipped {skip_count}, Added {success_count}, Errors {error_count} ({rate:.1f} img/sec)")

                # Batch commit
                if not dry_run and i % batch_size == 0:
                    conn.commit()

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user")
                break
            except Exception as e:
                print(f"Error processing {dcm_path}: {e}")
                error_count += 1

        # Final commit
        if not dry_run:
            conn.commit()

        # Summary
        elapsed = time.time() - start_time
        print()
        print("="*60)
        print("Ingestion Complete!")
        print("="*60)
        print(f"Time elapsed: {elapsed:.1f} seconds")
        print(f"Images processed: {len(dicom_files)}")
        print(f"  - Skipped (already exist): {skip_count}")
        print(f"  - Successfully added: {success_count}")
        print(f"  - Errors: {error_count}")
        print()

        # Verify
        cursor.execute("SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages")
        total_count = cursor.fetchone()[0]
        print(f"Total images in database: {total_count}")

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Ingest MIMIC-CXR images into IRIS')
    parser.add_argument('mimic_path', help='Path to MIMIC-CXR files directory')
    parser.add_argument('--limit', type=int, help='Limit number of images to ingest')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (don\'t actually insert)')
    parser.add_argument('--batch-size', type=int, default=100, help='Commit batch size')

    args = parser.parse_args()

    ingest_mimic_images(
        mimic_path=args.mimic_path,
        limit=args.limit,
        dry_run=args.dry_run,
        batch_size=args.batch_size
    )
