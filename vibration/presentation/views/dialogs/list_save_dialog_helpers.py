"""
ListSaveDialog용 플로팅 헬퍼.

스펙트럼 피킹, FFT 플로팅, 데이터 추출 유틸리티를 제공합니다.
cn_3F_trend_optimized.py에서 모듈화 아키텍처를 위해 추출.

의존성:
- numpy: 배열 연산
- matplotlib: 플로팅
- file_parser.FileParser: 파일 로딩
- fft_engine.FFTEngine: FFT 연산
"""

import os
import sys
import json
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

_project_root = Path(__file__).parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from vibration.core.services.file_parser import FileParser
from vibration.core.services.fft_engine import FFTEngine


class SpectrumPicker:
    """
    스펙트럼 피킹 인터랙션을 처리합니다.
    
    스펙트럼 플롯에서의 마우스/키보드 탐색 및 마커 배치를 관리합니다.
    
    속성:
        ax: 스펙트럼 플롯용 Matplotlib 축
        canvas: 플롯용 FigureCanvas
        data_dict: 파일명을 (frequency, spectrum) 튜플에 매핑하는 딕셔너리
        markers: (marker, label) 튜플 목록
        hover_dot: 호버 표시기용 Matplotlib 라인 객체
        hover_pos: 현재 호버 위치 [x, y]
        mouse_tracking_enabled: 마우스 추적 활성화 여부
    """
    
    def __init__(self, ax, canvas, data_dict: Dict[str, Tuple]):
        """
        스펙트럼 피커를 초기화합니다.
        
        인자:
            ax: 스펙트럼 플롯용 Matplotlib 축
            canvas: 플롯용 FigureCanvas
            data_dict: 파일명을 (frequency, spectrum) 튜플에 매핑하는 딕셔너리
        """
        self.ax = ax
        self.canvas = canvas
        self.data_dict = data_dict
        self.markers: List[Tuple] = []
        self.hover_pos = [None, None]
        self.mouse_tracking_enabled = True
        
        # 호버 표시기 생성
        self.hover_dot = self.ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
    
    def on_mouse_move(self, event) -> None:
        """호버링을 위한 마우스 이동 이벤트를 처리합니다."""
        if not self.mouse_tracking_enabled or not event.inaxes:
            if self.hover_pos[0] is not None:
                self.hover_dot.set_data([], [])
                self.hover_pos = [None, None]
                self.canvas.draw_idle()
            return
        
        closest_x, closest_y, min_dist = None, None, np.inf
        for line in self.ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()
            if len(x_data) == 0 or len(y_data) == 0:
                continue
            for x, y in zip(x_data, y_data):
                dist = np.hypot(event.xdata - x, event.ydata - y)
                if dist < min_dist:
                    min_dist = dist
                    closest_x, closest_y = x, y
        
        if closest_x is not None:
            self.hover_dot.set_data([closest_x], [closest_y])
            self.hover_pos = [closest_x, closest_y]
            self.canvas.draw_idle()
    
    def on_mouse_click(self, event) -> None:
        if not event.inaxes:
            return
        if event.button == 1:
            x, y = self.hover_dot.get_data()
            if x is not None and len(x) > 0 and y is not None and len(y) > 0:
                self.add_marker(float(x[0]), float(y[0]))
        elif event.button == 3:
            self.clear_markers()
    
    def on_key_press(self, event) -> None:
        """데이터 피킹을 위한 키보드 탐색을 처리합니다."""
        x, y = self.hover_dot.get_data()
        if not x or not y:
            return
        
        all_x_data, all_y_data = [], []
        for line in self.ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()
            if len(x_data) > 0:
                all_x_data.extend(x_data)
                all_y_data.extend(y_data)
        
        current_index = None
        min_dist = np.inf
        for idx, (x_val, y_val) in enumerate(zip(all_x_data, all_y_data)):
            dist = np.hypot(x[0] - x_val, y[0] - y_val)
            if dist < min_dist:
                min_dist = dist
                current_index = idx
        
        if current_index is None:
            return
        
        candidates = []
        if event.key == 'left':
            candidates = [(i, abs(all_x_data[i] - x[0])) 
                         for i in range(len(all_x_data)) if all_x_data[i] < x[0]]
        elif event.key == 'right':
            candidates = [(i, abs(all_x_data[i] - x[0])) 
                         for i in range(len(all_x_data)) if all_x_data[i] > x[0]]
        elif event.key == 'enter':
            self.add_marker(all_x_data[current_index], all_y_data[current_index])
            return
        
        if candidates:
            candidates.sort(key=lambda t: t[1])
            current_index = candidates[0][0]
        
        new_x = all_x_data[current_index]
        new_y = all_y_data[current_index]
        self.hover_pos = [new_x, new_y]
        self.hover_dot.set_data([new_x], [new_y])
        self.canvas.draw_idle()
    
    def add_marker(self, x: float, y: float) -> None:
        min_distance = float('inf')
        closest_file = None
        closest_x = closest_y = None

        for file_name, (data_x, data_y) in self.data_dict.items():
            x_array = np.array(data_x)
            y_array = np.array(data_y)
            idx = int((np.abs(x_array - x)).argmin())
            x_val = float(x_array[idx])
            y_val = float(y_array[idx])
            dist = np.hypot(x_val - x, y_val - y)
            if dist < min_distance:
                min_distance = dist
                closest_file = file_name
                closest_x, closest_y = x_val, y_val

        if closest_file is not None and closest_x is not None and closest_y is not None:
            marker = self.ax.plot(
                np.round(closest_x, 4), np.round(closest_y, 4),
                marker='o', color='red', markersize=7
            )[0]
            label = self.ax.text(
                closest_x, closest_y,
                f"  file: {closest_file}\n  X: {closest_x:.4f}, Y: {closest_y:.4e}",
                fontsize=7, fontweight='bold', color='black',
                ha='left', va='bottom'
            )
            self.markers.append((marker, label))
            self.canvas.draw_idle()
    
    def clear_markers(self) -> None:
        """플롯에서 모든 마커를 제거합니다."""
        for marker, label in self.markers:
            marker.remove()
            label.remove()
        self.markers.clear()
        self.canvas.draw_idle()


def load_file_with_fft(
    file_path: str,
    directory_path: str
) -> Optional[Dict[str, Any]]:
     """
     파일을 로드하고 FFT를 연산합니다.
     
     인자:
         file_path: 파일의 전체 경로
         directory_path: JSON 메타데이터용 기본 디렉토리
     
     반환:
         data, frequency, spectrum, sampling_rate, view_type을 포함하는 딕셔너리,
         로드 실패 시 None
     """
     if not os.path.exists(file_path):
         return None
     
     try:
         base_name = os.path.splitext(os.path.basename(file_path))[0]
         
         parser = FileParser(file_path)
         if not parser.is_valid():
             return None
         
         data = parser.get_data()
         sampling_rate = parser.get_sampling_rate()
         
         if sampling_rate is None:
             return None
         
         # JSON 메타데이터 대체
         json_folder = os.path.join(directory_path, "trend_data", "full")
         json_path = os.path.join(json_folder, f"{base_name}_full.json")
         
         json_metadata = {}
         if os.path.exists(json_path):
             try:
                 with open(json_path, 'r') as f:
                     json_metadata = json.load(f)
             except:
                 pass
         
         delta_f = json_metadata.get("delta_f", 1.0)
         overlap = json_metadata.get("overlap", 50.0)
         window_str = json_metadata.get("window", "hanning").lower()
         view_type_str = json_metadata.get("view_type", "ACC").upper()
         
         view_type_map = {"ACC": 1, "VEL": 2, "DIS": 3}
         view_type = view_type_map.get(view_type_str, 1)
         
         engine = FFTEngine(
             sampling_rate=sampling_rate,
             delta_f=delta_f,
             overlap=overlap,
             window_type=window_str
         )
         
         result = engine.compute(data=data, view_type=view_type, type_flag=2)
         frequency = result['frequency']
         spectrum = result['spectrum']
         
         time = np.arange(len(data)) / sampling_rate
         
         return {
             'base_name': base_name,
             'data': data,
             'time': time,
             'frequency': frequency,
             'spectrum': spectrum,
             'sampling_rate': sampling_rate,
             'view_type': view_type
         }
         
     except Exception as e:
         print(f"File load failed: {file_path} - {e}")
         return None


def export_spectrum_to_csv(
    save_path: str,
    data_dict: Dict[str, Tuple],
    spectrum_dict: Dict[str, np.ndarray]
) -> bool:
    """
    스펙트럼 데이터를 CSV 파일로 내보냅니다.
    
    인자:
        save_path: CSV 파일 저장 경로
        data_dict: 파일명을 (frequency, spectrum) 튜플에 매핑하는 딕셔너리
        spectrum_dict: 파일명을 스펙트럼 배열에 매핑하는 딕셔너리
    
    반환:
        성공 시 True, 실패 시 False
    """
    if not spectrum_dict:
        return False
    
    try:
        if not save_path.endswith(".csv"):
            save_path += ".csv"
        
        with open(save_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            file_names = list(spectrum_dict.keys())
            writer.writerow(["Frequency (Hz)", *file_names])
            
            first_file = file_names[0]
            frequencies = data_dict[first_file][0]
            
            for i, freq in enumerate(frequencies):
                row = [freq]
                for fname in file_names:
                    spectrum = spectrum_dict[fname]
                    value = float(spectrum[i]) if i < len(spectrum) else ""
                    row.append(value)
                writer.writerow(row)
        
        return True
        
    except Exception as e:
        print(f"CSV export failed: {e}")
        return False


VIEW_LABELS = {
    1: "Vibration Acceleration\n(m/s^2, RMS)",
    2: "Vibration Velocity\n(mm/s, RMS)",
    3: "Vibration Displacement\n(um, RMS)"
}


def get_view_label(view_type: int) -> str:
    """뷰 타입에 대한 Y축 라벨을 반환합니다."""
    return VIEW_LABELS.get(view_type, "Vibration (mm/s, RMS)")


if __name__ == "__main__":
    print("ListSaveDialog helpers test: OK")
    print(f"SpectrumPicker methods: {len([m for m in dir(SpectrumPicker) if not m.startswith('_')])}")
    print(f"Utility functions: load_file_with_fft, export_spectrum_to_csv, get_view_label")
