"""
Waterfall spectrum presenter (MVP pattern).

Coordinates WaterfallTabView and FFTService for batch waterfall visualization.
Uses constructor injection for dependencies - no service locator pattern.
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable

import numpy as np

from vibration.core.services.fft_service import FFTService
from vibration.core.domain.models import FFTResult, SignalData
from vibration.presentation.views.tabs.waterfall_tab import WaterfallTabView

logger = logging.getLogger(__name__)

VIEW_TYPE_INT_TO_STR = {1: 'ACC', 2: 'VEL', 3: 'DIS'}


class WaterfallPresenter:
    """
    Presenter for waterfall spectrum tab (MVP pattern).
    
    Computes batch FFT for multiple files and renders as offset waterfall.
    
    Args:
        view: Waterfall tab view instance.
        fft_service: FFT computation service instance.
        file_loader: Optional callable (filepath) -> (data, sampling_rate, metadata).
    """
    
    def __init__(self, view: WaterfallTabView, fft_service: FFTService,
                 file_loader: Optional[Callable] = None):
        self.view = view
        self.fft_service = fft_service
        self.file_loader = file_loader
        
        self._file_paths: List[str] = []
        self._current_view_type: str = 'ACC'
        self._cache: Dict[str, Any] = {}
        self._cached_params: Optional[Dict] = None
        
        self._connect_signals()
        logger.debug("WaterfallPresenter initialized")
    
    def _connect_signals(self):
        self.view.compute_requested.connect(self._on_compute_requested)
        self.view.view_type_changed.connect(self._on_view_type_changed)
        self.view.auto_scale_toggled.connect(self._on_auto_scale_toggled)
    
    def load_files(self, file_paths: List[str]) -> None:
        """Load files for waterfall analysis."""
        self._file_paths = list(file_paths)
        self._invalidate_cache()
        logger.info(f"Loaded {len(file_paths)} files for waterfall analysis")
    
    def load_signals(self, signals: List[SignalData]) -> None:
        """Load pre-loaded signal data directly."""
        self._signals = signals
        self._invalidate_cache()
        logger.info(f"Loaded {len(signals)} signals for waterfall")
    
    def _invalidate_cache(self):
        self._cache = {}
        self._cached_params = None
    
    def _on_compute_requested(self, force_recalculate: bool = False) -> None:
        if not self._file_paths and not hasattr(self, '_signals'):
            logger.warning("No files/signals loaded")
            return
        
        params = self.view.get_parameters()
        view_type_int = params.get('view_type', 1)
        view_type_str = VIEW_TYPE_INT_TO_STR.get(view_type_int, 'ACC')
        
        self._current_view_type = view_type_str
        self.view.set_view_type(view_type_int)
        
        cache_valid = self._is_cache_valid(params) and not force_recalculate
        
        if not cache_valid:
            self._compute_spectra(params, view_type_str)
        
        if 'spectra' in self._cache and self._cache['spectra']:
            self.view.plot_waterfall(self._cache['spectra'])
            logger.info(f"Rendered waterfall with {len(self._cache['spectra'])} spectra")
    
    def _is_cache_valid(self, params: Dict) -> bool:
        if not self._cache.get('computed'):
            return False
        if self._cached_params != params:
            return False
        return True
    
    def _compute_spectra(self, params: Dict, view_type: str) -> None:
        logger.debug("Computing waterfall spectra...")
        
        window_type = params.get('window_type', 'hanning')
        if hasattr(self.fft_service, 'window_type'):
            self.fft_service.window_type = window_type
        
        spectra = []
        
        if hasattr(self, '_signals') and self._signals:
            for signal in self._signals:
                try:
                    result = self.fft_service.compute_spectrum(
                        data=signal.data,
                        view_type=view_type,
                        input_signal_type=signal.signal_type
                    )
                    spectra.append({
                        'frequency': result.frequency,
                        'spectrum': result.spectrum,
                        'label': signal.channel,
                        'timestamp': getattr(signal, 'timestamp', None)
                    })
                except Exception as e:
                    logger.error(f"FFT error for {signal.channel}: {e}")
        
        elif self.file_loader and self._file_paths:
            for path in self._file_paths:
                try:
                    data, sr, meta = self.file_loader(path)
                    if data is None or len(data) == 0:
                        continue
                    
                    temp_service = FFTService(
                        sampling_rate=sr,
                        delta_f=params.get('delta_f', 1.0),
                        overlap=params.get('overlap', 50.0),
                        window_type=window_type
                    )
                    
                    result = temp_service.compute_spectrum(
                        data=data,
                        view_type=view_type
                    )
                    
                    spectra.append({
                        'frequency': result.frequency,
                        'spectrum': result.spectrum,
                        'label': meta.get('filename', path),
                        'timestamp': meta.get('timestamp')
                    })
                except Exception as e:
                    logger.error(f"Error processing {path}: {e}")
        
        self._cache = {
            'computed': True,
            'spectra': spectra,
            'params': params.copy()
        }
        self._cached_params = params.copy()
        
        logger.info(f"Computed {len(spectra)} waterfall spectra")
    
    def _on_view_type_changed(self, view_type_int: int) -> None:
        view_type_str = VIEW_TYPE_INT_TO_STR.get(view_type_int, 'ACC')
        if view_type_str == self._current_view_type:
            return
        
        self._current_view_type = view_type_str
        self.view.set_view_type(view_type_int)
        
        self._invalidate_cache()
        
        if self._file_paths or hasattr(self, '_signals'):
            self._on_compute_requested(force_recalculate=True)
    
    def _on_auto_scale_toggled(self, enabled: bool) -> None:
        logger.debug(f"Auto scale X: {enabled}")
        if 'spectra' in self._cache:
            self.view.plot_waterfall(self._cache['spectra'])
    
    def get_cached_spectra(self) -> List[Dict]:
        """Get cached spectra data."""
        return self._cache.get('spectra', [])
    
    def has_data(self) -> bool:
        """Check if data is loaded."""
        return bool(self._file_paths) or (hasattr(self, '_signals') and bool(self._signals))


if __name__ == "__main__":
    print("WaterfallPresenter Test")
    print("=" * 50)
    
    import inspect
    sig = inspect.signature(WaterfallPresenter.__init__)
    params = list(sig.parameters.keys())
    print(f"Constructor params: {params}")
    
    assert 'view' in params
    assert 'fft_service' in params
    print("DI signature OK")
    
    from unittest.mock import MagicMock
    
    mock_view = MagicMock(spec=WaterfallTabView)
    mock_view.compute_requested = MagicMock()
    mock_view.view_type_changed = MagicMock()
    mock_view.auto_scale_toggled = MagicMock()
    
    mock_service = MagicMock(spec=FFTService)
    
    presenter = WaterfallPresenter(view=mock_view, fft_service=mock_service)
    
    test_files = ['/path/file1.txt', '/path/file2.txt']
    presenter.load_files(test_files)
    
    assert presenter.has_data()
    print("File loading OK")
    
    print("\nWaterfallPresenter tests passed!")
