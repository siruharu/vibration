"""
Domain models for vibration analysis.

Dataclasses representing core business entities.
These models are framework-agnostic and have NO Qt dependencies.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

import numpy as np


@dataclass
class FFTResult:
    """
    Result of FFT computation.
    
    Contains the frequency-domain representation of a time signal
    after FFT processing, along with metadata about the computation.
    
    Attributes:
        frequency: Frequency vector (Hz).
        spectrum: FFT spectrum amplitude values.
        view_type: Signal type of output ('ACC', 'VEL', 'DIS').
        window_type: Window function used ('hanning', 'flattop', 'hamming', etc).
        sampling_rate: Original sampling rate (Hz).
        delta_f: Frequency resolution (Hz).
        overlap: Overlap percentage (0-100).
        acf: Amplitude Correction Factor.
        ecf: Energy Correction Factor.
        rms: Root Mean Square value of the signal.
        psd: Power Spectral Density (optional).
        metadata: Additional computation metadata.
    """
    frequency: np.ndarray
    spectrum: np.ndarray
    view_type: str
    window_type: str
    sampling_rate: float
    delta_f: float
    overlap: float
    acf: float = 1.0
    ecf: float = 1.0
    rms: float = 0.0
    psd: Optional[np.ndarray] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize fields after initialization."""
        if isinstance(self.view_type, str):
            self.view_type = self.view_type.upper()
        
        if isinstance(self.window_type, str):
            self.window_type = self.window_type.lower()
        
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def max_frequency(self) -> float:
        """Get maximum frequency in the spectrum."""
        if len(self.frequency) > 0:
            return float(self.frequency[-1])
        return 0.0
    
    @property
    def peak_frequency(self) -> float:
        """Get frequency at maximum spectrum amplitude."""
        if len(self.spectrum) > 0:
            peak_idx = np.argmax(self.spectrum)
            return float(self.frequency[peak_idx])
        return 0.0
    
    @property
    def peak_amplitude(self) -> float:
        """Get maximum spectrum amplitude."""
        if len(self.spectrum) > 0:
            return float(np.max(self.spectrum))
        return 0.0
    
    @property
    def num_points(self) -> int:
        """Get number of frequency points."""
        return len(self.frequency)


@dataclass
class SignalData:
    """
    Raw signal data container.
    
    Represents time-domain signal data with associated metadata.
    
    Attributes:
        data: Signal amplitude values.
        sampling_rate: Sampling rate (Hz).
        signal_type: Type of signal ('ACC', 'VEL', 'DIS').
        channel: Channel identifier/name.
        metadata: Additional signal metadata.
    """
    data: np.ndarray
    sampling_rate: float
    signal_type: str = 'ACC'
    channel: str = ''
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize fields after initialization."""
        if isinstance(self.signal_type, str):
            self.signal_type = self.signal_type.upper()
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def duration(self) -> float:
        """Get signal duration in seconds."""
        if self.sampling_rate > 0:
            return len(self.data) / self.sampling_rate
        return 0.0
    
    @property
    def num_samples(self) -> int:
        """Get number of samples."""
        return len(self.data)
