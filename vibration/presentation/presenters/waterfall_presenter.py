"""
Waterfall analysis presenter - coordinates WaterfallTabView and analysis services.

Implements plot_waterfall_spectrum logic with caching to avoid redundant FFT computation
on axis/angle changes. Uses FFTService for frequency analysis.
"""
import logging
import os
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, cast, Union

import numpy as np

from vibration.presentation.views.tabs.waterfall_tab import WaterfallTabView
from vibration.presentation.views.dialogs.progress_dialog import ProgressDialog
from vibration.core.services.fft_service import FFTService, WindowType, ViewType
from vibration.core.services.file_service import FileService
from vibration.infrastructure.event_bus import get_event_bus

logger = logging.getLogger(__name__)


VIEW_TYPE_MAP = {1: 'ACC', 2: 'VEL', 3: 'DIS'}
VIEW_TYPE_LABELS = {
    'ACC': 'Vibration Acceleration\n(m/s², RMS)',
    'VEL': 'Vibration Velocity\n(mm/s, RMS)',
    'DIS': 'Vibration Displacement\n(μm, RMS)'
}


class WaterfallPresenter:
    """
    Presenter for waterfall analysis tab.
    
    Coordinates WaterfallTabView and FFTService for waterfall 3D spectrum rendering.
    Implements cache to avoid redundant FFT computation on axis/angle changes.
    """
    
    def __init__(self, view: WaterfallTabView, directory_path: str = ""):
        self.view = view
        self._directory_path = directory_path
        
        self._event_bus = get_event_bus()
        self._event_bus.files_loaded.connect(self._on_files_loaded)
        self._event_bus.directory_selected.connect(self._on_directory_changed)
        
        self._file_service = FileService()
        
        self._waterfall_cache: Dict[str, Any] = {
            'computed': False,
            'spectra': [],
            'params': {}
        }
        
        self._current_x_min: Optional[float] = None
        self._current_x_max: Optional[float] = None
        self._current_z_min: Optional[float] = None
        self._current_z_max: Optional[float] = None
        
        self._connect_signals()
        logger.debug("WaterfallPresenter initialized")
    
    def _connect_signals(self):
        self.view.compute_requested.connect(self._on_compute_requested)
        self.view.set_x_axis_requested.connect(self._on_set_x_axis)
        self.view.set_z_axis_requested.connect(self._on_set_z_axis)
        self.view.auto_scale_x_requested.connect(self._on_auto_scale_x)
        self.view.auto_scale_z_requested.connect(self._on_auto_scale_z)
        self.view.angle_changed.connect(self._on_angle_changed)
    
    def _on_files_loaded(self, files: List[str]) -> None:
        logger.info(f"Received {len(files)} files from Data Query")
        self.view.set_files(files)
    
    def _on_directory_changed(self, directory_path: str) -> None:
        self._directory_path = directory_path
        logger.debug(f"Directory changed to: {directory_path}")
    
    def set_directory_path(self, directory_path: str) -> None:
        self._directory_path = directory_path
    
    def _on_compute_requested(self, force_recalculate: bool = True):
        logger.debug(f"Compute requested (force_recalculate={force_recalculate})")
        self.plot_waterfall_spectrum(force_recalculate=force_recalculate)
    
    def _on_set_x_axis(self):
        x_min, x_max = self.view.get_x_axis_limits()
        if x_min is not None and x_max is not None:
            self._current_x_min = x_min
            self._current_x_max = x_max
            self.view.set_auto_x_checked(False)
            self.plot_waterfall_spectrum(
                x_min=x_min, x_max=x_max,
                z_min=self._current_z_min, z_max=self._current_z_max,
                force_recalculate=False
            )
    
    def _on_set_z_axis(self):
        z_min, z_max = self.view.get_z_axis_limits()
        if z_min is not None and z_max is not None:
            self._current_z_min = z_min
            self._current_z_max = z_max
            self.view.set_auto_z_checked(False)
            self.plot_waterfall_spectrum(
                x_min=self._current_x_min, x_max=self._current_x_max,
                z_min=z_min, z_max=z_max,
                force_recalculate=False
            )
    
    def _on_auto_scale_x(self):
        self._current_x_min = None
        self._current_x_max = None
        self.view.set_auto_x_checked(True)
        self.plot_waterfall_spectrum(
            x_min=None, x_max=None,
            z_min=self._current_z_min, z_max=self._current_z_max,
            force_recalculate=False
        )
    
    def _on_auto_scale_z(self):
        self._current_z_min = None
        self._current_z_max = None
        self.view.set_auto_z_checked(True)
        self.plot_waterfall_spectrum(
            x_min=self._current_x_min, x_max=self._current_x_max,
            z_min=None, z_max=None,
            force_recalculate=False
        )
    
    def _on_angle_changed(self):
        self.plot_waterfall_spectrum(
            x_min=self._current_x_min, x_max=self._current_x_max,
            z_min=self._current_z_min, z_max=self._current_z_max,
            force_recalculate=False
        )
    
    def plot_waterfall_spectrum(
        self,
        x_min: Optional[float] = None,
        x_max: Optional[float] = None,
        z_min: Optional[float] = None,
        z_max: Optional[float] = None,
        force_recalculate: bool = False
    ):
        selected_files = self.view.get_selected_files()
        if not selected_files:
            logger.warning("No files selected for waterfall plot")
            return
        
        params: Dict[str, Any] = self.view.get_parameters()  # type: ignore[assignment]
        delta_f: float = params.get('delta_f', 1.0)
        overlap: float = params.get('overlap', 0.0)
        window_type: str = params.get('window_type', 'hanning')
        view_type: int = params.get('view_type', 1)
        angle: float = params.get('angle', 270.0)
        
        current_params = {
            'delta_f': delta_f,
            'overlap': overlap,
            'window_type': window_type,
            'view_type': view_type,
            'file_count': len(selected_files),
            'file_names': tuple(selected_files)
        }
        
        cache_valid = (
            self._waterfall_cache.get('computed', False) and
            self._waterfall_cache.get('params') == current_params and
            not force_recalculate
        )
        
        if not cache_valid:
            logger.info("Computing FFT for waterfall plot...")
            self._compute_waterfall_fft(selected_files, delta_f, overlap, window_type, view_type)
            self._waterfall_cache['params'] = current_params
        else:
            logger.debug("Using cached waterfall data")
        
        self._render_waterfall(x_min, x_max, z_min, z_max, angle, view_type)
    
    def _compute_waterfall_fft(
        self,
        selected_files: List[str],
        delta_f: float,
        overlap: float,
        window_type: str,
        view_type: int
    ):
        self._waterfall_cache['spectra'] = []
        
        progress_dialog = ProgressDialog(len(selected_files), self.view)
        progress_dialog.show()
        
        items_with_time = []
        for file_name in selected_files:
            try:
                timestamp = self._extract_timestamp_from_filename(file_name)
            except Exception:
                timestamp = datetime.max
            items_with_time.append((file_name, timestamp))
        
        sorted_items = sorted(items_with_time, key=lambda x: x[1], reverse=False)
        
        for draw_idx, (file_name, timestamp) in enumerate(sorted_items):
            file_path = os.path.join(self._directory_path, file_name)
            progress_dialog.label.setText(f"{file_name} 처리 중...")
            
            try:
                file_data = self._file_service.load_file(file_path)
            except Exception as e:
                logger.warning(f"Failed to load file {file_name}: {e}")
                progress_dialog.update_progress(draw_idx + 1)
                continue
            
            if not file_data.get('is_valid') or file_data.get('data') is None:
                progress_dialog.update_progress(draw_idx + 1)
                continue
            
            data = file_data['data']
            sampling_rate = file_data.get('sampling_rate', 0)
            record_length = file_data.get('record_length')
            metadata = file_data.get('metadata', {})
            
            if sampling_rate is None or sampling_rate <= 0:
                progress_dialog.update_progress(draw_idx + 1)
                continue
            
            b_sensitivity = self._extract_numeric_value(metadata.get('b_sensitivity'))
            sensitivity = self._extract_numeric_value(metadata.get('sensitivity'))
            
            if b_sensitivity is not None and sensitivity is not None and sensitivity != 0:
                scaled_data = (b_sensitivity / sensitivity) * data
            else:
                scaled_data = data
            
            effective_delta_f = delta_f
            if record_length:
                try:
                    duration = float(record_length)
                    hz_value = round(1 / duration + 0.01, 2)
                    effective_delta_f = max(delta_f, hz_value)
                except (ValueError, ZeroDivisionError):
                    pass
            
            try:
                view_type_str = VIEW_TYPE_MAP.get(view_type, 'ACC')
                window_type_literal = cast(WindowType, window_type)
                view_type_literal = cast(ViewType, view_type_str)
                fft_service = FFTService(
                    sampling_rate=sampling_rate,
                    delta_f=effective_delta_f,
                    overlap=overlap,
                    window_type=window_type_literal
                )
                fft_result = fft_service.compute_spectrum(scaled_data, view_type=view_type_literal)
                
                frequency = fft_result.frequency
                spectrum = np.round(fft_result.spectrum, 4)
                
            except Exception as e:
                logger.warning(f"FFT computation failed for {file_name}: {e}")
                progress_dialog.update_progress(draw_idx + 1)
                continue
            
            try:
                name_only = os.path.splitext(file_name)[0]
                parts = name_only.split("_")
                if len(parts) >= 3:
                    date = parts[0]
                    time = parts[1]
                    rest = '_'.join(parts[2:])
                    x_label = f"{date}\n{time}_{rest}"
                else:
                    x_label = file_name
            except Exception:
                x_label = file_name
            
            self._waterfall_cache['spectra'].append({
                'file_name': file_name,
                'frequency': frequency,
                'spectrum': spectrum,
                'timestamp': timestamp,
                'x_label': x_label,
                'sampling_rate': sampling_rate
            })
            
            progress_dialog.update_progress(draw_idx + 1)
        
        progress_dialog.close()
        self._waterfall_cache['computed'] = True
        logger.info(f"Waterfall cache created with {len(self._waterfall_cache['spectra'])} files")
    
    def _render_waterfall(
        self,
        x_min: Optional[float],
        x_max: Optional[float],
        z_min: Optional[float],
        z_max: Optional[float],
        angle: float,
        view_type: int
    ):
        if len(self._waterfall_cache['spectra']) == 0:
            logger.warning("No data to display in waterfall plot")
            return
        
        fig = self.view.get_figure()
        fig.clf()
        ax = fig.add_subplot(111)
        self.view.set_axes(ax)
        ax.set_title("Waterfall Spectrum", fontsize=7)
        
        all_frequencies = []
        all_spectra = []
        for cached in self._waterfall_cache['spectra']:
            all_frequencies.extend(cached['frequency'])
            all_spectra.extend(cached['spectrum'])
        
        global_xmin: float = float(np.min(all_frequencies))
        global_xmax: float = float(np.max(all_frequencies))
        global_zmin: float = float(np.min(all_spectra))
        global_zmax: float = float(np.max(all_spectra))
        
        eff_x_min: float = global_xmin if x_min is None else x_min
        eff_x_max: float = global_xmax if x_max is None else x_max
        eff_z_min: float = global_zmin if z_min is None else z_min
        eff_z_max: float = global_zmax if z_max is None else z_max
        
        angle_rad = np.deg2rad(angle)
        
        fixed_ymin, fixed_ymax = 0, 130
        num_files = len(self._waterfall_cache['spectra'])
        offset_range = fixed_ymax - fixed_ymin
        offset_distance = offset_range / max(num_files, 1)
        dx = offset_distance * np.cos(angle_rad)
        dy = offset_distance * np.sin(angle_rad)
        
        max_labels = 5
        total_files = num_files
        if total_files <= max_labels:
            label_indices = list(range(total_files))
        else:
            label_indices = np.linspace(0, total_files - 1, max_labels, dtype=int).tolist()
        
        yticks_for_labels = []
        labels_for_ticks = []
        
        x_scale = 530
        
        for draw_idx, cached_data in enumerate(self._waterfall_cache['spectra']):
            f = cached_data['frequency']
            P_magnitude = cached_data['spectrum']
            file_name = cached_data['file_name']
            
            mask_freq = (f >= eff_x_min) & (f <= eff_x_max)
            f_filtered = f[mask_freq]
            p_filtered = P_magnitude[mask_freq]
            
            if len(f_filtered) == 0:
                continue
            
            x_range = eff_x_max - eff_x_min
            if x_range <= 0:
                continue
            f_normalized = (f_filtered - eff_x_min) / x_range
            
            if eff_z_max > eff_z_min:
                p_clipped = np.clip(p_filtered, eff_z_min, eff_z_max)
                y_normalized = (p_clipped - eff_z_min) / (eff_z_max - eff_z_min)
            else:
                global_max = np.max(all_spectra) if np.max(all_spectra) > 0 else 1
                y_normalized = p_filtered / global_max
            
            scale_factor = (fixed_ymax - fixed_ymin)
            y_scaled = y_normalized * scale_factor
            
            base_x = draw_idx * dx
            base_y = draw_idx * dy
            offset_x = f_normalized * x_scale + base_x
            offset_y = y_scaled + base_y
            
            ax.plot(offset_x, offset_y, alpha=0.6, linewidth=0.8)
            
            if draw_idx == 0:
                if len(offset_x) >= 2:
                    xticks = np.linspace(offset_x[0], offset_x[-1], 7)
                    xtick_labels = np.linspace(eff_x_min, eff_x_max, 7)
                    ax.set_xticks(xticks)
                    ax.set_xticklabels([f"{val:.1f}" for val in xtick_labels])
                
                if len(offset_y) >= 2:
                    ax.yaxis.set_ticks_position('left')
                    ymin_plot = min(offset_y)
                    ymax_plot = max(offset_y)
                    yticks = np.linspace(ymin_plot, ymax_plot, 7)
                    ytick_labels = np.linspace(eff_z_min, eff_z_max, 7)
                    ax.set_yticks(yticks)
                    ax.set_yticklabels([f"{val:.4f}" for val in ytick_labels], fontsize=7)
                    ax.tick_params(axis='y', labelleft=True)
                    ax.set_ylim(0, 150)
            
            if draw_idx in label_indices:
                center_y = np.min(offset_y)
                base_name = file_name.replace(".txt", "")
                parts = base_name.split("_")
                if len(parts) >= 2:
                    label_text = parts[0] + "_" + parts[1] + "\n" + "_".join(parts[2:])
                else:
                    label_text = base_name
                
                yticks_for_labels.append(center_y)
                labels_for_ticks.append(label_text)
        
        ax_right = ax.twinx()
        ax_right.set_ylim(ax.get_ylim())
        ax_right.set_yticks([])
        ax_right.tick_params(right=False)
        
        for y, label in zip(yticks_for_labels, labels_for_ticks):
            ax_right.text(1.02, y, label, transform=ax_right.get_yaxis_transform(),
                         fontsize=7, va='center', ha='left')
        
        view_type_str = VIEW_TYPE_MAP.get(view_type, 'ACC')
        zlabel = VIEW_TYPE_LABELS.get(view_type_str, 'RMS Vibration')
        ax.set_ylabel(zlabel, fontsize=7)
        ax.set_xlabel("Frequency (Hz)", fontsize=7)
        
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')
        ax.tick_params(axis='y', labelrotation=0)
        ax.tick_params(axis='x', labelsize=7)
        ax.tick_params(axis='y', labelsize=7)
        
        self._add_grid_lines(ax, eff_x_min, eff_x_max, x_scale)
        
        self.view.draw()
    
    def _add_grid_lines(self, ax, x_min: float, x_max: float, x_scale: float):
        x_range = x_max - x_min
        if x_range <= 100:
            interval = 10
        elif x_range <= 200:
            interval = 20
        elif x_range <= 500:
            interval = 50
        elif x_range <= 1000:
            interval = 100
        elif x_range <= 2000:
            interval = 200
        elif x_range <= 5000:
            interval = 500
        else:
            interval = 1000
        
        grid_ticks = np.arange(
            int(x_min / interval) * interval,
            x_max + interval,
            interval
        )
        
        for tick_val in grid_ticks:
            if x_min <= tick_val <= x_max:
                normalized = (tick_val - x_min) / x_range
                x_pos = normalized * x_scale
                ax.axvline(x=x_pos, color='gray', linestyle='--',
                          linewidth=0.5, alpha=0.3)
    
    def _extract_timestamp_from_filename(self, filename: str) -> datetime:
        match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)
        
        if match:
            timestamp_str = match.group(1)
            timestamp_str = timestamp_str.replace('_', ' ')
            timestamp_str = timestamp_str[:10] + ' ' + timestamp_str[11:].replace('-', ':')
            
            try:
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return datetime.now()
        else:
            return datetime.now()
    
    def _extract_numeric_value(self, s: Optional[str]) -> Optional[float]:
        if s is None:
            return None
        match = re.search(r"[-+]?[0-9]*\.?[0-9]+", str(s))
        return float(match.group()) if match else None
    
    def clear_cache(self):
        self._waterfall_cache = {
            'computed': False,
            'spectra': [],
            'params': {}
        }
        self._current_x_min = None
        self._current_x_max = None
        self._current_z_min = None
        self._current_z_max = None
