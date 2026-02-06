"""
Plotting helpers for ListSaveDialog.

Provides spectrum picking, FFT plotting, and data extraction utilities.
Extracted from cn_3F_trend_optimized.py for modular architecture.

Dependencies:
- numpy: Array operations
- matplotlib: Plotting
- file_parser.FileParser: File loading
- fft_engine.FFTEngine: FFT computation
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

from file_parser import FileParser
from fft_engine import FFTEngine


class SpectrumPicker:
    """
    Handles spectrum picking interactions.
    
    Manages mouse/keyboard navigation and marker placement on spectrum plots.
    
    Attributes:
        ax: Matplotlib axes for spectrum plot
        canvas: FigureCanvas for the plot
        data_dict: Dictionary mapping filenames to (frequency, spectrum) tuples
        markers: List of (marker, label) tuples
        hover_dot: Matplotlib line object for hover indicator
        hover_pos: Current hover position [x, y]
        mouse_tracking_enabled: Whether mouse tracking is active
    """
    
    def __init__(self, ax, canvas, data_dict: Dict[str, Tuple]):
        """
        Initialize spectrum picker.
        
        Args:
            ax: Matplotlib axes for spectrum plot
            canvas: FigureCanvas for the plot
            data_dict: Dictionary mapping filenames to (frequency, spectrum) tuples
        """
        self.ax = ax
        self.canvas = canvas
        self.data_dict = data_dict
        self.markers: List[Tuple] = []
        self.hover_pos = [None, None]
        self.mouse_tracking_enabled = True
        
        # Create hover indicator
        self.hover_dot = self.ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
    
    def on_mouse_move(self, event) -> None:
        """Handle mouse move event for hovering."""
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
        """Handle mouse click event for marker placement."""
        if not event.inaxes:
            return
        x, y = self.hover_dot.get_data()
        if event.button == 1 and x and y:
            self.add_marker(x[0], y[0])
        elif event.button == 3:
            self.clear_markers()
    
    def on_key_press(self, event) -> None:
        """Handle keyboard navigation for data picking."""
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
        """Add marker at closest data point."""
        min_distance = float('inf')
        closest_file, closest_x, closest_y = None, None, None
        
        for file_name, (data_x, data_y) in self.data_dict.items():
            x_array = np.array(data_x)
            y_array = np.array(data_y)
            idx = (np.abs(x_array - x)).argmin()
            x_val, y_val = x_array[idx], y_array[idx]
            dist = np.hypot(x_val - x, y_val - y)
            if dist < min_distance:
                min_distance = dist
                closest_file, closest_x, closest_y = file_name, x_val, y_val
        
        if closest_file is not None:
            marker = self.ax.plot(closest_x, closest_y, marker='o', 
                                 color='red', markersize=7)[0]
            label = self.ax.text(
                float(closest_x), float(closest_y) + 0.001,
                f"file: {closest_file}\nX: {float(closest_x):.4f}, Y: {float(closest_y):.4f}",
                fontsize=7, fontweight='bold', color='black', ha='center', va='bottom'
            )
            self.markers.append((marker, label))
            self.canvas.draw_idle()
    
    def clear_markers(self) -> None:
        """Remove all markers from the plot."""
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
    Load file and compute FFT.
    
    Args:
        file_path: Full path to the file
        directory_path: Base directory for JSON metadata
    
    Returns:
        Dictionary with data, frequency, spectrum, sampling_rate, view_type,
        or None if loading fails
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
        
        # JSON metadata fallback
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
    Export spectrum data to CSV file.
    
    Args:
        save_path: Path to save CSV file
        data_dict: Dictionary mapping filenames to (frequency, spectrum) tuples
        spectrum_dict: Dictionary mapping filenames to spectrum arrays
    
    Returns:
        True if successful, False otherwise
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
    """Get Y-axis label for view type."""
    return VIEW_LABELS.get(view_type, "Vibration (mm/s, RMS)")


if __name__ == "__main__":
    print("ListSaveDialog helpers test: OK")
    print(f"SpectrumPicker methods: {len([m for m in dir(SpectrumPicker) if not m.startswith('_')])}")
    print(f"Utility functions: load_file_with_fft, export_spectrum_to_csv, get_view_label")
