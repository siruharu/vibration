"""Shared pytest fixtures for vibration analysis tests."""
import pytest
import numpy as np


@pytest.fixture
def sample_signal():
    """Generate sample signal for testing."""
    return np.random.randn(1024)


@pytest.fixture
def sample_sampling_rate():
    """Standard sampling rate for tests."""
    return 10240.0
