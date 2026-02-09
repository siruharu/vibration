"""
파일 목록 테이블 모델.

테이블 뷰에 파일 메타데이터를 표시하는 QAbstractTableModel.
cn_3F_trend_optimized.py Tab 1에서 모듈화 아키텍처를 위해 추출.
"""
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex
from PyQt5.QtGui import QBrush, QColor

COL_DATE = 0
COL_TIME = 1
COL_COUNT = 2
COL_CH = 3
COL_FS = 4
COL_SENSITIVITY = 5
COL_FILES = 6
COL_STATUS = 7
COL_SELECT = 8

ANOMALY_RED = QColor(255, 180, 180)
ANOMALY_YELLOW = QColor(255, 255, 180)


class FileListModel(QAbstractTableModel):
    """
    파일 목록 테이블 모델.
    
    날짜, 시간, 개수, 파일명으로 그룹화된 파일 데이터를 표시합니다.
    다중 파일 작업을 위한 체크박스 선택을 지원합니다.
    """
    
    def __init__(self, parent=None):
        """파일 목록 모델을 초기화합니다."""
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._headers = ['Date', 'Time', 'Count', 'Ch', 'Fs(Hz)', 'Sensitivity', 'Files', 'Status', 'Select']
        self._checked_rows: set = set()
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """행 수를 반환합니다."""
        if parent.isValid():
            return 0
        return len(self._data)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """열 수를 반환합니다."""
        if parent.isValid():
            return 0
        return len(self._headers)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """주어진 인덱스와 역할에 대한 데이터를 반환합니다."""
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        
        if row >= len(self._data):
            return None
        
        row_data = self._data[row]
        
        if role == Qt.DisplayRole:
            if col == COL_DATE:
                return row_data.get('date', '')
            elif col == COL_TIME:
                return row_data.get('time', '')
            elif col == COL_COUNT:
                return str(row_data.get('count', 0))
            elif col == COL_CH:
                return row_data.get('channel', '')
            elif col == COL_FS:
                sr = row_data.get('sampling_rate', 0.0)
                return f"{sr:.0f}" if sr else ''
            elif col == COL_SENSITIVITY:
                return row_data.get('sensitivity', '')
            elif col == COL_FILES:
                files = row_data.get('files', [])
                return ', '.join(files) if isinstance(files, list) else str(files)
            elif col == COL_STATUS:
                if row_data.get('is_anomaly', False):
                    return 'Anomaly'
                return 'OK'
            elif col == COL_SELECT:
                return None
        
        elif role == Qt.CheckStateRole and col == COL_SELECT:
            return Qt.Checked if row in self._checked_rows else Qt.Unchecked
        
        elif role == Qt.BackgroundRole:
            if row_data.get('is_anomaly', False):
                anomaly_type = row_data.get('anomaly_type', 'warning')
                if anomaly_type == 'error':
                    return QBrush(ANOMALY_RED)
                return QBrush(ANOMALY_YELLOW)
        
        return None
    
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """체크박스 열의 데이터를 설정합니다."""
        if not index.isValid():
            return False
        
        if role == Qt.CheckStateRole and index.column() == COL_SELECT:
            row = index.row()
            if value == Qt.Checked:
                self._checked_rows.add(row)
            else:
                self._checked_rows.discard(row)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True
        return False
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """항목 플래그를 반환합니다 (Select 열에 체크박스 활성화)."""
        if not index.isValid():
            return Qt.NoItemFlags
        
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == COL_SELECT:
            flags |= Qt.ItemIsUserCheckable
        return flags
    
    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole) -> Any:
        """헤더 데이터를 반환합니다."""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return None
    
    def set_files(self, files: List[Dict[str, Any]]) -> None:
        """
        파일 목록을 업데이트합니다.
        
        인자:
            files: date, time, count, files 키를 포함하는 딕셔너리 목록
        """
        self.beginResetModel()
        self._data = files
        self._checked_rows.clear()
        self.endResetModel()
    
    def get_files(self) -> List[Dict[str, Any]]:
        """현재 파일 목록을 반환합니다."""
        return self._data.copy()
    
    def get_row_data(self, row: int) -> Optional[Dict[str, Any]]:
        """특정 행의 데이터를 반환합니다."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None
    
    def get_checked_rows(self) -> List[int]:
        """체크된 행 인덱스 목록을 반환합니다."""
        return sorted(self._checked_rows)
    
    def get_checked_files(self) -> List[str]:
        """체크된 행의 파일명 목록을 반환합니다."""
        result = []
        for row in sorted(self._checked_rows):
            if row < len(self._data):
                files = self._data[row].get('files', [])
                if isinstance(files, list):
                    result.extend(files)
                else:
                    result.append(str(files))
        return result
    
    def set_all_checked(self, checked: bool) -> None:
        """모든 행을 체크하거나 해제합니다."""
        self.beginResetModel()
        if checked:
            self._checked_rows = set(range(len(self._data)))
        else:
            self._checked_rows.clear()
        self.endResetModel()
    
    def toggle_all(self) -> None:
        """모든 체크박스를 토글합니다."""
        all_checked = len(self._checked_rows) == len(self._data)
        self.set_all_checked(not all_checked)
    
    def remove_rows(self, rows: List[int]) -> None:
        """지정된 행들을 제거합니다."""
        for row in sorted(rows, reverse=True):
            if 0 <= row < len(self._data):
                self.beginRemoveRows(QModelIndex(), row, row)
                self._data.pop(row)
                self._checked_rows.discard(row)
                updated = set()
                for r in self._checked_rows:
                    if r > row:
                        updated.add(r - 1)
                    elif r < row:
                        updated.add(r)
                self._checked_rows = updated
                self.endRemoveRows()


if __name__ == "__main__":
    print("FileListModel Test")
    print("=" * 50)
    
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    model = FileListModel()
    
    test_data = [
        {'date': '2025-04-10', 'time': '13:36:13', 'count': 3, 'files': ['a.txt', 'b.txt', 'c.txt']},
        {'date': '2025-04-10', 'time': '13:37:14', 'count': 2, 'files': ['d.txt', 'e.txt']},
    ]
    model.set_files(test_data)
    
    assert model.rowCount() == 2, "Row count should be 2"
    assert model.columnCount() == 9, "Column count should be 9"
    
    idx = model.index(0, 0)
    assert model.data(idx) == '2025-04-10', "Date should match"
    
    check_idx = model.index(0, COL_SELECT)
    model.setData(check_idx, Qt.Checked, Qt.CheckStateRole)
    assert 0 in model._checked_rows, "Row 0 should be checked"
    
    checked_files = model.get_checked_files()
    assert checked_files == ['a.txt', 'b.txt', 'c.txt'], f"Unexpected: {checked_files}"
    
    print("All tests passed!")
