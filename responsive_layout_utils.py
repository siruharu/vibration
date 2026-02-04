"""
반응형 레이아웃 유틸리티
- DPI 스케일링
- 동적 폰트 크기
- 그래프 범례 관리
"""

from PyQt5 import QtWidgets, QtCore
import matplotlib.pyplot as plt


class ResponsiveLayoutMixin:
    """반응형 레이아웃을 위한 Mixin 클래스"""

    def get_dpi_scale_factor(self):
        """현재 DPI 스케일 팩터 계산"""
        try:
            screen = QtWidgets.QApplication.primaryScreen()
            dpi = screen.logicalDotsPerInch()
            base_dpi = 96.0  # Windows 기본 DPI
            return dpi / base_dpi
        except:
            return 1.0

    def scale_size(self, base_size):
        """크기를 DPI에 맞게 스케일링"""
        factor = self.get_dpi_scale_factor()
        if isinstance(base_size, tuple):
            return tuple(int(s * factor) for s in base_size)
        return int(base_size * factor)

    def get_dynamic_font_size(self, base_size=10):
        """창 크기에 따른 동적 폰트 크기"""
        try:
            window_width = self.width()

            if window_width < 1400:
                return max(7, base_size - 2)
            elif window_width < 1700:
                return max(8, base_size - 1)
            else:
                return base_size
        except:
            return base_size

    def setup_figure_with_legend(self, figure, ax, rect=[0, 0, 0.85, 1]):
        """Figure에 범례 공간 확보"""
        figure.set_tight_layout({'rect': rect})
        return figure, ax

    def update_legend_position(self, ax, max_items=15):
        """범례 위치 업데이트 (그래프 외부)"""
        handles, labels = ax.get_legend_handles_labels()

        if not handles:
            return

        # 항목이 많으면 샘플링
        if len(handles) > max_items:
            step = max(1, len(handles) // max_items)
            handles = handles[::step]
            labels = labels[::step]

        # 동적 폰트 크기
        font_size = self.get_dynamic_font_size(base_size=9)

        # 범례 설정
        ax.legend(
            handles, labels,
            loc='upper left',
            bbox_to_anchor=(1.01, 1),
            fontsize=max(6, font_size - 2),
            frameon=True,
            fancybox=True,
            shadow=False,
            ncol=1,
            borderaxespad=0
        )

    def apply_responsive_figure_style(self, figure, ax, title="", xlabel="", ylabel=""):
        """반응형 그래프 스타일 적용"""
        font_size = self.get_dynamic_font_size(base_size=10)

        ax.set_title(title, fontsize=font_size + 1, fontname='AppleGothic', pad=10)
        ax.set_xlabel(xlabel, fontsize=font_size, fontname='AppleGothic')
        ax.set_ylabel(ylabel, fontsize=font_size, fontname='AppleGothic')
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.tick_params(labelsize=font_size - 1)

        return ax


def get_screen_size():
    """화면 크기 반환"""
    screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
    return screen.width(), screen.height()


def calculate_window_size(width_ratio=0.85, height_ratio=0.85, min_width=1200, min_height=800):
    """화면 비율 기반 창 크기 계산"""
    screen_width, screen_height = get_screen_size()

    width = max(min_width, int(screen_width * width_ratio))
    height = max(min_height, int(screen_height * height_ratio))

    return width, height


def create_responsive_button(text, min_width=100, min_height=30, style_class="default"):
    """반응형 버튼 생성"""
    button = QtWidgets.QPushButton(text)
    button.setMinimumSize(min_width, min_height)

    styles = {
        "default": """
            QPushButton {
                background-color: #5a5a5a;
                color: white;
                font-size: 11pt;
                border-radius: 3px;
                padding: 5px 15px;
            }
            QPushButton:hover { background-color: #6a6a6a; }
            QPushButton:pressed { background-color: #4a4a4a; }
        """,
        "primary": """
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                font-size: 11pt;
                font-weight: bold;
                border-radius: 3px;
                padding: 5px 15px;
            }
            QPushButton:hover { background-color: #5a5a5a; }
            QPushButton:pressed { background-color: #3a3a3a; }
        """
    }

    button.setStyleSheet(styles.get(style_class, styles["default"]))
    return button