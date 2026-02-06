"""Example test to verify pytest setup."""
import numpy as np


def test_example_passes():
    """Verify pytest is working."""
    assert 1 + 1 == 2


def test_numpy_available():
    """Verify NumPy is available."""
    arr = np.array([1, 2, 3])
    assert len(arr) == 3


def test_fixture_usage(sample_signal):
    """Verify fixtures work."""
    assert len(sample_signal) == 1024
