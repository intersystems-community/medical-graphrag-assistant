"""Pure IRIS Vector Memory System - Agent learning with semantic search"""

from .vector_memory import (
    VectorMemory,
    remember_correction,
    remember_knowledge,
    remember_preference,
    recall_similar
)

__all__ = [
    'VectorMemory',
    'remember_correction',
    'remember_knowledge',
    'remember_preference',
    'recall_similar'
]
