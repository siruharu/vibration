"""
Domain models for vibration analysis.

Dataclasses representing core business entities.
These models are framework-agnostic and have NO Qt dependencies.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Union
from datetime import datetime

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


@dataclass
class TrendResult:
    """
    Result of trend analysis across multiple files.
    
    Contains aggregated RMS trend data from batch processing.
    
    Attributes:
        timestamps: Timestamps for each data point (datetime or index).
        rms_values: RMS values for each file.
        filenames: List of processed filenames.
        view_type: Signal type of output ('ACC', 'VEL', 'DIS').
        frequency_band: (min_freq, max_freq) band filter applied.
        channel_data: Per-channel aggregated data.
        peak_values: Peak values for each file (optional).
        peak_frequencies: Peak frequencies for each file (optional).
        sampling_rate: Common sampling rate (Hz).
        metadata: Additional analysis metadata.
    """
    timestamps: Union[np.ndarray, List[Union[datetime, int]]]
    rms_values: np.ndarray
    filenames: List[str]
    view_type: str
    frequency_band: Optional[Tuple[float, float]] = None
    channel_data: Optional[Dict[str, Dict[str, Any]]] = None
    peak_values: Optional[np.ndarray] = None
    peak_frequencies: Optional[np.ndarray] = None
    sampling_rate: float = 0.0
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize fields after initialization."""
        if isinstance(self.view_type, str):
            self.view_type = self.view_type.upper()
        
        if self.metadata is None:
            self.metadata = {}
        
        # Convert lists to numpy arrays if needed
        if isinstance(self.rms_values, list):
            self.rms_values = np.array(self.rms_values)
        
        if self.peak_values is not None and isinstance(self.peak_values, list):
            self.peak_values = np.array(self.peak_values)
        
        if self.peak_frequencies is not None and isinstance(self.peak_frequencies, list):
            self.peak_frequencies = np.array(self.peak_frequencies)
    
    @property
    def num_files(self) -> int:
        """Get number of processed files."""
        return len(self.filenames)
    
    @property
    def mean_rms(self) -> float:
        """Get mean RMS value across all files."""
        if len(self.rms_values) > 0:
            return float(np.mean(self.rms_values))
        return 0.0
    
    @property
    def max_rms(self) -> float:
        """Get maximum RMS value."""
        if len(self.rms_values) > 0:
            return float(np.max(self.rms_values))
        return 0.0
    
    @property
    def min_rms(self) -> float:
        """Get minimum RMS value."""
        if len(self.rms_values) > 0:
            return float(np.min(self.rms_values))
        return 0.0
    
    @property
    def std_rms(self) -> float:
        """Get standard deviation of RMS values."""
        if len(self.rms_values) > 1:
            return float(np.std(self.rms_values))
        return 0.0
    
    @property
    def success_count(self) -> int:
        """Get count of successfully processed files."""
        # RMS value of 0 typically indicates failure
        return int(np.sum(self.rms_values > 0))


@dataclass
class FileMetadata:
    """
    Metadata for a loaded vibration data file.
    
    Contains file system information and parsed metadata from file header.
    
    Attributes:
        filename: Name of the file (without path).
        filepath: Full absolute path to the file.
        size: File size in bytes.
        date_modified: Last modification timestamp.
        num_channels: Number of data channels in file.
        sampling_rate: Sampling rate in Hz.
        sensitivity: Sensor sensitivity (optional, mV/g).
        b_sensitivity: B-weighting sensitivity (optional).
        duration: Recording duration in seconds.
        channel: Channel identifier/name.
        metadata: Additional raw metadata from file.
    """
    filename: str
    filepath: str
    size: int
    date_modified: str
    num_channels: int = 1
    sampling_rate: float = 0.0
    sensitivity: Optional[float] = None
    b_sensitivity: Optional[float] = None
    duration: Optional[float] = None
    channel: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize fields after initialization."""
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def size_kb(self) -> float:
        """Get file size in kilobytes."""
        return self.size / 1024.0
    
    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.size / (1024.0 * 1024.0)
    
    @property
    def has_sensitivity(self) -> bool:
        """Check if sensitivity is defined."""
        return self.sensitivity is not None and self.sensitivity > 0
