"""Peak analysis tab view for band peak trend over time with multi-channel support."""
from typing import List, Optional, Dict, Any

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QPushButton, QLabel, QLineEdit)
from PyQt5.QtCore import pyqtSignal

from vibration.presentation.views.widgets import PlotWidget
from vibration.presentation.views.widgets.marker_manager import MarkerManager

VIEW_TYPE_LABELS = {
    'ACC': 'Peak Acceleration\n(m/s², RMS)',
    'VEL': 'Peak Velocity\n(mm/s, RMS)',
    'DIS': 'Peak Displacement\n(μm, RMS)'
}
CHANNEL_COLORS = ['r', 'g', 'b', 'c', 'm', 'y']


class PeakTabView(QWidget):
    """View for peak analysis tab with band peak trend display and multi-channel support."""
    
    compute_requested = pyqtSignal()
    load_requested = pyqtSignal()
    save_requested = pyqtSignal()
    view_type_changed = pyqtSignal(int)
    frequency_band_changed = pyqtSignal(float, float)
    point_clicked = pyqtSignal(float, float, str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_view_type = 'ACC'
        self._marker_manager: Optional[MarkerManager] = None
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addLayout(self._create_controls())
        
        self.plot_widget = PlotWidget(figsize=(12, 6))
        self.plot_widget.set_title('Band Peak Trend')
        layout.addWidget(self.plot_widget, stretch=1)
        
        self._init_marker_manager()
    
    def _init_marker_manager(self):
        ax = self.plot_widget.get_axes()
        canvas = self.plot_widget.get_canvas()
        self._marker_manager = MarkerManager(ax, canvas, parent=self)
        self._marker_manager.init_hover_dot(color='black', size=6)
        
        canvas.mpl_connect('motion_notify_event', self._marker_manager.on_mouse_move)
        canvas.mpl_connect('button_press_event', self._on_canvas_click)
        canvas.mpl_connect('key_press_event', self._on_key_press)
    
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
        
        self.save_btn = QPushButton('Save CSV')
        layout.addWidget(self.save_btn)
        
        layout.addStretch()
        return layout
    
    def _connect_signals(self):
        self.compute_btn.clicked.connect(self.compute_requested)
        self.save_btn.clicked.connect(self.save_requested)
        self.view_type_combo.currentIndexChanged.connect(
            lambda: self.view_type_changed.emit(self.view_type_combo.currentData()))
    
    def _on_canvas_click(self, event):
        if self._marker_manager:
            self._marker_manager.on_mouse_click(event, data_lookup=self._lookup_point_data)
    
    def _on_key_press(self, event):
        if event.key == 'escape' and self._marker_manager:
            self._marker_manager.clear_markers()
            self.plot_widget.draw_idle()
    
    def _lookup_point_data(self, x: float, y: float):
        return (x, y, None)
    
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
    
    def plot_peak_trend(self, channel_data: Dict[str, Dict], x_labels: List[str],
                        title: str = 'Band Peak Trend'):
        self.plot_widget.clear()
        ax = self.plot_widget.get_axes()
        
        if self._marker_manager:
            self._marker_manager.axes = ax
            self._marker_manager._hover_dot = None
            self._marker_manager.init_hover_dot(color='black', size=6)
        
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
        ax.set_facecolor('white')
        ax.grid(True, alpha=0.3, linestyle='--', color='gray', linewidth=0.5)
        ax.tick_params(labelsize=7)
    
    def set_view_type(self, view_type: str):
        self._current_view_type = view_type
    
    def clear_plot(self):
        self.plot_widget.clear()
        if self._marker_manager:
            self._marker_manager.clear_markers()
    
    def get_marker_manager(self) -> Optional[MarkerManager]:
        return self._marker_manager
