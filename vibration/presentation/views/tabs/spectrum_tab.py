"""
Spectrum analysis tab view.

Displays FFT spectrum and waveform with interactive plotting and view type selection.
Extracted from cn_3F_trend_optimized.py for modular architecture.
"""
from typing import List, Optional, Tuple

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QComboBox, QPushButton, QSplitter, QLabel
)
from PyQt5.QtCore import pyqtSignal, Qt

from vibration.presentation.views.widgets import PlotWidget


VIEW_TYPE_LABELS = {
    'ACC': 'Vibration Acceleration\n(m/s², RMS)',
    'VEL': 'Vibration Velocity\n(mm/s, RMS)',
    'DIS': 'Vibration Displacement\n(μm, RMS)'
}

PLOT_COLORS = ['b', 'g', 'r', 'c', 'm', 'y']


class SpectrumTabView(QWidget):
    """
    View for spectrum analysis tab.
    
    Displays waveform and spectrum plots with FFT parameter controls.
    Emits signals for presenter to handle computation.
    """
    
    compute_requested = pyqtSignal()
    next_file_requested = pyqtSignal()
    view_type_changed = pyqtSignal(int)
    window_type_changed = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize spectrum tab view."""
        super().__init__(parent)
        self._current_view_type = 'ACC'
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.addLayout(self._create_controls(), 0, 0, Qt.AlignTop)
        
        splitter = QSplitter(Qt.Vertical)
        self.waveform_plot = PlotWidget(figsize=(10, 4))
        self.waveform_plot.set_title('Waveform')
        splitter.addWidget(self.waveform_plot)
        
        self.spectrum_plot = PlotWidget(figsize=(10, 4))
        self.spectrum_plot.set_title('Vibration Spectrum')
        splitter.addWidget(self.spectrum_plot)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1, 0)
        layout.setRowStretch(1, 1)
    
    def _create_controls(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        
        layout.addWidget(QLabel('Window:'))
        self.window_combo = QComboBox()
        self.window_combo.addItems(['Rectangular', 'Hanning', 'Flattop'])
        self.window_combo.setCurrentText('Hanning')
        layout.addWidget(self.window_combo)
        
        layout.addWidget(QLabel('Overlap:'))
        self.overlap_combo = QComboBox()
        self.overlap_combo.addItems(['0%', '25%', '50%', '75%'])
        self.overlap_combo.setCurrentText('50%')
        layout.addWidget(self.overlap_combo)
        
        layout.addWidget(QLabel('Type:'))
        self.view_type_combo = QComboBox()
        self.view_type_combo.addItem('ACC', 1)
        self.view_type_combo.addItem('VEL', 2)
        self.view_type_combo.addItem('DIS', 3)
        layout.addWidget(self.view_type_combo)
        
        self.plot_btn = QPushButton('Plot')
        layout.addWidget(self.plot_btn)
        self.next_btn = QPushButton('Next')
        layout.addWidget(self.next_btn)
        
        layout.addStretch()
        return layout
    
    def _connect_signals(self):
        self.plot_btn.clicked.connect(self.compute_requested)
        self.next_btn.clicked.connect(self.next_file_requested)
        self.view_type_combo.currentIndexChanged.connect(
            lambda: self.view_type_changed.emit(self.view_type_combo.currentData())
        )
        self.window_combo.currentTextChanged.connect(self.window_type_changed)
    
    def get_parameters(self) -> dict:
        return {
            'window_type': self.window_combo.currentText(),
            'overlap': float(self.overlap_combo.currentText().replace('%', '')),
            'view_type': self.view_type_combo.currentData()
        }
    
    def plot_spectrum(self, frequencies: List[float], spectrum: List[float],
                      label: str = '', color_index: int = 0, clear: bool = True):
        """Plot spectrum data on frequency axis."""
        self._plot_data(self.spectrum_plot, frequencies, spectrum, 
                        'Frequency (Hz)', label, color_index, clear)
    
    def plot_waveform(self, time: List[float], amplitude: List[float],
                      label: str = '', color_index: int = 0, clear: bool = True):
        """Plot waveform data on time axis."""
        self._plot_data(self.waveform_plot, time, amplitude,
                        'Time (s)', label, color_index, clear)
    
    def _plot_data(self, plot_widget: PlotWidget, x_data: List[float], 
                   y_data: List[float], xlabel: str, label: str,
                   color_index: int, clear: bool):
        if clear:
            plot_widget.clear()
        ax = plot_widget.get_axes()
        color = PLOT_COLORS[color_index % len(PLOT_COLORS)]
        ax.plot(x_data, y_data, color=color, linewidth=0.5, label=label, alpha=0.8)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(VIEW_TYPE_LABELS.get(self._current_view_type, ''))
        ax.grid(True)
        if label:
            ax.legend(loc='upper right', fontsize=7)
        plot_widget.draw_idle()
    
    def set_view_type(self, view_type: str):
        self._current_view_type = view_type
    
    def clear_plots(self):
        self.spectrum_plot.clear()
        self.waveform_plot.clear()
