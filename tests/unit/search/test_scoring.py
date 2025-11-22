"""
Unit tests for src/search/scoring.py

Tests similarity score calculations and display logic for medical image search.
Following TDD: These tests should FAIL initially until scoring.py is implemented.
"""

import pytest
import numpy as np
from src.search.scoring import (
    calculate_similarity,
    get_score_color,
    get_confidence_level,
    get_hex_color
)


class TestCalculateSimilarity:
    """Test cosine similarity calculations."""
    
    def test_identical_vectors_return_one(self):
        """Identical vectors should have similarity of 1.0"""
        vec = [1.0, 2.0, 3.0, 4.0, 5.0]
        similarity = calculate_similarity(vec, vec)
        assert similarity == pytest.approx(1.0, abs=0.01)
    
    def test_orthogonal_vectors_return_zero(self):
        """Orthogonal vectors should have similarity near 0.0"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = calculate_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0, abs=0.01)
    
    def test_opposite_vectors_return_negative_one(self):
        """Opposite vectors should have similarity of -1.0"""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [-1.0, -2.0, -3.0]
        similarity = calculate_similarity(vec1, vec2)
        assert similarity == pytest.approx(-1.0, abs=0.01)
    
    def test_similar_vectors_return_high_score(self):
        """Similar vectors should have high positive similarity"""
        vec1 = [1.0, 2.0, 3.0, 4.0, 5.0]
        vec2 = [1.1, 2.1, 2.9, 4.1, 4.9]  # Slightly perturbed
        similarity = calculate_similarity(vec1, vec2)
        assert similarity > 0.95
        assert similarity <= 1.0
    
    def test_returns_float_type(self):
        """Similarity should return float, not numpy type"""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = calculate_similarity(vec1, vec2)
        assert isinstance(similarity, float)
        assert not isinstance(similarity, np.floating)
    
    def test_handles_numpy_arrays(self):
        """Should accept numpy arrays as input"""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([1.0, 2.0, 3.0])
        similarity = calculate_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0, abs=0.01)
    
    def test_handles_lists(self):
        """Should accept Python lists as input"""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = calculate_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0, abs=0.01)
    
    def test_handles_high_dimensional_vectors(self):
        """Should work with 1024-dim vectors (NV-CLIP size)"""
        vec1 = np.random.rand(1024).tolist()
        vec2 = vec1.copy()  # Identical
        similarity = calculate_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0, abs=0.01)
    
    def test_normalized_vectors(self):
        """Should work with pre-normalized vectors"""
        # Unit vectors
        vec1 = [0.707, 0.707, 0.0]  # sqrt(2)/2
        vec2 = [0.707, 0.0, 0.707]
        similarity = calculate_similarity(vec1, vec2)
        assert -1.0 <= similarity <= 1.0
    
    def test_zero_vector_raises_error(self):
        """Zero vectors should raise ValueError or return NaN"""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        with pytest.raises((ValueError, ZeroDivisionError)):
            calculate_similarity(vec1, vec2)


class TestGetScoreColor:
    """Test score color code mapping."""
    
    def test_strong_score_returns_green(self):
        """Scores ≥ 0.7 should return 'green'"""
        assert get_score_color(0.7) == 'green'
        assert get_score_color(0.75) == 'green'
        assert get_score_color(0.9) == 'green'
        assert get_score_color(1.0) == 'green'
    
    def test_moderate_score_returns_yellow(self):
        """Scores 0.5-0.7 should return 'yellow'"""
        assert get_score_color(0.5) == 'yellow'
        assert get_score_color(0.6) == 'yellow'
        assert get_score_color(0.69) == 'yellow'
    
    def test_weak_score_returns_gray(self):
        """Scores < 0.5 should return 'gray'"""
        assert get_score_color(0.0) == 'gray'
        assert get_score_color(0.3) == 'gray'
        assert get_score_color(0.49) == 'gray'
    
    def test_boundary_values(self):
        """Test exact boundary values"""
        # 0.7 boundary (strong vs moderate)
        assert get_score_color(0.699999) == 'yellow'
        assert get_score_color(0.7) == 'green'
        
        # 0.5 boundary (moderate vs weak)
        assert get_score_color(0.499999) == 'gray'
        assert get_score_color(0.5) == 'yellow'
    
    def test_negative_scores_return_gray(self):
        """Negative scores (dissimilar) should return 'gray'"""
        assert get_score_color(-0.5) == 'gray'
        assert get_score_color(-1.0) == 'gray'
    
    def test_returns_string(self):
        """Should return string type"""
        result = get_score_color(0.8)
        assert isinstance(result, str)
    
    def test_lowercase_output(self):
        """Color strings should be lowercase"""
        assert get_score_color(0.8).islower()
        assert get_score_color(0.6).islower()
        assert get_score_color(0.3).islower()


class TestGetConfidenceLevel:
    """Test confidence level label generation."""
    
    def test_strong_confidence(self):
        """Scores ≥ 0.7 should return 'strong'"""
        assert get_confidence_level(0.7) == 'strong'
        assert get_confidence_level(0.8) == 'strong'
        assert get_confidence_level(1.0) == 'strong'
    
    def test_moderate_confidence(self):
        """Scores 0.5-0.7 should return 'moderate'"""
        assert get_confidence_level(0.5) == 'moderate'
        assert get_confidence_level(0.6) == 'moderate'
        assert get_confidence_level(0.69) == 'moderate'
    
    def test_weak_confidence(self):
        """Scores < 0.5 should return 'weak'"""
        assert get_confidence_level(0.0) == 'weak'
        assert get_confidence_level(0.3) == 'weak'
        assert get_confidence_level(0.49) == 'weak'
    
    def test_boundary_values(self):
        """Test exact boundary values"""
        assert get_confidence_level(0.699999) == 'moderate'
        assert get_confidence_level(0.7) == 'strong'
        assert get_confidence_level(0.499999) == 'weak'
        assert get_confidence_level(0.5) == 'moderate'
    
    def test_returns_string(self):
        """Should return string type"""
        result = get_confidence_level(0.8)
        assert isinstance(result, str)
    
    def test_lowercase_output(self):
        """Confidence levels should be lowercase"""
        assert get_confidence_level(0.8).islower()


class TestGetHexColor:
    """Test hex color code generation for UI."""
    
    def test_green_hex(self):
        """Green score should return green hex color"""
        hex_color = get_hex_color(0.8)
        assert hex_color.startswith('#')
        assert len(hex_color) == 7
        # Should be greenish (high G value)
        assert hex_color.lower() in ['#28a745', '#2ecc71', '#27ae60', '#00ff00']  # Common greens
    
    def test_yellow_hex(self):
        """Yellow score should return yellow/orange hex color"""
        hex_color = get_hex_color(0.6)
        assert hex_color.startswith('#')
        assert len(hex_color) == 7
        # Should be yellowish/orange
        assert hex_color.lower() in ['#ffc107', '#f39c12', '#ffeb3b', '#ffa500']  # Common yellows
    
    def test_gray_hex(self):
        """Gray score should return gray hex color"""
        hex_color = get_hex_color(0.3)
        assert hex_color.startswith('#')
        assert len(hex_color) == 7
        # Should be grayish
        assert hex_color.lower() in ['#6c757d', '#95a5a6', '#7f8c8d', '#808080']  # Common grays
    
    def test_returns_valid_hex_format(self):
        """All results should be valid hex colors"""
        for score in [0.0, 0.3, 0.5, 0.7, 0.9, 1.0]:
            hex_color = get_hex_color(score)
            assert hex_color.startswith('#')
            assert len(hex_color) == 7
            # Verify it's valid hex
            try:
                int(hex_color[1:], 16)
            except ValueError:
                pytest.fail(f"Invalid hex color: {hex_color}")


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_complete_scoring_workflow(self):
        """Test full workflow: similarity → color → confidence"""
        # Setup: Two similar vectors
        vec1 = [1.0, 2.0, 3.0, 4.0, 5.0]
        vec2 = [1.1, 2.0, 3.1, 3.9, 5.0]
        
        # Step 1: Calculate similarity
        score = calculate_similarity(vec1, vec2)
        assert 0.0 <= score <= 1.0
        
        # Step 2: Get color
        color = get_score_color(score)
        assert color in ['green', 'yellow', 'gray']
        
        # Step 3: Get confidence
        confidence = get_confidence_level(score)
        assert confidence in ['strong', 'moderate', 'weak']
        
        # Step 4: Get hex color
        hex_color = get_hex_color(score)
        assert hex_color.startswith('#')
        
        # Validate consistency
        if score >= 0.7:
            assert color == 'green'
            assert confidence == 'strong'
        elif score >= 0.5:
            assert color == 'yellow'
            assert confidence == 'moderate'
        else:
            assert color == 'gray'
            assert confidence == 'weak'
    
    def test_medical_image_search_scenario(self):
        """Simulate realistic medical image search scores"""
        # Simulate NV-CLIP embeddings (1024-dim)
        query_embedding = np.random.rand(1024)
        
        # Simulate 5 image embeddings with varying similarity
        image_embeddings = [
            query_embedding + np.random.rand(1024) * 0.1,  # Very similar
            query_embedding + np.random.rand(1024) * 0.3,  # Moderately similar
            query_embedding + np.random.rand(1024) * 0.5,  # Less similar
            np.random.rand(1024),                           # Random (dissimilar)
            -query_embedding                                 # Opposite
        ]
        
        results = []
        for img_emb in image_embeddings:
            score = calculate_similarity(query_embedding.tolist(), img_emb.tolist())
            color = get_score_color(score)
            confidence = get_confidence_level(score)
            results.append({
                'score': score,
                'color': color,
                'confidence': confidence
            })
        
        # Validate all results are valid
        for result in results:
            assert -1.0 <= result['score'] <= 1.0
            assert result['color'] in ['green', 'yellow', 'gray']
            assert result['confidence'] in ['strong', 'moderate', 'weak']


# Fixtures for reusable test data
@pytest.fixture
def sample_embeddings():
    """Provide sample NV-CLIP-like embeddings."""
    return {
        'query': np.random.rand(1024).tolist(),
        'similar': (np.random.rand(1024) * 1.1).tolist(),
        'different': np.random.rand(1024).tolist(),
    }


@pytest.fixture
def score_examples():
    """Provide example scores for each category."""
    return {
        'strong': [0.7, 0.8, 0.9, 1.0],
        'moderate': [0.5, 0.55, 0.6, 0.65],
        'weak': [0.0, 0.1, 0.3, 0.49]
    }


# Parametrized tests for comprehensive coverage
@pytest.mark.parametrize("score,expected_color", [
    (1.0, 'green'),
    (0.85, 'green'),
    (0.7, 'green'),
    (0.69, 'yellow'),
    (0.6, 'yellow'),
    (0.5, 'yellow'),
    (0.49, 'gray'),
    (0.3, 'gray'),
    (0.0, 'gray'),
    (-0.5, 'gray'),
])
def test_score_color_mapping(score, expected_color):
    """Test all score-to-color mappings."""
    assert get_score_color(score) == expected_color


@pytest.mark.parametrize("score,expected_confidence", [
    (1.0, 'strong'),
    (0.75, 'strong'),
    (0.7, 'strong'),
    (0.65, 'moderate'),
    (0.5, 'moderate'),
    (0.45, 'weak'),
    (0.0, 'weak'),
])
def test_score_confidence_mapping(score, expected_confidence):
    """Test all score-to-confidence mappings."""
    assert get_confidence_level(score) == expected_confidence
