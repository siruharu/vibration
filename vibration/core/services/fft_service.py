"""
진동 분석을 위한 FFT 서비스.

fft_engine.FFTEngine을 래핑하여 신호 처리 비즈니스 로직을 제공합니다.
Qt 의존성 없음 - 순수 Python/NumPy 구현.
"""

import sys
from pathlib import Path
from typing import Optional, Literal

import numpy as np

from .fft_engine import FFTEngine
from vibration.core.domain.models import FFTResult


ViewType = Literal['ACC', 'VEL', 'DIS']
WindowType = Literal['hanning', 'flattop', 'hamming', 'blackman', 'rectangular']


class FFTService:
    """
    FFT 연산과 신호 변환을 위한 서비스 레이어.
    
    FFTEngine을 래핑하여 다음 비즈니스 로직을 제공합니다:
    - 시간 영역 신호에서 주파수 스펙트럼 계산
    - 가속도, 속도, 변위 간 변환
    - 저주파 필터링을 위한 제로 패딩 적용
    
    인자:
        sampling_rate: 샘플링 레이트 (Hz).
        delta_f: 주파수 분해능 (Hz).
        overlap: 오버랩 비율 (0-100).
        window_type: 윈도우 함수 유형.
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
        시간 영역 신호에서 FFT 스펙트럼을 계산합니다.
        
        인자:
            data: 시간 영역 신호 데이터 (1차원 배열).
            view_type: 원하는 출력 유형 ('ACC', 'VEL', 'DIS').
            input_signal_type: 입력 신호 유형 ('ACC', 'VEL', 'DIS').
            zero_padding_freq: 이 값 이하의 주파수를 제로 처리 (Hz).
        
        반환:
            주파수 및 스펙트럼 데이터가 포함된 FFTResult.
        
        예외:
            ValueError: 데이터가 FFT 연산에 필요한 길이보다 짧은 경우.
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
        주파수 영역 적분/미분을 통한 신호 유형 간 스펙트럼 변환.
        
        mdl_FFT_N 변환 로직 기반:
        - ACC -> VEL: jω로 나눔 (적분)
        - ACC -> DIS: (jω)²으로 나눔 (이중 적분)
        - VEL -> ACC: jω를 곱함 (미분)
        - VEL -> DIS: jω로 나눔 (적분)
        - DIS -> ACC: (jω)²를 곱함 (이중 미분)
        - DIS -> VEL: jω를 곱함 (미분)
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
        """차단 주파수 이하의 스펙트럼 값을 제로 처리합니다."""
        result = spectrum.copy()
        mask = frequency < (cutoff_freq + 0.01)
        result[mask] = 0
        return result
    
    def get_parameters(self) -> dict:
        """현재 FFT 파라미터를 반환합니다."""
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
