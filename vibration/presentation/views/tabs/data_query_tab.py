"""
데이터 조회 탭 뷰.

디렉토리 선택 및 파일 목록 표시를 위한 Tab 1.
cn_3F_trend_optimized.py에서 모듈화 아키텍처를 위해 추출.
"""
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextBrowser, QTableView, QHeaderView, QFileDialog, QMessageBox,
    QLabel, QDateEdit, QMenu, QAction, QInputDialog
)
from PyQt5.QtCore import pyqtSignal, Qt, QDate
from PyQt5.QtGui import QCursor

from vibration.presentation.models.file_list_model import FileListModel, COL_FILES, COL_SELECT
from vibration.presentation.views.dialogs.responsive_layout_utils import WidgetSizes, APP_FONT_FAMILY


class DataQueryTabView(QWidget):
    """데이터 조회 탭 뷰 - 파일 선택 및 로딩."""
    
    directory_selected = pyqtSignal(str)
    files_loaded = pyqtSignal(str)
    files_chosen = pyqtSignal(list)
    switch_to_spectrum_requested = pyqtSignal()
    sensitivity_changed = pyqtSignal(float)
    save_project_requested = pyqtSignal()
    load_project_requested = pyqtSignal()
    quarantine_requested = pyqtSignal(list)
    delete_requested = pyqtSignal(list)
    
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
        self.directory_display.setFixedHeight(WidgetSizes.dir_display_height())
        top_layout.addWidget(self.directory_display, stretch=1)
        
        self.choose_btn = QPushButton("Choose")
        top_layout.addWidget(self.choose_btn)
        
        layout.addLayout(top_layout)
        
        date_style = (
            f"QDateEdit {{ background-color: lightgray; font-family: '{APP_FONT_FAMILY}'; "
            f"font-size: 10pt; padding: 2px 5px; }}"
        )
        
        filter_layout = QHBoxLayout()
        
        from_label = QLabel("From:")
        from_label.setStyleSheet(f"font-family: '{APP_FONT_FAMILY}'; font-size: 10pt;")
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate(2020, 1, 1))
        self.date_from.setStyleSheet(date_style)
        
        to_label = QLabel("To:")
        to_label.setStyleSheet(f"font-family: '{APP_FONT_FAMILY}'; font-size: 10pt;")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setStyleSheet(date_style)
        
        filter_layout.addWidget(from_label)
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(to_label)
        filter_layout.addWidget(self.date_to)
        
        filter_layout.addSpacing(20)
        
        self.measurement_type_label = QLabel("Type: --")
        self.measurement_type_label.setStyleSheet(
            f"font-family: '{APP_FONT_FAMILY}'; font-size: 10pt; font-weight: bold; "
            f"padding: 2px 8px; background-color: lightgray; border-radius: 3px;"
        )
        filter_layout.addWidget(self.measurement_type_label)
        
        filter_layout.addStretch(1)
        
        self.save_project_btn = QPushButton("Save Project")
        self.load_project_btn = QPushButton("Load Project")
        filter_layout.addWidget(self.save_project_btn)
        filter_layout.addWidget(self.load_project_btn)
        
        layout.addLayout(filter_layout)
        
        self.file_table = QTableView()
        self.file_table.setModel(self._model)
        self.file_table.horizontalHeader().setSectionResizeMode(COL_FILES, QHeaderView.Stretch)
        self.file_table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.file_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_table.customContextMenuRequested.connect(self._on_context_menu)
        self.file_table.setSelectionBehavior(QTableView.SelectRows)
        layout.addWidget(self.file_table, stretch=1)
    
    def _connect_signals(self):
        self.select_btn.clicked.connect(self._on_select_clicked)
        self.load_btn.clicked.connect(self._on_load_clicked)
        self.choose_btn.clicked.connect(self._on_choose_clicked)
        self.save_project_btn.clicked.connect(self.save_project_requested.emit)
        self.load_project_btn.clicked.connect(self.load_project_requested.emit)
    
    def _on_select_clicked(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Parent Folder", "", QFileDialog.ShowDirsOnly
        )
        if dir_path:
            self.directory_display.setText(dir_path)
            self.directory_selected.emit(dir_path)
    
    def _on_load_clicked(self):
        self.files_loaded.emit("")
    
    def _on_choose_clicked(self):
        selected = self._model.get_checked_files()
        if selected:
            self.files_chosen.emit(selected)
            self.switch_to_spectrum_requested.emit()
        else:
            QMessageBox.warning(self, "No Files Selected", "No files have been selected.")
    
    def _on_header_clicked(self, logical_index: int):
        if logical_index == COL_SELECT:
            self._model.toggle_all()
    
    def _on_context_menu(self, pos):
        indexes = self.file_table.selectionModel().selectedRows()
        if not indexes:
            return
        
        rows = [idx.row() for idx in indexes]
        
        menu = QMenu(self)
        quarantine_action = QAction("Move to Quarantine", self)
        delete_action = QAction("Delete File(s)", self)
        
        quarantine_action.triggered.connect(lambda: self.quarantine_requested.emit(rows))
        delete_action.triggered.connect(lambda: self.delete_requested.emit(rows))
        
        menu.addAction(quarantine_action)
        menu.addAction(delete_action)
        menu.exec_(QCursor.pos())
    
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
    
    def get_date_range(self):
        from_date = self.date_from.date().toPyDate()
        to_date = self.date_to.date().toPyDate()
        return from_date, to_date
    
    def set_measurement_type(self, mtype: str):
        self.measurement_type_label.setText(f"Type: {mtype}")
    
    def ask_project_description(self) -> Optional[str]:
        text, ok = QInputDialog.getText(
            self, "Project Description", "Enter project description:"
        )
        if ok:
            return text
        return None
    
    def ask_save_location(self) -> Optional[str]:
        path = QFileDialog.getExistingDirectory(
            self, "Select Save Location", "", QFileDialog.ShowDirsOnly
        )
        return path if path else None
    
    def ask_load_project_file(self) -> Optional[str]:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Project", "", "Project Files (*.json)"
        )
        return path if path else None
    
    def clear(self):
        self._model.set_files([])
        self.directory_display.clear()
        self.measurement_type_label.setText("Type: --")


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
