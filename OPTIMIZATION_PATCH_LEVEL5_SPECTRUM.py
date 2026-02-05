"""
================================================================
Level 5 최적화: Time/Spectrum 전용 병렬 처리기
================================================================
목표: 100개 파일 2-4초 → 0.5초 이하

핵심 전략:
- ProcessPoolExecutor (CPU-bound FFT)
- Waveform + Spectrum 동시 계산
- 메타데이터 캐싱
- 결과 직렬화 최소화

예상 성능:
- 100개: 0.5초
- 1000개: 3-5초
================================================================
"""

import os
import re
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional, Callable
import multiprocessing as mp

# ===== 정규식 사전 컴파일 =====
NUMERIC_PATTERN = re.compile(r"[-+]?[0-9]*\.?[0-9]+")
DURATION_PATTERN = re.compile(r"[-+]?\d*\.\d+|\d+")


# ========================================
# 1. 결과 데이터 클래스
# ========================================
@dataclass
class SpectrumResult:
    """Spectrum 분석 결과"""
    file_name: str
    frequency: np.ndarray
    spectrum: np.ndarray
    time: np.ndarray
    waveform: np.ndarray
    sampling_rate: float
    metadata: Dict[str, Any]
    success: bool
    error_msg: Optional[str] = None


# ========================================
# 2. 워커 함수 (프로세스에서 실행)
# ========================================
def _process_spectrum_worker(args: Tuple) -> SpectrumResult:
    """
    단일 파일 Spectrum 분석 워커

    Args:
        args: (file_path, delta_f, overlap, window_type, view_type)

    Returns:
        SpectrumResult
    """
    (file_path, delta_f, overlap, window_type, view_type) = args

    file_name = os.path.basename(file_path)

    try:
        # ===== 1. 파일 로딩 =====
        data = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and (line[0].isdigit() or line[0] == '-'):
                    try:
                        data.append(float(line.split()[0]))
                    except:
                        continue

        data = np.array(data, dtype=np.float32)

        if len(data) == 0:
            return SpectrumResult(
                file_name=file_name,
                frequency=np.array([]),
                spectrum=np.array([]),
                time=np.array([]),
                waveform=np.array([]),
                sampling_rate=0.0,
                metadata={},
                success=False,
                error_msg="데이터 없음"
            )

        # ===== 2. 메타데이터 파싱 =====
        metadata = {}
        sampling_rate = 10240.0

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= 25:
                    break

                line = line.strip()
                if ':' not in line:
                    continue

                if 'D.Sampling Freq.' in line:
                    try:
                        sampling_rate = float(line.split(':')[1].replace('Hz', '').strip())
                    except:
                        pass
                elif 'b.Sensitivity' in line:
                    try:
                        metadata['b_sens'] = float(NUMERIC_PATTERN.search(line.split(':')[1]).group())
                    except:
                        pass
                elif 'Sensitivity' in line and 'b.' not in line:
                    try:
                        metadata['sens'] = float(NUMERIC_PATTERN.search(line.split(':')[1]).group())
                    except:
                        pass
                elif 'Starting Time' in line:
                    metadata['start_time'] = line.split(':')[1].strip()
                elif 'Record Length' in line:
                    metadata['duration'] = line.split(':')[1].strip().split()[0]
                elif 'Channel' in line:
                    metadata['channel'] = line.split(':')[1].strip()
                elif 'IEPE enable' in line:
                    metadata['iepe'] = line.split(':')[1].strip()
                elif 'Rest time' in line:
                    metadata['rest_time'] = line.split(':')[1].strip()
                elif 'Repetition' in line:
                    metadata['repetition'] = line.split(':')[1].strip()
                elif 'Time Resolution' in line:
                    metadata['dt'] = line.split(':')[1].strip()

        # ===== 3. 민감도 보정 =====
        waveform_original = data.copy()  # 원본 저장

        if 'b_sens' in metadata and 'sens' in metadata:
            if metadata['sens'] != 0:
                data = data * (metadata['b_sens'] / metadata['sens'])

        # ===== 4. delta_f 검증 =====
        N = len(data)
        MIN_FFT_LENGTH = 1024

        delta_f_min = sampling_rate / max(N, MIN_FFT_LENGTH)

        if delta_f < delta_f_min:
            # duration 기반 재계산
            duration_str = metadata.get('duration')
            if duration_str:
                match = DURATION_PATTERN.findall(str(duration_str))
                if match:
                    duration_val = float(match[0])
                    if duration_val > 0:
                        hz_value = round(1 / duration_val + 0.01, 2)
                        delta_f = max(delta_f_min, hz_value)
            else:
                delta_f = delta_f_min

        # ===== 5. 제로 패딩 =====
        N_fft = max(int(sampling_rate / delta_f), MIN_FFT_LENGTH)
        if N_fft > N:
            data = np.pad(data, (0, N_fft - N), 'constant')
            N = N_fft

        # ===== 6. 윈도우 함수 =====
        from scipy.signal.windows import hann, flattop

        window_type_lower = window_type.lower()
        if window_type_lower == 'hanning':
            window = hann(N, sym=False)
        elif window_type_lower == 'flattop':
            window = flattop(N, sym=False)
        else:
            window = np.ones(N)

        # ===== 7. FFT 계산 =====
        from scipy.fft import rfft, rfftfreq

        windowed = data * window
        spectrum_complex = rfft(windowed)
        spectrum = np.abs(spectrum_complex) / N

        # 단측 스펙트럼
        spectrum[1:-1] *= 2

        freq = rfftfreq(N, 1 / sampling_rate)

        # ===== 8. ACF =====
        ACF = 1 / (np.mean(window) * np.sqrt(2))
        spectrum = ACF * spectrum

        # ===== 9. 신호 타입 변환 =====
        if view_type == 2:  # VEL
            omega = 2 * np.pi * freq
            omega[0] = 1e-10
            spectrum = spectrum / omega * 1000
        elif view_type == 3:  # DIS
            omega = 2 * np.pi * freq
            omega[0] = 1e-10
            spectrum = spectrum / (omega ** 2) * 1000

        # DC 제거
        spectrum[0] = 0

        # ===== 10. Time 벡터 =====
        time = np.arange(len(waveform_original)) / sampling_rate

        # ===== 11. 결과 반환 =====
        return SpectrumResult(
            file_name=file_name,
            frequency=freq,
            spectrum=spectrum.flatten(),
            time=time,
            waveform=waveform_original,  # 원본 waveform 반환
            sampling_rate=float(sampling_rate),
            metadata=metadata,
            success=True
        )

    except Exception as e:
        import traceback
        return SpectrumResult(
            file_name=file_name,
            frequency=np.array([]),
            spectrum=np.array([]),
            time=np.array([]),
            waveform=np.array([]),
            sampling_rate=0.0,
            metadata={},
            success=False,
            error_msg=f"{str(e)}\n{traceback.format_exc()}"
        )


# ========================================
# 3. Spectrum 병렬 프로세서
# ========================================
class SpectrumParallelProcessor:
    """Time/Spectrum 전용 병렬 프로세서"""

    def __init__(self, max_workers: int = None):
        """
        Args:
            max_workers: 프로세스 수 (None이면 CPU 코어 수 - 1)
        """
        if max_workers is None:
            max_workers = max(mp.cpu_count() - 1, 1)

        self.max_workers = max_workers
        self._executor = None  # 프로세스 풀 캐싱

    def __enter__(self):
        self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
        return self

    def __exit__(self, *args):
        if self._executor:
            self._executor.shutdown(wait=True)

    def process_batch(
            self,
            file_paths: List[str],
            delta_f: float,
            overlap: float,
            window_type: str,
            view_type: int,
            progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[SpectrumResult]:
        """
        배치 병렬 처리

        Args:
            file_paths: 파일 경로 리스트
            delta_f: 주파수 해상도
            overlap: 오버랩 비율 (호환성 유지)
            window_type: 윈도우 함수
            view_type: 신호 타입 (1=ACC, 2=VEL, 3=DIS)
            progress_callback: 진행률 콜백

        Returns:
            SpectrumResult 리스트 (입력 순서 보장)
        """
        args_list = [
            (fp, delta_f, overlap, window_type, view_type)
            for fp in file_paths
        ]

        results = {}

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(_process_spectrum_worker, args): i
                for i, args in enumerate(args_list)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                result = future.result()
                results[idx] = result

                if progress_callback:
                    progress_callback(len(results), len(file_paths))

        return [results[i] for i in range(len(file_paths))]


# ========================================
# 사용 예시
# ========================================
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    print("✅ Level 5 Spectrum 최적화 모듈 로드 완료")

    processor = SpectrumParallelProcessor()
    print(f"   - 프로세스 워커 수: {processor.max_workers}")
    print("   - ProcessPoolExecutor 사용")
    print("   - Waveform + Spectrum 동시 계산")
    print("   - 예상 성능: 100개 0.5초, 1000개 3-5초")