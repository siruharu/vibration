"""
Data query presenter (MVP pattern).

Coordinates DataQueryTabView and file_parser for file loading workflow.
Uses constructor injection for dependencies.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from collections import defaultdict
import sys

_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from file_parser import FileParser
from vibration.presentation.views.tabs.data_query_tab import DataQueryTabView

logger = logging.getLogger(__name__)


class DataQueryPresenter:
    """
    Presenter for data query tab (MVP pattern).
    
    Coordinates view and file_parser.FileParser for directory
    selection and file loading workflow.
    """
    
    def __init__(self, view: DataQueryTabView):
        self.view = view
        self._directory_path: str = ""
        self._all_files: List[str] = []
        self._grouped_data: List[Dict[str, Any]] = []
        self._connect_signals()
        logger.debug("DataQueryPresenter initialized")
    
    def _connect_signals(self):
        self.view.directory_selected.connect(self._on_directory_selected)
        self.view.files_loaded.connect(self._on_load_requested)
        self.view.files_chosen.connect(self._on_files_chosen)
    
    def _on_directory_selected(self, directory: str):
        self._directory_path = directory
        logger.info(f"Directory selected: {directory}")
    
    def _on_load_requested(self, _):
        if not self._directory_path:
            logger.warning("No directory selected")
            return
        
        self._load_files_from_directory()
    
    def _load_files_from_directory(self):
        file_dict = defaultdict(list)
        
        try:
            files = os.listdir(self._directory_path)
            self._all_files = [f for f in files if f.endswith(".txt")]
        except OSError as e:
            logger.error(f"Failed to list directory: {e}")
            self._all_files = []
            return
        
        for filename in self._all_files:
            parts = filename.split("_")
            if len(parts) >= 2:
                date_part = parts[0]
                time_part = parts[1]
                time_parts = time_part.split("-")
                if len(time_parts) == 3:
                    formatted_time = f"{time_parts[0]}:{time_parts[1]}:{time_parts[2]}"
                    key = (date_part, formatted_time)
                    file_dict[key].append(filename)
        
        grouped = []
        for (date, time), files in sorted(file_dict.items()):
            grouped.append({
                'date': date,
                'time': time,
                'count': len(files),
                'files': files
            })
        
        self._grouped_data = grouped
        self.view.set_files(grouped)
        logger.info(f"Loaded {len(grouped)} file groups from {len(self._all_files)} files")
    
    def _on_files_chosen(self, files: List[str]):
        logger.info(f"Files chosen: {len(files)} files")
    
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
