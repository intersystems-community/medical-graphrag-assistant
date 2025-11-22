"""Search module for medical image semantic search."""

from .scoring import (
    calculate_similarity,
    get_score_color,
    get_confidence_level,
    get_hex_color,
    score_result
)

__all__ = [
    'calculate_similarity',
    'get_score_color',
    'get_confidence_level',
    'get_hex_color',
    'score_result'
]
