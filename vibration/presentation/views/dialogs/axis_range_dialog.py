"""
Axis range configuration dialog.

Allows users to set custom axis ranges for plots.
Extracted from cn_3F_trend_optimized.py for modular architecture.
"""

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QCheckBox, QLineEdit,
    QDialogButtonBox, QMessageBox
)


class AxisRangeDialog(QDialog):
    """Dialog for configuring axis range settings.
    
    Allows users to set custom minimum and maximum values for plot axes,
    or enable auto-ranging mode. Validates input and provides user feedback.
    
    Attributes:
        auto_checkbox (QCheckBox): Checkbox to enable/disable auto-ranging
        min_input (QLineEdit): Input field for minimum axis value
        max_input (QLineEdit): Input field for maximum axis value
    """

    def __init__(self, axis_name, current_min, current_max, parent=None):
        """Initialize the axis range dialog.
        
        Args:
            axis_name (str): Name of the axis (e.g., 'X', 'Y', 'Frequency')
            current_min (float): Current minimum value
            current_max (float): Current maximum value
            parent (QWidget, optional): Parent widget. Defaults to None.
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
        """Toggle input field enabled state based on auto-range checkbox.
        
        Args:
            state (int): Checkbox state (unused, uses isChecked() instead)
        """
        enabled = not self.auto_checkbox.isChecked()
        self.min_input.setEnabled(enabled)
        self.max_input.setEnabled(enabled)

    def get_range(self):
        """Get the configured axis range.
        
        Returns:
            tuple: (min_value, max_value) as floats, or (None, None) if auto-range
                   is enabled or input validation fails.
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
