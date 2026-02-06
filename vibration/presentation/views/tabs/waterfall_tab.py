"""
Waterfall spectrum tab view for pseudo-3D visualization.

Displays FFT spectra as offset 2D lines creating a waterfall effect.
Extracted from cn_3F_trend_optimized.py:3617-3990 for modular architecture.
"""
from typing import List, Optional, Dict, Any

import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QPushButton, QLabel, QLineEdit, QCheckBox)
from PyQt5.QtCore import pyqtSignal

from vibration.presentation.views.widgets import PlotWidget


VIEW_TYPE_LABELS = {
    1: ('ACC', 'Vibration Acceleration\n(m/s², RMS)'),
    2: ('VEL', 'Vibration Velocity\n(mm/s, RMS)'),
    3: ('DIS', 'Vibration Displacement\n(μm, RMS)')
}


class WaterfallTabView(QWidget):
    """
    View for waterfall spectrum analysis tab.
    
    Displays multiple FFT spectra with y-offset to create pseudo-3D effect.
    Emits signals for presenter to handle computation.
    """
    
    compute_requested = pyqtSignal()
    angle_changed = pyqtSignal(float)
    x_range_changed = pyqtSignal(float, float)
    z_range_changed = pyqtSignal(float, float)
    view_type_changed = pyqtSignal(int)
    auto_scale_toggled = pyqtSignal(bool)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize waterfall tab view."""
        super().__init__(parent)
        self._current_view_type = 1
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addLayout(self._create_controls())
        
        self.plot_widget = PlotWidget(figsize=(12, 6))
        self.plot_widget.set_title('Waterfall Spectrum')
        layout.addWidget(self.plot_widget, stretch=1)
    
    def _create_controls(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        
        layout.addWidget(QLabel('Delta F:'))
        self.delta_f_input = QLineEdit()
        self.delta_f_input.setPlaceholderText('Hz')
        self.delta_f_input.setMaximumWidth(60)
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
        
        layout.addWidget(QLabel('Angle:'))
        self.angle_input = QLineEdit('270')
        self.angle_input.setMaximumWidth(50)
        layout.addWidget(self.angle_input)
        
        self.auto_scale_x = QCheckBox('Auto X')
        self.auto_scale_x.setChecked(True)
        layout.addWidget(self.auto_scale_x)
        
        self.plot_btn = QPushButton('Plot')
        layout.addWidget(self.plot_btn)
        
        layout.addStretch()
        return layout
    
    def _connect_signals(self):
        self.plot_btn.clicked.connect(self.compute_requested)
        self.view_type_combo.currentIndexChanged.connect(
            lambda: self.view_type_changed.emit(self.view_type_combo.currentData()))
        self.auto_scale_x.toggled.connect(self.auto_scale_toggled)
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get current control parameters."""
        delta_f = self.delta_f_input.text().strip()
        return {
            'delta_f': float(delta_f) if delta_f else 1.0,
            'window_type': self.window_combo.currentText().lower(),
            'overlap': float(self.overlap_combo.currentText().replace('%', '')),
            'view_type': self.view_type_combo.currentData(),
            'angle': float(self.angle_input.text() or '270')
        }
    
    def plot_waterfall(self, spectra: List[Dict[str, Any]],
                       x_min: float = None, x_max: float = None,
                       z_min: float = None, z_max: float = None):
        """
        Plot waterfall spectra with offset.
        
        Args:
            spectra: List of dicts with 'frequency', 'spectrum', 'label' keys
            x_min, x_max: Frequency range limits
            z_min, z_max: Amplitude range limits
        """
        if not spectra:
            return
        
        self.plot_widget.clear()
        ax = self.plot_widget.get_axes()
        
        params = self.get_parameters()
        angle_rad = np.deg2rad(params['angle'])
        
        if x_min is None:
            x_min = min(np.min(s['frequency']) for s in spectra)
        if x_max is None:
            x_max = max(np.max(s['frequency']) for s in spectra)
        if z_min is None:
            z_min = min(np.min(s['spectrum']) for s in spectra)
        if z_max is None:
            z_max = max(np.max(s['spectrum']) for s in spectra)
        
        self._render_waterfall(ax, spectra, x_min, x_max, z_min, z_max, angle_rad)
        self._configure_axes(ax)
        self.plot_widget.draw_idle()
    
    def _render_waterfall(self, ax, spectra: List[Dict], x_min: float, x_max: float,
                          z_min: float, z_max: float, angle_rad: float):
        """Render waterfall lines with offset."""
        n_files = len(spectra)
        fixed_ymin, fixed_ymax = 0, 130
        offset_range = fixed_ymax - fixed_ymin
        offset_dist = offset_range / max(n_files, 1)
        dx = offset_dist * np.cos(angle_rad)
        dy = offset_dist * np.sin(angle_rad)
        x_scale = 530
        
        for idx, data in enumerate(spectra):
            f = np.asarray(data['frequency'])
            p = np.asarray(data['spectrum'])
            
            mask = (f >= x_min) & (f <= x_max)
            f_filtered, p_filtered = f[mask], p[mask]
            if len(f_filtered) == 0:
                continue
            
            x_range = x_max - x_min
            f_norm = (f_filtered - x_min) / x_range if x_range > 0 else f_filtered
            p_clipped = np.clip(p_filtered, z_min, z_max)
            y_norm = (p_clipped - z_min) / (z_max - z_min) if z_max > z_min else p_clipped
            
            offset_x = f_norm * x_scale + idx * dx
            offset_y = y_norm * (fixed_ymax - fixed_ymin) + idx * dy
            
            ax.plot(offset_x, offset_y, alpha=0.6, linewidth=0.7,
                    label=data.get('label', ''))
    
    def _configure_axes(self, ax):
        """Configure axes appearance."""
        view_type = self._current_view_type
        _, ylabel = VIEW_TYPE_LABELS.get(view_type, ('ACC', 'Amplitude'))
        
        ax.set_xlabel('Frequency (Hz)', fontsize=8)
        ax.set_ylabel(ylabel, fontsize=8)
        ax.set_title('Waterfall Spectrum', fontsize=9)
        ax.tick_params(labelsize=7)
        ax.set_facecolor('white')
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    def set_view_type(self, view_type: int):
        """Set current view type."""
        self._current_view_type = view_type
    
    def clear_plot(self):
        """Clear the plot."""
        self.plot_widget.clear()
