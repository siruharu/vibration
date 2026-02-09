"""
트렌드 분석 프레젠터 (MVP 패턴).

TrendTabView와 TrendService를 조율하여 배치 트렌드 분석 워크플로우를 처리합니다.
생성자 주입 방식으로 의존성을 관리합니다 - 서비스 로케이터 패턴 미사용.
"""
import logging
import os
from typing import List, Optional, Tuple
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from vibration.core.services.trend_service import TrendService
from vibration.core.services.file_service import FileService
from vibration.core.domain.models import TrendResult
from vibration.presentation.views.tabs.trend_tab import TrendTabView
from vibration.presentation.views.dialogs import ProgressDialog
from vibration.presentation.views.dialogs.list_save_dialog import ListSaveDialog
from vibration.infrastructure.event_bus import get_event_bus

logger = logging.getLogger(__name__)


VIEW_TYPE_INT_TO_STR = {1: 'ACC', 2: 'VEL', 3: 'DIS'}
VIEW_TYPE_STR_TO_INT = {'ACC': 1, 'VEL': 2, 'DIS': 3}


class TrendPresenter:
    """
    트렌드 분석 탭 프레젠터 (MVP 패턴).
    
    인자:
        view: 트렌드 탭 뷰 인스턴스.
        trend_service: 트렌드 연산 서비스 인스턴스.
    """
    
    def __init__(self, view: TrendTabView, trend_service: TrendService, file_service: FileService):
        self.view = view
        self.trend_service = trend_service
        self.file_service = file_service
        
        self._file_paths: List[str] = []
        self._directory_path: str = ""
        self._current_view_type: str = 'ACC'
        self._last_result: Optional[TrendResult] = None
        self._trend_cache: dict = {
            'computed': False,
            'result': None,
            'params': {}
        }
        
        self._event_bus = get_event_bus()
        self._event_bus.files_loaded.connect(self._on_files_loaded)
        self._event_bus.directory_selected.connect(self._on_directory_selected)
        
        self._connect_signals()
        logger.debug("TrendPresenter initialized")
    
    def _connect_signals(self):
        """뷰 시그널을 프레젠터 메서드에 연결합니다."""
        self.view.compute_requested.connect(self._on_compute_requested)
        self.view.load_data_requested.connect(self._on_load_data_requested)
        self.view.save_requested.connect(self._on_save_requested)
        self.view.list_save_requested.connect(self._on_list_save_requested)
        self.view.view_type_changed.connect(self._on_view_type_changed)
    
    def load_files(self, file_paths: List[str]) -> None:
        """
        트렌드 분석을 위한 파일을 로드합니다.
        
        인자:
            file_paths: 분석할 파일 경로 목록.
        """
        self._file_paths = list(file_paths)
        logger.info(f"Loaded {len(file_paths)} files for trend analysis")
    
    def _on_compute_requested(self) -> None:
        """연산 및 플롯 버튼 클릭 처리."""
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
        delta_f = params.get('delta_f', 1.0)
        overlap = params.get('overlap', 50.0)
        band_min = params.get('band_min', 0.0)
        band_max = params.get('band_max', 10000.0)
        frequency_band = (band_min, band_max) if band_min < band_max else None
        
        file_paths = [os.path.join(self._directory_path, f) for f in selected_files]
        
        current_params = {
            'delta_f': delta_f,
            'overlap': overlap,
            'window_type': window_type,
            'view_type': view_type_str,
            'frequency_band': frequency_band,
            'file_count': len(file_paths),
            'file_names': tuple(selected_files)
        }
        
        cache_valid = (
            self._trend_cache.get('computed', False) and
            self._trend_cache.get('params') == current_params
        )
        
        if cache_valid:
            logger.debug("Using cached trend data")
            result = self._trend_cache['result']
            self._update_view_with_result(result)
            return
        
        self.view.clear_plot()
        
        progress_dialog = ProgressDialog(len(file_paths), self.view)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        def update_progress(current, total):
            progress_dialog.update_progress(current)
            QApplication.processEvents()
        
        try:
            result = self.trend_service.compute_trend(
                file_paths=file_paths,
                delta_f=delta_f,
                overlap=overlap,
                window_type=window_type,
                view_type=view_type_str,
                frequency_band=frequency_band,
                progress_callback=update_progress
            )
            
            self._last_result = result
            self._trend_cache = {
                'computed': True,
                'result': result,
                'params': current_params
            }
            self._update_view_with_result(result)
            
            logger.info(f"Computed trend for {result.num_files} files, view_type={view_type_str}")
            
        except Exception as e:
            logger.error(f"Error computing trend: {e}")
        finally:
            progress_dialog.close()
    
    def _on_load_data_requested(self) -> None:
        """데이터 로드 및 플롯 버튼 클릭 처리."""
        logger.debug("Load data requested - same as compute for now")
        self._on_compute_requested()
    
    def _on_save_requested(self) -> None:
        """데이터 추출 버튼 클릭 처리."""
        if not self._last_result:
            logger.warning("No data to save")
            return
        logger.debug("Save trend data requested")
    
    def _update_view_with_result(self, result: TrendResult) -> None:
        """
        트렌드 결과로 뷰를 업데이트합니다.
        
        인자:
            result: 서비스에서 반환된 TrendResult.
        """
        if not result.channel_data:
            logger.warning("No channel data in result")
            return
        
        self.view.plot_trend(
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
        
        self.view.set_trend_data(all_x, all_y, all_files)
    
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
        
        if self._file_paths:
            self._on_compute_requested()
    
    def _on_directory_selected(self, directory: str) -> None:
        self._directory_path = directory
        self.view.set_directory_path(directory)
        logger.info(f"Directory path updated: {directory}")
    
    def _on_files_loaded(self, files: List[str]) -> None:
        logger.info(f"Received {len(files)} files from Data Query")
        self.view.set_files(files)
    
    def _on_list_save_requested(self, channel_files: dict, directory_path: str) -> None:
        """
        리스트 저장 버튼 클릭 처리 - 상세 분석 다이얼로그를 엽니다.
        
        인자:
            channel_files: 채널 이름을 파일 목록에 매핑하는 딕셔너리
            directory_path: 파일이 위치한 디렉토리
        """
        try:
            dialog = ListSaveDialog(
                channel_files=channel_files,
                parent=self.view,
                directory_path=directory_path
            )
            
            dialog.setWindowModality(Qt.ApplicationModal)
            dialog.resize(1600, 900)
            dialog.show()
            
            logger.info(f"Opened Detail Analysis dialog with {sum(len(v) for v in channel_files.values())} files")
            
        except Exception as e:
            logger.error(f"Error opening Detail Analysis dialog: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_frequency_band_changed(self, min_freq: float, max_freq: float) -> None:
        """
        주파수 대역 변경 처리.
        
        인자:
            min_freq: 최소 주파수 (Hz).
            max_freq: 최대 주파수 (Hz).
        """
        logger.debug(f"Frequency band changed to {min_freq}-{max_freq} Hz")
        
        if self._file_paths:
            self._on_compute_requested()
    
    def get_last_result(self) -> Optional[TrendResult]:
        """마지막 연산 결과를 반환합니다."""
        return self._last_result
    
    def get_current_view_type(self) -> str:
        """현재 뷰 타입을 문자열로 반환합니다."""
        return self._current_view_type
    
    def has_data(self) -> bool:
        """파일 로드 여부를 확인합니다."""
        return bool(self._file_paths)
    
    def get_file_count(self) -> int:
        """로드된 파일 수를 반환합니다."""
        return len(self._file_paths)
    
    def _on_files_loaded(self, files: List[str]) -> None:
        logger.info(f"Received {len(files)} files from Data Query")
        self.view.set_files(files)


if __name__ == "__main__":
    print("TrendPresenter Test")
    print("=" * 50)
    
    import inspect
    sig = inspect.signature(TrendPresenter.__init__)
    params = list(sig.parameters.keys())
    print(f"Constructor params: {params}")
    
    assert 'view' in params, "Missing 'view' parameter"
    assert 'trend_service' in params, "Missing 'trend_service' parameter"
    print("DI signature OK")
    
    from unittest.mock import MagicMock
    
    mock_view = MagicMock(spec=TrendTabView)
    mock_view.compute_requested = MagicMock()
    mock_view.view_type_changed = MagicMock()
    mock_view.frequency_band_changed = MagicMock()
    
    mock_service = MagicMock(spec=TrendService)
    
    presenter = TrendPresenter(view=mock_view, trend_service=mock_service)
    
    test_files = ['/path/to/file1.txt', '/path/to/file2.txt']
    presenter.load_files(test_files)
    
    assert presenter.has_data(), "Data should be loaded"
    assert presenter.get_file_count() == 2, "Should have 2 files"
    print("File loading OK")
    
    print("\nTrendPresenter tests passed!")
