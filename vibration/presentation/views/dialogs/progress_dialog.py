"""
장시간 작업을 위한 진행률 다이얼로그.

cn_3F_trend_optimized.py에서 모듈화 아키텍처를 위해 추출.
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt5.QtCore import Qt


class ProgressDialog(QDialog):
    """
    장시간 작업의 진행률을 표시하는 모달 다이얼로그.
    
    백분율 완료 상태와 상태 라벨이 포함된 진행률 바를 표시합니다.
    QApplication.processEvents()를 통해 즉시 업데이트를 처리합니다.
    
    속성:
        label: 현재 진행률 백분율을 표시하는 QLabel
        progress_bar: 완료 상태를 표시하는 QProgressBar
        layout: 다이얼로그 위젯을 포함하는 QVBoxLayout
    """
    
    def __init__(self, total_tasks, parent=None):
        """
        진행률 다이얼로그를 초기화합니다.
        
        인자:
            total_tasks: 진행률 계산을 위한 총 작업 수
            parent: 부모 위젯 (선택사항)
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
        진행률 바와 라벨을 업데이트합니다.
        
        인자:
            value: 현재 진행률 값 (0 ~ total_tasks)
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
