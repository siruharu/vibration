"""
피크 분석 프레젠터 (MVP 패턴).

PeakTabView와 PeakService를 조율하여 배치 피크 분석 워크플로우를 처리합니다.
생성자 주입 방식으로 의존성을 관리합니다 - 서비스 로케이터 패턴 미사용.
"""
import logging
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from vibration.core.services.peak_service import PeakService, ViewType
from vibration.core.services.file_service import FileService
from vibration.core.domain.models import TrendResult
from vibration.presentation.views.tabs.peak_tab import PeakTabView
from vibration.presentation.views.dialogs.progress_dialog import ProgressDialog
from vibration.presentation.views.dialogs.list_save_dialog import ListSaveDialog
from vibration.infrastructure.event_bus import get_event_bus
from typing import cast
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)

VIEW_TYPE_INT_TO_STR = {1: 'ACC', 2: 'VEL', 3: 'DIS'}
VIEW_TYPE_STR_TO_INT = {'ACC': 1, 'VEL': 2, 'DIS': 3}


class PeakPresenter:
    """
    피크 분석 탭 프레젠터 (MVP 패턴).
    
    인자:
        view: 피크 탭 뷰 인스턴스.
        peak_service: 피크 연산 서비스 인스턴스.
        file_service: 파일 작업 서비스 인스턴스.
    """
    
    def __init__(self, view: PeakTabView, peak_service: PeakService, file_service: FileService):
        self.view = view
        self.peak_service = peak_service
        self.file_service = file_service
        
        self._file_paths: List[str] = []
        self._directory_path: str = ""
        self._current_view_type: str = 'ACC'
        self._last_result: Optional[TrendResult] = None
        self._progress_dialog: Optional[ProgressDialog] = None
        
        self._event_bus = get_event_bus()
        self._event_bus.files_loaded.connect(self._on_files_loaded)
        self._event_bus.directory_selected.connect(self._on_directory_selected)
        
        self._connect_signals()
        logger.debug("PeakPresenter initialized")
    
    def _connect_signals(self):
        self.view.compute_requested.connect(self._on_compute_requested)
        self.view.view_type_changed.connect(self._on_view_type_changed)
        self.view.save_requested.connect(self._on_save_requested)
        self.view.list_save_requested.connect(self._on_list_save_requested)
    
    def load_files(self, file_paths: List[str]) -> None:
        self._file_paths = list(file_paths)
        logger.info(f"Loaded {len(file_paths)} files for peak analysis")
    
    def _on_compute_requested(self) -> None:
        selected_filenames = self.view.get_selected_files()
        if not selected_filenames or not self._directory_path:
            logger.warning("No files selected or directory not set")
            return
        
        from pathlib import Path
        file_paths = [str(Path(self._directory_path) / filename) for filename in selected_filenames]
        
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
        
        self._progress_dialog = ProgressDialog(len(file_paths), self.view)
        self._progress_dialog.show()
        
        def update_progress(current: int, total: int):
            if self._progress_dialog:
                self._progress_dialog.update_progress(current)
        
        try:
            result = self.peak_service.compute_peak_trend(
                file_paths=file_paths,
                delta_f=delta_f,
                overlap=overlap,
                window_type=window_type,
                view_type=cast(ViewType, view_type_str),
                frequency_band=frequency_band,
                progress_callback=update_progress
            )
            
            self._last_result = result
            self._update_view_with_result(result)
            
            logger.info(f"Computed peak trend for {result.num_files} files, view_type={view_type_str}")
            
        except Exception as e:
            logger.error(f"Error computing peak trend: {e}")
        finally:
            if self._progress_dialog:
                self._progress_dialog.close()
                self._progress_dialog = None
    
    def _update_view_with_result(self, result: TrendResult) -> None:
        if not result.channel_data:
            logger.warning("No channel data in result")
            return
        
        self.view.plot_peak_trend(
            channel_data=result.channel_data,
            clear=True
        )
        
        all_x = []
        all_y = []
        all_files = []
        for ch in sorted(result.channel_data.keys()):
            data = result.channel_data[ch]
            all_x.extend(data['x'])
            all_y.extend(data['y'])
            all_files.extend(data.get('labels', []))
        
        self.view.set_peak_data(all_x, all_y, all_files)
    
    def _on_view_type_changed(self, view_type_int: int) -> None:
        view_type_str = VIEW_TYPE_INT_TO_STR.get(view_type_int, 'ACC')
        
        if view_type_str == self._current_view_type:
            return
        
        self._current_view_type = view_type_str
        self.view.set_view_type(view_type_str)
        
        logger.debug(f"View type changed to {view_type_str}")
        
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
    
    def _on_files_loaded(self, files: List[str]) -> None:
        logger.info(f"Received {len(files)} files from Data Query")
        self.view.set_files(files)
    
    def _on_directory_selected(self, directory: str) -> None:
        self._directory_path = directory
        self.view.set_directory_path(directory)
        logger.info(f"Directory updated: {directory}")
    
    def _on_list_save_requested(self, channel_files: dict, directory_path: str) -> None:
        try:
            dialog = ListSaveDialog(
                channel_files=channel_files,
                parent=self.view,
                directory_path=directory_path
            )
            
            dialog.setWindowModality(Qt.ApplicationModal)
            dialog.resize(1600, 900)
            dialog.show()
            
            logger.info(f"Opened Detail Analysis for {sum(len(v) for v in channel_files.values())} peak files")
            
        except Exception as e:
            logger.error(f"Error opening Detail Analysis: {e}")
            import traceback
            traceback.print_exc()


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
    mock_file_service = MagicMock(spec=FileService)
    
    presenter = PeakPresenter(view=mock_view, peak_service=mock_service, file_service=mock_file_service)
    
    test_files = ['/path/to/file1.txt', '/path/to/file2.txt']
    presenter.load_files(test_files)
    
    assert presenter.has_data(), "Data should be loaded"
    assert presenter.get_file_count() == 2, "Should have 2 files"
    print("File loading OK")
    
    print("\nPeakPresenter tests passed!")
