"""
Spectrum analysis presenter (MVP pattern).

Coordinates SpectrumTabView and FFTService for spectrum analysis workflow.
Uses constructor injection for dependencies - no service locator pattern.
"""
import logging
from typing import Optional, List

import numpy as np

from vibration.core.services.fft_service import FFTService
from vibration.core.domain.models import FFTResult, SignalData
from vibration.presentation.views.tabs.spectrum_tab import SpectrumTabView

logger = logging.getLogger(__name__)


VIEW_TYPE_INT_TO_STR = {1: 'ACC', 2: 'VEL', 3: 'DIS'}
VIEW_TYPE_STR_TO_INT = {'ACC': 1, 'VEL': 2, 'DIS': 3}


class SpectrumPresenter:
    """
    Presenter for spectrum analysis tab (MVP pattern).
    
    Args:
        view: Spectrum tab view instance.
        fft_service: FFT computation service instance.
    """
    
    def __init__(self, view: SpectrumTabView, fft_service: FFTService):
        self.view = view
        self.fft_service = fft_service
        
        self._current_data: Optional[np.ndarray] = None
        self._current_sampling_rate: float = 0.0
        self._current_view_type: str = 'ACC'
        self._signal_data_list: List[SignalData] = []
        self._last_results: List[FFTResult] = []
        
        self._connect_signals()
        logger.debug("SpectrumPresenter initialized")
    
    def _connect_signals(self):
        self.view.compute_requested.connect(self._on_compute_requested)
        self.view.view_type_changed.connect(self._on_view_type_changed)
        self.view.window_type_changed.connect(self._on_window_type_changed)
        self.view.next_file_requested.connect(self._on_next_file_requested)
    
    def load_data(self, data: np.ndarray, sampling_rate: float,
                  signal_type: str = 'ACC', label: str = '') -> None:
        """
        Load single signal data for analysis.
        
        Args:
            data: Time-domain signal data (1D array).
            sampling_rate: Sampling rate in Hz.
            signal_type: Type of signal ('ACC', 'VEL', 'DIS').
            label: Label for the signal (e.g., filename).
        """
        self._current_data = np.asarray(data).flatten()
        self._current_sampling_rate = sampling_rate
        
        self._signal_data_list = [SignalData(
            data=self._current_data,
            sampling_rate=sampling_rate,
            signal_type=signal_type.upper(),
            channel=label
        )]
        
        logger.info(f"Loaded data: {len(self._current_data)} samples at {sampling_rate} Hz")
    
    def load_multiple_signals(self, signals: List[SignalData]) -> None:
        """
        Load multiple signals for batch analysis.
        
        Args:
            signals: List of SignalData objects to analyze.
        """
        self._signal_data_list = signals
        
        if signals:
            first = signals[0]
            self._current_data = first.data
            self._current_sampling_rate = first.sampling_rate
        
        logger.info(f"Loaded {len(signals)} signals for analysis")
    
    def _on_compute_requested(self) -> None:
        if not self._signal_data_list:
            logger.warning("No data loaded, cannot compute")
            return
        
        params = self.view.get_parameters()
        view_type_int = params.get('view_type', 1)
        view_type_str = VIEW_TYPE_INT_TO_STR.get(view_type_int, 'ACC')
        
        self._current_view_type = view_type_str
        self.view.set_view_type(view_type_str)
        
        window_type = params.get('window_type', 'Hanning').lower()
        if self.fft_service.window_type != window_type:
            self.fft_service.window_type = window_type
        
        self.view.clear_plots()
        self._last_results = []
        
        for idx, signal_data in enumerate(self._signal_data_list):
            try:
                result = self._compute_single_signal(signal_data, view_type_str)
                self._last_results.append(result)
                
                time_array = self._generate_time_array(
                    len(signal_data.data), signal_data.sampling_rate
                )
                self.view.plot_waveform(
                    time=time_array.tolist(),
                    amplitude=signal_data.data.tolist(),
                    label=signal_data.channel,
                    color_index=idx,
                    clear=(idx == 0)
                )
                
                self.view.plot_spectrum(
                    frequencies=result.frequency.tolist(),
                    spectrum=result.spectrum.tolist(),
                    label=signal_data.channel,
                    color_index=idx,
                    clear=(idx == 0)
                )
                
                logger.debug(f"Plotted signal {idx}: {signal_data.channel}")
                
            except Exception as e:
                logger.error(f"Error computing FFT for signal {idx}: {e}")
        
        logger.info(f"Computed {len(self._last_results)} spectra, view_type={view_type_str}")
    
    def _compute_single_signal(self, signal_data: SignalData,
                                view_type: str) -> FFTResult:
        return self.fft_service.compute_spectrum(
            data=signal_data.data,
            view_type=view_type,
            input_signal_type=signal_data.signal_type
        )
    
    def _generate_time_array(self, num_samples: int,
                              sampling_rate: float) -> np.ndarray:
        duration = num_samples / sampling_rate
        return np.linspace(0, duration, num_samples)
    
    def _on_view_type_changed(self, view_type_int: int) -> None:
        """
        Handle view type change (ACC/VEL/DIS).
        
        Args:
            view_type_int: View type as integer (1=ACC, 2=VEL, 3=DIS).
        """
        view_type_str = VIEW_TYPE_INT_TO_STR.get(view_type_int, 'ACC')
        
        if view_type_str == self._current_view_type:
            return
        
        self._current_view_type = view_type_str
        self.view.set_view_type(view_type_str)
        
        logger.debug(f"View type changed to {view_type_str}")
        
        if self._signal_data_list:
            self._on_compute_requested()
    
    def _on_window_type_changed(self, window_type: str) -> None:
        """
        Handle window type change.
        
        Args:
            window_type: Window function name (e.g., 'Hanning', 'Flattop').
        """
        normalized = window_type.lower()
        
        if self.fft_service.window_type == normalized:
            return
        
        self.fft_service.window_type = normalized
        logger.debug(f"Window type changed to {normalized}")
        
        if self._signal_data_list:
            self._on_compute_requested()
    
    def _on_next_file_requested(self) -> None:
        logger.debug("Next file requested")
    
    def get_last_results(self) -> List[FFTResult]:
        """Get results from last computation."""
        return self._last_results.copy()
    
    def get_current_view_type(self) -> str:
        """Get current view type as string."""
        return self._current_view_type
    
    def has_data(self) -> bool:
        """Check if data is loaded."""
        return bool(self._signal_data_list)


if __name__ == "__main__":
    print("SpectrumPresenter Test")
    print("=" * 50)
    
    import inspect
    sig = inspect.signature(SpectrumPresenter.__init__)
    params = list(sig.parameters.keys())
    print(f"Constructor params: {params}")
    
    assert 'view' in params, "Missing 'view' parameter"
    assert 'fft_service' in params, "Missing 'fft_service' parameter"
    print("DI signature OK")
    
    from unittest.mock import MagicMock
    
    mock_view = MagicMock(spec=SpectrumTabView)
    mock_view.compute_requested = MagicMock()
    mock_view.view_type_changed = MagicMock()
    mock_view.window_type_changed = MagicMock()
    mock_view.next_file_requested = MagicMock()
    
    mock_service = MagicMock(spec=FFTService)
    mock_service.window_type = 'hanning'
    
    presenter = SpectrumPresenter(view=mock_view, fft_service=mock_service)
    
    test_data = np.sin(np.linspace(0, 2 * np.pi, 1000))
    presenter.load_data(test_data, sampling_rate=1000.0, label="test")
    
    assert presenter.has_data(), "Data should be loaded"
    print("Data loading OK")
    
    print("\nSpectrumPresenter tests passed!")
