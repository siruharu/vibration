"""
피크 분석 서비스.

PeakParallelProcessor를 래핑하여 배치 피크 트렌드 연산을 수행합니다.
Qt 의존성 없음 - 순수 Python/NumPy 구현.
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Callable, Literal

import numpy as np

from .OPTIMIZATION_PATCH_LEVEL5_TREND import PeakParallelProcessor
from vibration.core.domain.models import TrendResult


ViewType = Literal['ACC', 'VEL', 'DIS']
WindowType = Literal['hanning', 'flattop', 'rectangular']

VIEW_TYPE_MAP = {'ACC': 1, 'VEL': 2, 'DIS': 3}
VIEW_TYPE_REVERSE = {1: 'ACC', 2: 'VEL', 3: 'DIS'}


class PeakService:
    """
    피크 분석과 배치 처리를 위한 서비스 레이어.

    PeakParallelProcessor를 래핑하여 다음 비즈니스 로직을 제공합니다:
    - 다중 파일에 걸친 피크 트렌드 계산
    - 채널별 결과 집계
    - 파일명에서 타임스탬프 추출

    인자:
        max_workers: 병렬 워커 수 (기본값: CPU 코어 수 - 1).
    """
    
    def __init__(self, max_workers: int = None):
        """
        피크 서비스를 초기화합니다.

        인자:
            max_workers: 병렬 워커 수.
        """
        self.max_workers = max_workers
        self._processor = PeakParallelProcessor(max_workers=max_workers)
    
    def compute_peak_trend(
        self,
        file_paths: List[str],
        delta_f: float = 1.0,
        overlap: float = 50.0,
        window_type: WindowType = 'hanning',
        view_type: ViewType = 'ACC',
        frequency_band: Optional[Tuple[float, float]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> TrendResult:
        """
        다중 파일에 걸쳐 피크 트렌드를 계산합니다.

        인자:
            file_paths: 분석할 파일 경로 목록.
            delta_f: 주파수 분해능 (Hz).
            overlap: 오버랩 비율 (미사용, 호환성 유지 목적).
            window_type: 윈도우 함수 ('hanning', 'flattop', 'rectangular').
            view_type: 신호 유형 ('ACC', 'VEL', 'DIS').
            frequency_band: (min_freq, max_freq) 대역 필터.
            progress_callback: 진행률 콜백 (current, total) (선택사항).

        반환:
            피크 값을 주요 데이터로 포함하는 TrendResult (rms_values 필드에 저장).
        """
        if not file_paths:
            return TrendResult(
                timestamps=[],
                rms_values=np.array([]),
                filenames=[],
                view_type=view_type,
                frequency_band=frequency_band
            )
        
        band_min, band_max = frequency_band if frequency_band else (0.0, 5000.0)
        view_type_int = VIEW_TYPE_MAP.get(view_type.upper(), 1)
        
        raw_results = self._processor.process_batch(
            file_paths=file_paths,
            delta_f=delta_f,
            overlap=overlap,
            window_type=window_type.lower(),
            view_type=view_type_int,
            band_min=band_min,
            band_max=band_max,
            progress_callback=progress_callback
        )
        
        return self._aggregate_results(raw_results, view_type.upper(), frequency_band)
    
    def find_peaks(
        self,
        frequencies: np.ndarray,
        spectrum: np.ndarray,
        num_peaks: int = 10,
        threshold: float = 0.1
    ) -> List[Tuple[float, float]]:
        """
        스펙트럼에서 피크를 탐색합니다.

        인자:
            frequencies: 주파수 배열.
            spectrum: 스펙트럼 진폭 배열.
            num_peaks: 탐색할 피크 수.
            threshold: 최소 진폭 임계값 (최대값 대비 상대값).

        반환:
            진폭 내림차순으로 정렬된 (주파수, 진폭) 튜플 목록.
        """
        if len(spectrum) == 0:
            return []
        
        # 극대값 탐색
        peaks = []
        max_val = np.max(spectrum)
        threshold_val = max_val * threshold
        
        for i in range(1, len(spectrum) - 1):
            if spectrum[i] > spectrum[i-1] and spectrum[i] > spectrum[i+1]:
                if spectrum[i] >= threshold_val:
                    peaks.append((float(frequencies[i]), float(spectrum[i])))
        
        # 진폭 내림차순 정렬 후 상위 N개 선택
        peaks.sort(key=lambda x: x[1], reverse=True)
        return peaks[:num_peaks]
    
    def _aggregate_results(
        self,
        raw_results: List,
        view_type: str,
        frequency_band: Optional[Tuple[float, float]]
    ) -> TrendResult:
        """원시 프로세서 결과를 피크 값이 포함된 TrendResult로 집계합니다."""
        success_results = [r for r in raw_results if r.success]
        
        if not success_results:
            return TrendResult(
                timestamps=[],
                rms_values=np.array([]),
                filenames=[],
                view_type=view_type,
                frequency_band=frequency_band,
                metadata={'total_files': len(raw_results), 'failed_count': len(raw_results)}
            )
        
        filenames = []
        peak_values = []
        peak_frequencies = []
        rms_values = []
        timestamps = []
        channel_data = {}
        
        for result in success_results:
            filenames.append(result.file_name)
            peak_values.append(result.peak_value)
            peak_frequencies.append(result.peak_freq)
            rms_values.append(result.rms_value)
            
            ts = self._extract_timestamp(result.file_name)
            timestamps.append(ts)
            
            channel = self._extract_channel(result.file_name)
            if channel not in channel_data:
                channel_data[channel] = {'x': [], 'y': [], 'labels': []}
            channel_data[channel]['x'].append(ts)
            channel_data[channel]['y'].append(result.peak_value)  # Use peak_value for Y
            channel_data[channel]['labels'].append(result.file_name)
        
        sampling_rate = success_results[0].sampling_rate if success_results else 0.0
        
        # Return TrendResult with peak_values as primary (stored in rms_values for compatibility)
        return TrendResult(
            timestamps=timestamps,
            rms_values=np.array(peak_values),  # Peak values as primary metric
            filenames=filenames,
            view_type=view_type,
            frequency_band=frequency_band,
            channel_data=channel_data,
            peak_values=np.array(peak_values),
            peak_frequencies=np.array(peak_frequencies),
            sampling_rate=sampling_rate,
            metadata={
                'total_files': len(raw_results),
                'success_count': len(success_results),
                'failed_count': len(raw_results) - len(success_results),
                'original_rms_values': rms_values,
                'analysis_type': 'peak'
            }
        )
    
    def _extract_timestamp(self, filename: str) -> datetime:
        """
        파일명에서 타임스탬프를 추출합니다.

        패턴: YYYYMMDD_HHMMSS 또는 유사 형식.
        파싱 실패 시 현재 시간으로 대체합니다.
        """
        patterns = [
            r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})',
            r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})',
            r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    groups = match.groups()
                    return datetime(
                        int(groups[0]), int(groups[1]), int(groups[2]),
                        int(groups[3]), int(groups[4]), int(groups[5])
                    )
                except (ValueError, IndexError):
                    continue
        
        return datetime.now()
    
    def _extract_channel(self, filename: str) -> str:
        """파일명에서 채널 식별자를 추출합니다 (일반적으로 확장자 전 마지막 세그먼트)."""
        base = Path(filename).stem
        parts = base.split('_')
        return parts[-1] if parts else '0'
    
    def get_parameters(self) -> dict:
        """현재 프로세서 파라미터를 반환합니다."""
        return {
            'max_workers': self._processor.processor.max_workers
        }


if __name__ == "__main__":
    print("PeakService Test")
    print("=" * 50)
    
    svc = PeakService(max_workers=2)
    print(f"Max workers: {svc.get_parameters()['max_workers']}")
    
    # Test empty file list
    empty_result = svc.compute_peak_trend([], view_type='ACC')
    assert empty_result.num_files == 0
    print("Empty file list handled correctly")
    
    # Test find_peaks
    freqs = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    spectrum = np.array([0.1, 0.3, 0.2, 0.8, 0.3, 0.9, 0.2, 0.7, 0.1, 0.2, 0.1])
    peaks = svc.find_peaks(freqs, spectrum, num_peaks=3)
    assert len(peaks) <= 3
    print(f"Found {len(peaks)} peaks: {peaks}")
    
    # Verify no Qt dependency
    import sys
    assert 'PyQt5' not in sys.modules, "Qt dependency detected!"
    print("\nNo Qt dependency - OK")
    print("PeakService Test PASSED")
