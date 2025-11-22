"""
BiomedCLIP embeddings for medical images.

Uses microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224
for generating embeddings from chest X-ray DICOM images.
"""

import torch
from transformers import AutoModel, AutoProcessor
from typing import List, Union
import numpy as np
from PIL import Image
import pydicom


class BiomedCLIPEmbeddings:
    """BiomedCLIP image embeddings for medical imaging."""

    def __init__(self, model_name: str = "microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"):
        """
        Initialize BiomedCLIP model.

        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self.provider = "biomedclip"
        self.dimension = 512  # BiomedCLIP output dimension

        print(f"Loading BiomedCLIP model: {model_name}")
        self.model = AutoModel.from_pretrained(model_name)
        self.processor = AutoProcessor.from_pretrained(model_name)

        # Use GPU if available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval()  # Set to evaluation mode

        print(f"BiomedCLIP loaded on device: {self.device}")
        print(f"Embedding dimension: {self.dimension}")

    def _load_image(self, image_input: Union[str, np.ndarray, Image.Image]) -> Image.Image:
        """
        Load image from various input types.

        Args:
            image_input: File path, numpy array, or PIL Image

        Returns:
            PIL Image in grayscale
        """
        if isinstance(image_input, str):
            # Check if DICOM or regular image
            if image_input.lower().endswith('.dcm'):
                # Load DICOM
                ds = pydicom.dcmread(image_input)
                img_array = ds.pixel_array

                # Normalize to 0-255 for 8-bit grayscale
                img_array = ((img_array - img_array.min()) /
                            (img_array.max() - img_array.min()) * 255).astype(np.uint8)

                img = Image.fromarray(img_array).convert('L')
            else:
                # Load regular image file
                img = Image.open(image_input).convert('L')

        elif isinstance(image_input, np.ndarray):
            # Numpy array
            img = Image.fromarray(image_input).convert('L')

        elif isinstance(image_input, Image.Image):
            # Already a PIL Image
            img = image_input.convert('L')

        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        return img

    def embed_image(self, image_input: Union[str, np.ndarray, Image.Image]) -> List[float]:
        """
        Generate embedding for a single image.

        Args:
            image_input: DICOM path, image path, numpy array, or PIL Image

        Returns:
            512-dimensional embedding vector
        """
        img = self._load_image(image_input)

        # Process image
        inputs = self.processor(images=img, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Generate embedding
        with torch.no_grad():
            embeddings = self.model.get_image_features(**inputs)

        # Convert to list
        embedding = embeddings.cpu().numpy()[0].tolist()

        return embedding

    def embed_images(self, image_inputs: List[Union[str, np.ndarray, Image.Image]],
                    batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple images in batches.

        Args:
            image_inputs: List of DICOM paths, image paths, arrays, or PIL Images
            batch_size: Number of images to process per batch

        Returns:
            List of 512-dimensional embedding vectors
        """
        all_embeddings = []

        # Process in batches
        for i in range(0, len(image_inputs), batch_size):
            batch = image_inputs[i:i + batch_size]

            # Load all images in batch
            images = [self._load_image(img_input) for img_input in batch]

            # Process batch
            inputs = self.processor(images=images, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate embeddings
            with torch.no_grad():
                embeddings = self.model.get_image_features(**inputs)

            # Convert to list
            batch_embeddings = embeddings.cpu().numpy().tolist()
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text query (for cross-modal search).

        Args:
            text: Text query (e.g., "pneumonia chest infiltrate")

        Returns:
            512-dimensional embedding vector
        """
        # Process text
        inputs = self.processor(text=[text], return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Generate embedding
        with torch.no_grad():
            embeddings = self.model.get_text_features(**inputs)

        # Convert to list
        embedding = embeddings.cpu().numpy()[0].tolist()

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
def create_biomedclip_embeddings() -> BiomedCLIPEmbeddings:
    """Factory function to create BiomedCLIP embeddings."""
    return BiomedCLIPEmbeddings()


if __name__ == '__main__':
    # Test
    print("Testing BiomedCLIP embeddings...")

    embedder = BiomedCLIPEmbeddings()

    # Test text embedding
    text_emb = embedder.embed_text("chest X-ray showing pneumonia")
    print(f"\nText embedding dimension: {len(text_emb)}")
    print(f"Sample values: {text_emb[:5]}")

    print("\nBiomedCLIP ready for image processing!")
