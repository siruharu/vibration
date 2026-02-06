"""
FFT Service for vibration analysis.

Wraps fft_engine.FFTEngine with business logic for signal processing.
NO Qt dependencies - pure Python/NumPy implementation.
"""

import sys
from pathlib import Path
from typing import Optional, Literal

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from fft_engine import FFTEngine
from vibration.core.domain.models import FFTResult


ViewType = Literal['ACC', 'VEL', 'DIS']
WindowType = Literal['hanning', 'flattop', 'hamming', 'blackman', 'rectangular']


class FFTService:
    """
    Service layer for FFT computation with signal conversion.
    
    Wraps FFTEngine and provides business logic for:
    - Computing frequency spectrum from time-domain signals
    - Converting between acceleration, velocity, and displacement
    - Applying zero padding for low-frequency filtering
    
    Args:
        sampling_rate: Sampling rate in Hz.
        delta_f: Frequency resolution in Hz.
        overlap: Overlap percentage (0-100).
        window_type: Window function type.
    """
    
    VIEW_TYPE_MAP = {'ACC': 1, 'VEL': 2, 'DIS': 3}
    VIEW_TYPE_REVERSE = {1: 'ACC', 2: 'VEL', 3: 'DIS'}
    
    def __init__(
        self,
        sampling_rate: float,
        delta_f: float,
        overlap: float,
        window_type: WindowType = 'hanning'
    ):
        self.sampling_rate = sampling_rate
        self.delta_f = delta_f
        self.overlap = overlap
        self.window_type = window_type.lower()
        
        self._engine = FFTEngine(
            sampling_rate=sampling_rate,
            delta_f=delta_f,
            overlap=overlap,
            window_type=window_type
        )
    
    def compute_spectrum(
        self,
        data: np.ndarray,
        view_type: ViewType = 'ACC',
        input_signal_type: ViewType = 'ACC',
        zero_padding_freq: float = 0.0
    ) -> FFTResult:
        """
        Compute FFT spectrum from time-domain signal.
        
        Args:
            data: Time-domain signal data (1D array).
            view_type: Desired output type ('ACC', 'VEL', 'DIS').
            input_signal_type: Type of input signal ('ACC', 'VEL', 'DIS').
            zero_padding_freq: Zero out frequencies below this value (Hz).
        
        Returns:
            FFTResult with frequency and spectrum data.
        
        Raises:
            ValueError: If data is too short for FFT computation.
        """
        data = np.asarray(data).flatten()
        
        if len(data) < self._engine.nfft:
            raise ValueError(
                f"Data length ({len(data)}) is shorter than required NFFT ({self._engine.nfft})"
            )
        
        result = self._engine.compute(data, view_type=1, type_flag=2)
        
        frequency = result['frequency']
        spectrum = result['spectrum'].copy()
        
        spectrum = self._apply_signal_conversion(
            spectrum, frequency, input_signal_type, view_type
        )
        
        if zero_padding_freq > 0:
            spectrum = self._apply_zero_padding(spectrum, frequency, zero_padding_freq)
        
        spectrum[0] = 0
        
        return FFTResult(
            frequency=frequency,
            spectrum=spectrum,
            view_type=view_type,
            window_type=self.window_type,
            sampling_rate=self.sampling_rate,
            delta_f=self.delta_f,
            overlap=self.overlap,
            acf=result.get('acf', 1.0),
            ecf=result.get('ecf', 1.0),
            rms=result.get('rms', 0.0),
            psd=result.get('psd'),
            metadata={'input_signal_type': input_signal_type}
        )
    
    def _apply_signal_conversion(
        self,
        spectrum: np.ndarray,
        frequency: np.ndarray,
        from_type: ViewType,
        to_type: ViewType
    ) -> np.ndarray:
        """
        Convert spectrum between signal types using frequency-domain integration/differentiation.
        
        Based on mdl_FFT_N conversion logic:
        - ACC -> VEL: divide by jω (integrate)
        - ACC -> DIS: divide by (jω)² (double integrate)
        - VEL -> ACC: multiply by jω (differentiate)
        - VEL -> DIS: divide by jω (integrate)
        - DIS -> ACC: multiply by (jω)² (double differentiate)
        - DIS -> VEL: multiply by jω (differentiate)
        """
        if from_type == to_type:
            return spectrum
        
        iomega = 1j * 2 * np.pi * frequency
        
        from_idx = self.VIEW_TYPE_MAP[from_type]
        to_idx = self.VIEW_TYPE_MAP[to_type]
        
        result = np.empty_like(spectrum, dtype=complex)
        result[0] = 0
        
        if from_idx == 1 and to_idx == 2:
            result[1:] = spectrum[1:] / iomega[1:]
            result = np.abs(result) * 1000
        elif from_idx == 1 and to_idx == 3:
            result[1:] = spectrum[1:] / (iomega[1:] ** 2)
            result = np.abs(result) * 1000
        elif from_idx == 2 and to_idx == 1:
            result = spectrum * iomega
            result = np.abs(result) / 1000
        elif from_idx == 2 and to_idx == 3:
            result[1:] = spectrum[1:] / iomega[1:]
            result = np.abs(result)
        elif from_idx == 3 and to_idx == 1:
            result = spectrum * (iomega ** 2)
            result = np.abs(result) / 1000
        elif from_idx == 3 and to_idx == 2:
            result = spectrum * iomega
            result = np.abs(result)
        
        return np.real(result)
    
    def _apply_zero_padding(
        self,
        spectrum: np.ndarray,
        frequency: np.ndarray,
        cutoff_freq: float
    ) -> np.ndarray:
        """Zero out spectrum values below cutoff frequency."""
        result = spectrum.copy()
        mask = frequency < (cutoff_freq + 0.01)
        result[mask] = 0
        return result
    
    def get_parameters(self) -> dict:
        """Get current FFT parameters."""
        return {
            'sampling_rate': self.sampling_rate,
            'delta_f': self.delta_f,
            'overlap': self.overlap,
            'window_type': self.window_type,
            'nfft': self._engine.nfft,
            'noverlap': self._engine.noverlap
        }


if __name__ == "__main__":
    print("FFT Service Test")
    print("=" * 50)
    
    svc = FFTService(sampling_rate=10240.0, delta_f=1.0, overlap=50.0)
    
    t = np.linspace(0, 1, 10240)
    signal = np.sin(2 * np.pi * 100 * t) + 0.1 * np.random.randn(len(t))
    
    result = svc.compute_spectrum(signal, view_type='ACC')
    
    print(f"Frequency points: {result.num_points}")
    print(f"Peak frequency: {result.peak_frequency:.1f} Hz")
    print(f"Peak amplitude: {result.peak_amplitude:.6f}")
    print(f"View type: {result.view_type}")
    print(f"Window: {result.window_type}")
    
    assert 'frequency' in result.__dict__
    assert 'spectrum' in result.__dict__
    print("\nFFT Service OK")
