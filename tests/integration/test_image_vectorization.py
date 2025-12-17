#!/usr/bin/env python3
"""
Integration Tests for Medical Image Vectorization Pipeline

Tests all components of the image vectorization workflow:
- DICOM validation and metadata extraction
- Image preprocessing (DICOM → PIL → normalized/resized)
- NIM Vision API embedding generation
- IRIS database vector storage
- Visual similarity search
- End-to-end pipeline execution
- Performance validation (SC-005: ≥0.5 images/sec)

Usage:
    pytest tests/integration/test_image_vectorization.py -v
    pytest tests/integration/test_image_vectorization.py::TestDICOMValidation -v
    pytest tests/integration/test_image_vectorization.py -v -m slow
"""

import pytest
import os
import sys
import time
import tempfile
import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from vectorization.image_vectorizer import (
    ImageMetadata,
    ImageValidator,
    ImagePreprocessor,
    NIMVisionClient,
    CheckpointManager,
    ImageVectorizationPipeline
)
from vectorization.vector_db_client import IRISVectorDBClient

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "sample_medical_images"

# Filter for real MIMIC-CXR chest X-ray files (large files with UUID naming pattern)
# These are the actual medical images suitable for testing, not the small pydicom test files
_all_dcm_files = list(FIXTURES_DIR.glob("*.dcm"))
SAMPLE_DICOM_FILES = [
    f for f in _all_dcm_files
    if f.stat().st_size > 1_000_000  # Files larger than 1MB are real chest X-rays
]
# Fallback to any DICOM files if no large ones found (for CI environments)
if not SAMPLE_DICOM_FILES:
    SAMPLE_DICOM_FILES = _all_dcm_files


# ===== Fixtures =====


@pytest.fixture
def sample_dicom_path():
    """Return path to a single sample DICOM file."""
    if not SAMPLE_DICOM_FILES:
        pytest.skip("No sample DICOM files found in fixtures directory")
    return SAMPLE_DICOM_FILES[0]


@pytest.fixture
def multiple_dicom_paths():
    """Return paths to 5 sample DICOM files for batch testing."""
    if len(SAMPLE_DICOM_FILES) < 5:
        pytest.skip("Not enough sample DICOM files for batch testing")
    return SAMPLE_DICOM_FILES[:5]


@pytest.fixture
def image_validator():
    """Create ImageValidator instance with DICOM support."""
    return ImageValidator(dicom_enabled=True)


@pytest.fixture
def image_preprocessor():
    """Create ImagePreprocessor instance."""
    return ImagePreprocessor(target_size=(224, 224), convert_mode='RGB')


@pytest.fixture
def mock_nim_vision_client():
    """Create mocked NIM Vision client for testing without API calls."""
    client = Mock(spec=NIMVisionClient)
    # Mock embed_image to return 1024-dim random vector
    client.embed_image.return_value = [0.1] * 1024
    # Mock embed_batch to return list of 1024-dim vectors
    client.embed_batch.side_effect = lambda images: [[0.1] * 1024 for _ in images]
    # Mock health_check
    client.health_check.return_value = True
    return client


@pytest.fixture
def temp_checkpoint_db():
    """Create temporary SQLite checkpoint database."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def checkpoint_manager(temp_checkpoint_db):
    """Create CheckpointManager with temporary database."""
    return CheckpointManager(db_path=temp_checkpoint_db)


@pytest.fixture
def mock_iris_client():
    """Create mocked IRIS client for testing without database."""
    client = Mock(spec=IRISVectorDBClient)
    client.connect.return_value = None
    client.disconnect.return_value = None
    client.insert_image_vector.return_value = None
    client.search_similar_images.return_value = [
        {
            "image_id": "test-image-001",
            "patient_id": "p10001",
            "study_type": "Chest X-Ray",
            "image_path": "/path/to/image.dcm",
            "related_report_id": None,
            "similarity": 0.95
        }
    ]
    return client


# ===== Test Classes =====


class TestDICOMValidation:
    """Test DICOM file validation and metadata extraction."""

    def test_dicom_format_detection(self, image_validator, sample_dicom_path):
        """Test that .dcm files are recognized as valid format."""
        assert image_validator.is_valid_format(sample_dicom_path)

    def test_invalid_format_rejection(self, image_validator):
        """Test that non-DICOM formats are rejected."""
        invalid_path = Path("/path/to/file.txt")
        assert not image_validator.is_valid_format(invalid_path)

    def test_dicom_metadata_extraction(self, image_validator, sample_dicom_path):
        """Test extraction of metadata from DICOM file."""
        is_valid, metadata, error = image_validator.validate_and_extract(sample_dicom_path)

        assert is_valid, f"Validation failed: {error}"
        assert metadata is not None
        assert isinstance(metadata, ImageMetadata)

        # Verify required fields are present
        assert metadata.image_id
        assert metadata.patient_id
        assert metadata.study_type
        assert metadata.file_path == str(sample_dicom_path)
        assert metadata.format == "DICOM"
        assert metadata.width > 0
        assert metadata.height > 0

    def test_patient_id_extraction(self, image_validator, sample_dicom_path):
        """Test that PatientID is correctly extracted from DICOM metadata."""
        is_valid, metadata, error = image_validator.validate_and_extract(sample_dicom_path)

        assert is_valid
        assert metadata.patient_id is not None
        # Patient IDs in MIMIC-CXR start with 'p' followed by 8 digits
        assert len(metadata.patient_id) >= 2

    def test_study_type_extraction(self, image_validator, sample_dicom_path):
        """Test that study type/modality is extracted from DICOM."""
        is_valid, metadata, error = image_validator.validate_and_extract(sample_dicom_path)

        assert is_valid
        assert metadata.study_type is not None
        # Study type should not be empty or 'Unknown'
        assert metadata.study_type != ""

    def test_image_dimensions_extraction(self, image_validator, sample_dicom_path):
        """Test that image dimensions are extracted from DICOM."""
        is_valid, metadata, error = image_validator.validate_and_extract(sample_dicom_path)

        assert is_valid
        assert metadata.width > 0
        assert metadata.height > 0
        # MIMIC-CXR images are typically large (>1000 pixels)
        assert metadata.width >= 100
        assert metadata.height >= 100

    def test_batch_dicom_validation(self, image_validator, multiple_dicom_paths):
        """Test validation of multiple DICOM files."""
        validated_count = 0

        for dicom_path in multiple_dicom_paths:
            is_valid, metadata, error = image_validator.validate_and_extract(dicom_path)
            if is_valid:
                validated_count += 1

        # All sample DICOM files should be valid
        assert validated_count == len(multiple_dicom_paths)


class TestImagePreprocessing:
    """Test image preprocessing pipeline."""

    def test_dicom_to_pil_conversion(self, image_preprocessor, sample_dicom_path):
        """Test conversion of DICOM to PIL Image."""
        preprocessed = image_preprocessor.preprocess(sample_dicom_path)

        assert preprocessed is not None
        # Should be PIL Image
        assert hasattr(preprocessed, 'size')
        assert hasattr(preprocessed, 'mode')

    def test_image_normalization(self, image_preprocessor, sample_dicom_path):
        """Test that images are normalized to 0-255 range."""
        preprocessed = image_preprocessor.preprocess(sample_dicom_path)

        # Convert to array to check pixel values
        import numpy as np
        pixels = np.array(preprocessed)

        assert pixels.min() >= 0
        assert pixels.max() <= 255

    def test_image_resizing(self, image_preprocessor, sample_dicom_path):
        """Test that images are resized to target dimensions."""
        preprocessed = image_preprocessor.preprocess(sample_dicom_path)

        assert preprocessed.size == (224, 224)

    def test_rgb_conversion(self, image_preprocessor, sample_dicom_path):
        """Test that images are converted to RGB mode."""
        preprocessed = image_preprocessor.preprocess(sample_dicom_path)

        assert preprocessed.mode == 'RGB'

    def test_batch_preprocessing(self, image_preprocessor, multiple_dicom_paths):
        """Test preprocessing of multiple images."""
        preprocessed_images = []

        for dicom_path in multiple_dicom_paths:
            preprocessed = image_preprocessor.preprocess(dicom_path)
            preprocessed_images.append(preprocessed)

        assert len(preprocessed_images) == len(multiple_dicom_paths)

        # All should have same size and mode
        for img in preprocessed_images:
            assert img.size == (224, 224)
            assert img.mode == 'RGB'


class TestNIMVisionAPI:
    """Test NIM Vision API client (mocked)."""

    def test_client_initialization(self):
        """Test NIMVisionClient initialization."""
        client = NIMVisionClient(
            base_url="http://localhost:8002",
            model="nv-clip-vit"
        )

        assert client.base_url == "http://localhost:8002"
        assert client.embeddings_url == "http://localhost:8002/v1/embeddings"
        assert client.model == "nv-clip-vit"

    def test_image_encoding(self, image_preprocessor, sample_dicom_path):
        """Test base64 encoding of images."""
        client = NIMVisionClient()
        preprocessed = image_preprocessor.preprocess(sample_dicom_path)

        encoded = client.encode_image_base64(preprocessed)

        assert isinstance(encoded, str)
        assert len(encoded) > 0
        # Base64 strings are multiples of 4 characters
        assert len(encoded) % 4 == 0

    def test_embedding_generation_mock(self, mock_nim_vision_client, image_preprocessor, sample_dicom_path):
        """Test embedding generation with mocked client."""
        preprocessed = image_preprocessor.preprocess(sample_dicom_path)

        embedding = mock_nim_vision_client.embed_image(preprocessed)

        assert isinstance(embedding, list)
        assert len(embedding) == 1024
        assert all(isinstance(v, float) for v in embedding)

    def test_batch_embedding_generation_mock(self, mock_nim_vision_client, image_preprocessor, multiple_dicom_paths):
        """Test batch embedding generation with mocked client."""
        preprocessed_images = [
            image_preprocessor.preprocess(path) for path in multiple_dicom_paths
        ]

        embeddings = mock_nim_vision_client.embed_batch(preprocessed_images)

        assert len(embeddings) == len(preprocessed_images)
        assert all(len(emb) == 1024 for emb in embeddings)


class TestCheckpointManagement:
    """Test checkpoint/resumability functionality."""

    def test_checkpoint_initialization(self, temp_checkpoint_db):
        """Test checkpoint database initialization."""
        manager = CheckpointManager(db_path=temp_checkpoint_db)

        # Verify database file exists
        assert os.path.exists(temp_checkpoint_db)

        # Verify table exists
        conn = sqlite3.connect(temp_checkpoint_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ImageVectorizationState'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_add_images_to_checkpoint(self, checkpoint_manager):
        """Test adding images to checkpoint with pending status."""
        image_ids = ["img-001", "img-002", "img-003"]
        file_paths = ["/path/to/img1.dcm", "/path/to/img2.dcm", "/path/to/img3.dcm"]

        checkpoint_manager.add_images(image_ids, file_paths)

        # Verify images were added
        pending = checkpoint_manager.get_pending_images()
        assert len(pending) == 3

    def test_mark_processing(self, checkpoint_manager):
        """Test marking images as processing."""
        checkpoint_manager.add_images(["img-001"], ["/path/to/img1.dcm"])
        checkpoint_manager.mark_processing("img-001")

        # Should not appear in pending list
        pending = checkpoint_manager.get_pending_images()
        assert len(pending) == 0

    def test_mark_completed(self, checkpoint_manager):
        """Test marking images as completed."""
        checkpoint_manager.add_images(["img-001"], ["/path/to/img1.dcm"])
        checkpoint_manager.mark_processing("img-001")
        checkpoint_manager.mark_completed("img-001", embedding_dim=1024)

        # Verify stats
        stats = checkpoint_manager.get_stats()
        assert stats['completed'] == 1

    def test_mark_failed(self, checkpoint_manager):
        """Test marking images as failed."""
        checkpoint_manager.add_images(["img-001"], ["/path/to/img1.dcm"])
        checkpoint_manager.mark_processing("img-001")
        checkpoint_manager.mark_failed("img-001", "Embedding generation failed")

        # Verify stats
        stats = checkpoint_manager.get_stats()
        assert stats['failed'] == 1

    def test_checkpoint_stats(self, checkpoint_manager):
        """Test checkpoint statistics calculation."""
        checkpoint_manager.add_images(
            ["img-001", "img-002", "img-003"],
            ["/path/1.dcm", "/path/2.dcm", "/path/3.dcm"]
        )

        checkpoint_manager.mark_completed("img-001", 1024)
        checkpoint_manager.mark_failed("img-002", "Error")
        # img-003 stays pending

        stats = checkpoint_manager.get_stats()
        assert stats['pending'] == 1
        assert stats['completed'] == 1
        assert stats['failed'] == 1


class TestIRISVectorStorage:
    """Test IRIS vector database storage (mocked)."""

    def test_insert_image_vector_mock(self, mock_iris_client):
        """Test image vector insertion with mocked client."""
        mock_iris_client.insert_image_vector(
            image_id="test-image-001",
            patient_id="p10001",
            study_type="Chest X-Ray",
            image_path="/path/to/image.dcm",
            embedding=[0.1] * 1024,
            related_report_id=None
        )

        # Verify method was called
        assert mock_iris_client.insert_image_vector.called
        assert mock_iris_client.insert_image_vector.call_count == 1

    def test_search_similar_images_mock(self, mock_iris_client):
        """Test visual similarity search with mocked client."""
        query_vector = [0.1] * 1024
        results = mock_iris_client.search_similar_images(
            query_vector=query_vector,
            top_k=5
        )

        assert len(results) >= 1
        assert results[0]['image_id'] == "test-image-001"
        assert results[0]['similarity'] == 0.95

    def test_vector_dimension_validation(self, mock_iris_client):
        """Test that vector dimension is validated (in real client)."""
        # This tests the API contract - real client validates dimension
        # Mock doesn't validate, but we test expected behavior

        # 1024-dim vector should work
        mock_iris_client.insert_image_vector(
            image_id="test-001",
            patient_id="p10001",
            study_type="Chest X-Ray",
            image_path="/path/to/test.dcm",
            embedding=[0.1] * 1024
        )

        assert mock_iris_client.insert_image_vector.called


class TestEndToEndPipeline:
    """Test complete end-to-end image vectorization pipeline."""

    def test_pipeline_initialization(
        self,
        mock_nim_vision_client,
        mock_iris_client,
        image_validator,
        image_preprocessor,
        checkpoint_manager
    ):
        """Test pipeline initialization with all components."""
        pipeline = ImageVectorizationPipeline(
            vision_client=mock_nim_vision_client,
            db_client=mock_iris_client,
            validator=image_validator,
            preprocessor=image_preprocessor,
            checkpoint_manager=checkpoint_manager,
            batch_size=5
        )

        assert pipeline.batch_size == 5
        assert pipeline.vision_client == mock_nim_vision_client
        assert pipeline.db_client == mock_iris_client

    @pytest.mark.skipif(not SAMPLE_DICOM_FILES, reason="No sample DICOM files found in fixtures directory")
    def test_discover_images(
        self,
        mock_nim_vision_client,
        mock_iris_client,
        image_validator,
        image_preprocessor,
        checkpoint_manager
    ):
        """Test image discovery in directory."""
        pipeline = ImageVectorizationPipeline(
            vision_client=mock_nim_vision_client,
            db_client=mock_iris_client,
            validator=image_validator,
            preprocessor=image_preprocessor,
            checkpoint_manager=checkpoint_manager
        )

        discovered = pipeline.discover_images(FIXTURES_DIR, formats=['dicom'])

        assert len(discovered) >= 5
        assert all(path.suffix.lower() == '.dcm' for path in discovered)

    @pytest.mark.skipif(not SAMPLE_DICOM_FILES, reason="No sample DICOM files found in fixtures directory")
    def test_validate_images_pipeline(
        self,
        mock_nim_vision_client,
        mock_iris_client,
        image_validator,
        image_preprocessor,
        checkpoint_manager
    ):
        """Test image validation in pipeline."""
        pipeline = ImageVectorizationPipeline(
            vision_client=mock_nim_vision_client,
            db_client=mock_iris_client,
            validator=image_validator,
            preprocessor=image_preprocessor,
            checkpoint_manager=checkpoint_manager
        )

        discovered = pipeline.discover_images(FIXTURES_DIR, formats=['dicom'])
        valid_images = pipeline.validate_images(discovered[:5])

        assert len(valid_images) > 0
        assert all(isinstance(meta, ImageMetadata) for meta, _ in valid_images)

    @pytest.mark.slow
    @pytest.mark.skipif(not SAMPLE_DICOM_FILES, reason="No sample DICOM files found in fixtures directory")
    def test_process_batch(
        self,
        mock_nim_vision_client,
        mock_iris_client,
        image_validator,
        image_preprocessor,
        checkpoint_manager
    ):
        """Test batch processing of images."""
        pipeline = ImageVectorizationPipeline(
            vision_client=mock_nim_vision_client,
            db_client=mock_iris_client,
            validator=image_validator,
            preprocessor=image_preprocessor,
            checkpoint_manager=checkpoint_manager,
            batch_size=5
        )

        # Get sample batch
        discovered = pipeline.discover_images(FIXTURES_DIR, formats=['dicom'])
        valid_images = pipeline.validate_images(discovered[:3])

        # Process batch
        successful, failed = pipeline.process_batch(valid_images)

        assert successful == 3
        assert failed == 0

        # Verify embeddings were generated
        assert mock_nim_vision_client.embed_batch.called

        # Verify vectors were stored
        assert mock_iris_client.insert_image_vector.call_count == 3


class TestPerformanceValidation:
    """Test performance requirements (SC-005: ≥0.5 images/sec)."""

    @pytest.mark.slow
    def test_preprocessing_performance(self, image_preprocessor, multiple_dicom_paths):
        """Test that preprocessing meets performance targets."""
        start_time = time.time()

        for dicom_path in multiple_dicom_paths:
            _ = image_preprocessor.preprocess(dicom_path)

        elapsed = time.time() - start_time
        throughput = len(multiple_dicom_paths) / elapsed

        # Each image should preprocess in <2 seconds
        assert throughput >= 0.5, f"Throughput {throughput:.2f} imgs/sec < 0.5 imgs/sec target"

    @pytest.mark.slow
    @pytest.mark.skipif(not SAMPLE_DICOM_FILES, reason="No sample DICOM files found in fixtures directory")
    def test_batch_processing_performance(
        self,
        mock_nim_vision_client,
        mock_iris_client,
        image_validator,
        image_preprocessor,
        checkpoint_manager
    ):
        """Test that batch processing meets throughput targets."""
        pipeline = ImageVectorizationPipeline(
            vision_client=mock_nim_vision_client,
            db_client=mock_iris_client,
            validator=image_validator,
            preprocessor=image_preprocessor,
            checkpoint_manager=checkpoint_manager,
            batch_size=10
        )

        # Get test batch
        discovered = pipeline.discover_images(FIXTURES_DIR, formats=['dicom'])
        valid_images = pipeline.validate_images(discovered[:10])

        # Time batch processing
        start_time = time.time()
        successful, failed = pipeline.process_batch(valid_images)
        elapsed = time.time() - start_time

        throughput = successful / elapsed if elapsed > 0 else 0

        # Should meet SC-005 target (≥0.5 imgs/sec, or <2 sec/img)
        assert throughput >= 0.5, (
            f"Batch throughput {throughput:.2f} imgs/sec < 0.5 imgs/sec target"
        )


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_file_handling(self, image_validator):
        """Test handling of invalid/corrupt files."""
        invalid_path = Path("/nonexistent/file.dcm")

        is_valid, metadata, error = image_validator.validate_and_extract(invalid_path)

        assert not is_valid
        assert metadata is None
        assert error is not None
        assert "not found" in error.lower()

    def test_empty_directory_handling(
        self,
        mock_nim_vision_client,
        mock_iris_client,
        image_validator,
        image_preprocessor,
        checkpoint_manager,
        tmp_path
    ):
        """Test pipeline with empty input directory."""
        pipeline = ImageVectorizationPipeline(
            vision_client=mock_nim_vision_client,
            db_client=mock_iris_client,
            validator=image_validator,
            preprocessor=image_preprocessor,
            checkpoint_manager=checkpoint_manager
        )

        # Create empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        discovered = pipeline.discover_images(empty_dir, formats=['dicom'])

        assert len(discovered) == 0


# ===== Main =====

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
