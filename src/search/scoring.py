"""
Similarity scoring module for medical image search.

Provides functions to calculate cosine similarity between embeddings
and map scores to visual display elements (colors, confidence levels).
"""

from typing import List, Union
import numpy as np


# Score thresholds (calibrated from research.md)
STRONG_THRESHOLD = 0.7    # Green, high confidence
MODERATE_THRESHOLD = 0.5  # Yellow, moderate confidence
# Below 0.5 = weak (gray)

# UI color mappings
COLOR_MAP = {
    'green': '#28a745',    # Bootstrap success green
    'yellow': '#ffc107',   # Bootstrap warning yellow/amber
    'gray': '#6c757d'      # Bootstrap secondary gray
}


def calculate_similarity(
    embedding1: Union[List[float], np.ndarray],
    embedding2: Union[List[float], np.ndarray]
) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Cosine similarity measures the cosine of the angle between two vectors,
    ranging from -1 (opposite) to 1 (identical). For normalized embeddings
    (like NV-CLIP), this is equivalent to dot product.
    
    Args:
        embedding1: First embedding vector (list or numpy array)
        embedding2: Second embedding vector (list or numpy array)
        
    Returns:
        float: Cosine similarity score between -1.0 and 1.0
        
    Raises:
        ValueError: If either vector is all zeros (undefined cosine)
        
    Example:
        >>> emb1 = [1.0, 2.0, 3.0]
        >>> emb2 = [1.0, 2.0, 3.0]
        >>> similarity = calculate_similarity(emb1, emb2)
        >>> assert similarity == 1.0  # Identical vectors
        
        >>> emb1 = [1.0, 0.0, 0.0]
        >>> emb2 = [0.0, 1.0, 0.0]
        >>> similarity = calculate_similarity(emb1, emb2)
        >>> assert similarity == 0.0  # Orthogonal vectors
    """
    # Convert to numpy arrays if needed
    vec1 = np.array(embedding1, dtype=np.float64)
    vec2 = np.array(embedding2, dtype=np.float64)
    
    # Calculate norms
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    # Check for zero vectors
    if norm1 == 0.0 or norm2 == 0.0:
        raise ValueError(
            "Cannot calculate cosine similarity with zero vector. "
            "One or both embeddings have zero magnitude."
        )
    
    # Cosine similarity = dot product / (norm1 * norm2)
    dot_product = np.dot(vec1, vec2)
    similarity = dot_product / (norm1 * norm2)
    
    # Return as Python float (not numpy.float64)
    return float(similarity)


def get_score_color(score: float) -> str:
    """
    Get color code for similarity score.
    
    Maps similarity scores to color categories for visual display:
    - Green: Strong match (score ≥ 0.7)
    - Yellow: Moderate match (0.5 ≤ score < 0.7)
    - Gray: Weak match (score < 0.5)
    
    Args:
        score: Similarity score (typically 0.0-1.0, but accepts any float)
        
    Returns:
        str: Color code ('green', 'yellow', or 'gray')
        
    Example:
        >>> get_score_color(0.85)
        'green'
        >>> get_score_color(0.6)
        'yellow'
        >>> get_score_color(0.3)
        'gray'
    """
    if score >= STRONG_THRESHOLD:
        return 'green'
    elif score >= MODERATE_THRESHOLD:
        return 'yellow'
    else:
        return 'gray'


def get_confidence_level(score: float) -> str:
    """
    Get human-readable confidence level for similarity score.
    
    Maps similarity scores to confidence labels:
    - Strong: High confidence match (score ≥ 0.7)
    - Moderate: Medium confidence match (0.5 ≤ score < 0.7)
    - Weak: Low confidence match (score < 0.5)
    
    Args:
        score: Similarity score (typically 0.0-1.0)
        
    Returns:
        str: Confidence level ('strong', 'moderate', or 'weak')
        
    Example:
        >>> get_confidence_level(0.9)
        'strong'
        >>> get_confidence_level(0.55)
        'moderate'
        >>> get_confidence_level(0.2)
        'weak'
    """
    if score >= STRONG_THRESHOLD:
        return 'strong'
    elif score >= MODERATE_THRESHOLD:
        return 'moderate'
    else:
        return 'weak'


def get_hex_color(score: float) -> str:
    """
    Get hex color code for UI rendering.
    
    Converts score to hex color for direct use in HTML/CSS.
    Uses Bootstrap-compatible color palette.
    
    Args:
        score: Similarity score
        
    Returns:
        str: Hex color code (e.g., '#28a745' for green)
        
    Example:
        >>> hex_color = get_hex_color(0.8)
        >>> assert hex_color.startswith('#')
        >>> assert len(hex_color) == 7
    """
    color_name = get_score_color(score)
    return COLOR_MAP[color_name]


# Convenience function for complete scoring
def score_result(score: float) -> dict:
    """
    Generate complete scoring metadata for a search result.
    
    Convenience function that combines all scoring functions
    to produce a complete metadata dictionary.
    
    Args:
        score: Similarity score (0.0-1.0)
        
    Returns:
        dict: Complete scoring metadata with keys:
            - score: Original score value
            - color: Color code ('green'/'yellow'/'gray')
            - confidence_level: Human label ('strong'/'moderate'/'weak')
            - hex_color: Hex color for UI ('#xxxxxx')
            
    Example:
        >>> metadata = score_result(0.87)
        >>> assert metadata['color'] == 'green'
        >>> assert metadata['confidence_level'] == 'strong'
        >>> assert metadata['hex_color'] == '#28a745'
    """
    return {
        'score': score,
        'color': get_score_color(score),
        'confidence_level': get_confidence_level(score),
        'hex_color': get_hex_color(score)
    }


if __name__ == '__main__':
    # Demo usage
    print("Similarity Scoring Demo")
    print("=" * 50)
    
    # Example embeddings
    query_emb = [1.0, 2.0, 3.0, 4.0, 5.0]
    
    test_cases = [
        ([1.0, 2.0, 3.0, 4.0, 5.0], "Identical"),
        ([1.1, 2.0, 3.1, 3.9, 5.0], "Very similar"),
        ([2.0, 3.0, 4.0, 5.0, 6.0], "Moderately similar"),
        ([0.0, 1.0, 0.0, 1.0, 0.0], "Different"),
        ([-1.0, -2.0, -3.0, -4.0, -5.0], "Opposite"),
    ]
    
    for test_emb, description in test_cases:
        score = calculate_similarity(query_emb, test_emb)
        metadata = score_result(score)
        
        print(f"\n{description}:")
        print(f"  Score: {score:.3f}")
        print(f"  Color: {metadata['color']} ({metadata['hex_color']})")
        print(f"  Confidence: {metadata['confidence_level']}")
