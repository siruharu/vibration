"""
스펙트럼 팝업 윈도우 — 파형 시간 범위 선택 시 독립 스펙트럼 표시.
"""
from typing import List, Optional

import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QApplication
from PyQt5.QtCore import Qt

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from vibration.presentation.views.dialogs.responsive_layout_utils import PlotFontSizes
from vibration.presentation.views.tabs.spectrum_tab import VIEW_TYPE_LABELS


class SpectrumWindow(QWidget):
    """
    독립 스펙트럼 팝업 윈도우.
    
    파형에서 시간 범위를 선택하면 해당 구간의 FFT 스펙트럼을 표시합니다.
    여러 윈도우가 동시에 존재할 수 있습니다.
    """
    
    def __init__(self, t_start: float, t_end: float, parent: Optional[QWidget] = None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(f"Spectrum [{t_start:.3f}s - {t_end:.3f}s]")
        self.resize(800, 500)
        
        self.markers = []
        self.hover_dot = None
        self.hover_pos = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        dpi = QApplication.primaryScreen().logicalDotsPerInch()
        self.figure = Figure(figsize=(8, 4), dpi=dpi)
        self.figure.set_tight_layout(True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Vibration Spectrum", fontsize=PlotFontSizes.TITLE)
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        
        self.hover_dot = self.ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
        
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self.canvas.mpl_connect("button_press_event", self._on_mouse_click)
        
        layout.addWidget(self.canvas)
    
    def plot_spectrum(self, frequencies: List[float], spectrum: List[float],
                      label: str = '', view_type: str = 'ACC'):
        self.ax.clear()
        self.ax.set_title("Vibration Spectrum", fontsize=PlotFontSizes.TITLE)
        self.hover_dot = self.ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
        
        self.ax.plot(frequencies, spectrum, 'b-', linewidth=0.5, label=label, alpha=0.8)
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel(VIEW_TYPE_LABELS.get(view_type, ''))
        self.ax.grid(True)
        if label:
            self.ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1),
                          fontsize=PlotFontSizes.LEGEND, frameon=True, fancybox=True, shadow=True)
        self.canvas.draw_idle()
    
    def _on_mouse_move(self, event):
        if not event.inaxes:
            if self.hover_pos is not None:
                self.hover_dot.set_data([], [])
                self.hover_pos = None
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
    
    def _on_mouse_click(self, event):
        if not event.inaxes:
            return
        
        if event.button == 1:
            x, y = self.hover_dot.get_data()
            if x is not None and len(x) > 0 and y is not None and len(y) > 0:
                self._add_marker(float(x[0]), float(y[0]))
        elif event.button == 3:
            self._clear_markers()
    
    def _add_marker(self, x: float, y: float):
        marker, = self.ax.plot([x], [y], 'ro', markersize=8, zorder=10)
        label = self.ax.text(x, y, f'  ({x:.2f}, {y:.2e})',
                            fontsize=PlotFontSizes.MARKER_LABEL, color='red',
                            verticalalignment='bottom')
        self.markers.append((marker, label))
        self.canvas.draw_idle()
    
    def _clear_markers(self):
        for marker, label in self.markers:
            marker.remove()
            label.remove()
        self.markers.clear()
        self.canvas.draw_idle()
    
    def closeEvent(self, a0):
        self.canvas.mpl_disconnect(0)
        self.figure.clear()
        super().closeEvent(a0)
