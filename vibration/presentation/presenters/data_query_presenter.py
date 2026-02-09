"""
데이터 조회 프레젠터 (MVP 패턴).

DataQueryTabView와 file_parser를 조율하여 파일 로딩 워크플로우를 처리합니다.
생성자 주입 방식으로 의존성을 관리합니다.
"""
import os
import shutil
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from collections import defaultdict, Counter

from vibration.core.services.file_parser import FileParser
from vibration.core.services.file_service import FileService
from vibration.core.services.project_service import ProjectService
from vibration.presentation.views.tabs.data_query_tab import DataQueryTabView
from vibration.infrastructure.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class DataQueryPresenter:
    """
    데이터 조회 탭 프레젠터 (MVP 패턴).
    
    뷰와 file_parser.FileParser를 조율하여
    디렉토리 선택 및 파일 로딩 워크플로우를 처리합니다.
    """
    
    def __init__(
        self,
        view: DataQueryTabView,
        file_service: Optional[FileService] = None,
        project_service: Optional[ProjectService] = None,
    ):
        self.view = view
        self._file_service = file_service or FileService()
        self._project_service = project_service or ProjectService()
        self._directory_path: str = ""
        self._all_files: List[str] = []
        self._all_file_paths: List[str] = []
        self._grouped_data: List[Dict[str, Any]] = []
        self._measurement_type: str = 'Unknown'
        self._event_bus = get_event_bus()
        self._connect_signals()
        logger.debug("DataQueryPresenter initialized")
    
    def _connect_signals(self):
        self.view.directory_selected.connect(self._on_directory_selected)
        self.view.files_loaded.connect(self._on_load_requested)
        self.view.files_chosen.connect(self._on_files_chosen)
        self.view.switch_to_spectrum_requested.connect(self._on_switch_to_spectrum)
        self.view.save_project_requested.connect(self._on_save_project)
        self.view.load_project_requested.connect(self._on_load_project)
        self.view.quarantine_requested.connect(self._on_quarantine)
        self.view.delete_requested.connect(self._on_delete)
    
    def _on_directory_selected(self, directory: str):
        self._directory_path = directory
        self._event_bus.directory_selected.emit(directory)
        logger.info(f"Directory selected: {directory}")
    
    def _on_load_requested(self, _):
        if not self._directory_path:
            logger.warning("No directory selected")
            return
        
        self._load_files_from_directory()
    
    def _load_files_from_directory(self):
        date_from, date_to = self.view.get_date_range()
        
        file_paths = self._file_service.scan_subdirectories(
            self._directory_path,
            date_from=date_from,
            date_to=date_to,
        )
        
        if not file_paths:
            try:
                files = os.listdir(self._directory_path)
                file_paths = [
                    os.path.join(self._directory_path, f)
                    for f in files if f.endswith(".txt")
                ]
            except OSError as e:
                logger.error(f"Failed to list directory: {e}")
                return
        
        self._all_file_paths = sorted(file_paths)
        self._all_files = [Path(fp).name for fp in self._all_file_paths]
        
        metadata_cache: Dict[str, Dict[str, Any]] = {}
        for fp in self._all_file_paths:
            metadata_cache[fp] = FileParser.parse_header_only(fp)
        
        file_dict: Dict[tuple, List[str]] = defaultdict(list)
        file_path_dict: Dict[tuple, List[str]] = defaultdict(list)
        
        for fp in self._all_file_paths:
            filename = Path(fp).name
            parts = filename.split("_")
            if len(parts) >= 2:
                date_part = parts[0]
                time_part = parts[1]
                time_parts = time_part.split("-")
                if len(time_parts) == 3:
                    formatted_time = f"{time_parts[0]}:{time_parts[1]}:{time_parts[2]}"
                    key = (date_part, formatted_time)
                    file_dict[key].append(filename)
                    file_path_dict[key].append(fp)
        
        grouped = []
        for (date_str, time_str), files in sorted(file_dict.items()):
            paths = file_path_dict[(date_str, time_str)]
            first_meta = metadata_cache.get(paths[0], {}) if paths else {}
            
            sr = first_meta.get('sampling_rate', 0.0)
            channel = first_meta.get('channel', '')
            sensitivity = first_meta.get('sensitivity', '')
            
            channels_in_group = set()
            for fp in paths:
                fname = Path(fp).name
                fname_parts = fname.split("_")
                if len(fname_parts) >= 4:
                    ch_part = fname_parts[3].replace('.txt', '')
                    channels_in_group.add(ch_part)
            
            channel_display = ', '.join(sorted(channels_in_group)) if channels_in_group else channel
            
            grouped.append({
                'date': date_str,
                'time': time_str,
                'count': len(files),
                'channel': channel_display,
                'sampling_rate': sr,
                'sensitivity': sensitivity,
                'files': files,
                'file_paths': paths,
                'is_anomaly': False,
                'anomaly_type': '',
            })
        
        self._detect_anomalies(grouped, metadata_cache)
        self._detect_measurement_type(metadata_cache)
        
        self._grouped_data = grouped
        self.view.set_files(grouped)
        self.view.set_measurement_type(self._measurement_type)
        logger.info(f"Loaded {len(grouped)} file groups from {len(self._all_files)} files")
    
    def _detect_anomalies(
        self,
        grouped: List[Dict[str, Any]],
        metadata_cache: Dict[str, Dict[str, Any]],
    ):
        sr_counter: Counter = Counter()
        for group in grouped:
            sr = group.get('sampling_rate', 0.0)
            if sr > 0:
                sr_counter[sr] += 1
        
        if not sr_counter:
            return
        
        majority_sr = sr_counter.most_common(1)[0][0]
        
        for group in grouped:
            sr = group.get('sampling_rate', 0.0)
            if sr > 0 and sr != majority_sr:
                group['is_anomaly'] = True
                group['anomaly_type'] = 'error'
                continue
            
            paths = group.get('file_paths', [])
            for fp in paths:
                meta = metadata_cache.get(fp, {})
                file_sr = meta.get('sampling_rate', 0.0)
                if file_sr > 0 and file_sr != majority_sr:
                    group['is_anomaly'] = True
                    group['anomaly_type'] = 'warning'
                    break
    
    def _detect_measurement_type(self, metadata_cache: Dict[str, Dict[str, Any]]):
        for _fp, meta in metadata_cache.items():
            iepe = meta.get('iepe', '').strip().lower()
            sensitivity = meta.get('sensitivity', '')
            
            if iepe in ('on', 'enable', 'enabled', '1', 'true'):
                if 'mv/g' in sensitivity.lower() or 'mv/G' in sensitivity:
                    self._measurement_type = 'ACC'
                    return
            
            if sensitivity:
                self._measurement_type = 'Pa'
                return
        
        self._measurement_type = 'Unknown'
    
    def _on_files_chosen(self, files: List[str]):
        logger.info(f"Files chosen: {len(files)} files")
        self._event_bus.files_loaded.emit(files)
        logger.debug(f"Emitted files_loaded event with {len(files)} file names")
    
    def _on_save_project(self):
        if not self._directory_path or not self._grouped_data:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self.view, "No Data", "Load data before saving a project.")
            return
        
        description = self.view.ask_project_description()
        if description is None:
            return
        
        save_location = self.view.ask_save_location()
        if not save_location:
            return
        
        project_data = ProjectService.build_project_data(
            parent_folder=self._directory_path,
            description=description,
            grouped_data=self._grouped_data,
            measurement_type=self._measurement_type,
        )
        
        try:
            json_path = self._project_service.save_project(project_data, save_location)
            self._event_bus.project_saved.emit(json_path)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self.view, "Project Saved", f"Project saved to:\n{json_path}"
            )
            logger.info(f"Project saved: {json_path}")
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self.view, "Error", f"Failed to save project:\n{e}")
    
    def _on_load_project(self):
        json_path = self.view.ask_load_project_file()
        if not json_path:
            return
        
        project_data = self._project_service.load_project(json_path)
        if not project_data:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self.view, "Error", "Failed to load project file.")
            return
        
        self._directory_path = project_data.parent_folder
        self.view.set_directory(self._directory_path)
        self._measurement_type = project_data.measurement_type
        self.view.set_measurement_type(self._measurement_type)
        
        grouped = []
        file_groups: Dict[tuple, List] = defaultdict(list)
        for fi in project_data.files:
            key = (fi.date, fi.time)
            file_groups[key].append(fi)
        
        for (date_str, time_str), file_infos in sorted(file_groups.items()):
            files = []
            file_paths = []
            channels = set()
            for fi in file_infos:
                fname = Path(fi.relative_path).name
                files.append(fname)
                file_paths.append(
                    os.path.join(self._directory_path, fi.relative_path)
                )
                if fi.channel:
                    channels.add(fi.channel)
            
            first = file_infos[0]
            grouped.append({
                'date': date_str,
                'time': time_str,
                'count': len(files),
                'channel': ', '.join(sorted(channels)),
                'sampling_rate': first.sampling_rate,
                'sensitivity': first.sensitivity,
                'files': files,
                'file_paths': file_paths,
                'is_anomaly': first.is_anomaly,
                'anomaly_type': 'warning' if first.is_anomaly else '',
            })
        
        self._grouped_data = grouped
        self._all_files = []
        self._all_file_paths = []
        for g in grouped:
            self._all_files.extend(g['files'])
            self._all_file_paths.extend(g.get('file_paths', []))
        
        self.view.set_files(grouped)
        
        project_dir = Path(json_path).parent
        self._project_service.create_project_folders(str(project_dir))
        
        self._event_bus.project_loaded.emit(json_path)
        logger.info(f"Project loaded: {json_path}")
    
    def _on_quarantine(self, rows: List[int]):
        quarantine_dir = Path(self._directory_path) / 'quarantine'
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        moved_count = 0
        for group_idx in sorted(rows, reverse=True):
            model = self.view.get_model()
            row_data = model.get_row_data(group_idx)
            if not row_data:
                continue
            
            for fp in row_data.get('file_paths', []):
                src = Path(fp)
                if src.exists():
                    dest = quarantine_dir / src.name
                    shutil.move(str(src), str(dest))
                    moved_count += 1
        
        if moved_count > 0:
            self.view.get_model().remove_rows(rows)
            logger.info(f"Quarantined {moved_count} files to {quarantine_dir}")
    
    def _on_delete(self, rows: List[int]):
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self.view,
            "Confirm Delete",
            f"Are you sure you want to delete files in {len(rows)} group(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        
        deleted_count = 0
        for group_idx in sorted(rows, reverse=True):
            model = self.view.get_model()
            row_data = model.get_row_data(group_idx)
            if not row_data:
                continue
            
            for fp in row_data.get('file_paths', []):
                src = Path(fp)
                if src.exists():
                    src.unlink()
                    deleted_count += 1
        
        if deleted_count > 0:
            self.view.get_model().remove_rows(rows)
            logger.info(f"Deleted {deleted_count} files")
    
    def get_directory(self) -> str:
        return self._directory_path
    
    def get_all_files(self) -> List[str]:
        return self._all_files.copy()
    
    def get_selected_files(self) -> List[str]:
        return self.view.get_selected_files()
    
    def get_selected_file_paths(self) -> List[str]:
        selected = self.view.get_selected_files()
        return [os.path.join(self._directory_path, f) for f in selected]
    
    def load_file(self, filename: str) -> Optional[FileParser]:
        filepath = os.path.join(self._directory_path, filename)
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return None
        try:
            parser = FileParser(filepath)
            if parser.is_valid():
                return parser
            logger.warning(f"Invalid file: {filename}")
        except Exception as e:
            logger.error(f"Failed to parse file {filename}: {e}")
        return None
    
    def set_directory(self, path: str):
        self._directory_path = path
        self.view.set_directory(path)
    
    def _on_switch_to_spectrum(self):
        self._event_bus.tab_changed.emit('spectrum')


if __name__ == "__main__":
    print("DataQueryPresenter Test")
    print("=" * 50)
    
    import inspect
    sig = inspect.signature(DataQueryPresenter.__init__)
    params = list(sig.parameters.keys())
    print(f"Constructor params: {params}")
    
    assert 'view' in params, "Missing 'view' parameter"
    print("DI signature OK")
    
    from unittest.mock import MagicMock
    mock_view = MagicMock(spec=DataQueryTabView)
    mock_view.directory_selected = MagicMock()
    mock_view.files_loaded = MagicMock()
    mock_view.files_chosen = MagicMock()
    
    presenter = DataQueryPresenter(view=mock_view)
    assert presenter.get_directory() == "", "Initial directory should be empty"
    print("Initialization OK")
    
    print("\nDataQueryPresenter tests passed!")
