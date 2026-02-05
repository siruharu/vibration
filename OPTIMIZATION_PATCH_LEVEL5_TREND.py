"""
================================================================
Level 5 최적화: Trend 전용 병렬 처리기
================================================================
목표: 1000개 파일 18분 → 2-3분 (6배 개선)

핵심 전략:
- ProcessPoolExecutor (CPU-bound 작업)
- 파일 로딩 + FFT + RMS 계산을 워커에서 한 번에 처리
- 메타데이터 파싱 최소화 (상위 25줄만)
- NumPy 직접 사용 (중간 변환 제거)

예상 성능:
- 1000개: 2-3분
- 10000개: 20-30분
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


# ========================================
# 1. 결과 데이터 클래스
# ========================================
@dataclass
class TrendResult:
    """Trend 분석 결과"""
    file_name: str
    rms_value: float
    peak_value: float
    peak_freq: float
    sampling_rate: float
    metadata: Dict[str, Any]
    success: bool
    error_msg: Optional[str] = None


# ========================================
# 2. 워커 함수 (프로세스에서 실행)
# ========================================
def _process_trend_worker(args: Tuple) -> TrendResult:
    """
    단일 파일 처리 워커

    Args:
        args: (file_path, delta_f, overlap, window_type,
               view_type, band_min, band_max)

    Returns:
        TrendResult
    """
    (file_path, delta_f, overlap, window_type,
     view_type, band_min, band_max) = args

    file_name = os.path.basename(file_path)

    try:
        # ===== 1. 파일 로딩 (NumPy 직접) =====
        # 숫자 데이터만 추출 (주석 제외)
        data = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                # 숫자로 시작하는 줄만
                if line and (line[0].isdigit() or line[0] == '-'):
                    try:
                        data.append(float(line.split()[0]))
                    except:
                        continue

        data = np.array(data, dtype=np.float32)

        if len(data) == 0:
            return TrendResult(
                file_name=file_name,
                rms_value=0.0, peak_value=0.0, peak_freq=0.0,
                sampling_rate=0.0, metadata={},
                success=False, error_msg="데이터 없음"
            )

        # ===== 2. 메타데이터 파싱 (상위 25줄만) =====
        metadata = {}
        sampling_rate = 10240.0  # 기본값

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= 25:  # 헤더는 보통 상위 25줄 내
                    break

                line = line.strip()
                if ':' not in line:
                    continue

                # 필수 메타데이터만 추출
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

        # ===== 3. 민감도 보정 =====
        if 'b_sens' in metadata and 'sens' in metadata:
            if metadata['sens'] != 0:
                data = data * (metadata['b_sens'] / metadata['sens'])

        # ===== 4. FFT 준비 =====
        N = len(data)
        MIN_FFT_LENGTH = 1024

        # delta_f 검증
        delta_f_min = sampling_rate / max(N, MIN_FFT_LENGTH)
        if delta_f < delta_f_min:
            delta_f = delta_f_min

        # 제로 패딩
        N_fft = max(int(sampling_rate / delta_f), MIN_FFT_LENGTH)
        if N_fft > N:
            data = np.pad(data, (0, N_fft - N), 'constant')
            N = N_fft

        # ===== 5. 윈도우 함수 =====
        from scipy.signal.windows import hann, flattop

        if window_type == 'hanning':
            window = hann(N, sym=False)
        elif window_type == 'flattop':
            window = flattop(N, sym=False)
        else:  # rectangular
            window = np.ones(N)

        # ===== 6. FFT 계산 =====
        from scipy.fft import rfft, rfftfreq

        # 윈도우 적용
        windowed = data * window

        # FFT
        spectrum_complex = rfft(windowed)
        spectrum = np.abs(spectrum_complex) / N

        # 단측 스펙트럼 (DC와 Nyquist 제외하고 2배)
        spectrum[1:-1] *= 2

        # 주파수 벡터
        freq = rfftfreq(N, 1 / sampling_rate)

        # ===== 7. ACF (Amplitude Correction Factor) =====
        ACF = 1 / (np.mean(window) * np.sqrt(2))
        spectrum = ACF * spectrum

        # ===== 8. 신호 타입 변환 (ACC → VEL/DIS) =====
        if view_type == 2:  # VEL
            # ω = 2πf, V = A / (jω)
            omega = 2 * np.pi * freq
            omega[0] = 1e-10  # DC 방지
            spectrum = spectrum / omega * 1000  # mm/s
        elif view_type == 3:  # DIS
            # D = A / (jω)^2
            omega = 2 * np.pi * freq
            omega[0] = 1e-10
            spectrum = spectrum / (omega ** 2) * 1000  # μm

        # ===== 9. Band 필터링 =====
        mask = (freq >= band_min) & (freq <= band_max)
        spectrum_band = spectrum[mask]
        freq_band = freq[mask]

        if len(spectrum_band) == 0:
            return TrendResult(
                file_name=file_name,
                rms_value=0.0, peak_value=0.0, peak_freq=0.0,
                sampling_rate=sampling_rate, metadata=metadata,
                success=False, error_msg="Band 범위 내 데이터 없음"
            )

        # ===== 10. RMS & Peak 계산 =====
        # RMS: √(∑P²)
        rms_value = np.sqrt(np.sum(spectrum_band ** 2))

        # Peak
        peak_idx = np.argmax(spectrum_band)
        peak_value = spectrum_band[peak_idx]
        peak_freq = freq_band[peak_idx]

        # ===== 11. 결과 반환 =====
        return TrendResult(
            file_name=file_name,
            rms_value=float(rms_value),
            peak_value=float(peak_value),
            peak_freq=float(peak_freq),
            sampling_rate=float(sampling_rate),
            metadata=metadata,
            success=True
        )

    except Exception as e:
        import traceback
        return TrendResult(
            file_name=file_name,
            rms_value=0.0, peak_value=0.0, peak_freq=0.0,
            sampling_rate=0.0, metadata={},
            success=False,
            error_msg=f"{str(e)}\n{traceback.format_exc()}"
        )


# ========================================
# 3. Trend 병렬 프로세서
# ========================================
class TrendParallelProcessor:
    """Trend 전용 병렬 프로세서 (ProcessPoolExecutor)"""

    def __init__(self, max_workers: int = None):
        """
        Args:
            max_workers: 프로세스 수 (None이면 CPU 코어 수 - 1)
        """
        if max_workers is None:
            # CPU 코어 수 - 1 (시스템 여유 확보)
            max_workers = max(mp.cpu_count() - 1, 1)

        self.max_workers = max_workers

    def process_batch(
            self,
            file_paths: List[str],
            delta_f: float,
            overlap: float,
            window_type: str,
            view_type: int,
            band_min: float,
            band_max: float,
            progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[TrendResult]:
        """
        배치 병렬 처리

        Args:
            file_paths: 파일 경로 리스트
            delta_f: 주파수 해상도
            overlap: 오버랩 비율 (사용 안 함, 호환성 유지)
            window_type: 윈도우 함수 ('hanning', 'flattop', 'rectangular')
            view_type: 신호 타입 (1=ACC, 2=VEL, 3=DIS)
            band_min: Band 최소 주파수
            band_max: Band 최대 주파수
            progress_callback: 진행률 콜백 (current, total)

        Returns:
            TrendResult 리스트 (입력 순서 보장)
        """
        # 인자 리스트 생성
        args_list = [
            (fp, delta_f, overlap, window_type.lower(),
             view_type, band_min, band_max)
            for fp in file_paths
        ]

        results = {}

        # 프로세스 풀 실행
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 작업 제출
            future_to_idx = {
                executor.submit(_process_trend_worker, args): i
                for i, args in enumerate(args_list)
            }

            # 완료된 작업 수집
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                result = future.result()
                results[idx] = result

                # 진행률 콜백
                if progress_callback:
                    progress_callback(len(results), len(file_paths))

        # 입력 순서대로 정렬
        return [results[i] for i in range(len(file_paths))]


# ========================================
# 4. JSON 저장 헬퍼 (기존과 호환)
# ========================================
def save_trend_result_to_json(
        result: TrendResult,
        directory_path: str,
        delta_f: float,
        window_type: str,
        overlap: float,
        band_min: float,
        band_max: float,
        view_type: str
) -> bool:
    """
    단일 TrendResult를 JSON 파일로 저장

    Returns:
        성공 여부
    """
    try:
        import json

        base_name = os.path.splitext(result.file_name)[0]
        save_folder = os.path.join(directory_path, 'trend_data')
        os.makedirs(save_folder, exist_ok=True)

        save_path = os.path.join(save_folder, f"{base_name}.json")

        # 채널 번호 추출
        channel_num = result.file_name.split('_')[-1].replace('.txt', '')

        trend_data = {
            "rms_value": result.rms_value,
            "peak_value": result.peak_value,
            "peak_freq": result.peak_freq,
            "delta_f": delta_f,
            "window": window_type,
            "overlap": overlap,
            "band_min": band_min,
            "band_max": band_max,
            "sampling_rate": result.sampling_rate,
            "start_time": result.metadata.get('start_time', ''),
            "duration": result.metadata.get('duration', ''),
            "channel_num": channel_num,
            "view_type": view_type,
            "filename": result.file_name,
        }

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(trend_data, f, indent=4, ensure_ascii=False)

        return True

    except Exception as e:
        print(f"⚠️ JSON 저장 실패: {result.file_name}, {e}")
        return False


# ========================================
# 5. Peak Trend 전용 워커 (RMS와 거의 동일)
# ========================================
def _process_peak_worker(args: Tuple) -> TrendResult:
    """
    Band Peak Trend 워커 (RMS와 99% 동일)
    유일한 차이: Peak 값을 메인으로 사용
    """
    # _process_trend_worker와 완전히 동일한 코드
    # (이미 peak_value, peak_freq를 계산하므로 재사용)
    return _process_trend_worker(args)


# ========================================
# 6. Peak Trend 전용 프로세서 (래퍼)
# ========================================
class PeakParallelProcessor:
    """
    Band Peak Trend 전용 프로세서
    (내부적으로 TrendParallelProcessor 재사용)
    """

    def __init__(self, max_workers: int = None):
        self.processor = TrendParallelProcessor(max_workers)

    def process_batch(
            self,
            file_paths: List[str],
            delta_f: float,
            overlap: float,
            window_type: str,
            view_type: int,
            band_min: float,
            band_max: float,
            progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[TrendResult]:
        """
        Peak Trend 배치 처리
        (RMS 프로세서와 동일하지만, Peak 값 위주로 사용)
        """
        return self.processor.process_batch(
            file_paths=file_paths,
            delta_f=delta_f,
            overlap=overlap,
            window_type=window_type,
            view_type=view_type,
            band_min=band_min,
            band_max=band_max,
            progress_callback=progress_callback
        )
# ========================================
# 사용 예시
# ========================================
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    print("✅ Level 5 Trend 최적화 모듈 로드 완료")

    processor = TrendParallelProcessor()
    print(f"   - 프로세스 워커 수: {processor.max_workers}")
    print("   - ProcessPoolExecutor 사용 (CPU-bound)")
    print("   - 파일 로딩 + FFT + RMS 통합 처리")
    print("   - 예상 성능: 1000개 2-3분, 10000개 20-30분")