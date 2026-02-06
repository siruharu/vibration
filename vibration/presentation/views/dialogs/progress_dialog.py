"""
Progress dialog for long-running operations.

Extracted from cn_3F_trend_optimized.py for modular architecture.
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt5.QtCore import Qt


class ProgressDialog(QDialog):
    """
    Modal dialog displaying progress of long-running operations.
    
    Shows a progress bar with percentage completion and status label.
    Updates are processed immediately via QApplication.processEvents().
    
    Attributes:
        label: QLabel displaying current progress percentage
        progress_bar: QProgressBar showing completion status
        layout: QVBoxLayout containing dialog widgets
    """
    
    def __init__(self, total_tasks, parent=None):
        """
        Initialize progress dialog.
        
        Args:
            total_tasks: Total number of tasks for progress calculation
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.setWindowTitle("진행 상황")
        self.setFixedSize(300, 100)

        self.layout = QVBoxLayout()
        self.label = QLabel("파일 처리 중...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, total_tasks)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)  # ✅ 퍼센트 텍스트 표시

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.progress_bar)
        self.setLayout(self.layout)

    def update_progress(self, value):
        """
        Update progress bar and label.
        
        Args:
            value: Current progress value (0 to total_tasks)
        """
        self.progress_bar.setValue(value)
        percent = int((value / self.progress_bar.maximum()) * 100)
        self.label.setText(f"{percent}% 완료 중...")
        QApplication.processEvents()


if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    dialog = ProgressDialog(total_tasks=100)
    dialog.show()
    
    # Simulate progress
    for i in range(101):
        dialog.update_progress(i)
        app.processEvents()
    
    print("ProgressDialog test: OK")
