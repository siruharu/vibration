"""
축 범위 설정 다이얼로그.

사용자가 플롯의 사용자 정의 축 범위를 설정할 수 있습니다.
cn_3F_trend_optimized.py에서 모듈화 아키텍처를 위해 추출.
"""

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QCheckBox, QLineEdit,
    QDialogButtonBox, QMessageBox
)


class AxisRangeDialog(QDialog):
    """축 범위 설정 다이얼로그.
    
    사용자가 플롯 축의 사용자 정의 최소/최대 값을 설정하거나
    자동 범위 모드를 활성화할 수 있습니다. 입력값을 검증하고 피드백을 제공합니다.
    
    속성:
        auto_checkbox (QCheckBox): 자동 범위 활성화/비활성화 체크박스
        min_input (QLineEdit): 축 최소값 입력 필드
        max_input (QLineEdit): 축 최대값 입력 필드
    """

    def __init__(self, axis_name, current_min, current_max, parent=None):
        """축 범위 다이얼로그를 초기화합니다.
        
        인자:
            axis_name (str): 축 이름 (예: 'X', 'Y', 'Frequency')
            current_min (float): 현재 최소값
            current_max (float): 현재 최대값
            parent (QWidget, optional): 부모 위젯. 기본값 None.
        """
        super().__init__(parent)
        self.setWindowTitle(f"Set {axis_name} Axis Range")
        self.setModal(True)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        # Auto Range checkbox
        self.auto_checkbox = QCheckBox("Auto Range")
        self.auto_checkbox.setChecked(False)
        self.auto_checkbox.stateChanged.connect(self.toggle_inputs)
        layout.addWidget(self.auto_checkbox)

        # Min/Max input fields
        form_layout = QFormLayout()

        self.min_input = QLineEdit(f"{current_min:.2f}")
        self.min_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: #333333;
                border: 1px solid #cccccc;
                padding: 5px;
            }
        """)
        form_layout.addRow(f"{axis_name} min:", self.min_input)

        self.max_input = QLineEdit(f"{current_max:.2f}")
        self.max_input.setStyleSheet(self.min_input.styleSheet())
        form_layout.addRow(f"{axis_name} max:", self.max_input)

        layout.addLayout(form_layout)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def toggle_inputs(self, state):
        """자동 범위 체크박스에 따라 입력 필드 활성화 상태를 전환합니다.
        
        인자:
            state (int): 체크박스 상태 (미사용, isChecked() 사용)
        """
        enabled = not self.auto_checkbox.isChecked()
        self.min_input.setEnabled(enabled)
        self.max_input.setEnabled(enabled)

    def get_range(self):
        """설정된 축 범위를 반환합니다.
        
        반환:
            tuple: (min_value, max_value) float 튜플, 자동 범위 활성화 시
                   또는 입력값 검증 실패 시 (None, None).
        """
        if self.auto_checkbox.isChecked():
            return None, None

        try:
            min_val = float(self.min_input.text())
            max_val = float(self.max_input.text())

            if min_val >= max_val:
                QMessageBox.warning(
                    self, "경고", "min은 max보다 작아야 합니다"
                )
                return None, None

            return min_val, max_val
        except ValueError:
            QMessageBox.warning(self, "경고", "올바른 숫자를 입력하세요")
            return None, None


if __name__ == "__main__":
    import sys
    
    app = QtWidgets.QApplication(sys.argv)
    dialog = AxisRangeDialog("Frequency", 0.0, 100.0)
    dialog.show()
    print("AxisRangeDialog test: OK")
    sys.exit(app.exec_())
