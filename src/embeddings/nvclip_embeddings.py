"""
NVIDIA NV-CLIP embeddings for multimodal medical imaging.

Simple drop-in replacement for BiomedCLIP using NVIDIA NIM.
Supports both image and text embeddings for cross-modal search.
"""

import os
import base64
from openai import OpenAI
from PIL import Image
import io
import numpy as np
import pydicom
from typing import List, Union


class NVCLIPEmbeddings:
    """NVIDIA NV-CLIP multimodal embeddings wrapper."""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None
    ):
        """
        Initialize NV-CLIP embeddings.

        Args:
            api_key: NVIDIA API key (or set NVIDIA_API_KEY env var)
            base_url: Base URL for NV-CLIP API (or set NVCLIP_BASE_URL env var)
                     Default: https://integrate.api.nvidia.com/v1 (NVIDIA Cloud)
                     For local NIM: http://localhost:8002/v1
        """
        # Get base URL from parameter, env var, or default
        self.base_url = base_url or os.getenv('NVCLIP_BASE_URL', 'https://integrate.api.nvidia.com/v1')

        # API key: required for cloud, optional for local NIM
        self.api_key = api_key or os.getenv('NVIDIA_API_KEY')
        is_local_nim = 'localhost' in self.base_url or '127.0.0.1' in self.base_url

        if not self.api_key and not is_local_nim:
            raise ValueError(
                "NVIDIA API key required for cloud API. Set NVIDIA_API_KEY env var or pass api_key parameter.\n"
                "Get your key at: https://build.nvidia.com/nvidia/nvclip\n"
                "For local NIM, set NVCLIP_BASE_URL=http://localhost:8002/v1"
            )

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=self.api_key or "dummy",  # Local NIM doesn't validate key
            base_url=self.base_url
        )

        self.model = "nvidia/nvclip"
        self.provider = "nvclip"
        self.dimension = 1024  # NV-CLIP ViT-H output dimension

        print(f"NV-CLIP initialized ({'Local NIM' if is_local_nim else 'Cloud API'})")
        print(f"Endpoint: {self.base_url}")
        print(f"Model: {self.model}")
        print(f"Embedding dimension: {self.dimension}")

    def _image_to_base64(self, img: Image.Image) -> str:
        """
        Convert PIL Image to base64 string.

        Args:
            img: PIL Image

        Returns:
            Base64-encoded PNG string
        """
        buffered = io.BytesIO()
        # Convert to RGB if grayscale
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def _load_image(self, image_input: Union[str, np.ndarray, Image.Image]) -> Image.Image:
        """
        Load image from various input types.

        Args:
            image_input: File path, numpy array, or PIL Image

        Returns:
            PIL Image in RGB
        """
        if isinstance(image_input, str):
            # Check if DICOM or regular image
            if image_input.lower().endswith('.dcm'):
                # Load DICOM
                ds = pydicom.dcmread(image_input)
                img_array = ds.pixel_array

                # Normalize to 0-255 for 8-bit
                img_array = ((img_array - img_array.min()) /
                            (img_array.max() - img_array.min()) * 255).astype(np.uint8)

                img = Image.fromarray(img_array).convert('RGB')
            else:
                # Load regular image file
                img = Image.open(image_input).convert('RGB')

        elif isinstance(image_input, np.ndarray):
            # Numpy array
            img = Image.fromarray(image_input).convert('RGB')

        elif isinstance(image_input, Image.Image):
            # Already a PIL Image
            img = image_input.convert('RGB')

        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        # Resize to NV-CLIP's acceptable range (224-518)
        max_dim = max(img.size)
        if max_dim > 518:
            scale = 518 / max_dim
            new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        elif max_dim < 224:
            img = img.resize((224, 224), Image.Resampling.LANCZOS)

        return img

    def embed_image(self, image_input: Union[str, np.ndarray, Image.Image]) -> List[float]:
        """
        Generate embedding for a single image.

        Args:
            image_input: DICOM path, image path, numpy array, or PIL Image

        Returns:
            1024-dimensional embedding vector
        """
        img = self._load_image(image_input)

        # Convert to data URI format
        image_data_uri = f"data:image/jpeg;base64,{self._image_to_base64(img)}"

        # Call NV-CLIP API using OpenAI client
        response = self.client.embeddings.create(
            input=[image_data_uri],
            model=self.model,
            encoding_format="float"
        )

        embedding = response.data[0].embedding

        return embedding

    def embed_images(
        self,
        image_inputs: List[Union[str, np.ndarray, Image.Image]],
        batch_size: int = 10
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple images.

        Note: NV-CLIP API processes one image at a time.
        batch_size parameter maintained for API compatibility.

        Args:
            image_inputs: List of DICOM paths, image paths, arrays, or PIL Images
            batch_size: Processing batch size (for rate limiting)

        Returns:
            List of 1024-dimensional embedding vectors
        """
        all_embeddings = []

        for i, img_input in enumerate(image_inputs):
            try:
                embedding = self.embed_image(img_input)
                all_embeddings.append(embedding)

                if (i + 1) % batch_size == 0:
                    print(f"Processed {i + 1}/{len(image_inputs)} images")

            except Exception as e:
                print(f"Error processing image {i}: {e}")
                # Append zero vector on error
                all_embeddings.append([0.0] * self.dimension)

        return all_embeddings

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text query (for cross-modal search).

        Args:
            text: Text query (e.g., "pneumonia chest infiltrate")

        Returns:
            1024-dimensional embedding vector
        """
        # Call NV-CLIP API using OpenAI client
        response = self.client.embeddings.create(
            input=[text],
            model=self.model,
            encoding_format="float"
        )

        embedding = response.data[0].embedding

        return embedding

    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Cosine similarity
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

        return float(similarity)


# Factory integration
def create_nvclip_embeddings(api_key: str = None) -> NVCLIPEmbeddings:
    """Factory function to create NV-CLIP embeddings."""
    return NVCLIPEmbeddings(api_key=api_key)


if __name__ == '__main__':
    # Test
    print("Testing NV-CLIP embeddings...")
    print()

    try:
        embedder = NVCLIPEmbeddings()

        # Test text embedding
        text_emb = embedder.embed_text("chest X-ray showing pneumonia")
        print(f"Text embedding dimension: {len(text_emb)}")
        print(f"Sample values: {text_emb[:5]}")
        print()
        print("✅ NV-CLIP ready for image processing!")

    except ValueError as e:
        print(f"⚠️ {e}")
        print()
        print("To get an NVIDIA API key:")
        print("1. Visit: https://build.nvidia.com/nvidia/nv-clip")
        print("2. Sign up / log in")
        print("3. Get your API key")
        print("4. Add to .env: NVIDIA_API_KEY=your_key_here")
