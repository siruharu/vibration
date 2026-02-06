"""
Peak analysis presenter (MVP pattern).

Coordinates PeakTabView and PeakService for batch peak analysis workflow.
Uses constructor injection for dependencies - no service locator pattern.
"""
import logging
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from vibration.core.services.peak_service import PeakService
from vibration.core.domain.models import TrendResult
from vibration.presentation.views.tabs.peak_tab import PeakTabView

logger = logging.getLogger(__name__)

VIEW_TYPE_INT_TO_STR = {1: 'ACC', 2: 'VEL', 3: 'DIS'}
VIEW_TYPE_STR_TO_INT = {'ACC': 1, 'VEL': 2, 'DIS': 3}


class PeakPresenter:
    """
    Presenter for peak analysis tab (MVP pattern).
    
    Args:
        view: Peak tab view instance.
        peak_service: Peak computation service instance.
    """
    
    def __init__(self, view: PeakTabView, peak_service: PeakService):
        self.view = view
        self.peak_service = peak_service
        
        self._file_paths: List[str] = []
        self._current_view_type: str = 'ACC'
        self._last_result: Optional[TrendResult] = None
        
        self._connect_signals()
        logger.debug("PeakPresenter initialized")
    
    def _connect_signals(self):
        self.view.compute_requested.connect(self._on_compute_requested)
        self.view.view_type_changed.connect(self._on_view_type_changed)
        self.view.frequency_band_changed.connect(self._on_frequency_band_changed)
        self.view.save_requested.connect(self._on_save_requested)
    
    def load_files(self, file_paths: List[str]) -> None:
        self._file_paths = list(file_paths)
        logger.info(f"Loaded {len(file_paths)} files for peak analysis")
    
    def _on_compute_requested(self) -> None:
        if not self._file_paths:
            logger.warning("No files loaded, cannot compute peak trend")
            return
        
        params = self.view.get_parameters()
        view_type_int = params.get('view_type', 1)
        view_type_str = VIEW_TYPE_INT_TO_STR.get(view_type_int, 'ACC')
        
        self._current_view_type = view_type_str
        self.view.set_view_type(view_type_str)
        
        window_type = params.get('window_type', 'Hanning').lower()
        delta_f = params.get('delta_f', 1.0)
        overlap = params.get('overlap', 50.0)
        
        band_min = params.get('band_min', 0.0)
        band_max = params.get('band_max', 10000.0)
        frequency_band = (band_min, band_max) if band_min < band_max else None
        
        self.view.clear_plot()
        
        try:
            result = self.peak_service.compute_peak_trend(
                file_paths=self._file_paths,
                delta_f=delta_f,
                overlap=overlap,
                window_type=window_type,
                view_type=view_type_str,
                frequency_band=frequency_band
            )
            
            self._last_result = result
            self._update_view_with_result(result)
            
            logger.info(f"Computed peak trend for {result.num_files} files, view_type={view_type_str}")
            
        except Exception as e:
            logger.error(f"Error computing peak trend: {e}")
    
    def _update_view_with_result(self, result: TrendResult) -> None:
        if not result.channel_data:
            logger.warning("No channel data in result")
            return
        
        x_labels = [ts.strftime('%Y-%m-%d\n%H:%M:%S') for ts in result.timestamps]
        
        band_str = ""
        if result.frequency_band:
            band_str = f" ({result.frequency_band[0]:.0f}-{result.frequency_band[1]:.0f} Hz)"
        title = f"{result.view_type} Band Peak Trend{band_str}"
        
        self.view.plot_peak_trend(
            channel_data=result.channel_data,
            x_labels=x_labels,
            title=title
        )
    
    def _on_view_type_changed(self, view_type_int: int) -> None:
        view_type_str = VIEW_TYPE_INT_TO_STR.get(view_type_int, 'ACC')
        
        if view_type_str == self._current_view_type:
            return
        
        self._current_view_type = view_type_str
        self.view.set_view_type(view_type_str)
        
        logger.debug(f"View type changed to {view_type_str}")
        
        if self._file_paths:
            self._on_compute_requested()
    
    def _on_frequency_band_changed(self, min_freq: float, max_freq: float) -> None:
        logger.debug(f"Frequency band changed to {min_freq}-{max_freq} Hz")
        
        if self._file_paths:
            self._on_compute_requested()
    
    def _on_save_requested(self) -> None:
        if not self._last_result:
            logger.warning("No data to save")
            return
        logger.info("Save requested - delegate to external handler")
    
    def get_last_result(self) -> Optional[TrendResult]:
        return self._last_result
    
    def get_current_view_type(self) -> str:
        return self._current_view_type
    
    def has_data(self) -> bool:
        return bool(self._file_paths)
    
    def get_file_count(self) -> int:
        return len(self._file_paths)


if __name__ == "__main__":
    print("PeakPresenter Test")
    print("=" * 50)
    
    import inspect
    sig = inspect.signature(PeakPresenter.__init__)
    params = list(sig.parameters.keys())
    print(f"Constructor params: {params}")
    
    assert 'view' in params, "Missing 'view' parameter"
    assert 'peak_service' in params, "Missing 'peak_service' parameter"
    print("DI signature OK")
    
    from unittest.mock import MagicMock
    
    mock_view = MagicMock(spec=PeakTabView)
    mock_view.compute_requested = MagicMock()
    mock_view.view_type_changed = MagicMock()
    mock_view.frequency_band_changed = MagicMock()
    mock_view.save_requested = MagicMock()
    
    mock_service = MagicMock(spec=PeakService)
    
    presenter = PeakPresenter(view=mock_view, peak_service=mock_service)
    
    test_files = ['/path/to/file1.txt', '/path/to/file2.txt']
    presenter.load_files(test_files)
    
    assert presenter.has_data(), "Data should be loaded"
    assert presenter.get_file_count() == 2, "Should have 2 files"
    print("File loading OK")
    
    print("\nPeakPresenter tests passed!")
