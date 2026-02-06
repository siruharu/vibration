"""Trend analysis tab view for RMS trend over time with multi-channel support."""
from typing import List, Optional, Dict, Any

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QPushButton, QLabel, QLineEdit)
from PyQt5.QtCore import pyqtSignal

from vibration.presentation.views.widgets import PlotWidget

VIEW_TYPE_LABELS = {'ACC': 'Vibration Acceleration\n(m/s², RMS)',
                    'VEL': 'Vibration Velocity\n(mm/s, RMS)',
                    'DIS': 'Vibration Displacement\n(μm, RMS)'}
CHANNEL_COLORS = ['r', 'g', 'b', 'c', 'm', 'y']


class TrendTabView(QWidget):
    """View for trend analysis tab with RMS trend display and multi-channel support."""
    
    compute_requested = pyqtSignal()
    load_requested = pyqtSignal()
    view_type_changed = pyqtSignal(int)
    frequency_band_changed = pyqtSignal(float, float)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_view_type = 'ACC'
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addLayout(self._create_controls())
        self.plot_widget = PlotWidget(figsize=(12, 6))
        self.plot_widget.set_title('Overall RMS Trend')
        layout.addWidget(self.plot_widget, stretch=1)
    
    def _create_controls(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        
        layout.addWidget(QLabel('Delta F (Hz):'))
        self.delta_f_input = QLineEdit()
        self.delta_f_input.setPlaceholderText('Hz')
        self.delta_f_input.setMaximumWidth(80)
        layout.addWidget(self.delta_f_input)
        
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
        
        layout.addWidget(QLabel('Band:'))
        self.band_min_input = QLineEdit()
        self.band_min_input.setPlaceholderText('Min')
        self.band_min_input.setMaximumWidth(60)
        layout.addWidget(self.band_min_input)
        self.band_max_input = QLineEdit()
        self.band_max_input.setPlaceholderText('Max')
        self.band_max_input.setMaximumWidth(60)
        layout.addWidget(self.band_max_input)
        
        self.compute_btn = QPushButton('Compute')
        layout.addWidget(self.compute_btn)
        self.load_btn = QPushButton('Load')
        layout.addWidget(self.load_btn)
        layout.addStretch()
        return layout
    
    def _connect_signals(self):
        self.compute_btn.clicked.connect(self.compute_requested)
        self.load_btn.clicked.connect(self.load_requested)
        self.view_type_combo.currentIndexChanged.connect(
            lambda: self.view_type_changed.emit(self.view_type_combo.currentData()))
    
    def get_parameters(self) -> Dict[str, Any]:
        delta_f = self.delta_f_input.text().strip()
        band_min = self.band_min_input.text().strip()
        band_max = self.band_max_input.text().strip()
        return {
            'delta_f': float(delta_f) if delta_f else 1.0,
            'window_type': self.window_combo.currentText(),
            'overlap': float(self.overlap_combo.currentText().replace('%', '')),
            'view_type': self.view_type_combo.currentData(),
            'band_min': float(band_min) if band_min else 0.0,
            'band_max': float(band_max) if band_max else 10000.0
        }
    
    def plot_trend(self, channel_data: Dict[str, Dict], x_labels: List[str],
                   title: str = 'Overall RMS Trend'):
        """
        Plot trend data with multi-channel support.
        
        Args:
            channel_data: Dict mapping channel ID to {'x': [...], 'y': [...]}
            x_labels: Labels for x-axis ticks
            title: Plot title
        """
        self.plot_widget.clear()
        ax = self.plot_widget.get_axes()
        for i, (ch, data) in enumerate(channel_data.items()):
            color = CHANNEL_COLORS[i % len(CHANNEL_COLORS)]
            ax.plot(data['x'], data['y'], label=f'Channel {ch}',
                    color=color, marker='o', markersize=2, linewidth=0.5)
        self._configure_axes(ax, x_labels)
        ax.set_title(title, fontsize=10)
        ax.legend(loc='upper right', fontsize=7)
        self.plot_widget.draw_idle()
    
    def _configure_axes(self, ax, x_labels: List[str]):
        ax.set_xlabel('Date & Time', fontsize=9)
        ax.set_ylabel(VIEW_TYPE_LABELS.get(self._current_view_type, ''), fontsize=9)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.tick_params(labelsize=7)
    
    def set_view_type(self, view_type: str):
        self._current_view_type = view_type
    
    def clear_plot(self):
        self.plot_widget.clear()
