"""
스펙트럼 분석 프레젠터 (MVP 패턴).

SpectrumTabView와 FFTService를 조율하여 스펙트럼 분석 워크플로우를 처리합니다.
생성자 주입 방식으로 의존성을 관리합니다 - 서비스 로케이터 패턴 미사용.
"""
import logging
import os
from typing import Dict, Optional, List, Tuple

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from vibration.core.services.fft_service import FFTService
from vibration.core.services.file_service import FileService
from vibration.core.domain.models import FFTResult, SignalData
from vibration.presentation.views.tabs.spectrum_tab import SpectrumTabView
from vibration.presentation.views.dialogs import ProgressDialog
from vibration.presentation.views.dialogs.spectrum_window import SpectrumWindow
from vibration.infrastructure.event_bus import get_event_bus

logger = logging.getLogger(__name__)


VIEW_TYPE_INT_TO_STR = {1: 'ACC', 2: 'VEL', 3: 'DIS'}
VIEW_TYPE_STR_TO_INT = {'ACC': 1, 'VEL': 2, 'DIS': 3}


class SpectrumPresenter:
    """
    스펙트럼 분석 탭 프레젠터 (MVP 패턴).
    
    인자:
        view: 스펙트럼 탭 뷰 인스턴스.
        fft_service: FFT 연산 서비스 인스턴스.
    """
    
    def __init__(self, view: SpectrumTabView, fft_service: FFTService, file_service: FileService):
        self.view = view
        self.fft_service = fft_service
        self.file_service = file_service
        
        self._current_data: Optional[np.ndarray] = None
        self._current_sampling_rate: float = 0.0
        self._current_view_type: str = 'ACC'
        self._signal_data_list: List[SignalData] = []
        self._last_results: List[FFTResult] = []
        self._directory_path: str = ""
        self._custom_sensitivity: Optional[float] = None
        self._all_files: List[str] = []
        self._spectrum_windows: List[SpectrumWindow] = []
        self._computed_cache: Dict[str, Tuple[SignalData, FFTResult]] = {}
        
        self._event_bus = get_event_bus()
        self._event_bus.files_loaded.connect(self._on_files_loaded)
        self._event_bus.directory_selected.connect(self._on_directory_selected)
        
        self._connect_signals()
        logger.debug("SpectrumPresenter initialized")
    
    def _connect_signals(self):
        self.view.compute_requested.connect(self._on_compute_requested)
        self.view.view_type_changed.connect(self._on_view_type_changed)
        self.view.window_type_changed.connect(self._on_window_type_changed)
        self.view.next_file_requested.connect(self._on_next_file_requested)
        self.view.file_clicked.connect(self._on_file_clicked)
        self.view.date_filter_changed.connect(self._on_date_filter_changed)
        self.view.Sensitivity_edit.returnPressed.connect(self._on_sensitivity_changed)
        self.view.refresh_requested.connect(self._on_compute_requested)
        self.view.close_all_windows_requested.connect(self._on_close_all_windows)
        self.view.axis_range_changed.connect(self._on_axis_range_changed)
        self.view.time_range_selected.connect(self._on_time_range_selected)
    
    def load_data(self, data: np.ndarray, sampling_rate: float,
                  signal_type: str = 'ACC', label: str = '') -> None:
        """
        단일 신호 데이터를 분석을 위해 로드합니다.
        
        인자:
            data: 시간 영역 신호 데이터 (1차원 배열).
            sampling_rate: 샘플링 레이트 (Hz).
            signal_type: 신호 유형 ('ACC', 'VEL', 'DIS').
            label: 신호 라벨 (예: 파일명).
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
        배치 분석을 위해 다중 신호를 로드합니다.
        
        인자:
            signals: 분석할 SignalData 객체 목록.
        """
        self._signal_data_list = signals
        
        if signals:
            first = signals[0]
            self._current_data = first.data
            self._current_sampling_rate = first.sampling_rate
        
        logger.info(f"Loaded {len(signals)} signals for analysis")
    
    def _on_compute_requested(self) -> None:
        if not self._directory_path:
            logger.warning("No directory selected")
            return
        
        selected_files = self.view.get_selected_files()
        if not selected_files:
            logger.warning("No files selected")
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
        self._signal_data_list = []
        self._computed_cache.clear()
        
        self._load_and_plot_files(selected_files)
    
    def _load_and_plot_files(self, filenames: List[str]) -> None:
        """파일 로드 → FFT → 플롯. 결과를 _computed_cache에 축적."""
        nfft = self.fft_service._engine.nfft
        skipped_files: List[Tuple[str, int]] = []
        computed_batch: List[Tuple[str, SignalData, FFTResult]] = []
        
        progress_dialog = ProgressDialog(len(filenames), self.view)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        try:
            for idx, filename in enumerate(filenames):
                progress_dialog.update_progress(idx + 1)
                QApplication.processEvents()
                
                filepath = os.path.join(self._directory_path, filename)
                
                if not os.path.exists(filepath):
                    logger.warning(f"File not found: {filepath}")
                    continue
                
                try:
                    file_data = self.file_service.load_file(filepath)
                    
                    if not file_data['is_valid']:
                        logger.warning(f"Invalid file: {filename}")
                        continue
                    
                    raw_data = file_data['data']
                    if self._custom_sensitivity is not None:
                        raw_data = raw_data / (self._custom_sensitivity / 1000.0)
                    
                    if len(raw_data) < nfft:
                        skipped_files.append((filename, len(raw_data)))
                        logger.warning(
                            f"Skipped {filename}: data length ({len(raw_data)}) "
                            f"< NFFT ({nfft})"
                        )
                        continue
                    
                    signal_data = SignalData(
                        data=raw_data,
                        sampling_rate=file_data['sampling_rate'],
                        signal_type='ACC',
                        channel=filename
                    )
                    
                    result = self._compute_single_signal(signal_data, self._current_view_type)
                    computed_batch.append((filename, signal_data, result))
                    
                except Exception as e:
                    logger.error(f"Error processing file {filename}: {e}")
        finally:
            progress_dialog.close()
        
        if skipped_files:
            skip_msg_lines = [
                f"  - {fname} (길이: {dlen})"
                for fname, dlen in skipped_files[:10]
            ]
            if len(skipped_files) > 10:
                skip_msg_lines.append(f"  ... 외 {len(skipped_files) - 10}개")
            skip_msg = "\n".join(skip_msg_lines)
            self.view.show_warning(
                "데이터 길이 부족",
                f"다음 {len(skipped_files)}개 파일의 데이터 길이가 "
                f"NFFT({nfft})보다 짧아 분석에서 제외되었습니다:\n\n{skip_msg}"
            )
        
        if not computed_batch:
            return
        
        plotted_count = len(self._last_results)
        self.view.begin_batch()
        try:
            for filename, signal_data, result in computed_batch:
                self._signal_data_list.append(signal_data)
                self._last_results.append(result)
                self._computed_cache[filename] = (signal_data, result)
                
                time_array = self._generate_time_array(
                    len(signal_data.data), signal_data.sampling_rate
                )
                self.view.plot_waveform(
                    time=time_array.tolist(),
                    amplitude=signal_data.data.tolist(),
                    label=filename,
                    color_index=plotted_count,
                    clear=(plotted_count == 0)
                )
                self.view.plot_spectrum(
                    frequencies=result.frequency.tolist(),
                    spectrum=result.spectrum.tolist(),
                    label=filename,
                    color_index=plotted_count,
                    clear=(plotted_count == 0)
                )
                plotted_count += 1
        finally:
            self.view.end_batch()
        
        logger.info(
            f"Computed {len(computed_batch)} spectra, "
            f"total={len(self._last_results)}, "
            f"view_type={self._current_view_type}"
        )
    
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
        뷰 타입 변경 처리 (ACC/VEL/DIS).
        
        인자:
            view_type_int: 정수형 뷰 타입 (1=ACC, 2=VEL, 3=DIS).
        """
        view_type_str = VIEW_TYPE_INT_TO_STR.get(view_type_int, 'ACC')
        
        if view_type_str == self._current_view_type:
            return
        
        self._current_view_type = view_type_str
        self.view.set_view_type(view_type_str)
        
        logger.debug(f"View type changed to {view_type_str}")
    
    def _on_window_type_changed(self, window_type: str) -> None:
        """
        윈도우 타입 변경 처리.
        
        인자:
            window_type: 윈도우 함수 이름 (예: 'Hanning', 'Flattop').
        """
        normalized = window_type.lower()
        
        if self.fft_service.window_type == normalized:
            return
        
        self.fft_service.window_type = normalized
        logger.debug(f"Window type changed to {normalized}")
    
    def _on_next_file_requested(self) -> None:
        logger.debug("Next file requested")
        
        if not self._directory_path:
            logger.warning("No directory selected")
            return
        
        selected_items = self.view.file_list.selectedItems()
        if not selected_items:
            logger.warning("No files selected")
            return
        
        last_selected = selected_items[-1]
        current_index = self.view.file_list.row(last_selected)
        total_count = self.view.file_list.count()
        
        if current_index >= total_count - 1:
            logger.info("Already at last file")
            return
        
        next_index = current_index + 1
        next_item = self.view.file_list.item(next_index)
        if not next_item:
            logger.warning(f"Could not find item at index {next_index}")
            return
        
        next_filename = next_item.text()
        next_item.setSelected(True)
        
        if next_filename in self._computed_cache:
            logger.debug(f"Cache hit: {next_filename}")
            return
        
        self._load_and_plot_files([next_filename])
        logger.info(
            f"Next: added {next_filename}, total plotted={len(self._last_results)}"
        )
    
    def _on_file_clicked(self, filename: str) -> None:
        if not self._directory_path:
            logger.warning("No directory path set")
            return
        
        filepath = os.path.join(self._directory_path, filename)
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return
        
        try:
            file_data = self.file_service.load_file(filepath)
            metadata = file_data.get('metadata', {})
            
            self.view.set_file_metadata(metadata)
            
            if file_data['is_valid']:
                self.load_data(
                    data=file_data['data'],
                    sampling_rate=file_data['sampling_rate'],
                    signal_type='ACC',
                    label=filename
                )
                logger.info(f"Loaded file: {filename}")
            else:
                logger.warning(f"Invalid file data: {filename}")
                
        except Exception as e:
            logger.error(f"Error loading file {filename}: {e}")
    
    def _on_directory_selected(self, directory: str) -> None:
        self._directory_path = directory
        logger.info(f"Directory path updated: {directory}")
    
    def _on_files_loaded(self, files: List[str]) -> None:
        logger.info(f"Received {len(files)} files from Data Query")
        self._all_files = list(files)
        self.view.set_files(files)
    
    def _on_date_filter_changed(self, from_date: str, to_date: str) -> None:
        filtered = []
        for filename in self._all_files:
            try:
                date_part = filename.split('_')[0]
                if len(filename.split('_')) >= 2:
                    date_part = filename.split('_')[0]
                if from_date <= date_part <= to_date:
                    filtered.append(filename)
            except (IndexError, ValueError):
                filtered.append(filename)
        
        self.view.Querry_list.clear()
        self.view.Querry_list.addItems(filtered)
        logger.info(f"Date filter applied: {from_date} ~ {to_date}, {len(filtered)}/{len(self._all_files)} files")
    
    def _on_sensitivity_changed(self) -> None:
        try:
            value = float(self.view.Sensitivity_edit.text())
            self._custom_sensitivity = value
            logger.info(f"Custom sensitivity set: {value} mV/g")
        except ValueError:
            self._custom_sensitivity = None
            logger.warning("Invalid sensitivity value, reset to default")
    
    def _on_close_all_windows(self) -> None:
        for window in self._spectrum_windows:
            window.close()
        self._spectrum_windows.clear()
        logger.info("All spectrum windows closed")
    
    def _on_axis_range_changed(self, plot_type: str, axis: str,
                                val_min: float, val_max: float) -> None:
        if plot_type == 'wave':
            ax = self.view.waveax
            canvas = self.view.wavecanvas
        else:
            ax = self.view.ax
            canvas = self.view.canvas
        
        if axis == 'x':
            ax.set_xlim(val_min, val_max)
        else:
            ax.set_ylim(val_min, val_max)
        canvas.draw_idle()
        logger.debug(f"Axis range set: {plot_type} {axis} [{val_min}, {val_max}]")
    
    def _on_time_range_selected(self, t_start: float, t_end: float) -> None:
        if not self._signal_data_list:
            logger.warning("No signal data for time range selection")
            return
        
        window = SpectrumWindow(t_start, t_end)
        plotted_count = 0
        
        for signal in self._signal_data_list:
            sr = signal.sampling_rate
            i_start = int(t_start * sr)
            i_end = int(t_end * sr)
            i_start = max(0, i_start)
            i_end = min(len(signal.data), i_end)
            
            if i_end - i_start < 2:
                logger.warning(f"Selected time range too short for {signal.channel}")
                continue
            
            segment = signal.data[i_start:i_end]
            
            try:
                result = self.fft_service.compute_spectrum(
                    data=segment,
                    view_type=self._current_view_type,
                    input_signal_type=signal.signal_type
                )
                
                window.plot_spectrum(
                    frequencies=result.frequency.tolist(),
                    spectrum=result.spectrum.tolist(),
                    label=f"{signal.channel} [{t_start:.3f}s-{t_end:.3f}s]",
                    view_type=self._current_view_type,
                    color_index=plotted_count,
                    clear=(plotted_count == 0)
                )
                plotted_count += 1
            except Exception as e:
                logger.error(f"Error computing spectrum for {signal.channel}: {e}")
        
        if plotted_count > 0:
            window.show()
            self._spectrum_windows.append(window)
            logger.info(
                f"Spectrum window created for range [{t_start:.3f}s, {t_end:.3f}s] "
                f"with {plotted_count} signals"
            )
        else:
            window.close()
    
    def get_last_results(self) -> List[FFTResult]:
        """마지막 연산 결과를 반환합니다."""
        return self._last_results.copy()
    
    def get_current_view_type(self) -> str:
        """현재 뷰 타입을 문자열로 반환합니다."""
        return self._current_view_type
    
    def has_data(self) -> bool:
        """데이터 로드 여부를 확인합니다."""
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
    
    mock_fft_service = MagicMock(spec=FFTService)
    mock_fft_service.window_type = 'hanning'
    
    mock_file_service = MagicMock(spec=FileService)
    
    presenter = SpectrumPresenter(view=mock_view, fft_service=mock_fft_service, file_service=mock_file_service)
    
    test_data = np.sin(np.linspace(0, 2 * np.pi, 1000))
    presenter.load_data(test_data, sampling_rate=1000.0, label="test")
    
    assert presenter.has_data(), "Data should be loaded"
    print("Data loading OK")
    
    print("\nSpectrumPresenter tests passed!")
