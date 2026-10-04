import pytest
from main import cosine_similarity,recall_probability

def test_same_direction_is_1():
    assert cosine_similarity([1,2,3],[1,2,3]) == pytest.approx(1,0)

def test_right_angle_is_0():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0,0)

def test_opposite_direction_is_minus_1():
    assert cosine_similarity([1, 2], [-1, -2]) == pytest.approx(-1,0)

def test_length_does_not_matter():
    assert cosine_similarity([1, 2], [10, 20]) == pytest.approx(1,0)