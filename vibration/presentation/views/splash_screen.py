"""CNAVE 애플리케이션용 모던 스플래시 스크린."""
from typing import Optional
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from vibration.presentation.views.dialogs.responsive_layout_utils import APP_FONT_FAMILY
from vibration import __version__


class ModernSplashScreen(QtWidgets.QWidget):
    """CNAVE 애플리케이션 스플래시 스크린 (진행률 추적 포함)."""

    def __init__(self, version: Optional[str] = None, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        if version is None:
            version = f"v{__version__}"
        self.version = version

        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 450)

        screen = QtWidgets.QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        self._setup_ui()

        self.close_timer = QtCore.QTimer()
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close)
        self.close_timer.start(10000)

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        frame = QtWidgets.QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #0078d7;
                border-radius: 15px;
            }
        """)

        frame_layout = QtWidgets.QVBoxLayout(frame)
        frame_layout.setContentsMargins(40, 40, 40, 40)
        frame_layout.setSpacing(20)

        logo_label = QtWidgets.QLabel()
        try:
            from vibration import get_resource_path
            icon_path = get_resource_path("icn.ico")
            pixmap = QtGui.QPixmap(str(icon_path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(128, 128, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                logo_label.setPixmap(pixmap)
            else:
                raise Exception("Icon load failed")
        except Exception:
            logo_label.setText("🚀")
            logo_label.setStyleSheet("font-size: 64px;")
        logo_label.setAlignment(QtCore.Qt.AlignCenter)
        frame_layout.addWidget(logo_label)

        company_label = QtWidgets.QLabel("CNAVE")
        company_label.setStyleSheet(f"""
            QLabel {{
                font-size: 32px;
                font-weight: bold;
                color: #003366;
                font-family: '{APP_FONT_FAMILY}';
            }}
        """)
        company_label.setAlignment(QtCore.Qt.AlignCenter)
        frame_layout.addWidget(company_label)

        app_label = QtWidgets.QLabel("CNXMW Post Processor")
        app_label.setStyleSheet(f"""
            QLabel {{
                font-size: 18px;
                color: #666666;
                font-family: '{APP_FONT_FAMILY}';
            }}
        """)
        app_label.setAlignment(QtCore.Qt.AlignCenter)
        frame_layout.addWidget(app_label)

        version_label = QtWidgets.QLabel(self.version)
        version_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                color: #999999;
                font-family: '{APP_FONT_FAMILY}';
            }}
        """)
        version_label.setAlignment(QtCore.Qt.AlignCenter)
        frame_layout.addWidget(version_label)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #cccccc;
                border-radius: 8px;
                text-align: center;
                background-color: #f0f0f0;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 6px;
            }
        """)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        frame_layout.addWidget(self.progress_bar)

        self.status_label = QtWidgets.QLabel("Starting...")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: #666666;
                font-family: '{APP_FONT_FAMILY}';
            }}
        """)
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        frame_layout.addWidget(self.status_label)

        frame_layout.addStretch()

        copyright_label = QtWidgets.QLabel("© 2024-2026 CNAVE. All rights reserved.")
        copyright_label.setStyleSheet(f"""
            QLabel {{
                font-size: 10px;
                color: #999999;
                font-family: '{APP_FONT_FAMILY}';
            }}
        """)
        copyright_label.setAlignment(QtCore.Qt.AlignCenter)
        frame_layout.addWidget(copyright_label)

        layout.addWidget(frame)

        self._start_progress_animation()

    def _start_progress_animation(self):
        self.progress_value = 0
        self.progress_timer = QtCore.QTimer()
        self.progress_timer.timeout.connect(self._update_progress)
        self.progress_timer.start(30)

    def _update_progress(self):
        self.progress_value += 1
        self.progress_bar.setValue(self.progress_value)

        if self.progress_value < 30:
            self.status_label.setText("Initializing...")
        elif self.progress_value < 60:
            self.status_label.setText("Loading modules...")
        elif self.progress_value < 90:
            self.status_label.setText("Setting up UI...")
        else:
            self.status_label.setText("Almost ready...")

        if self.progress_value >= 100:
            self.progress_timer.stop()

    def set_progress(self, value: int, message: Optional[str] = None):
        """진행률 바 값과 선택적 상태 메시지를 설정합니다."""
        self.progress_bar.setValue(value)
        if message:
            self.status_label.setText(message)
        QtWidgets.QApplication.processEvents()
