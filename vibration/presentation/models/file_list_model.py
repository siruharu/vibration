"""
File list table model.

QAbstractTableModel for displaying file metadata in table view.
Extracted from cn_3F_trend_optimized.py Tab 1 for modular architecture.
"""
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex


class FileListModel(QAbstractTableModel):
    """
    Model for file list table.
    
    Displays grouped file data with date, time, count, and filenames.
    Supports checkbox selection for multi-file operations.
    """
    
    def __init__(self, parent=None):
        """Initialize file list model."""
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._headers = ['Date', 'Time', 'Count', 'Files', 'Select']
        self._checked_rows: set = set()
    
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows."""
        if parent.isValid():
            return 0
        return len(self._data)
    
    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns."""
        if parent.isValid():
            return 0
        return len(self._headers)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Return data for given index and role."""
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        
        if row >= len(self._data):
            return None
        
        if role == Qt.DisplayRole:
            if col == 0:
                return self._data[row].get('date', '')
            elif col == 1:
                return self._data[row].get('time', '')
            elif col == 2:
                return str(self._data[row].get('count', 0))
            elif col == 3:
                files = self._data[row].get('files', [])
                return ', '.join(files) if isinstance(files, list) else str(files)
            elif col == 4:
                return None  # Checkbox handled by CheckStateRole
        
        elif role == Qt.CheckStateRole and col == 4:
            return Qt.Checked if row in self._checked_rows else Qt.Unchecked
        
        return None
    
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """Set data for checkbox column."""
        if not index.isValid():
            return False
        
        if role == Qt.CheckStateRole and index.column() == 4:
            row = index.row()
            if value == Qt.Checked:
                self._checked_rows.add(row)
            else:
                self._checked_rows.discard(row)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True
        return False
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Return item flags (enable checkbox for Select column)."""
        if not index.isValid():
            return Qt.NoItemFlags
        
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 4:
            flags |= Qt.ItemIsUserCheckable
        return flags
    
    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole) -> Any:
        """Return header data."""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return None
    
    def set_files(self, files: List[Dict[str, Any]]) -> None:
        """
        Update file list.
        
        Args:
            files: List of dicts with keys: date, time, count, files
        """
        self.beginResetModel()
        self._data = files
        self._checked_rows.clear()
        self.endResetModel()
    
    def get_files(self) -> List[Dict[str, Any]]:
        """Get current file list."""
        return self._data.copy()
    
    def get_checked_rows(self) -> List[int]:
        """Get list of checked row indices."""
        return sorted(self._checked_rows)
    
    def get_checked_files(self) -> List[str]:
        """Get list of filenames from checked rows."""
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
        """Check or uncheck all rows."""
        self.beginResetModel()
        if checked:
            self._checked_rows = set(range(len(self._data)))
        else:
            self._checked_rows.clear()
        self.endResetModel()
    
    def toggle_all(self) -> None:
        """Toggle all checkboxes."""
        all_checked = len(self._checked_rows) == len(self._data)
        self.set_all_checked(not all_checked)


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
    assert model.columnCount() == 5, "Column count should be 5"
    
    idx = model.index(0, 0)
    assert model.data(idx) == '2025-04-10', "Date should match"
    
    check_idx = model.index(0, 4)
    model.setData(check_idx, Qt.Checked, Qt.CheckStateRole)
    assert 0 in model._checked_rows, "Row 0 should be checked"
    
    checked_files = model.get_checked_files()
    assert checked_files == ['a.txt', 'b.txt', 'c.txt'], f"Unexpected: {checked_files}"
    
    print("All tests passed!")
