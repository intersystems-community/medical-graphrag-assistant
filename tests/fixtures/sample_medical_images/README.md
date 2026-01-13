# Sample MIMIC-CXR Medical Images - Test Fixtures

This directory contains a sample of 50 DICOM chest X-ray images from the MIMIC-CXR dataset for integration testing of the image vectorization pipeline.

## Dataset Information

- **Source**: MIMIC-CXR Database v2.1.0
- **Dataset**: Critical Care Chest X-Ray Database
- **Institution**: Beth Israel Deaconess Medical Center
- **Total Images in Full Dataset**: 19,091 DICOM files
- **Sample Size**: 50 DICOM files (symlinked)
- **Format**: DICOM (.dcm)
- **Modality**: Chest X-Ray

## File Organization

Files are symlinked from the full MIMIC-CXR dataset located at:
```
~/ws/mimic-cxr/physionet.org/files/mimic-cxr/2.1.0/files/
```

Original file structure:
```
p{10-19}/p{patient_id}/s{study_id}/{image_hash}.dcm
```

## Sample Characteristics

The sample includes images from multiple patients and studies to ensure diversity:

- **Patients**: Multiple unique patients (p10407730, p10181426, p10365197, p10132759, p10190130)
- **Studies**: Various study IDs representing different imaging sessions
- **Image Hashes**: Unique SHA-256 hashes identifying individual images

## DICOM Metadata

Each DICOM file contains medical imaging metadata including:

- **PatientID**: De-identified patient identifier
- **StudyDescription**: Description of the imaging study
- **Modality**: Imaging modality (typically "DX" for Digital Radiography or "CR" for Computed Radiography)
- **Columns/Rows**: Image dimensions in pixels
- **PixelData**: Raw image pixel array

## Usage in Tests

These images are used by:

1. **Integration Tests**: `tests/integration/test_image_vectorization.py`
   - Validates DICOM parsing with pydicom
   - Tests image preprocessing (normalization, resizing)
   - Verifies NIM Vision API embedding generation
   - Confirms IRIS database vector storage

2. **Image Vectorizer Script**: `src/vectorization/image_vectorizer.py`
   - Development testing of the full pipeline
   - Performance benchmarking (SC-005: ≥0.5 images/sec)
   - Visual similarity search testing

## Example Usage

### Validate DICOM Files

```python
from pathlib import Path
import pydicom

fixtures_dir = Path("tests/fixtures/sample_medical_images")
for dcm_file in fixtures_dir.glob("*.dcm"):
    ds = pydicom.dcmread(dcm_file)
    print(f"Patient: {ds.PatientID}, Study: {ds.StudyDescription}, Size: {ds.Rows}x{ds.Columns}")
```

### Run Image Vectorization Pipeline

```bash
python src/vectorization/image_vectorizer.py \
  --input tests/fixtures/sample_medical_images \
  --format dicom \
  --batch-size 10 \
  --test-search tests/fixtures/sample_medical_images/030fc0af-f26c3b88-6e03c1ab-5dae4289-1f25be42.dcm
```

### Run Integration Tests

```bash
pytest tests/integration/test_image_vectorization.py -v
```

## Dataset Citation

If using MIMIC-CXR data in publications, please cite:

> Johnson, A., Pollard, T., Mark, R., Berkowitz, S., & Horng, S. (2019).
> MIMIC-CXR Database (version 2.1.0). PhysioNet.
> https://doi.org/10.13026/C2JT1Q

## Data Access

The full MIMIC-CXR dataset requires credentialed access through PhysioNet:
https://physionet.org/content/mimic-cxr/2.1.0/

This sample is used strictly for development and testing purposes under the approved data use agreement.

## Notes

- **Symlinks**: Files are symlinked rather than copied to save disk space (~100MB per file × 50 = ~5GB)
- **Privacy**: All patient identifiers are de-identified per HIPAA Safe Harbor standards
- **Image Quality**: Images are production-quality clinical chest X-rays suitable for diagnostic evaluation
- **Processing**: Images require DICOM-to-PIL conversion and normalization before embedding generation

## Related Files

- **Image Vectorizer**: `src/vectorization/image_vectorizer.py`
- **Vector DB Client**: `src/vectorization/vector_db_client.py`
- **Integration Tests**: `tests/integration/test_image_vectorization.py`
- **NIM Vision Deployment**: `scripts/aws/deploy-nim-vision.sh`
- **Full Dataset Documentation**: `MIMIC_CXR_INTEGRATION.md`
