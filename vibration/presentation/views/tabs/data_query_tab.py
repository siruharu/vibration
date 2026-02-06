"""
Data query tab view.

Tab 1 for directory selection and file list display.
Extracted from cn_3F_trend_optimized.py for modular architecture.
"""
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTextBrowser, QTableView, QHeaderView, QFileDialog, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt

from vibration.presentation.models.file_list_model import FileListModel


class DataQueryTabView(QWidget):
    """
    View for data query tab (Tab 1).
    
    Provides directory selection, file list display with checkboxes,
    and file selection for other tabs. Emits signals for presenter.
    """
    
    directory_selected = pyqtSignal(str)
    files_loaded = pyqtSignal(list)
    files_chosen = pyqtSignal(list)
    sensitivity_changed = pyqtSignal(float)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._model = FileListModel(self)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        top_layout = QHBoxLayout()
        
        self.select_btn = QPushButton("Select")
        self.load_btn = QPushButton("Load Data")
        top_layout.addWidget(self.select_btn)
        top_layout.addWidget(self.load_btn)
        
        self.directory_display = QTextBrowser()
        self.directory_display.setFixedHeight(50)
        top_layout.addWidget(self.directory_display, stretch=1)
        
        self.choose_btn = QPushButton("Choose")
        top_layout.addWidget(self.choose_btn)
        
        layout.addLayout(top_layout)
        
        self.file_table = QTableView()
        self.file_table.setModel(self._model)
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.file_table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        layout.addWidget(self.file_table, stretch=1)
    
    def _connect_signals(self):
        self.select_btn.clicked.connect(self._on_select_clicked)
        self.load_btn.clicked.connect(self._on_load_clicked)
        self.choose_btn.clicked.connect(self._on_choose_clicked)
    
    def _on_select_clicked(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Directory", "", QFileDialog.ShowDirsOnly
        )
        if dir_path:
            self.directory_display.setText(dir_path)
            self.directory_selected.emit(dir_path)
    
    def _on_load_clicked(self):
        self.files_loaded.emit([])
    
    def _on_choose_clicked(self):
        selected = self._model.get_checked_files()
        if selected:
            self.files_chosen.emit(selected)
        else:
            QMessageBox.warning(self, "No Files Selected", "No files have been selected.")
    
    def _on_header_clicked(self, logical_index: int):
        if logical_index == 4:
            self._model.toggle_all()
    
    def get_directory(self) -> str:
        return self.directory_display.toPlainText()
    
    def set_directory(self, path: str):
        self.directory_display.setText(path)
    
    def set_files(self, files: List[Dict[str, Any]]):
        self._model.set_files(files)
    
    def get_selected_files(self) -> List[str]:
        return self._model.get_checked_files()
    
    def get_model(self) -> FileListModel:
        return self._model
    
    def clear(self):
        self._model.set_files([])
        self.directory_display.clear()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    view = DataQueryTabView()
    view.resize(800, 600)
    view.show()
    
    test_data = [
        {'date': '2025-04-10', 'time': '13:36:13', 'count': 3, 'files': ['a.txt', 'b.txt', 'c.txt']},
        {'date': '2025-04-10', 'time': '13:37:14', 'count': 2, 'files': ['d.txt', 'e.txt']},
    ]
    view.set_files(test_data)
    
    print("DataQueryTabView test window displayed")
    sys.exit(app.exec_())
