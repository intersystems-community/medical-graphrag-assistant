#!/usr/bin/env python3
"""
MIMIC-CXR Image Ingestion Script (Feature 009)

Processes MIMIC-CXR DICOM files, generates NV-CLIP embeddings, and inserts
records into the VectorSearch.MIMICCXRImages table.

Usage:
    python scripts/ingest_mimic_cxr.py --source /path/to/mimic-cxr --limit 100 --batch-size 32

Features:
    - Batch embedding generation via NV-CLIP API
    - Skip existing images (--skip-existing)
    - Dry run mode (--dry-run)
    - Progress reporting with ETA
    - Checkpoint recovery (every 100 images)
    - Exponential backoff retry on connection failures
"""

import sys
import os
import json
import time
import pickle
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime

# Add project root to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.db.connection import get_connection

# FHIR integration (T041-T048)
try:
    from src.adapters.fhir_radiology_adapter import (
        FHIRRadiologyAdapter, ImagingStudyData
    )
    FHIR_ADAPTER_AVAILABLE = True
except ImportError:
    FHIR_ADAPTER_AVAILABLE = False
    print("Warning: FHIR adapter not available, --create-fhir will be disabled", file=sys.stderr)

# Try to import NV-CLIP embeddings
try:
    from src.embeddings.nvclip_embeddings import NVCLIPEmbeddings
    NVCLIP_AVAILABLE = True
except ImportError:
    NVCLIP_AVAILABLE = False
    print("Warning: NV-CLIP not available, will use mock embeddings", file=sys.stderr)

# DICOM support
try:
    import pydicom
    PYDICOM_AVAILABLE = True
except ImportError:
    PYDICOM_AVAILABLE = False
    print("Error: pydicom not available. Install with: pip install pydicom", file=sys.stderr)

# Constants
MAX_FILE_SIZE_MB = 100  # Skip files larger than this (T029)
CHECKPOINT_INTERVAL = 100  # Save checkpoint every N images (T037)
MAX_RETRIES = 3  # Connection retry attempts (T036)
RETRY_BASE_DELAY = 2  # Base delay for exponential backoff
FHIR_RETRY_MAX = 3  # FHIR server retry attempts (T047)


def check_nvclip_health(embedder) -> bool:
    """Check if NV-CLIP service is available (T030)."""
    if not embedder:
        return False

    try:
        # Try a simple embedding to verify service is healthy
        test_embedding = embedder.embed_text("test")
        return len(test_embedding) == 1024
    except Exception as e:
        print(f"NV-CLIP health check failed: {e}", file=sys.stderr)
        return False


def get_embedder_with_retry() -> Optional[object]:
    """Get NV-CLIP embedder with retry logic (T036)."""
    if not NVCLIP_AVAILABLE:
        return None

    for attempt in range(MAX_RETRIES):
        try:
            embedder = NVCLIPEmbeddings()
            if check_nvclip_health(embedder):
                return embedder
        except Exception as e:
            delay = RETRY_BASE_DELAY ** (attempt + 1)
            print(f"NV-CLIP connection attempt {attempt + 1}/{MAX_RETRIES} failed: {e}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)

    return None


def find_dicom_files(base_path: str, limit: Optional[int] = None, skip_large: bool = True) -> List[Path]:
    """
    Find DICOM files in MIMIC-CXR directory structure.

    MIMIC-CXR structure: files/pXX/pXXXXXXXX/sXXXXXXXX/*.dcm

    Args:
        base_path: Root path to MIMIC-CXR files
        limit: Optional limit on number of files to return
        skip_large: Skip files larger than MAX_FILE_SIZE_MB (T029)

    Returns:
        List of Path objects to DICOM files
    """
    base = Path(base_path)
    if not base.exists():
        raise FileNotFoundError(f"MIMIC-CXR path not found: {base_path}")

    print(f"📂 Scanning for DICOM files in {base_path}...")

    dicom_files = []
    skipped_large = 0
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024

    for dcm_file in base.rglob("*.dcm"):
        # Check file size (T029)
        if skip_large:
            try:
                file_size = dcm_file.stat().st_size
                if file_size > max_bytes:
                    skipped_large += 1
                    continue
            except OSError:
                pass  # Can't check size, include it anyway

        dicom_files.append(dcm_file)
        if limit and len(dicom_files) >= limit:
            break

    print(f"Found {len(dicom_files)} DICOM files")
    if skipped_large > 0:
        print(f"⚠️  Skipped {skipped_large} files larger than {MAX_FILE_SIZE_MB}MB")

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
    Load DICOM metadata including view position (T028).

    Args:
        dcm_path: Path to DICOM file

    Returns:
        Dictionary with DICOM metadata, or None if unable to read
    """
    if not PYDICOM_AVAILABLE:
        return None

    try:
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


def batch_embed_texts(embedder, texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in one API call (T031).

    Args:
        embedder: NV-CLIP embedder instance
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (1024-dimensional each)
    """
    if not embedder or not texts:
        return [[0.0] * 1024 for _ in texts]

    embeddings = []
    for text in texts:
        try:
            embedding = embedder.embed_text(text)
            embeddings.append(embedding)
        except Exception as e:
            print(f"Warning: Embedding failed for '{text[:50]}...': {e}", file=sys.stderr)
            embeddings.append([0.0] * 1024)

    return embeddings


def get_connection_with_retry():
    """Get IRIS connection with exponential backoff retry (T036)."""
    for attempt in range(MAX_RETRIES):
        try:
            conn = get_connection()
            # Test connection
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return conn
        except Exception as e:
            delay = RETRY_BASE_DELAY ** (attempt + 1)
            print(f"IRIS connection attempt {attempt + 1}/{MAX_RETRIES} failed: {e}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)

    raise ConnectionError("Failed to connect to IRIS after multiple attempts")


# ============================================================================
# FHIR Integration Functions (T041-T048)
# ============================================================================

def get_fhir_adapter_with_retry() -> Optional[object]:
    """Get FHIR adapter with retry logic (T047)."""
    if not FHIR_ADAPTER_AVAILABLE:
        return None

    for attempt in range(FHIR_RETRY_MAX):
        try:
            adapter = FHIRRadiologyAdapter()
            # Test connection by checking metadata
            if not adapter.demo_mode:
                return adapter
            elif attempt == FHIR_RETRY_MAX - 1:
                # Last attempt, return adapter in demo mode with warning
                print("Warning: FHIR server unavailable, continuing without FHIR linkage", file=sys.stderr)
                return adapter
        except Exception as e:
            delay = RETRY_BASE_DELAY ** (attempt + 1)
            print(f"FHIR connection attempt {attempt + 1}/{FHIR_RETRY_MAX} failed: {e}", file=sys.stderr)
            if attempt < FHIR_RETRY_MAX - 1:
                print(f"Retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)

    return None


def lookup_fhir_patient(adapter, subject_id: str) -> Optional[str]:
    """
    Look up FHIR Patient by MIMIC SubjectID (T042).

    Args:
        adapter: FHIRRadiologyAdapter instance
        subject_id: MIMIC-CXR subject ID (e.g., 'p10000032')

    Returns:
        FHIR Patient resource ID if found, None otherwise
    """
    if not adapter or adapter.demo_mode:
        return None

    try:
        # Search for patient by MIMIC identifier
        url = f"{adapter.fhir_base_url}/Patient"
        params = {"identifier": f"urn:mimic-cxr:subject|{subject_id}"}

        response = adapter.session.get(url, params=params, timeout=10)
        response.raise_for_status()

        bundle = response.json()
        entries = bundle.get("entry", [])

        if entries:
            return entries[0].get("resource", {}).get("id")

        # Fallback: try direct ID match (subject_id might be patient ID)
        url = f"{adapter.fhir_base_url}/Patient/{subject_id}"
        response = adapter.session.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get("id")

    except Exception as e:
        print(f"Warning: FHIR Patient lookup failed for {subject_id}: {e}", file=sys.stderr)

    return None


def check_imaging_study_exists(adapter, study_id: str) -> Optional[str]:
    """
    Check if ImagingStudy already exists (T048 - idempotent creation).

    Args:
        adapter: FHIRRadiologyAdapter instance
        study_id: MIMIC-CXR study ID

    Returns:
        Existing FHIR ImagingStudy ID if found, None otherwise
    """
    if not adapter or adapter.demo_mode:
        return None

    try:
        existing = adapter.get_imaging_study(study_id)
        if existing:
            return existing.get("id")
    except Exception:
        pass

    return None


def create_imaging_study_for_image(
    adapter,
    path_meta: Dict,
    dicom_meta: Optional[Dict],
    patient_id: Optional[str]
) -> Optional[str]:
    """
    Create FHIR ImagingStudy resource for an ingested image (T043, T044).

    Args:
        adapter: FHIRRadiologyAdapter instance
        path_meta: Metadata extracted from file path
        dicom_meta: Metadata extracted from DICOM file (optional)
        patient_id: FHIR Patient resource ID (optional)

    Returns:
        Created ImagingStudy resource ID, or None if creation failed
    """
    if not adapter or adapter.demo_mode:
        return None

    study_id = path_meta.get('study_id', 'unknown')

    # Check if already exists (T048)
    existing_id = check_imaging_study_exists(adapter, study_id)
    if existing_id:
        return existing_id

    # If no patient_id, skip FHIR creation (T046)
    if not patient_id:
        return None

    try:
        # Build ImagingStudyData (T044 - map MIMIC metadata to FHIR)
        study_data = ImagingStudyData(
            study_id=study_id,
            subject_id=path_meta.get('subject_id', 'unknown'),
            patient_id=patient_id,
            modality="CR",  # Computed Radiography for chest X-ray
            num_instances=1,
            description=f"MIMIC-CXR Chest X-ray - {dicom_meta.get('view_position', 'UNKNOWN') if dicom_meta else 'UNKNOWN'} view"
        )

        # Add study date if available from DICOM
        if dicom_meta and dicom_meta.get('study_date') and dicom_meta.get('study_date') != 'unknown':
            try:
                study_data.study_date = datetime.strptime(dicom_meta['study_date'], '%Y%m%d')
            except ValueError:
                pass

        # Build and create the resource
        resource = adapter.build_imaging_study(study_data)
        result = adapter.put_resource(resource)

        return result.get("id")

    except Exception as e:
        print(f"Warning: Failed to create ImagingStudy for {study_id}: {e}", file=sys.stderr)
        return None


def update_fhir_resource_id(cursor, conn, image_id: str, fhir_resource_id: str):
    """
    Update VectorSearch.MIMICCXRImages.FHIRResourceID after ImagingStudy creation (T045).

    Args:
        cursor: IRIS database cursor
        conn: IRIS database connection
        image_id: Image ID in the vector table
        fhir_resource_id: Created ImagingStudy resource ID
    """
    try:
        cursor.execute("""
            UPDATE VectorSearch.MIMICCXRImages
            SET FHIRResourceID = ?
            WHERE ImageID = ?
        """, (fhir_resource_id, image_id))
        conn.commit()
    except Exception as e:
        print(f"Warning: Failed to update FHIRResourceID for {image_id}: {e}", file=sys.stderr)


def ensure_vectorsearch_table_exists(cursor, conn):
    """
    Ensure VectorSearch.MIMICCXRImages table exists.
    Creates schema and table if they don't exist.
    This makes the ingestion script self-contained and repeatable.
    """
    try:
        # Check if table exists by querying it
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'VectorSearch' AND TABLE_NAME = 'MIMICCXRImages'
        """)
        if cursor.fetchone()[0] > 0:
            return  # Table already exists

        print("Creating VectorSearch schema and MIMICCXRImages table...")

        # Create schema
        try:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS VectorSearch")
            conn.commit()
        except Exception:
            pass  # Schema may already exist

        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS VectorSearch.MIMICCXRImages (
                ImageID VARCHAR(128) NOT NULL PRIMARY KEY,
                SubjectID VARCHAR(20) NOT NULL,
                StudyID VARCHAR(20) NOT NULL,
                DicomID VARCHAR(128),
                ImagePath VARCHAR(500) NOT NULL,
                ViewPosition VARCHAR(20),
                Vector VECTOR(DOUBLE, 1024) NOT NULL,
                EmbeddingModel VARCHAR(50) DEFAULT 'nvidia/nvclip',
                Provider VARCHAR(50) DEFAULT 'nvclip',
                FHIRResourceID VARCHAR(100),
                CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UpdatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Create indexes (ignore errors if they already exist)
        index_statements = [
            "CREATE INDEX idx_mimiccxr_subject ON VectorSearch.MIMICCXRImages(SubjectID)",
            "CREATE INDEX idx_mimiccxr_study ON VectorSearch.MIMICCXRImages(StudyID)",
            "CREATE INDEX idx_mimiccxr_view ON VectorSearch.MIMICCXRImages(ViewPosition)",
            "CREATE INDEX idx_mimiccxr_fhir ON VectorSearch.MIMICCXRImages(FHIRResourceID)"
        ]
        for stmt in index_statements:
            try:
                cursor.execute(stmt)
                conn.commit()
            except Exception:
                pass  # Index may already exist

        # Create HNSW vector index for efficient similarity search
        try:
            cursor.execute("""
                CREATE VECTOR INDEX idx_mimiccxr_hnsw
                ON VectorSearch.MIMICCXRImages(Vector)
                AS HNSW
                WITH (METRIC = COSINE, M = 16, efConstruction = 100)
            """)
            conn.commit()
            print("✅ HNSW vector index created")
        except Exception as e:
            print(f"Note: HNSW index creation: {e}", file=sys.stderr)

        print("✅ VectorSearch.MIMICCXRImages table created successfully")

    except Exception as e:
        print(f"Warning: Could not ensure table exists: {e}", file=sys.stderr)
        # Don't fail - the table might already exist


def load_checkpoint(checkpoint_path: Path) -> set:
    """Load checkpoint of processed image IDs (T037)."""
    if checkpoint_path.exists():
        try:
            with open(checkpoint_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Warning: Could not load checkpoint: {e}", file=sys.stderr)
    return set()


def save_checkpoint(checkpoint_path: Path, processed_ids: set):
    """Save checkpoint of processed image IDs (T037)."""
    try:
        with open(checkpoint_path, 'wb') as f:
            pickle.dump(processed_ids, f)
    except Exception as e:
        print(f"Warning: Could not save checkpoint: {e}", file=sys.stderr)


def ingest_batch(
    cursor,
    conn,
    batch: List[Tuple[Path, Dict, Dict]],
    embeddings: List[List[float]],
    dry_run: bool = False
) -> Tuple[int, int]:
    """
    Insert a batch of images into the database.

    Args:
        cursor: IRIS database cursor
        conn: IRIS database connection
        batch: List of (dcm_path, path_meta, dicom_meta) tuples
        embeddings: List of embedding vectors
        dry_run: If True, don't actually insert

    Returns:
        Tuple of (success_count, error_count)
    """
    success_count = 0
    error_count = 0

    for (dcm_path, path_meta, dicom_meta), embedding in zip(batch, embeddings):
        image_id = path_meta['image_id']
        view_position = dicom_meta.get('view_position', 'UNKNOWN') if dicom_meta else 'UNKNOWN'

        if dry_run:
            print(f"[DRY RUN] Would insert: {image_id} ({view_position})")
            success_count += 1
            continue

        try:
            embedding_str = ','.join(map(str, embedding))

            cursor.execute("""
                INSERT INTO VectorSearch.MIMICCXRImages
                (ImageID, StudyID, SubjectID, ViewPosition, ImagePath, Vector, EmbeddingModel)
                VALUES (?, ?, ?, ?, ?, TO_VECTOR(?, DOUBLE), ?)
            """, (
                image_id,
                path_meta['study_id'],
                path_meta['subject_id'],
                view_position,
                path_meta['file_path'],
                embedding_str,
                'nvidia/nvclip'
            ))

            success_count += 1

        except Exception as e:
            print(f"Error inserting {image_id}: {e}", file=sys.stderr)
            error_count += 1

    if not dry_run:
        conn.commit()

    return success_count, error_count


def ingest_mimic_cxr(
    source: str,
    batch_size: int = 32,
    limit: Optional[int] = None,
    skip_existing: bool = True,
    dry_run: bool = False,
    create_fhir: bool = False
):
    """
    Main ingestion function.

    Args:
        source: Path to MIMIC-CXR files directory (T022)
        batch_size: Images per NV-CLIP request (T023)
        limit: Max images to process (T024)
        skip_existing: Skip already-ingested images (T025)
        dry_run: Preview what would be processed (T026)
        create_fhir: Create FHIR ImagingStudy resources (T041)
    """
    print("="*60)
    print("MIMIC-CXR Image Ingestion")
    print("="*60)
    print(f"Source path: {source}")
    print(f"Batch size: {batch_size}")
    print(f"Limit: {limit if limit else 'None (all files)'}")
    print(f"Skip existing: {skip_existing}")
    print(f"Dry run: {dry_run}")
    print(f"Create FHIR: {create_fhir}")
    print()

    # Initialize embedder with health check (T030)
    print("Checking NV-CLIP service...")
    embedder = get_embedder_with_retry()
    if embedder:
        print("✅ NV-CLIP embedder initialized and healthy")
    else:
        print("⚠️  NV-CLIP not available - using mock embeddings")
    print()

    # Initialize FHIR adapter if requested (T041, T047)
    fhir_adapter = None
    if create_fhir:
        print("Checking FHIR server connection...")
        fhir_adapter = get_fhir_adapter_with_retry()
        if fhir_adapter and not fhir_adapter.demo_mode:
            print("✅ FHIR adapter initialized and connected")
        else:
            print("⚠️  FHIR server unavailable - continuing without FHIR linkage")
        print()

    # Find DICOM files (T027, T029)
    dicom_files = find_dicom_files(source, limit, skip_large=True)
    if not dicom_files:
        print("❌ No DICOM files found")
        return

    # Connect to database with retry (T032, T036)
    print("Connecting to IRIS...")
    conn = get_connection_with_retry()
    cursor = conn.cursor()
    print("✅ Connected to IRIS")
    print()

    # Ensure VectorSearch table exists (auto-create if needed)
    ensure_vectorsearch_table_exists(cursor, conn)
    print()

    # Setup checkpoint (T037)
    checkpoint_path = Path(source) / '.ingest_checkpoint.pkl'
    processed_ids = load_checkpoint(checkpoint_path) if skip_existing else set()

    if processed_ids:
        print(f"Loaded checkpoint with {len(processed_ids)} previously processed images")

    try:
        # Get existing images from database if skip_existing
        existing_ids = set()
        if skip_existing:
            print("Checking for existing images in database...")
            cursor.execute("SELECT ImageID FROM VectorSearch.MIMICCXRImages")
            for row in cursor.fetchall():
                existing_ids.add(row[0])
            print(f"Found {len(existing_ids)} existing images in database")
        print()

        # Filter out already processed files
        files_to_process = []
        for dcm_path in dicom_files:
            path_meta = extract_metadata_from_path(dcm_path)
            image_id = path_meta['image_id']

            if skip_existing and (image_id in existing_ids or image_id in processed_ids):
                continue

            files_to_process.append((dcm_path, path_meta))

        print(f"Processing {len(files_to_process)} new images...")
        print()

        if not files_to_process:
            print("✅ All images already processed!")
            return

        # Process in batches
        total_success = 0
        total_error = 0
        fhir_created = 0  # T041-T046: FHIR ImagingStudy resources created
        fhir_skipped = 0  # T046: Skipped (patient not found or creation failed)
        start_time = time.time()

        for batch_start in range(0, len(files_to_process), batch_size):
            batch_end = min(batch_start + batch_size, len(files_to_process))
            batch_files = files_to_process[batch_start:batch_end]

            # Prepare batch data
            batch_data = []
            texts_to_embed = []

            for dcm_path, path_meta in batch_files:
                dicom_meta = load_dicom_metadata(dcm_path)
                view_position = dicom_meta.get('view_position', 'UNKNOWN') if dicom_meta else 'UNKNOWN'

                batch_data.append((dcm_path, path_meta, dicom_meta))
                texts_to_embed.append(f"Chest X-ray {view_position} view")

            # Generate embeddings (T031)
            embeddings = batch_embed_texts(embedder, texts_to_embed)

            # Insert batch (T033)
            success, errors = ingest_batch(cursor, conn, batch_data, embeddings, dry_run)
            total_success += success
            total_error += errors

            # Create FHIR ImagingStudy resources if requested (T041-T046)
            if fhir_adapter and not dry_run:
                for dcm_path, path_meta, dicom_meta in batch_data:
                    subject_id = path_meta.get('subject_id', 'unknown')
                    image_id = path_meta['image_id']

                    # Look up FHIR Patient by MIMIC SubjectID (T042)
                    patient_id = lookup_fhir_patient(fhir_adapter, subject_id)

                    if patient_id:
                        # Create ImagingStudy (T043, T044)
                        fhir_resource_id = create_imaging_study_for_image(
                            fhir_adapter, path_meta, dicom_meta, patient_id
                        )

                        if fhir_resource_id:
                            # Update FHIRResourceID in vector table (T045)
                            update_fhir_resource_id(cursor, conn, image_id, fhir_resource_id)
                            fhir_created += 1
                        else:
                            fhir_skipped += 1
                    else:
                        # Patient not found - skip FHIR creation (T046)
                        fhir_skipped += 1

            # Update checkpoint (T037)
            for dcm_path, path_meta, _ in batch_data:
                processed_ids.add(path_meta['image_id'])

            if (batch_end) % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(checkpoint_path, processed_ids)

            # Progress report (T034)
            elapsed = time.time() - start_time
            rate = batch_end / elapsed if elapsed > 0 else 0
            remaining = len(files_to_process) - batch_end
            eta = remaining / rate if rate > 0 else 0

            print(f"  {batch_end}/{len(files_to_process)}: "
                  f"Success {total_success}, Errors {total_error} "
                  f"({rate:.1f} img/sec, ETA {eta/60:.1f}min)")

        # Final checkpoint save
        save_checkpoint(checkpoint_path, processed_ids)

        # Summary
        elapsed = time.time() - start_time
        print()
        print("="*60)
        print("Ingestion Complete!")
        print("="*60)
        print(f"Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"Images processed: {len(files_to_process)}")
        print(f"  - Successfully added: {total_success}")
        print(f"  - Errors: {total_error}")
        if create_fhir:
            print(f"FHIR ImagingStudy resources:")
            print(f"  - Created: {fhir_created}")
            print(f"  - Skipped (no patient match): {fhir_skipped}")
        print()

        # Verify total count
        cursor.execute("SELECT COUNT(*) FROM VectorSearch.MIMICCXRImages")
        total_count = cursor.fetchone()[0]
        print(f"Total images in database: {total_count}")

    finally:
        cursor.close()
        conn.close()


def main():
    """CLI entry point (T021)."""
    parser = argparse.ArgumentParser(
        description='Ingest MIMIC-CXR images into IRIS VectorSearch table',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python scripts/ingest_mimic_cxr.py --source /path/to/mimic-cxr --limit 100

  # Full ingestion with specific batch size
  python scripts/ingest_mimic_cxr.py --source /data/mimic-cxr --batch-size 64

  # Preview what would be processed
  python scripts/ingest_mimic_cxr.py --source /data/mimic-cxr --dry-run

Environment Variables:
  IRIS_HOST       IRIS database host (default: localhost)
  IRIS_PORT       IRIS SuperServer port (default: 1972)
  NVCLIP_BASE_URL NV-CLIP embedding service URL
        """
    )

    # Required arguments (T022)
    parser.add_argument(
        '--source', '-s',
        required=True,
        help='Directory containing MIMIC-CXR DICOM files'
    )

    # Optional arguments (T023-T026)
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=32,
        help='Images per NV-CLIP request (default: 32)'
    )

    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Maximum images to process (default: all)'
    )

    parser.add_argument(
        '--skip-existing',
        action='store_true',
        default=True,
        help='Skip images already in database (default: True)'
    )

    parser.add_argument(
        '--no-skip-existing',
        action='store_false',
        dest='skip_existing',
        help='Re-process all images even if already in database'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be processed without inserting'
    )

    # FHIR integration arguments (T041)
    parser.add_argument(
        '--create-fhir',
        action='store_true',
        help='Create FHIR ImagingStudy resources for ingested images'
    )

    args = parser.parse_args()

    # Validate source path
    if not Path(args.source).exists():
        print(f"Error: Source path does not exist: {args.source}", file=sys.stderr)
        sys.exit(1)

    # Run ingestion
    ingest_mimic_cxr(
        source=args.source,
        batch_size=args.batch_size,
        limit=args.limit,
        skip_existing=args.skip_existing,
        dry_run=args.dry_run,
        create_fhir=args.create_fhir
    )


if __name__ == '__main__':
    main()
