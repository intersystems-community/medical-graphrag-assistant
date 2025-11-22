#!/usr/bin/env python3
"""
Medical Image Vectorization Pipeline

Vectorizes medical images (DICOM, PNG, JPG) using NVIDIA NIM Vision for
multi-modal RAG capabilities. Processes images in batches, generates embeddings,
and stores vectors in IRIS database.

Usage:
    python src/vectorization/image_vectorizer.py \\
        --input /path/to/images \\
        --batch-size 10 \\
        --format png,jpg

    python src/vectorization/image_vectorizer.py \\
        --input /path/to/dicom \\
        --format dicom \\
        --resume

Performance Target (SC-005): ≥0.5 images/second (<2 sec/image)

Features:
- Image validation (format, corruption, metadata extraction)
- Format conversion (DICOM → PNG if needed)
- Resizing and normalization
- Batch embedding generation via NIM Vision API
- Checkpoint-based resumability
- Progress tracking with throughput metrics
- Visual similarity search testing

Requirements:
- NVIDIA NIM Vision service running on localhost:8002
- IRIS database with MedicalImageVectors table
- Python packages: Pillow, pydicom, requests, intersystems-iris
"""

import argparse
import sys
import os
import json
import base64
import time
import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from io import BytesIO

# Image processing imports
try:
    from PIL import Image
except ImportError:
    print("Error: Pillow library not found. Install with: pip install Pillow")
    sys.exit(1)

try:
    import pydicom
    DICOM_AVAILABLE = True
except ImportError:
    DICOM_AVAILABLE = False
    print("Warning: pydicom not installed. DICOM support disabled.")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from vectorization.vector_db_client import IRISVectorDBClient
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ImageMetadata:
    """Metadata extracted from medical images."""

    def __init__(
        self,
        image_id: str,
        patient_id: str,
        study_type: str,
        file_path: str,
        format: str,
        width: int,
        height: int,
        related_report_id: Optional[str] = None
    ):
        self.image_id = image_id
        self.patient_id = patient_id
        self.study_type = study_type
        self.file_path = file_path
        self.format = format
        self.width = width
        self.height = height
        self.related_report_id = related_report_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "image_id": self.image_id,
            "patient_id": self.patient_id,
            "study_type": self.study_type,
            "image_path": self.file_path,
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "related_report_id": self.related_report_id
        }


class NIMVisionClient:
    """Client for NVIDIA NIM Vision embedding API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        model: str = "nv-clip-vit",
        timeout: int = 60
    ):
        """
        Initialize NIM Vision client.

        Args:
            base_url: NIM Vision service URL
            model: Vision model name
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.embeddings_url = f"{self.base_url}/v1/embeddings"
        self.health_url = f"{self.base_url}/health"
        self.model = model
        self.timeout = timeout

        logger.info(f"NIM Vision client initialized: {self.base_url}")

    def health_check(self) -> bool:
        """Check if NIM Vision service is healthy."""
        try:
            response = requests.get(self.health_url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"NIM Vision health check failed: {e}")
            return False

    def encode_image_base64(self, image: Image.Image) -> str:
        """
        Encode PIL Image to base64 string.

        Args:
            image: PIL Image object

        Returns:
            Base64-encoded image string
        """
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def embed_image(self, image: Image.Image) -> List[float]:
        """
        Generate embedding for a single image.

        Args:
            image: PIL Image object

        Returns:
            1024-dimensional embedding vector

        Raises:
            RuntimeError: If embedding generation fails
        """
        image_b64 = self.encode_image_base64(image)

        payload = {
            "input": image_b64,
            "model": self.model
        }

        try:
            response = requests.post(
                self.embeddings_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["data"][0]["embedding"]
            return embedding

        except requests.exceptions.Timeout:
            raise RuntimeError(f"NIM Vision request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Could not connect to NIM Vision at {self.base_url}")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"NIM Vision API error: {e}")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Invalid NIM Vision response format: {e}")

    def embed_batch(self, images: List[Image.Image]) -> List[List[float]]:
        """
        Generate embeddings for a batch of images.

        Args:
            images: List of PIL Image objects

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for image in images:
            embedding = self.embed_image(image)
            embeddings.append(embedding)
        return embeddings


class ImageValidator:
    """Validates and extracts metadata from medical images."""

    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.dcm', '.dicom'}

    def __init__(self, dicom_enabled: bool = True):
        """
        Initialize image validator.

        Args:
            dicom_enabled: Whether to enable DICOM support
        """
        self.dicom_enabled = dicom_enabled and DICOM_AVAILABLE

        if not self.dicom_enabled and dicom_enabled:
            logger.warning("DICOM support requested but pydicom not available")

    def is_valid_format(self, file_path: Path) -> bool:
        """Check if file has supported format."""
        return file_path.suffix.lower() in self.SUPPORTED_FORMATS

    def extract_metadata_from_dicom(self, file_path: Path) -> Optional[ImageMetadata]:
        """
        Extract metadata from DICOM file.

        Args:
            file_path: Path to DICOM file

        Returns:
            ImageMetadata object or None if extraction fails
        """
        if not self.dicom_enabled:
            return None

        try:
            ds = pydicom.dcmread(str(file_path))

            # Extract patient ID
            patient_id = str(getattr(ds, 'PatientID', file_path.stem))

            # Extract study information
            study_type = str(getattr(ds, 'StudyDescription', 'Unknown'))
            if not study_type or study_type == 'Unknown':
                study_type = str(getattr(ds, 'Modality', 'Unknown'))

            # Extract image dimensions
            width = int(getattr(ds, 'Columns', 0))
            height = int(getattr(ds, 'Rows', 0))

            # Generate image ID from file
            image_id = file_path.stem

            return ImageMetadata(
                image_id=image_id,
                patient_id=patient_id,
                study_type=study_type,
                file_path=str(file_path),
                format='DICOM',
                width=width,
                height=height
            )

        except Exception as e:
            logger.error(f"DICOM metadata extraction failed for {file_path}: {e}")
            return None

    def extract_metadata_from_filename(self, file_path: Path) -> ImageMetadata:
        """
        Extract metadata from filename convention.

        Expected formats:
        - patient123_chest_xray_001.png
        - p00001_study_lateral.jpg

        Args:
            file_path: Path to image file

        Returns:
            ImageMetadata object with inferred fields
        """
        # Parse filename
        parts = file_path.stem.split('_')

        # Try to extract patient ID (first part starting with 'p' or 'patient')
        patient_id = parts[0] if parts else file_path.stem
        if patient_id.startswith('patient'):
            patient_id = patient_id.replace('patient', 'p')

        # Try to extract study type (second part)
        study_type = parts[1] if len(parts) > 1 else 'Unknown'

        # Get image dimensions
        try:
            with Image.open(file_path) as img:
                width, height = img.size
        except Exception:
            width, height = 0, 0

        return ImageMetadata(
            image_id=file_path.stem,
            patient_id=patient_id,
            study_type=study_type,
            file_path=str(file_path),
            format=file_path.suffix[1:].upper(),
            width=width,
            height=height
        )

    def validate_and_extract(self, file_path: Path) -> Tuple[bool, Optional[ImageMetadata], Optional[str]]:
        """
        Validate image and extract metadata.

        Args:
            file_path: Path to image file

        Returns:
            Tuple of (is_valid, metadata, error_message)
        """
        # Check format
        if not self.is_valid_format(file_path):
            return False, None, f"Unsupported format: {file_path.suffix}"

        # Check file exists
        if not file_path.exists():
            return False, None, "File not found"

        # Check file is readable
        if not os.access(file_path, os.R_OK):
            return False, None, "File not readable"

        # Try to open and validate image
        try:
            if file_path.suffix.lower() in {'.dcm', '.dicom'}:
                # DICOM file
                if not self.dicom_enabled:
                    return False, None, "DICOM support not available"

                metadata = self.extract_metadata_from_dicom(file_path)
                if metadata is None:
                    return False, None, "DICOM metadata extraction failed"

                return True, metadata, None
            else:
                # Standard image format
                with Image.open(file_path) as img:
                    # Verify image is not corrupted
                    img.verify()

                # Extract metadata from filename
                metadata = self.extract_metadata_from_filename(file_path)
                return True, metadata, None

        except Exception as e:
            return False, None, f"Image validation failed: {str(e)}"


class ImagePreprocessor:
    """Preprocesses images for embedding generation."""

    def __init__(
        self,
        target_size: Tuple[int, int] = (224, 224),
        convert_mode: str = 'RGB'
    ):
        """
        Initialize image preprocessor.

        Args:
            target_size: Target dimensions (width, height)
            convert_mode: Color mode (RGB, L, etc.)
        """
        self.target_size = target_size
        self.convert_mode = convert_mode

    def convert_dicom_to_image(self, dicom_path: Path) -> Image.Image:
        """
        Convert DICOM file to PIL Image.

        Args:
            dicom_path: Path to DICOM file

        Returns:
            PIL Image object
        """
        if not DICOM_AVAILABLE:
            raise RuntimeError("pydicom not available for DICOM conversion")

        ds = pydicom.dcmread(str(dicom_path))
        pixel_array = ds.pixel_array

        # Normalize to 0-255 range
        pixel_array = pixel_array - pixel_array.min()
        pixel_array = pixel_array / pixel_array.max() * 255
        pixel_array = pixel_array.astype('uint8')

        # Convert to PIL Image
        image = Image.fromarray(pixel_array)

        return image

    def preprocess(self, file_path: Path) -> Image.Image:
        """
        Preprocess image for embedding generation.

        Steps:
        1. Load image (convert DICOM if needed)
        2. Convert to RGB
        3. Resize to target dimensions
        4. Normalize

        Args:
            file_path: Path to image file

        Returns:
            Preprocessed PIL Image
        """
        # Load image
        if file_path.suffix.lower() in {'.dcm', '.dicom'}:
            image = self.convert_dicom_to_image(file_path)
        else:
            image = Image.open(file_path)

        # Convert color mode
        if image.mode != self.convert_mode:
            image = image.convert(self.convert_mode)

        # Resize
        if image.size != self.target_size:
            image = image.resize(self.target_size, Image.Resampling.LANCZOS)

        return image


class CheckpointManager:
    """Manages vectorization checkpoint state using SQLite."""

    def __init__(self, db_path: str = "image_vectorization_state.db"):
        """
        Initialize checkpoint manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database schema."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ImageVectorizationState (
                ImageID TEXT PRIMARY KEY,
                FilePath TEXT NOT NULL,
                Status TEXT NOT NULL CHECK(Status IN ('pending', 'processing', 'completed', 'failed')),
                ErrorMessage TEXT,
                ProcessedAt TIMESTAMP,
                EmbeddingDimension INTEGER
            )
        ''')

        self.conn.commit()
        logger.info(f"Checkpoint database initialized: {self.db_path}")

    def add_images(self, image_ids: List[str], file_paths: List[str]):
        """Add images to checkpoint with pending status."""
        cursor = self.conn.cursor()

        for image_id, file_path in zip(image_ids, file_paths):
            cursor.execute('''
                INSERT OR IGNORE INTO ImageVectorizationState
                (ImageID, FilePath, Status)
                VALUES (?, ?, 'pending')
            ''', (image_id, file_path))

        self.conn.commit()

    def mark_processing(self, image_id: str):
        """Mark image as currently processing."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE ImageVectorizationState
            SET Status = 'processing'
            WHERE ImageID = ?
        ''', (image_id,))
        self.conn.commit()

    def mark_completed(self, image_id: str, embedding_dim: int):
        """Mark image as successfully vectorized."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE ImageVectorizationState
            SET Status = 'completed',
                ProcessedAt = ?,
                EmbeddingDimension = ?
            WHERE ImageID = ?
        ''', (datetime.now().isoformat(), embedding_dim, image_id))
        self.conn.commit()

    def mark_failed(self, image_id: str, error_message: str):
        """Mark image as failed."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE ImageVectorizationState
            SET Status = 'failed',
                ErrorMessage = ?,
                ProcessedAt = ?
            WHERE ImageID = ?
        ''', (error_message, datetime.now().isoformat(), image_id))
        self.conn.commit()

    def get_pending_images(self) -> List[Tuple[str, str]]:
        """Get list of pending images (image_id, file_path)."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT ImageID, FilePath
            FROM ImageVectorizationState
            WHERE Status = 'pending'
        ''')
        return cursor.fetchall()

    def get_stats(self) -> Dict[str, int]:
        """Get checkpoint statistics."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT Status, COUNT(*)
            FROM ImageVectorizationState
            GROUP BY Status
        ''')
        stats = dict(cursor.fetchall())
        return {
            'pending': stats.get('pending', 0),
            'processing': stats.get('processing', 0),
            'completed': stats.get('completed', 0),
            'failed': stats.get('failed', 0)
        }

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


class ImageVectorizationPipeline:
    """Main image vectorization pipeline."""

    def __init__(
        self,
        vision_client: NIMVisionClient,
        db_client: IRISVectorDBClient,
        validator: ImageValidator,
        preprocessor: ImagePreprocessor,
        checkpoint_manager: CheckpointManager,
        batch_size: int = 10,
        error_log_path: str = "image_vectorization_errors.log"
    ):
        """
        Initialize vectorization pipeline.

        Args:
            vision_client: NIM Vision API client
            db_client: IRIS database client
            validator: Image validator
            preprocessor: Image preprocessor
            checkpoint_manager: Checkpoint manager
            batch_size: Images per batch
            error_log_path: Path to error log file
        """
        self.vision_client = vision_client
        self.db_client = db_client
        self.validator = validator
        self.preprocessor = preprocessor
        self.checkpoint = checkpoint_manager
        self.batch_size = batch_size
        self.error_log_path = error_log_path

        # Statistics
        self.stats = {
            'total_images': 0,
            'validated': 0,
            'validation_errors': 0,
            'processed': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }

    def log_error(self, image_id: str, error: str):
        """Log validation/processing error to file."""
        with open(self.error_log_path, 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"\n{'='*80}\n")
            f.write(f"Error - {timestamp}\n")
            f.write(f"{'='*80}\n")
            f.write(f"Image ID: {image_id}\n")
            f.write(f"Error: {error}\n")
            f.write(f"{'-'*80}\n")

    def discover_images(self, input_dir: Path, formats: List[str]) -> List[Path]:
        """
        Discover image files in directory.

        Args:
            input_dir: Input directory path
            formats: List of formats to include (e.g., ['png', 'jpg', 'dicom'])

        Returns:
            List of image file paths
        """
        image_files = []

        format_extensions = set()
        for fmt in formats:
            fmt = fmt.lower()
            if fmt == 'dicom':
                format_extensions.add('.dcm')
                format_extensions.add('.dicom')
            elif fmt in {'jpg', 'jpeg'}:
                format_extensions.add('.jpg')
                format_extensions.add('.jpeg')
            else:
                format_extensions.add(f'.{fmt}')

        for ext in format_extensions:
            image_files.extend(input_dir.glob(f"**/*{ext}"))

        return sorted(image_files)

    def validate_images(self, image_files: List[Path]) -> List[Tuple[ImageMetadata, Path]]:
        """
        Validate images and extract metadata.

        Args:
            image_files: List of image file paths

        Returns:
            List of (metadata, file_path) tuples for valid images
        """
        valid_images = []

        logger.info(f"Validating {len(image_files)} images...")

        for file_path in image_files:
            is_valid, metadata, error = self.validator.validate_and_extract(file_path)

            if is_valid:
                valid_images.append((metadata, file_path))
                self.stats['validated'] += 1
            else:
                self.stats['validation_errors'] += 1
                self.log_error(file_path.stem, error or "Unknown validation error")
                logger.warning(f"Validation failed: {file_path.name} - {error}")

        logger.info(f"✓ {len(valid_images)} valid images, {self.stats['validation_errors']} validation errors")

        return valid_images

    def process_batch(
        self,
        batch: List[Tuple[ImageMetadata, Path]]
    ) -> Tuple[int, int]:
        """
        Process a batch of images.

        Args:
            batch: List of (metadata, file_path) tuples

        Returns:
            Tuple of (successful, failed) counts
        """
        successful = 0
        failed = 0

        # Preprocess images
        preprocessed_images = []
        valid_metadata = []

        for metadata, file_path in batch:
            try:
                self.checkpoint.mark_processing(metadata.image_id)

                image = self.preprocessor.preprocess(file_path)
                preprocessed_images.append(image)
                valid_metadata.append(metadata)

            except Exception as e:
                error_msg = f"Preprocessing failed: {e}"
                self.log_error(metadata.image_id, error_msg)
                self.checkpoint.mark_failed(metadata.image_id, error_msg)
                failed += 1
                logger.error(f"Preprocessing failed for {metadata.image_id}: {e}")

        if not preprocessed_images:
            return successful, failed

        # Generate embeddings
        try:
            embeddings = self.vision_client.embed_batch(preprocessed_images)
        except Exception as e:
            # Batch embedding failed, mark all as failed
            error_msg = f"Batch embedding failed: {e}"
            for metadata in valid_metadata:
                self.log_error(metadata.image_id, error_msg)
                self.checkpoint.mark_failed(metadata.image_id, error_msg)
            failed += len(valid_metadata)
            logger.error(f"Batch embedding failed: {e}")
            return successful, failed

        # Store vectors
        for metadata, embedding in zip(valid_metadata, embeddings):
            try:
                self.db_client.insert_image_vector(
                    image_id=metadata.image_id,
                    patient_id=metadata.patient_id,
                    study_type=metadata.study_type,
                    image_path=metadata.file_path,
                    embedding=embedding,
                    related_report_id=metadata.related_report_id
                )

                self.checkpoint.mark_completed(metadata.image_id, len(embedding))
                successful += 1

            except Exception as e:
                error_msg = f"Database insertion failed: {e}"
                self.log_error(metadata.image_id, error_msg)
                self.checkpoint.mark_failed(metadata.image_id, error_msg)
                failed += 1
                logger.error(f"DB insertion failed for {metadata.image_id}: {e}")

        return successful, failed

    def run(self, input_dir: Path, formats: List[str], resume: bool = False):
        """
        Run complete vectorization pipeline.

        Args:
            input_dir: Input directory containing images
            formats: List of formats to process
            resume: Whether to resume from checkpoint
        """
        self.stats['start_time'] = time.time()

        logger.info("="*80)
        logger.info("Medical Image Vectorization Pipeline")
        logger.info("="*80)
        logger.info(f"Input directory: {input_dir}")
        logger.info(f"Image formats: {', '.join(formats)}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Resume mode: {resume}")
        logger.info("="*80)
        logger.info("")

        # Discover images
        image_files = self.discover_images(input_dir, formats)
        self.stats['total_images'] = len(image_files)

        logger.info(f"✓ Discovered {len(image_files)} image files")

        if len(image_files) == 0:
            logger.error("No image files found. Exiting.")
            return

        # Validate images
        valid_images = self.validate_images(image_files)

        if len(valid_images) == 0:
            logger.error("No valid images to process. Exiting.")
            return

        # Add to checkpoint
        image_ids = [meta.image_id for meta, _ in valid_images]
        file_paths = [meta.file_path for meta, _ in valid_images]
        self.checkpoint.add_images(image_ids, file_paths)

        # Filter for pending if resuming
        if resume:
            pending = {image_id for image_id, _ in self.checkpoint.get_pending_images()}
            valid_images = [(meta, path) for meta, path in valid_images if meta.image_id in pending]
            logger.info(f"✓ Resume mode: {len(valid_images)} pending images")

        # Process in batches
        total_batches = (len(valid_images) + self.batch_size - 1) // self.batch_size

        logger.info("")
        logger.info(f"Processing {len(valid_images)} images in {total_batches} batches...")
        logger.info("")

        for i in range(0, len(valid_images), self.batch_size):
            batch_num = (i // self.batch_size) + 1
            batch = valid_images[i:i + self.batch_size]

            batch_start = time.time()
            successful, failed = self.process_batch(batch)
            batch_time = time.time() - batch_start

            self.stats['processed'] += successful
            self.stats['failed'] += failed

            # Calculate throughput
            elapsed = time.time() - self.stats['start_time']
            throughput = self.stats['processed'] / elapsed if elapsed > 0 else 0

            # Estimate remaining time
            remaining_images = len(valid_images) - (i + len(batch))
            eta_seconds = remaining_images / throughput if throughput > 0 else 0
            eta_minutes = eta_seconds / 60

            logger.info(
                f"Batch {batch_num}/{total_batches}: "
                f"{successful} successful, {failed} failed | "
                f"{batch_time:.1f}s | "
                f"{throughput:.2f} imgs/sec | "
                f"ETA: {eta_minutes:.1f} min"
            )

        self.stats['end_time'] = time.time()
        self._print_summary()

    def _print_summary(self):
        """Print vectorization summary."""
        total_time = self.stats['end_time'] - self.stats['start_time']
        throughput = self.stats['processed'] / total_time if total_time > 0 else 0

        logger.info("")
        logger.info("="*80)
        logger.info("Vectorization Summary")
        logger.info("="*80)
        logger.info(f"Total images discovered:  {self.stats['total_images']}")
        logger.info(f"Validation errors:        {self.stats['validation_errors']}")
        logger.info(f"Valid images:             {self.stats['validated']}")
        logger.info(f"Successfully processed:   {self.stats['processed']}")
        logger.info(f"Failed:                   {self.stats['failed']}")
        logger.info(f"Elapsed time:             {total_time:.1f}s ({total_time/60:.1f} min)")
        logger.info(f"Throughput:               {throughput:.2f} images/sec")
        logger.info("="*80)
        logger.info("")

        # Check performance target (SC-005: <2 sec/image = 0.5 images/sec)
        if throughput >= 0.5:
            logger.info(f"✅ Performance target met: {throughput:.2f} imgs/sec ≥ 0.5 imgs/sec")
        else:
            logger.warning(f"⚠️  Performance below target: {throughput:.2f} imgs/sec < 0.5 imgs/sec")

        if self.stats['validation_errors'] > 0 or self.stats['failed'] > 0:
            logger.info(f"Error log: {self.error_log_path}")


def test_visual_similarity_search(
    db_client: IRISVectorDBClient,
    vision_client: NIMVisionClient,
    preprocessor: ImagePreprocessor,
    query_image_path: str,
    top_k: int = 5
):
    """
    Test visual similarity search with a query image.

    Args:
        db_client: IRIS database client
        vision_client: NIM Vision client
        preprocessor: Image preprocessor
        query_image_path: Path to query image
        top_k: Number of similar images to retrieve
    """
    logger.info("")
    logger.info("="*80)
    logger.info("Visual Similarity Search Test")
    logger.info("="*80)
    logger.info(f"Query image: {query_image_path}")
    logger.info(f"Top-K: {top_k}")
    logger.info("")

    # Preprocess query image
    query_image = preprocessor.preprocess(Path(query_image_path))

    # Generate embedding
    logger.info("Generating embedding for query image...")
    query_embedding = vision_client.embed_image(query_image)
    logger.info(f"✓ Generated {len(query_embedding)}-dimensional embedding")

    # Search for similar images
    logger.info(f"Searching for top-{top_k} similar images...")
    results = db_client.search_similar_images(
        query_vector=query_embedding,
        top_k=top_k
    )

    logger.info(f"✓ Found {len(results)} results")
    logger.info("")

    # Display results
    logger.info("Similar Images:")
    logger.info("-"*80)

    for i, result in enumerate(results, 1):
        logger.info(f"[{i}] Similarity: {result['similarity']:.4f}")
        logger.info(f"    Image ID: {result['image_id']}")
        logger.info(f"    Patient: {result['patient_id']}")
        logger.info(f"    Study Type: {result['study_type']}")
        logger.info(f"    Path: {result['image_path']}")
        logger.info("")

    logger.info("="*80)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Vectorize medical images using NVIDIA NIM Vision",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process PNG and JPG images
  python src/vectorization/image_vectorizer.py \\
      --input /path/to/images \\
      --format png,jpg \\
      --batch-size 10

  # Process DICOM files with resume
  python src/vectorization/image_vectorizer.py \\
      --input /path/to/dicom \\
      --format dicom \\
      --resume

  # Test visual similarity search
  python src/vectorization/image_vectorizer.py \\
      --input /path/to/images \\
      --format png \\
      --test-search /path/to/query.png

Performance Target:
  SC-005: ≥0.5 images/second (<2 sec/image)
        """
    )

    # Required arguments
    parser.add_argument(
        '--input',
        required=True,
        help='Input directory containing medical images'
    )

    # Optional arguments
    parser.add_argument(
        '--format',
        default='png,jpg',
        help='Comma-separated list of formats to process (png, jpg, dicom). Default: png,jpg'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of images per batch (default: 10)'
    )

    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from checkpoint (skip already processed images)'
    )

    parser.add_argument(
        '--checkpoint-db',
        default='image_vectorization_state.db',
        help='Path to checkpoint SQLite database (default: image_vectorization_state.db)'
    )

    parser.add_argument(
        '--error-log',
        default='image_vectorization_errors.log',
        help='Path to error log file (default: image_vectorization_errors.log)'
    )

    parser.add_argument(
        '--test-search',
        help='Test visual similarity search with specified query image'
    )

    # Service endpoints
    parser.add_argument(
        '--vision-url',
        default='http://localhost:8002',
        help='NIM Vision service URL (default: http://localhost:8002)'
    )

    parser.add_argument(
        '--iris-host',
        help='IRIS database host (default: from env or localhost)'
    )

    parser.add_argument(
        '--iris-port',
        type=int,
        help='IRIS database port (default: from env or 1972)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


def main():
    """Main entry point for image vectorization."""
    args = parse_arguments()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Parse formats
        formats = [fmt.strip().lower() for fmt in args.format.split(',')]

        # Validate input directory
        input_dir = Path(args.input)
        if not input_dir.exists():
            logger.error(f"Input directory not found: {input_dir}")
            sys.exit(1)

        if not input_dir.is_dir():
            logger.error(f"Input path is not a directory: {input_dir}")
            sys.exit(1)

        # Initialize components
        logger.info("Initializing components...")

        vision_client = NIMVisionClient(base_url=args.vision_url)

        # Health check
        if not vision_client.health_check():
            logger.error("NIM Vision service is not healthy")
            logger.error(f"Check service at: {args.vision_url}")
            sys.exit(1)

        db_client = IRISVectorDBClient(
            host=args.iris_host,
            port=args.iris_port
        )
        db_client.connect()

        validator = ImageValidator(dicom_enabled='dicom' in formats)
        preprocessor = ImagePreprocessor()

        # Test search mode
        if args.test_search:
            test_visual_similarity_search(
                db_client=db_client,
                vision_client=vision_client,
                preprocessor=preprocessor,
                query_image_path=args.test_search
            )
            sys.exit(0)

        # Vectorization mode
        checkpoint = CheckpointManager(db_path=args.checkpoint_db)

        pipeline = ImageVectorizationPipeline(
            vision_client=vision_client,
            db_client=db_client,
            validator=validator,
            preprocessor=preprocessor,
            checkpoint_manager=checkpoint,
            batch_size=args.batch_size,
            error_log_path=args.error_log
        )

        pipeline.run(
            input_dir=input_dir,
            formats=formats,
            resume=args.resume
        )

        checkpoint.close()
        db_client.disconnect()

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\n\nVectorization cancelled by user.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
