import os
import re
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import time

class ThreadSafeCache:
    """스레드 안전한 파일 캐시"""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Dict] = {}
        self.lock = Lock()
        self.max_size = max_size
        self.access_count: Dict[str, int] = {}

    def get(self, key: str) -> Optional[Dict]:
        """캐시에서 데이터 가져오기"""
        with self.lock:
            if key in self.cache:
                self.access_count[key] = self.access_count.get(key, 0) + 1
                return self.cache[key].copy()
            return None

    def set(self, key: str, value: Dict):
        """캐시에 데이터 저장"""
        with self.lock:
            if len(self.cache) >= self.max_size:
                least_used = min(self.access_count.items(), key=lambda x: x[1])
                del self.cache[least_used[0]]
                del self.access_count[least_used[0]]

            self.cache[key] = value
            self.access_count[key] = 1

    def clear(self):
        """캐시 비우기"""
        with self.lock:
            self.cache.clear()
            self.access_count.clear()

@dataclass
class FileProcessResult:
    """파일 처리 결과"""
    file_name: str
    frequency: np.ndarray
    spectrum: np.ndarray
    time: np.ndarray
    waveform: np.ndarray
    sampling_rate: float
    metadata: Dict[str, Any]
    success: bool
    error_msg: Optional[str] = None

def process_single_file_parallel(
    file_name: str,
    directory_path: str,
    delta_f: float,
    overlap: float,
    window_type: str,
    view_type: int,
    cache: ThreadSafeCache,
    mdl_FFT_N_func,
    load_file_func,
) -> FileProcessResult:
    try:
        file_path = os.path.join(directory_path, file_name)

        # ===== 1. 캐시 확인 =====
        cached = cache.get(file_name)

        if cached:
            data = cached['data']
            sampling_rate = cached['sampling_rate']
            metadata = {
                'dt': cached.get('dt'),
                'start_time': cached.get('start_time'),
                'duration': cached.get('duration'),
                'rest_time': cached.get('rest_time'),
                'repetition': cached.get('repetition'),
                'channel': cached.get('channel'),
                'iepe': cached.get('iepe'),
                'b_sensitivity': cached.get('b_sensitivity'),
                'sensitivity': cached.get('sensitivity'),
            }
        else:
            # ===== 2. 파일 읽기 =====
            data, record_length = load_file_func(file_path)

            if data is None or len(data) == 0:
                return FileProcessResult(
                    file_name=file_name,
                    frequency=np.array([]),
                    spectrum=np.array([]),
                    time=np.array([]),
                    waveform=np.array([]),
                    sampling_rate=0,
                    metadata={},
                    success=False,
                    error_msg="데이터 없음"
                )

            # ===== 3. 메타데이터 파싱 =====
            sampling_rate = 10240.0
            metadata = {}

            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        if "D.Sampling Freq." in line:
                            sampling_rate = float(line.split(":")[1].strip().replace("Hz", ""))
                        elif "Time Resolution(dt)" in line:
                            metadata['dt'] = line.split(":")[1].strip()
                        elif "Starting Time" in line:
                            metadata['start_time'] = line.split(":")[1].strip()
                        elif "Record Length" in line:
                            metadata['duration'] = line.split(":")[1].strip().split()[0]
                        elif "Rest time" in line:
                            metadata['rest_time'] = line.split(":")[1].strip().split()[0]
                        elif "Repetition" in line:
                            metadata['repetition'] = line.split(":")[1].strip()
                        elif "Channel" in line:
                            metadata['channel'] = line.split(":")[1].strip()
                        elif "IEPE enable" in line:
                            metadata['iepe'] = line.split(":")[1].strip()
                        elif "b.Sensitivity" in line:
                            metadata['b_sensitivity'] = line.split(":")[1].strip()
                        elif "Sensitivity" in line and "b.Sensitivity" not in line:
                            metadata['sensitivity'] = line.split(":")[1].strip()
            except:
                pass

            # ===== 4. 캐시 저장 =====
            cache.set(file_name, {
                'data': data.copy() if isinstance(data, np.ndarray) else data,
                'sampling_rate': sampling_rate,
                **metadata
            })

        # ===== 5. 민감도 보정 =====
        b_sensitivity = metadata.get('b_sensitivity')
        sensitivity = metadata.get('sensitivity')

        if b_sensitivity and sensitivity:
            try:
                b_sens = float(re.search(r"[-+]?[0-9]*\.?[0-9]+", str(b_sensitivity)).group())
                sens = float(re.search(r"[-+]?[0-9]*\.?[0-9]+", str(sensitivity)).group())
                if sens != 0:
                    data = (b_sens / sens) * data
            except:
                pass

        # ===== 6. delta_f 검증 및 제로패딩 =====
        N = len(data)
        MIN_FFT_LENGTH = 1024

        delta_f_min = sampling_rate / max(N, MIN_FFT_LENGTH)

        if delta_f < delta_f_min:
            duration = metadata.get('duration')
            if duration:
                try:
                    duration_val = float(re.findall(r"[-+]?\d*\.\d+|\d+", str(duration))[0])
                    if duration_val > 0:
                        delta_f = max(delta_f_min, round(1 / duration_val + 0.01, 2))
                except:
                    delta_f = delta_f_min
            else:
                delta_f = delta_f_min

        N_fft = max(int(sampling_rate / delta_f), MIN_FFT_LENGTH)
        if N_fft > N:
            data = np.pad(data, (0, N_fft - N), 'constant')

        # ===== 7. FFT 계산 =====
        window_flag = {"rectangular": 0, "hanning": 1, "flattop": 2}.get(window_type.lower(), 1)

        w, f, P, ACF, ECF, rms_w, Sxx = mdl_FFT_N_func(
            type_flag=2,
            tfs=sampling_rate,
            X=data,
            res=delta_f,
            ovrl=overlap,
            win=window_flag,
            sgnl=1,
            conv2sgnl=view_type,
            Zpadding=0
        )

        spectrum = ACF * np.abs(P)
        time = np.arange(len(data)) / sampling_rate

        # ===== 8. 결과 반환 =====
        return FileProcessResult(
            file_name=file_name,
            frequency=f,
            spectrum=spectrum.flatten(),
            time=time,
            waveform=data,
            sampling_rate=sampling_rate,
            metadata=metadata,
            success=True
        )

    except Exception as e:
        return FileProcessResult(
            file_name=file_name,
            frequency=np.array([]),
            spectrum=np.array([]),
            time=np.array([]),
            waveform=np.array([]),
            sampling_rate=0,
            metadata={},
            success=False,
            error_msg=str(e)
        )

class ParallelProcessor:
    """병렬 파일 처리 매니저"""

    def __init__(self, max_workers: int = 6):
        self.max_workers = max_workers
        self.cache = ThreadSafeCache(max_size=1000)

    def process_files(
            self,
            file_names: List[str],
            directory_path: str,
            delta_f: float,
            overlap: float,
            window_type: str,
            view_type: int,
            mdl_FFT_N_func,
            load_file_func,
            progress_callback=None
    ) -> List[FileProcessResult]:
        """
        여러 파일을 병렬로 처리

        Returns:
            List[FileProcessResult]: 처리 결과 리스트 (원본 순서 유지)
        """
        results = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 작업 제출
            future_to_index = {
                executor.submit(
                    process_single_file_parallel,
                    file_name,
                    directory_path,
                    delta_f,
                    overlap,
                    window_type,
                    view_type,
                    self.cache,
                    mdl_FFT_N_func,
                    load_file_func
                ): i
                for i, file_name in enumerate(file_names)
            }

            # 결과 수집 (완료된 순서대로)
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                result = future.result()
                results[index] = result

                # 진행률 콜백
                if progress_callback:
                    progress_callback(len(results), len(file_names))

        # 원본 순서대로 정렬
        return [results[i] for i in range(len(file_names))]

class BatchRenderer:
    """배치 그래프 렌더링"""

    @staticmethod
    def render_lines_batch(ax, results: List[FileProcessResult], colors, data_type='spectrum'):
        """
        여러 라인을 배치로 렌더링

        Parameters:
            ax: Matplotlib axes
            results: 처리 결과 리스트
            colors: 색상 리스트
            data_type: 'spectrum' 또는 'waveform'
        """
        from matplotlib.lines import Line2D

        lines = []

        for i, result in enumerate(results):
            if not result.success:
                continue

            color = colors[i % len(colors)]

            if data_type == 'spectrum':
                x_data = result.frequency
                y_data = result.spectrum
            else:  # waveform
                x_data = result.time
                y_data = result.waveform

            # Line2D 직접 생성 (plot()보다 빠름)
            line = Line2D(
                x_data, y_data,
                color=color,
                linewidth=0.5,
                label=result.file_name
            )
            ax.add_line(line)
            lines.append(line)

        # 축 범위 자동 조정
        ax.relim()
        ax.autoscale_view()

        return lines