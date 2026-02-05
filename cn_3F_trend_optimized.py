import faulthandler

import gc

gc.enable()
gc.set_threshold(700, 10, 10)

import PyQt5.QtGui

from performance_logger import PerformanceLogger
from OPTIMIZATION_PATCH_LEVEL1 import FileCache, BatchProcessor, MemoryEfficientProcessor
from responsive_layout_utils import ResponsiveLayoutMixin, calculate_window_size, create_responsive_button

# # ⭐ 추가: Level 2 최적화 임포트
# from OPTIMIZATION_PATCH_LEVEL2_PARALLEL import (
#     ParallelProcessor,
#     BatchRenderer,
#     ThreadSafeCache
# )

# ✅ Level 3 임포트 추가
from OPTIMIZATION_PATCH_LEVEL3_ULTRA import (
    UltraParallelProcessor as ParallelProcessor,
    UltraFastRenderer as BatchRenderer,
    ThreadSafeCache
)

# ⭐ Level 4 임포트 추가
from OPTIMIZATION_PATCH_LEVEL4_RENDERING import (
    ParallelTrendSaver  # 병렬 저장용
)

# ===== Level 5 Trend 최적화 =====
from OPTIMIZATION_PATCH_LEVEL5_TREND import (
    TrendParallelProcessor,
    TrendResult,
    save_trend_result_to_json
)

# ===== Level 5 Spectrum 최적화 =====
from OPTIMIZATION_PATCH_LEVEL5_SPECTRUM import (
    SpectrumParallelProcessor,
    SpectrumResult
)

faulthandler.enable(all_threads=True)

import sys
import os
import platform

# 폰트 설정 (OS별 분기)
if platform.system() == 'Windows':
    DEFAULT_FONT = 'Malgun Gothic'
elif platform.system() == 'Darwin':  # macOS
    DEFAULT_FONT = 'AppleGothic'
else:  # Linux
    DEFAULT_FONT = 'NanumGothic'

# ===== 최적화 모듈 (자동 추가) =====
from json_handler import save_json, load_json
# ====================================

from collections import defaultdict
import numpy as np
import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import warnings

warnings.filterwarnings('ignore', category=RuntimeWarning)

# ===== 폰트 설정 (마이너스 기호 문제 해결) =====
plt.rcParams['axes.unicode_minus'] = False  # ⭐ 추가됨
# ================================================

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox
import re
from matplotlib.figure import Figure

from datetime import datetime
from PyQt5.QtWidgets import QApplication
import matplotlib.dates as mdates
from PyQt5.QtWidgets import QSizePolicy
from scipy.fft import fft
from scipy.signal.windows import hann, flattop
import itertools
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt, QTimer
import csv
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from PyQt5.QtGui import QIcon
from matplotlib import rcParams

rcParams.update({'font.size': 7, 'font.family': DEFAULT_FONT})

# 로거 초기화 (한 번만)
perf_logger = PerformanceLogger(
    log_file="performance_log.txt",
    console_output=True  # 콘솔에도 출력
)


def set_plot_font(plot_item, font_size=7):
    font = PyQt5.QtGui.QFont("Malgun Gothic", font_size)
    for axis in ['bottom', 'left', 'top', 'right']:
        plot_item.getAxis(axis).setTickFont(font)
    plot_item.setTitle("제목입니다", size=f"{font_size + 2}pt")
    plot_item.setLabel("left", "Y축", **{'font-size': f'{font_size}pt'})
    plot_item.setLabel("bottom", "X축", **{'font-size': f'{font_size}pt'})


class ProgressDialog(QDialog):
    def __init__(self, total_tasks, parent=None):
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
        self.progress_bar.setValue(value)
        percent = int((value / self.progress_bar.maximum()) * 100)
        self.label.setText(f"{percent}% 완료 중...")
        QApplication.processEvents()


"""
✅ Detail Analysis - 축 클릭 감지 수정
- 축 레이블/눈금 클릭 시 Range 다이얼로그 표시
- Legend 그래프 밖 배치
- Auto X/Y 별도 체크박스
"""

import itertools
import os
import csv
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from responsive_layout_utils import ResponsiveLayoutMixin, create_responsive_button
from file_parser import FileParser
from fft_engine import FFTEngine


class AxisRangeDialog(QtWidgets.QDialog):
    """축 범위 설정 다이얼로그"""

    def __init__(self, axis_name, current_min, current_max, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Set {axis_name} Axis Range")
        self.setModal(True)
        self.setMinimumWidth(300)

        layout = QtWidgets.QVBoxLayout(self)

        # Auto Range 체크박스
        self.auto_checkbox = QtWidgets.QCheckBox("Auto Range")
        self.auto_checkbox.setChecked(False)
        self.auto_checkbox.stateChanged.connect(self.toggle_inputs)
        layout.addWidget(self.auto_checkbox)

        # Min/Max 입력
        form_layout = QtWidgets.QFormLayout()

        self.min_input = QtWidgets.QLineEdit(f"{current_min:.2f}")
        self.min_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: #333333;
                border: 1px solid #cccccc;
                padding: 5px;
            }
        """)
        form_layout.addRow(f"{axis_name} min:", self.min_input)

        self.max_input = QtWidgets.QLineEdit(f"{current_max:.2f}")
        self.max_input.setStyleSheet(self.min_input.styleSheet())
        form_layout.addRow(f"{axis_name} max:", self.max_input)

        layout.addLayout(form_layout)

        # 버튼
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def toggle_inputs(self, state):
        """Auto 체크 시 입력 비활성화"""
        enabled = not self.auto_checkbox.isChecked()
        self.min_input.setEnabled(enabled)
        self.max_input.setEnabled(enabled)

    def get_range(self):
        """범위 반환 (None이면 Auto)"""
        if self.auto_checkbox.isChecked():
            return None, None

        try:
            min_val = float(self.min_input.text())
            max_val = float(self.max_input.text())

            if min_val >= max_val:
                QtWidgets.QMessageBox.warning(self, "경고", "min은 max보다 작아야 합니다")
                return None, None

            return min_val, max_val
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "경고", "올바른 숫자를 입력하세요")
            return None, None


class ListSaveDialog(QtWidgets.QDialog, ResponsiveLayoutMixin):
    """Detail Analysis 다이얼로그"""

    def __init__(self, channel_files: dict, parent=None, headers=None, directory_path=None):
        super().__init__(parent)

        # ===== 창 설정 =====
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinMaxButtonsHint
        )
        self.setWindowTitle("Detail Analysis - Select Files to Save")

        from responsive_layout_utils import calculate_window_size
        width, height = calculate_window_size(0.85, 0.85, 1200, 800)
        self.resize(width, height)
        self.setMinimumSize(1200, 800)

        # 라이트 모드 스타일시트
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                color: #333333;
            }
            QLabel {
                color: #333333;
            }
            QCheckBox {
                color: #333333;
            }
        """)

        # ===== 초기화 =====
        self.directory_path = directory_path
        self.channel_files = channel_files
        self.color_cycle = itertools.cycle(plt.cm.tab10.colors)
        self.markers_spect = []
        self.hover_pos_spect = [None, None]
        self.mouse_tracking_enabled = True

        # ===== 메인 레이아웃 =====
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setStretchFactor(0, 15)
        self.splitter.setStretchFactor(1, 85)

        main_layout.addWidget(self.splitter)

        self.populate_list_widget()
        self.adjust_left_panel_width()

    def create_left_panel(self):
        """왼쪽 패널 생성"""
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot_button = create_responsive_button("Plot", 100, 35, "primary")
        self.plot_button.clicked.connect(self.on_file_items_clicked)
        layout.addWidget(self.plot_button)

        self.file_list_widget = QtWidgets.QListWidget()
        self.file_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.file_list_widget.setStyleSheet("""
            QListWidget {
                background-color: white;
                color: #333333;
                font-size: 10pt;
                border: 1px solid #cccccc;
                font-family: 'Courier New', monospace;
            }
            QListWidget::item {
                padding: 2px;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e5f3ff;
            }
        """)

        layout.addWidget(self.file_list_widget)

        return panel

    def create_right_panel(self):
        """오른쪽 패널 생성"""
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        waveform_widget = self.create_graph_widget("waveform")
        layout.addWidget(waveform_widget, stretch=1)

        spectrum_widget = self.create_graph_widget("spectrum")
        layout.addWidget(spectrum_widget, stretch=1)

        button_widget = self.create_button_panel()
        layout.addWidget(button_widget)

        return panel

    def create_graph_widget(self, graph_type):
        """그래프 위젯 생성"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        dpi = QtWidgets.QApplication.primaryScreen().logicalDotsPerInch()
        figure = plt.Figure(figsize=(10, 3.5), dpi=dpi)
        ax = figure.add_subplot(111)
        canvas = FigureCanvas(figure)
        canvas.setMinimumHeight(250)

        if graph_type == "waveform":
            ax.set_title("Waveform", fontsize=7)
            ax.set_xlabel("Time (s)", fontsize=7)
        else:
            ax.set_title("Vibration Spectrum", fontsize=7)
            ax.set_xlabel("Frequency (Hz)", fontsize=7)

        ax.tick_params(axis='both', labelsize=7)
        ax.grid(True)

        # ⭐ Legend를 그래프 밖 여백으로 배치
        self.setup_figure_with_legend(figure, ax, rect=[0, 0, 0.88, 1])

        if graph_type == "waveform":
            self.tab_waveform_figure = figure
            self.tab_waveax = ax
            self.tab_wavecanvas = canvas
        else:
            self.tab_figure = figure
            self.tab_ax = ax
            self.tab_canvas = canvas

        canvas.setFocusPolicy(QtCore.Qt.StrongFocus)

        # ⭐ 축 클릭 이벤트 연결
        canvas.mpl_connect('button_press_event',
                           lambda event: self.on_axis_click(event, graph_type))

        layout.addWidget(canvas)

        # 컨트롤 패널
        control = self.create_improved_control_panel(graph_type)
        layout.addWidget(control)

        return widget

    def on_axis_click(self, event, graph_type):
        """⭐ 축 클릭 시 Range 다이얼로그 열기 (수정됨)"""
        if event.button != 1:  # 왼쪽 클릭만
            return

        # ⭐ 그래프 영역 안 클릭은 피킹용으로 사용
        if event.inaxes is not None:
            return

        ax = self.tab_waveax if graph_type == "waveform" else self.tab_ax

        # ⭐ 축 영역 좌표 가져오기 (픽셀 좌표)
        bbox = ax.get_window_extent()

        # X축 영역: 그래프 아래쪽 (bbox.y0 - 50 ~ bbox.y0)
        if (bbox.x0 <= event.x <= bbox.x1 and
                event.y < bbox.y0 and event.y > bbox.y0 - 60):
            print(f"✅ X축 클릭 감지: x={event.x}, y={event.y}")
            self.show_axis_range_dialog(graph_type, 'X')
            return

        # Y축 영역: 그래프 왼쪽 (bbox.x0 - 100 ~ bbox.x0)
        if (bbox.y0 <= event.y <= bbox.y1 and
                event.x < bbox.x0 and event.x > bbox.x0 - 120):
            print(f"✅ Y축 클릭 감지: x={event.x}, y={event.y}")
            self.show_axis_range_dialog(graph_type, 'Y')
            return

    def create_improved_control_panel(self, graph_type):
        """컨트롤 패널"""
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Auto X 체크박스
        auto_x = QtWidgets.QCheckBox("Auto X")
        auto_x.setChecked(True)
        auto_x.setStyleSheet("color: #333333; font-size: 10pt;")
        auto_x.stateChanged.connect(
            lambda: self.toggle_auto_scale(graph_type, 'x', auto_x.isChecked())
        )

        # Auto Scale X 버튼
        auto_scale_x_btn = create_responsive_button("Auto Scale X", 100, 25, "default")
        auto_scale_x_btn.clicked.connect(lambda: self.auto_scale(graph_type, 'x'))

        # Auto Y 체크박스
        auto_y = QtWidgets.QCheckBox("Auto Y")
        auto_y.setChecked(True)
        auto_y.setStyleSheet("color: #333333; font-size: 10pt;")
        auto_y.stateChanged.connect(
            lambda: self.toggle_auto_scale(graph_type, 'y', auto_y.isChecked())
        )

        # Auto Scale Y 버튼
        auto_scale_y_btn = create_responsive_button("Auto Scale Y", 100, 25, "default")
        auto_scale_y_btn.clicked.connect(lambda: self.auto_scale(graph_type, 'y'))

        # 레이아웃
        layout.addWidget(auto_x)
        layout.addWidget(auto_scale_x_btn)
        layout.addWidget(auto_y)
        layout.addWidget(auto_scale_y_btn)
        layout.addStretch()

        # 속성 저장
        prefix = "waveform" if graph_type == "waveform" else "spectrum"
        setattr(self, f"tab_{prefix}_auto_x", auto_x)
        setattr(self, f"tab_{prefix}_auto_scale_x", auto_scale_x_btn)
        setattr(self, f"tab_{prefix}_auto_y", auto_y)
        setattr(self, f"tab_{prefix}_auto_scale_y", auto_scale_y_btn)

        return panel

    def show_axis_range_dialog(self, graph_type, axis_name):
        """축 범위 설정 다이얼로그 표시"""
        ax = self.tab_waveax if graph_type == "waveform" else self.tab_ax

        # 현재 범위 가져오기
        if axis_name == 'X':
            current_min, current_max = ax.get_xlim()
        else:
            current_min, current_max = ax.get_ylim()

        # 다이얼로그 열기
        dialog = AxisRangeDialog(axis_name, current_min, current_max, self)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            min_val, max_val = dialog.get_range()

            prefix = "waveform" if graph_type == "waveform" else "spectrum"
            canvas = self.tab_wavecanvas if graph_type == "waveform" else self.tab_canvas

            if min_val is None or max_val is None:
                # Auto Range
                if axis_name == 'X':
                    auto_checkbox = getattr(self, f"tab_{prefix}_auto_x")
                    auto_checkbox.setChecked(True)
                    ax.autoscale(enable=True, axis='x')
                else:
                    auto_checkbox = getattr(self, f"tab_{prefix}_auto_y")
                    auto_checkbox.setChecked(True)
                    ax.autoscale(enable=True, axis='y')
            else:
                # 수동 범위
                if axis_name == 'X':
                    auto_checkbox = getattr(self, f"tab_{prefix}_auto_x")
                    auto_checkbox.setChecked(False)
                    ax.set_xlim(min_val, max_val)
                else:
                    auto_checkbox = getattr(self, f"tab_{prefix}_auto_y")
                    auto_checkbox.setChecked(False)
                    ax.set_ylim(min_val, max_val)

            canvas.draw_idle()

    def toggle_auto_scale(self, graph_type, axis, is_auto):
        """Auto 체크박스 토글"""
        if is_auto:
            self.auto_scale(graph_type, axis)

    def auto_scale(self, graph_type, axis):
        """축 Auto Scale"""
        ax = self.tab_waveax if graph_type == "waveform" else self.tab_ax
        canvas = self.tab_wavecanvas if graph_type == "waveform" else self.tab_canvas

        prefix = "waveform" if graph_type == "waveform" else "spectrum"

        if axis == 'x':
            auto_checkbox = getattr(self, f"tab_{prefix}_auto_x")
            auto_checkbox.setChecked(True)
            ax.autoscale(enable=True, axis='x')
        else:
            auto_checkbox = getattr(self, f"tab_{prefix}_auto_y")
            auto_checkbox.setChecked(True)
            ax.autoscale(enable=True, axis='y')

        canvas.draw_idle()

    def create_button_panel(self):
        """하단 버튼 패널"""
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_save_button = create_responsive_button("Data Extraction", 120, 35)
        self.tab_save_button.clicked.connect(self.on_save_button_clicked)

        self.tab_close_button = create_responsive_button("Close", 120, 35)
        self.tab_close_button.clicked.connect(self.close_dialog)

        layout.addWidget(self.tab_save_button)
        layout.addWidget(self.tab_close_button)
        layout.addStretch()

        return panel

    # ===== 파일 리스트 관리 (생략 - 이전과 동일) =====
    def populate_list_widget(self):
        """채널별로 파일 리스트 표시"""
        self.file_list_widget.clear()

        for ch_num in range(1, 7):
            ch_key = f"Ch{ch_num}"
            files = self.channel_files.get(ch_key, [])

            header_item = QtWidgets.QListWidgetItem(f"Ch{ch_num}")
            header_item.setFlags(QtCore.Qt.ItemIsEnabled)
            header_item.setBackground(QtCore.Qt.lightGray)
            header_item.setForeground(QtCore.Qt.black)
            font = header_item.font()
            font.setBold(True)
            header_item.setFont(font)
            self.file_list_widget.addItem(header_item)

            if files:
                for file in sorted(files):
                    file_item = QtWidgets.QListWidgetItem(f"  {file}")
                    file_item.setData(QtCore.Qt.UserRole, file)
                    self.file_list_widget.addItem(file_item)
            else:
                empty_item = QtWidgets.QListWidgetItem("  -")
                empty_item.setFlags(QtCore.Qt.ItemIsEnabled)
                empty_item.setForeground(QtCore.Qt.gray)
                self.file_list_widget.addItem(empty_item)

    def adjust_left_panel_width(self):
        """왼쪽 패널 너비 자동 조정"""
        max_width = 0
        font_metrics = QtGui.QFontMetrics(self.file_list_widget.font())

        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            text_width = font_metrics.boundingRect(item.text()).width()
            max_width = max(max_width, text_width)

        scrollbar_width = self.file_list_widget.verticalScrollBar().sizeHint().width()
        optimal_width = max_width + scrollbar_width + 42
        final_width = max(250, min(optimal_width, 600))

        self.left_panel.setMinimumWidth(final_width)
        self.left_panel.setMaximumWidth(final_width)

        total_width = self.width()
        right_width = total_width - final_width - 20
        self.splitter.setSizes([final_width, right_width])

    def get_selected_files(self):
        """선택된 파일 추출"""
        selected_files = []
        for item in self.file_list_widget.selectedItems():
            file_name = item.data(QtCore.Qt.UserRole)
            if file_name:
                selected_files.append(file_name)
        return selected_files

    def on_file_items_clicked(self):
        """Plot 버튼"""
        selected_files = self.get_selected_files()

        if not selected_files:
            QtWidgets.QMessageBox.warning(self, "경고", "파일을 선택하세요")
            return

        self.tab_waveax.clear()
        self.tab_ax.clear()
        self.color_cycle = itertools.cycle(plt.cm.tab10.colors)
        self.data_dict = {}
        self.spectrum_data_dict1 = {}

        for file_name in selected_files:
            self.load_and_plot_file(file_name)

        self.finalize_plot()

    def load_and_plot_file(self, file_name):
        """파일 로드 (FileParser + FFTEngine)"""
        if not self.directory_path:
            return

        file_path = os.path.join(self.directory_path, file_name)
        if not os.path.exists(file_path):
            return

        try:
            base_name = os.path.splitext(file_name)[0]

            parser = FileParser(file_path)
            if not parser.is_valid():
                return

            data = parser.get_data()
            sampling_rate = parser.get_sampling_rate()

            if sampling_rate is None:
                return

            # JSON fallback
            json_folder = os.path.join(self.directory_path, "trend_data", "full")
            json_path = os.path.join(json_folder, f"{base_name}_full.json")

            import json
            json_metadata = {}
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r') as f:
                        json_metadata = json.load(f)
                except:
                    pass

            delta_f = json_metadata.get("delta_f", 1.0)
            overlap = json_metadata.get("overlap", 50.0)
            window_str = json_metadata.get("window", "hanning").lower()
            view_type_str = json_metadata.get("view_type", "ACC").upper()

            view_type_map = {"ACC": 1, "VEL": 2, "DIS": 3}
            view_type = view_type_map.get(view_type_str, 1)

            engine = FFTEngine(
                sampling_rate=sampling_rate,
                delta_f=delta_f,
                overlap=overlap,
                window_type=window_str
            )

            result = engine.compute(data=data, view_type=view_type, type_flag=2)
            frequency = result['frequency']
            spectrum = result['spectrum']

            time = np.arange(len(data)) / sampling_rate
            color = next(self.color_cycle)

            self.tab_waveax.plot(time, data, label=base_name, color=color, linewidth=0.5, alpha=0.8)
            self.tab_ax.plot(frequency, spectrum, label=base_name, color=color, linewidth=0.5, alpha=0.8)

            self.data_dict[base_name] = (frequency, spectrum)
            self.spectrum_data_dict1[base_name] = spectrum

            view_labels = {
                1: "Vibration Acceleration\n(m/s², RMS)",
                2: "Vibration Velocity\n(mm/s, RMS)",
                3: "Vibration Displacement\n(μm, RMS)"
            }
            ylabel = view_labels.get(view_type, "Vibration (mm/s, RMS)")
            self.tab_ax.set_ylabel(ylabel, fontsize=7)
            self.tab_waveax.set_ylabel(ylabel, fontsize=7)

        except Exception as e:
            print(f"❌ {file_name} 로드 실패: {e}")

    def finalize_plot(self):
        """그래프 마무리"""
        self.tab_waveax.set_title("Waveform", fontsize=7)
        self.tab_waveax.set_xlabel("Time (s)", fontsize=7)
        self.tab_waveax.legend(fontsize=7, loc='upper left', bbox_to_anchor=(1, 1))
        self.tab_waveax.grid(True)
        self.tab_waveax.tick_params(axis='both', labelsize=7)

        self.tab_ax.set_title("Vibration Spectrum", fontsize=7)
        self.tab_ax.set_xlabel("Frequency (Hz)", fontsize=7)
        self.tab_ax.legend(fontsize=7, loc='upper left', bbox_to_anchor=(1, 1))
        self.tab_ax.grid(True)
        self.tab_ax.tick_params(axis='both', labelsize=7)

        try:
            self.tab_waveform_figure.tight_layout(rect=[0, 0, 0.88, 1])
            self.tab_figure.tight_layout(rect=[0, 0, 0.88, 1])
        except:
            pass

        self.tab_wavecanvas.draw_idle()
        self.tab_canvas.draw_idle()

        # Picking 기능 (Spectrum만)
        self.hover_dot_spect = self.tab_ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
        self.tab_canvas.mpl_connect("motion_notify_event", self.on_mouse_move_spect)
        self.tab_canvas.mpl_connect("button_press_event", self.on_mouse_click_spect)
        self.tab_canvas.mpl_connect("key_press_event", self.on_key_press_spect)

    # ===== Picking 기능 (생략 - 기존과 동일) =====
    def on_mouse_move_spect(self, event):
        # ... (이전 코드 동일)
        pass

    def on_mouse_click_spect(self, event):
        # ... (이전 코드 동일)
        pass

    def on_key_press_spect(self, event):
        # ... (이전 코드 동일)
        pass

    def add_marker_spect(self, x, y):
        # ... (이전 코드 동일)
        pass

    def on_save_button_clicked(self):
        """CSV 저장"""
        if not hasattr(self, 'spectrum_data_dict1') or not self.spectrum_data_dict1:
            QtWidgets.QMessageBox.warning(self, "경고", "먼저 파일을 Plot 하세요")
            return
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "CSV 파일 저장", "", "CSV Files (*.csv)")
        if not save_path:
            return
        if not save_path.endswith(".csv"):
            save_path += ".csv"
        try:
            with open(save_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                file_names = list(self.spectrum_data_dict1.keys())
                writer.writerow(["Frequency (Hz)", *file_names])
                first_file = file_names[0]
                frequencies = self.data_dict[first_file][0]
                for i, freq in enumerate(frequencies):
                    row = [freq]
                    for fname in file_names:
                        spectrum = self.spectrum_data_dict1[fname]
                        value = float(spectrum[i]) if i < len(spectrum) else ""
                        row.append(value)
                    writer.writerow(row)
            QtWidgets.QMessageBox.information(self, "성공", f"저장 완료:\n{save_path}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "오류", f"저장 실패:\n{e}")

    def close_dialog(self):
        try:
            plt.close(self.tab_waveform_figure)
            plt.close(self.tab_figure)
        except:
            pass
        if hasattr(self, 'data_dict'):
            self.data_dict.clear()
        if hasattr(self, 'spectrum_data_dict1'):
            self.spectrum_data_dict1.clear()
        self.deleteLater()
        self.accept()

    def closeEvent(self, event):
        self.close_dialog()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close_dialog()
        else:
            super().keyPressEvent(event)

# """
# 개선된 Detail Analysis - UX 피드백 반영
# ✅ 우클릭 메뉴 제거 (Spectrum 피킹용)
# ✅ 축 클릭으로 Range 다이얼로그 열기
# ✅ Auto X/Y 별도 체크박스
# ✅ Legend를 그래프 밖 여백으로 배치
# ✅ Set Axis Range 다이얼로그 개선
# """
#
# import itertools
# import os
# import csv
# import numpy as np
# from PyQt5 import QtWidgets, QtCore, QtGui
# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# import matplotlib.pyplot as plt
# from responsive_layout_utils import ResponsiveLayoutMixin, create_responsive_button
# from file_parser import FileParser
# from fft_engine import FFTEngine
#
#
# class AxisRangeDialog(QtWidgets.QDialog):
#     """축 범위 설정 다이얼로그 (개선)"""
#
#     def __init__(self, axis_name, current_min, current_max, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle(f"Set {axis_name} Axis Range")
#         self.setModal(True)
#         self.setMinimumWidth(300)
#
#         layout = QtWidgets.QVBoxLayout(self)
#
#         # Auto Range 체크박스
#         self.auto_checkbox = QtWidgets.QCheckBox("Auto Range")
#         self.auto_checkbox.setChecked(False)
#         self.auto_checkbox.stateChanged.connect(self.toggle_inputs)
#         layout.addWidget(self.auto_checkbox)
#
#         # Min/Max 입력
#         form_layout = QtWidgets.QFormLayout()
#
#         self.min_input = QtWidgets.QLineEdit(f"{current_min:.2f}")
#         self.min_input.setStyleSheet("""
#             QLineEdit {
#                 background-color: white;
#                 color: #333333;
#                 border: 1px solid #cccccc;
#                 padding: 5px;
#             }
#         """)
#         form_layout.addRow(f"{axis_name} min:", self.min_input)
#
#         self.max_input = QtWidgets.QLineEdit(f"{current_max:.2f}")
#         self.max_input.setStyleSheet(self.min_input.styleSheet())
#         form_layout.addRow(f"{axis_name} max:", self.max_input)
#
#         layout.addLayout(form_layout)
#
#         # 버튼
#         buttons = QtWidgets.QDialogButtonBox(
#             QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
#         )
#         buttons.accepted.connect(self.accept)
#         buttons.rejected.connect(self.reject)
#         layout.addWidget(buttons)
#
#     def toggle_inputs(self, state):
#         """Auto 체크 시 입력 비활성화"""
#         enabled = not self.auto_checkbox.isChecked()
#         self.min_input.setEnabled(enabled)
#         self.max_input.setEnabled(enabled)
#
#     def get_range(self):
#         """범위 반환 (None이면 Auto)"""
#         if self.auto_checkbox.isChecked():
#             return None, None
#
#         try:
#             min_val = float(self.min_input.text())
#             max_val = float(self.max_input.text())
#
#             if min_val >= max_val:
#                 QtWidgets.QMessageBox.warning(self, "경고", "min은 max보다 작아야 합니다")
#                 return None, None
#
#             return min_val, max_val
#         except ValueError:
#             QtWidgets.QMessageBox.warning(self, "경고", "올바른 숫자를 입력하세요")
#             return None, None
#
#
# class ListSaveDialog(QtWidgets.QDialog, ResponsiveLayoutMixin):
#     """Detail Analysis 다이얼로그 (개선된 UX)"""
#
#     def __init__(self, channel_files: dict, parent=None, headers=None, directory_path=None):
#         super().__init__(parent)
#
#         # ===== 창 설정 =====
#         self.setWindowFlags(
#             QtCore.Qt.Window |
#             QtCore.Qt.WindowCloseButtonHint |
#             QtCore.Qt.WindowMinMaxButtonsHint
#         )
#         self.setWindowTitle("Detail Analysis - Select Files to Save")
#
#         from responsive_layout_utils import calculate_window_size
#         width, height = calculate_window_size(0.85, 0.85, 1200, 800)
#         self.resize(width, height)
#         self.setMinimumSize(1200, 800)
#
#         # 라이트 모드 스타일시트
#         self.setStyleSheet("""
#             QDialog {
#                 background-color: #f5f5f5;
#                 color: #333333;
#             }
#             QLabel {
#                 color: #333333;
#             }
#             QCheckBox {
#                 color: #333333;
#             }
#         """)
#
#         # ===== 초기화 =====
#         self.directory_path = directory_path
#         self.channel_files = channel_files
#         self.color_cycle = itertools.cycle(plt.cm.tab10.colors)
#         self.markers_spect = []
#         self.hover_pos_spect = [None, None]
#         self.mouse_tracking_enabled = True
#
#         # ===== 메인 레이아웃 =====
#         main_layout = QtWidgets.QHBoxLayout(self)
#         main_layout.setContentsMargins(10, 10, 10, 10)
#         main_layout.setSpacing(10)
#
#         self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
#
#         self.left_panel = self.create_left_panel()
#         right_panel = self.create_right_panel()
#
#         self.splitter.addWidget(self.left_panel)
#         self.splitter.addWidget(right_panel)
#         self.splitter.setStretchFactor(0, 15)
#         self.splitter.setStretchFactor(1, 85)
#
#         main_layout.addWidget(self.splitter)
#
#         self.populate_list_widget()
#         self.adjust_left_panel_width()
#
#     def create_left_panel(self):
#         """왼쪽 패널 생성"""
#         panel = QtWidgets.QWidget()
#         layout = QtWidgets.QVBoxLayout(panel)
#         layout.setContentsMargins(0, 0, 0, 0)
#
#         self.plot_button = create_responsive_button("Plot", 100, 35, "primary")
#         self.plot_button.clicked.connect(self.on_file_items_clicked)
#         layout.addWidget(self.plot_button)
#
#         self.file_list_widget = QtWidgets.QListWidget()
#         self.file_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
#         self.file_list_widget.setStyleSheet("""
#             QListWidget {
#                 background-color: white;
#                 color: #333333;
#                 font-size: 10pt;
#                 border: 1px solid #cccccc;
#                 font-family: 'Courier New', monospace;
#             }
#             QListWidget::item {
#                 padding: 2px;
#             }
#             QListWidget::item:selected {
#                 background-color: #0078d7;
#                 color: white;
#             }
#             QListWidget::item:hover {
#                 background-color: #e5f3ff;
#             }
#         """)
#
#         layout.addWidget(self.file_list_widget)
#
#         return panel
#
#     def create_right_panel(self):
#         """오른쪽 패널 생성"""
#         panel = QtWidgets.QWidget()
#         layout = QtWidgets.QVBoxLayout(panel)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(10)
#
#         waveform_widget = self.create_graph_widget("waveform")
#         layout.addWidget(waveform_widget, stretch=1)
#
#         spectrum_widget = self.create_graph_widget("spectrum")
#         layout.addWidget(spectrum_widget, stretch=1)
#
#         button_widget = self.create_button_panel()
#         layout.addWidget(button_widget)
#
#         return panel
#
#     def create_graph_widget(self, graph_type):
#         """그래프 위젯 생성"""
#         widget = QtWidgets.QWidget()
#         layout = QtWidgets.QVBoxLayout(widget)
#         layout.setContentsMargins(0, 0, 0, 0)
#
#         dpi = QtWidgets.QApplication.primaryScreen().logicalDotsPerInch()
#         figure = plt.Figure(figsize=(10, 3.5), dpi=dpi)
#         ax = figure.add_subplot(111)
#         canvas = FigureCanvas(figure)
#         canvas.setMinimumHeight(250)
#
#         if graph_type == "waveform":
#             ax.set_title("Waveform", fontsize=7)
#             ax.set_xlabel("Time (s)", fontsize=7)
#         else:
#             ax.set_title("Vibration Spectrum", fontsize=7)
#             ax.set_xlabel("Frequency (Hz)", fontsize=7)
#
#         ax.tick_params(axis='both', labelsize=7)
#         ax.grid(True)
#
#         # ⭐ Legend를 그래프 밖 여백으로 배치
#         self.setup_figure_with_legend(figure, ax, rect=[0, 0, 0.88, 1])
#
#         if graph_type == "waveform":
#             self.tab_waveform_figure = figure
#             self.tab_waveax = ax
#             self.tab_wavecanvas = canvas
#         else:
#             self.tab_figure = figure
#             self.tab_ax = ax
#             self.tab_canvas = canvas
#
#         canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
#
#         # ⭐ 축 클릭 이벤트 연결
#         canvas.mpl_connect('button_press_event',
#                           lambda event: self.on_axis_click(event, graph_type))
#
#         layout.addWidget(canvas)
#
#         # ⭐ 개선된 컨트롤 패널
#         control = self.create_improved_control_panel(graph_type)
#         layout.addWidget(control)
#
#         return widget
#
#     def create_improved_control_panel(self, graph_type):
#         """⭐ 개선된 컨트롤 패널"""
#         panel = QtWidgets.QWidget()
#         layout = QtWidgets.QHBoxLayout(panel)
#         layout.setContentsMargins(5, 5, 5, 5)
#         layout.setSpacing(10)
#
#         # Auto X 체크박스
#         auto_x = QtWidgets.QCheckBox("Auto X")
#         auto_x.setChecked(True)
#         auto_x.setStyleSheet("color: #333333; font-size: 10pt;")
#         auto_x.stateChanged.connect(
#             lambda: self.toggle_auto_scale(graph_type, 'x', auto_x.isChecked())
#         )
#
#         # Auto Scale X 버튼
#         auto_scale_x_btn = create_responsive_button("Auto Scale X", 100, 25, "default")
#         auto_scale_x_btn.clicked.connect(lambda: self.auto_scale(graph_type, 'x'))
#
#         # Auto Y 체크박스
#         auto_y = QtWidgets.QCheckBox("Auto Y")
#         auto_y.setChecked(True)
#         auto_y.setStyleSheet("color: #333333; font-size: 10pt;")
#         auto_y.stateChanged.connect(
#             lambda: self.toggle_auto_scale(graph_type, 'y', auto_y.isChecked())
#         )
#
#         # Auto Scale Y 버튼
#         auto_scale_y_btn = create_responsive_button("Auto Scale Y", 100, 25, "default")
#         auto_scale_y_btn.clicked.connect(lambda: self.auto_scale(graph_type, 'y'))
#
#         # 레이아웃
#         layout.addWidget(auto_x)
#         layout.addWidget(auto_scale_x_btn)
#         layout.addWidget(auto_y)
#         layout.addWidget(auto_scale_y_btn)
#         layout.addStretch()
#
#         # 속성 저장
#         prefix = "waveform" if graph_type == "waveform" else "spectrum"
#         setattr(self, f"tab_{prefix}_auto_x", auto_x)
#         setattr(self, f"tab_{prefix}_auto_scale_x", auto_scale_x_btn)
#         setattr(self, f"tab_{prefix}_auto_y", auto_y)
#         setattr(self, f"tab_{prefix}_auto_scale_y", auto_scale_y_btn)
#
#         return panel
#
#     def on_axis_click(self, event, graph_type):
#         """⭐ 축 클릭 시 Range 다이얼로그 열기"""
#         if event.button != 1:  # 왼쪽 클릭만
#             return
#
#         ax = self.tab_waveax if graph_type == "waveform" else self.tab_ax
#
#         # X축 클릭 확인
#         if event.inaxes and event.inaxes.xaxis.contains(event)[0]:
#             self.show_axis_range_dialog(graph_type, 'X')
#
#         # Y축 클릭 확인
#         elif event.inaxes and event.inaxes.yaxis.contains(event)[0]:
#             self.show_axis_range_dialog(graph_type, 'Y')
#
#     def show_axis_range_dialog(self, graph_type, axis_name):
#         """축 범위 설정 다이얼로그 표시"""
#         ax = self.tab_waveax if graph_type == "waveform" else self.tab_ax
#
#         # 현재 범위 가져오기
#         if axis_name == 'X':
#             current_min, current_max = ax.get_xlim()
#         else:
#             current_min, current_max = ax.get_ylim()
#
#         # 다이얼로그 열기
#         dialog = AxisRangeDialog(axis_name, current_min, current_max, self)
#
#         if dialog.exec_() == QtWidgets.QDialog.Accepted:
#             min_val, max_val = dialog.get_range()
#
#             prefix = "waveform" if graph_type == "waveform" else "spectrum"
#             canvas = self.tab_wavecanvas if graph_type == "waveform" else self.tab_canvas
#
#             if min_val is None or max_val is None:
#                 # Auto Range
#                 if axis_name == 'X':
#                     auto_checkbox = getattr(self, f"tab_{prefix}_auto_x")
#                     auto_checkbox.setChecked(True)
#                     ax.autoscale(enable=True, axis='x')
#                 else:
#                     auto_checkbox = getattr(self, f"tab_{prefix}_auto_y")
#                     auto_checkbox.setChecked(True)
#                     ax.autoscale(enable=True, axis='y')
#             else:
#                 # 수동 범위
#                 if axis_name == 'X':
#                     auto_checkbox = getattr(self, f"tab_{prefix}_auto_x")
#                     auto_checkbox.setChecked(False)
#                     ax.set_xlim(min_val, max_val)
#                 else:
#                     auto_checkbox = getattr(self, f"tab_{prefix}_auto_y")
#                     auto_checkbox.setChecked(False)
#                     ax.set_ylim(min_val, max_val)
#
#             canvas.draw_idle()
#
#     def toggle_auto_scale(self, graph_type, axis, is_auto):
#         """Auto 체크박스 토글"""
#         if is_auto:
#             self.auto_scale(graph_type, axis)
#
#     def auto_scale(self, graph_type, axis):
#         """축 Auto Scale"""
#         ax = self.tab_waveax if graph_type == "waveform" else self.tab_ax
#         canvas = self.tab_wavecanvas if graph_type == "waveform" else self.tab_canvas
#
#         prefix = "waveform" if graph_type == "waveform" else "spectrum"
#
#         if axis == 'x':
#             auto_checkbox = getattr(self, f"tab_{prefix}_auto_x")
#             auto_checkbox.setChecked(True)
#             ax.autoscale(enable=True, axis='x')
#         else:
#             auto_checkbox = getattr(self, f"tab_{prefix}_auto_y")
#             auto_checkbox.setChecked(True)
#             ax.autoscale(enable=True, axis='y')
#
#         canvas.draw_idle()
#
#     def create_button_panel(self):
#         """하단 버튼 패널"""
#         panel = QtWidgets.QWidget()
#         layout = QtWidgets.QHBoxLayout(panel)
#         layout.setContentsMargins(0, 0, 0, 0)
#
#         self.tab_save_button = create_responsive_button("Data Extraction", 120, 35)
#         self.tab_save_button.clicked.connect(self.on_save_button_clicked)
#
#         self.tab_close_button = create_responsive_button("Close", 120, 35)
#         self.tab_close_button.clicked.connect(self.close_dialog)
#
#         layout.addWidget(self.tab_save_button)
#         layout.addWidget(self.tab_close_button)
#         layout.addStretch()
#
#         return panel
#
#     # ===== 파일 리스트 관리 =====
#     def populate_list_widget(self):
#         """채널별로 파일 리스트 표시"""
#         self.file_list_widget.clear()
#
#         for ch_num in range(1, 7):
#             ch_key = f"Ch{ch_num}"
#             files = self.channel_files.get(ch_key, [])
#
#             header_item = QtWidgets.QListWidgetItem(f"Ch{ch_num}")
#             header_item.setFlags(QtCore.Qt.ItemIsEnabled)
#             header_item.setBackground(QtCore.Qt.lightGray)
#             header_item.setForeground(QtCore.Qt.black)
#             font = header_item.font()
#             font.setBold(True)
#             header_item.setFont(font)
#             self.file_list_widget.addItem(header_item)
#
#             if files:
#                 for file in sorted(files):
#                     file_item = QtWidgets.QListWidgetItem(f"  {file}")
#                     file_item.setData(QtCore.Qt.UserRole, file)
#                     self.file_list_widget.addItem(file_item)
#             else:
#                 empty_item = QtWidgets.QListWidgetItem("  -")
#                 empty_item.setFlags(QtCore.Qt.ItemIsEnabled)
#                 empty_item.setForeground(QtCore.Qt.gray)
#                 self.file_list_widget.addItem(empty_item)
#
#     def adjust_left_panel_width(self):
#         """왼쪽 패널 너비 자동 조정"""
#         max_width = 0
#         font_metrics = QtGui.QFontMetrics(self.file_list_widget.font())
#
#         for i in range(self.file_list_widget.count()):
#             item = self.file_list_widget.item(i)
#             text_width = font_metrics.boundingRect(item.text()).width()
#             max_width = max(max_width, text_width)
#
#         scrollbar_width = self.file_list_widget.verticalScrollBar().sizeHint().width()
#         optimal_width = max_width + scrollbar_width + 42
#         final_width = max(250, min(optimal_width, 600))
#
#         self.left_panel.setMinimumWidth(final_width)
#         self.left_panel.setMaximumWidth(final_width)
#
#         total_width = self.width()
#         right_width = total_width - final_width - 20
#         self.splitter.setSizes([final_width, right_width])
#
#     def get_selected_files(self):
#         """선택된 파일 추출"""
#         selected_files = []
#         for item in self.file_list_widget.selectedItems():
#             file_name = item.data(QtCore.Qt.UserRole)
#             if file_name:
#                 selected_files.append(file_name)
#         return selected_files
#
#     def on_file_items_clicked(self):
#         """Plot 버튼"""
#         selected_files = self.get_selected_files()
#
#         if not selected_files:
#             QtWidgets.QMessageBox.warning(self, "경고", "파일을 선택하세요")
#             return
#
#         self.tab_waveax.clear()
#         self.tab_ax.clear()
#         self.color_cycle = itertools.cycle(plt.cm.tab10.colors)
#         self.data_dict = {}
#         self.spectrum_data_dict1 = {}
#
#         for file_name in selected_files:
#             self.load_and_plot_file(file_name)
#
#         self.finalize_plot()
#
#     def load_and_plot_file(self, file_name):
#         """파일 로드 (FileParser + FFTEngine)"""
#         if not self.directory_path:
#             return
#
#         file_path = os.path.join(self.directory_path, file_name)
#         if not os.path.exists(file_path):
#             return
#
#         try:
#             base_name = os.path.splitext(file_name)[0]
#
#             parser = FileParser(file_path)
#             if not parser.is_valid():
#                 return
#
#             data = parser.get_data()
#             sampling_rate = parser.get_sampling_rate()
#
#             if sampling_rate is None:
#                 return
#
#             # JSON fallback
#             json_folder = os.path.join(self.directory_path, "trend_data", "full")
#             json_path = os.path.join(json_folder, f"{base_name}_full.json")
#
#             import json
#             json_metadata = {}
#             if os.path.exists(json_path):
#                 try:
#                     with open(json_path, 'r') as f:
#                         json_metadata = json.load(f)
#                 except:
#                     pass
#
#             delta_f = json_metadata.get("delta_f", 1.0)
#             overlap = json_metadata.get("overlap", 50.0)
#             window_str = json_metadata.get("window", "hanning").lower()
#             view_type_str = json_metadata.get("view_type", "ACC").upper()
#
#             view_type_map = {"ACC": 1, "VEL": 2, "DIS": 3}
#             view_type = view_type_map.get(view_type_str, 1)
#
#             engine = FFTEngine(
#                 sampling_rate=sampling_rate,
#                 delta_f=delta_f,
#                 overlap=overlap,
#                 window_type=window_str
#             )
#
#             result = engine.compute(data=data, view_type=view_type, type_flag=2)
#             frequency = result['frequency']
#             spectrum = result['spectrum']
#
#             time = np.arange(len(data)) / sampling_rate
#             color = next(self.color_cycle)
#
#             self.tab_waveax.plot(time, data, label=base_name, color=color, linewidth=0.5, alpha=0.8)
#             self.tab_ax.plot(frequency, spectrum, label=base_name, color=color, linewidth=0.5, alpha=0.8)
#
#             self.data_dict[base_name] = (frequency, spectrum)
#             self.spectrum_data_dict1[base_name] = spectrum
#
#             view_labels = {
#                 1: "Vibration Acceleration\n(m/s², RMS)",
#                 2: "Vibration Velocity\n(mm/s, RMS)",
#                 3: "Vibration Displacement\n(μm, RMS)"
#             }
#             ylabel = view_labels.get(view_type, "Vibration (mm/s, RMS)")
#             self.tab_ax.set_ylabel(ylabel, fontsize=7)
#             self.tab_waveax.set_ylabel(ylabel, fontsize=7)
#
#         except Exception as e:
#             print(f"❌ {file_name} 로드 실패: {e}")
#
#     def finalize_plot(self):
#         """그래프 마무리"""
#         self.tab_waveax.set_title("Waveform", fontsize=7)
#         self.tab_waveax.set_xlabel("Time (s)", fontsize=7)
#         self.tab_waveax.legend(fontsize=7, loc='upper left', bbox_to_anchor=(1, 1))
#         self.tab_waveax.grid(True)
#         self.tab_waveax.tick_params(axis='both', labelsize=7)
#
#         self.tab_ax.set_title("Vibration Spectrum", fontsize=7)
#         self.tab_ax.set_xlabel("Frequency (Hz)", fontsize=7)
#         self.tab_ax.legend(fontsize=7, loc='upper left', bbox_to_anchor=(1, 1))
#         self.tab_ax.grid(True)
#         self.tab_ax.tick_params(axis='both', labelsize=7)
#
#         try:
#             self.tab_waveform_figure.tight_layout(rect=[0, 0, 0.88, 1])
#             self.tab_figure.tight_layout(rect=[0, 0, 0.88, 1])
#         except:
#             pass
#
#         self.tab_wavecanvas.draw_idle()
#         self.tab_canvas.draw_idle()
#
#         # Picking 기능 (Spectrum만)
#         self.hover_dot_spect = self.tab_ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
#         self.tab_canvas.mpl_connect("motion_notify_event", self.on_mouse_move_spect)
#         self.tab_canvas.mpl_connect("button_press_event", self.on_mouse_click_spect)
#         self.tab_canvas.mpl_connect("key_press_event", self.on_key_press_spect)
#
#     # ===== Picking 기능 (이전과 동일) =====
#     def on_mouse_move_spect(self, event):
#         if not self.mouse_tracking_enabled or not event.inaxes:
#             if self.hover_pos_spect[0] is not None:
#                 self.hover_dot_spect.set_data([], [])
#                 self.hover_pos_spect = [None, None]
#                 self.tab_canvas.draw_idle()
#             return
#
#         closest_x, closest_y, min_dist = None, None, np.inf
#         for line in self.tab_ax.get_lines():
#             x_data, y_data = line.get_xdata(), line.get_ydata()
#             if len(x_data) == 0 or len(y_data) == 0:
#                 continue
#             for x, y in zip(x_data, y_data):
#                 dist = np.hypot(event.xdata - x, event.ydata - y)
#                 if dist < min_dist:
#                     min_dist = dist
#                     closest_x, closest_y = x, y
#
#         if closest_x is not None:
#             self.hover_dot_spect.set_data([closest_x], [closest_y])
#             self.hover_pos_spect = [closest_x, closest_y]
#             self.tab_canvas.draw_idle()
#
#     def on_mouse_click_spect(self, event):
#         if not event.inaxes:
#             return
#         x, y = self.hover_dot_spect.get_data()
#         if event.button == 1 and x and y:
#             self.add_marker_spect(x[0], y[0])
#         elif event.button == 3:  # 우클릭: 마커 삭제
#             for marker, label in self.markers_spect:
#                 marker.remove()
#                 label.remove()
#             self.markers_spect.clear()
#             self.tab_canvas.draw_idle()
#
#     def on_key_press_spect(self, event):
#         x, y = self.hover_dot_spect.get_data()
#         if not x or not y:
#             return
#         all_x_data, all_y_data = [], []
#         for line in self.tab_ax.get_lines():
#             x_data, y_data = line.get_xdata(), line.get_ydata()
#             if len(x_data) > 0:
#                 all_x_data.extend(x_data)
#                 all_y_data.extend(y_data)
#         current_index = None
#         min_dist = np.inf
#         for idx, (x_val, y_val) in enumerate(zip(all_x_data, all_y_data)):
#             dist = np.hypot(x[0] - x_val, y[0] - y_val)
#             if dist < min_dist:
#                 min_dist = dist
#                 current_index = idx
#         if current_index is None:
#             return
#         candidates = []
#         if event.key == 'left':
#             candidates = [(i, abs(all_x_data[i] - x[0])) for i in range(len(all_x_data)) if all_x_data[i] < x[0]]
#         elif event.key == 'right':
#             candidates = [(i, abs(all_x_data[i] - x[0])) for i in range(len(all_x_data)) if all_x_data[i] > x[0]]
#         elif event.key == 'enter':
#             self.add_marker_spect(all_x_data[current_index], all_y_data[current_index])
#             return
#         if candidates:
#             candidates.sort(key=lambda t: t[1])
#             current_index = candidates[0][0]
#         new_x = all_x_data[current_index]
#         new_y = all_y_data[current_index]
#         self.hover_pos_spect = [new_x, new_y]
#         self.hover_dot_spect.set_data([new_x], [new_y])
#         self.tab_canvas.draw_idle()
#
#     def add_marker_spect(self, x, y):
#         min_distance = float('inf')
#         closest_file, closest_x, closest_y = None, None, None
#         for file_name, (data_x, data_y) in self.data_dict.items():
#             x_array = np.array(data_x)
#             y_array = np.array(data_y)
#             idx = (np.abs(x_array - x)).argmin()
#             x_val, y_val = x_array[idx], y_array[idx]
#             dist = np.hypot(x_val - x, y_val - y)
#             if dist < min_distance:
#                 min_distance = dist
#                 closest_file, closest_x, closest_y = file_name, x_val, y_val
#         if closest_file is not None:
#             marker = self.tab_ax.plot(closest_x, closest_y, marker='o', color='red', markersize=7)[0]
#             label = self.tab_ax.text(
#                 float(closest_x), float(closest_y) + 0.001,
#                 f"file: {closest_file}\nX: {float(closest_x):.4f}, Y: {float(closest_y):.4f}",
#                 fontsize=7, fontweight='bold', color='black', ha='center', va='bottom'
#             )
#             self.markers_spect.append((marker, label))
#             self.tab_canvas.draw_idle()
#
#     def on_save_button_clicked(self):
#         """CSV 저장"""
#         if not hasattr(self, 'spectrum_data_dict1') or not self.spectrum_data_dict1:
#             QtWidgets.QMessageBox.warning(self, "경고", "먼저 파일을 Plot 하세요")
#             return
#         save_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "CSV 파일 저장", "", "CSV Files (*.csv)")
#         if not save_path:
#             return
#         if not save_path.endswith(".csv"):
#             save_path += ".csv"
#         try:
#             with open(save_path, mode='w', newline='', encoding='utf-8') as file:
#                 writer = csv.writer(file)
#                 file_names = list(self.spectrum_data_dict1.keys())
#                 writer.writerow(["Frequency (Hz)", *file_names])
#                 first_file = file_names[0]
#                 frequencies = self.data_dict[first_file][0]
#                 for i, freq in enumerate(frequencies):
#                     row = [freq]
#                     for fname in file_names:
#                         spectrum = self.spectrum_data_dict1[fname]
#                         value = float(spectrum[i]) if i < len(spectrum) else ""
#                         row.append(value)
#                     writer.writerow(row)
#             QtWidgets.QMessageBox.information(self, "성공", f"저장 완료:\n{save_path}")
#         except Exception as e:
#             QtWidgets.QMessageBox.critical(self, "오류", f"저장 실패:\n{e}")
#
#     def close_dialog(self):
#         try:
#             plt.close(self.tab_waveform_figure)
#             plt.close(self.tab_figure)
#         except:
#             pass
#         if hasattr(self, 'data_dict'):
#             self.data_dict.clear()
#         if hasattr(self, 'spectrum_data_dict1'):
#             self.spectrum_data_dict1.clear()
#         self.deleteLater()
#         self.accept()
#
#     def closeEvent(self, event):
#         self.close_dialog()
#         event.accept()
#
#     def keyPressEvent(self, event):
#         if event.key() == QtCore.Qt.Key_Escape:
#             self.close_dialog()
#         else:
#             super().keyPressEvent(event)


class Ui_MainWindow(ResponsiveLayoutMixin):

    def update_waterfall_angle(self):
        """
        각도만 변경 (재계산 없음)
        Enter 키를 누르면 실행됨
        """
        if hasattr(self, 'waterfall_cache') and self.waterfall_cache.get('computed', False):
            print("🔄 각도 변경 중 (재계산 없음)...")

            # 캐시된 데이터로 다시 그리기
            self.plot_waterfall_spectrum(
                x_min=self.current_x_min if hasattr(self, 'current_x_min') else None,
                x_max=self.current_x_max if hasattr(self, 'current_x_max') else None,
                z_min=self.current_z_min if hasattr(self, 'current_z_min') else None,
                z_max=self.current_z_max if hasattr(self, 'current_z_max') else None,
                force_recalculate=False  # ← 캐시 사용
            )
        else:
            print("⚠️ 먼저 Waterfall을 생성해주세요")

    def setupUi(self, MainWindow):
        self.main_window = MainWindow

        self._optimization_initialized = False

        font = QtGui.QFont("Malgun Gothic", 9)
        MainWindow.setMinimumSize(1920, 1027)  # 최소 크기 설정
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setFont(font)  # 또는 MainWindow.setFont(font)
        MainWindow.setWindowIcon(QIcon("icon.ico"))
        MainWindow.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.centralwidget.setObjectName("centralwidget")

        # self.file_cache = {}
        # ✅ 새로운 코드 추가
        # self.thread_safe_cache = ThreadSafeCache(max_size=1000)
        # self.parallel_processor = ParallelProcessor(max_sizee_workers=6)  # ⭐ 병렬 프로세서

        # ✅ 새로운 코드 (자동 최적화)
        self.thread_safe_cache = ThreadSafeCache()  # 기본 max_size=2000
        self.parallel_processor = ParallelProcessor()  # 자동으로 최적 워커 수 설정

        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)

        self.tabWidget = QtWidgets.QTabWidget()
        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)

        # 탭 생성
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.tabWidget.addTab(self.tab, "탭 1")

        # 탭 안 레이아웃 설정
        self.tab_layout = QtWidgets.QVBoxLayout(self.tab)

        # 버튼 영역 (Select, Data 버튼)
        self.button_layout = QtWidgets.QHBoxLayout()
        self.Select_button = QtWidgets.QPushButton("Select")
        self.Data_button = QtWidgets.QPushButton("Load Data")
        self.Select_button.clicked.connect(self.select_directory)
        self.Data_button.clicked.connect(self.load_data)
        self.button_layout.addWidget(self.Select_button)
        self.button_layout.addWidget(self.Data_button)

        # 디렉토리 텍스트
        self.Directory = QtWidgets.QTextBrowser()
        self.Directory.setFixedHeight(50)  # 높이 제한은 가능
        self.Directory.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Choose 버튼
        self.Choose_button = QtWidgets.QPushButton("Choose")
        self.Choose_button.clicked.connect(self.on_choose_button_clicked)

        # 버튼 + 디렉토리 + Choose 버튼을 수평 정렬
        self.top_control_layout = QtWidgets.QHBoxLayout()
        self.top_control_layout.addLayout(self.button_layout)
        self.top_control_layout.addWidget(self.Directory)
        self.top_control_layout.addWidget(self.Choose_button)

        # 테이블
        self.Data_list = QtWidgets.QTableWidget()
        self.Data_list.setColumnCount(5)
        self.Data_list.setRowCount(0)
        self.Data_list.setHorizontalHeaderLabels(["Time (HH:MM)", "Files Merged", "", "", ""])
        self.Data_list.setColumnWidth(3, 1440)  # 200은 원하는 너비 값
        self.Data_list.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # 전체 구성
        self.tab_layout.addLayout(self.top_control_layout)
        self.tab_layout.addWidget(self.Data_list)
        # tab_layout: 상단은 고정, 하단 테이블은 확장
        self.tab_layout.setStretch(0, 0)
        self.tab_layout.setStretch(1, 1)

        # top_control_layout: 버튼은 고정, 디렉토리만 확장
        self.top_control_layout.setStretch(0, 0)  # Select & Load
        self.top_control_layout.setStretch(1, 1)  # Directory (확장됨)
        self.top_control_layout.setStretch(2, 0)  # Choose 버튼
        #Time/spectrumtab
        self.tab_3 = QtWidgets.QWidget()
        self.tabWidget.addTab(self.tab_3, "")
        self.tab_3.setObjectName("tab_3")

        self.tab3_layout = QtWidgets.QGridLayout(self.tab_3)

        self.button_layout2 = QtWidgets.QHBoxLayout()

        self.Querry_list = QtWidgets.QListWidget()
        self.Querry_list.setObjectName("Querry_list")
        self.Querry_list.itemClicked.connect(self.on_querry_list_item_clicked)
        self.Querry_list.setMinimumWidth(300)
        self.Querry_list.setMaximumWidth(300)
        self.Querry_list.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.Querry_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.select_all_btn = QtWidgets.QPushButton("Select All")
        self.select_all_btn.setObjectName("select_all_btn")
        self.select_all_btn.clicked.connect(self.select_all_items)

        self.deselect_all_btn = QtWidgets.QPushButton("Deselect All")
        self.deselect_all_btn.setObjectName("deselect_all_btn")
        self.deselect_all_btn.clicked.connect(self.deselect_all_items)
        self.button_layout2.addWidget(self.select_all_btn)
        self.button_layout2.addWidget(self.deselect_all_btn)

        self.checksBox = QtWidgets.QGridLayout()
        self.checkBox = QtWidgets.QCheckBox()
        self.checkBox.setObjectName("checkBox")
        self.checksBox.addWidget(self.checkBox, 0, 0)

        self.checkBox_2 = QtWidgets.QCheckBox()
        self.checkBox_2.setObjectName("checkBox_2")
        self.checksBox.addWidget(self.checkBox_2, 0, 1)

        self.checkBox_3 = QtWidgets.QCheckBox()
        self.checkBox_3.setObjectName("checkBox_3")
        self.checksBox.addWidget(self.checkBox_3, 0, 2)

        self.checkBox_4 = QtWidgets.QCheckBox()
        self.checkBox_4.setObjectName("checkBox_4")
        self.checksBox.addWidget(self.checkBox_4, 1, 0)

        self.checkBox_5 = QtWidgets.QCheckBox()
        self.checkBox_5.setObjectName("checkBox_5")
        self.checksBox.addWidget(self.checkBox_5, 1, 1)

        self.checkBox_6 = QtWidgets.QCheckBox()
        self.checkBox_6.setObjectName("checkBox_6")
        self.checksBox.addWidget(self.checkBox_6, 1, 2)

        self.lift_layout = QtWidgets.QGridLayout()
        self.lift_layout.addLayout(self.checksBox, 0, 0)
        self.lift_layout.addLayout(self.button_layout2, 1, 0)
        self.lift_layout.addWidget(self.Querry_list, 2, 0)
        self.tab3_layout.addLayout(self.lift_layout, 0, 0, 2, 1, alignment=QtCore.Qt.AlignTop)
        self.tab3_layout.setColumnStretch(1, 4)

        self.data_listlayout = QtWidgets.QGridLayout()
        self.Sample_rate = QtWidgets.QTextBrowser()
        self.Sample_rate.setObjectName("Sample_rate")
        self.Sample_rate.setMaximumSize(113, 27)
        self.data_listlayout.addWidget(self.Sample_rate, 0, 0)

        self.Duration = QtWidgets.QTextBrowser()
        self.Duration.setMaximumSize(113, 27)
        self.Duration.setObjectName("Duration")
        self.data_listlayout.addWidget(self.Duration, 1, 0)

        self.Rest_time = QtWidgets.QTextBrowser()
        self.Rest_time.setMaximumSize(113, 27)
        self.Rest_time.setObjectName("Rest_time")
        self.data_listlayout.addWidget(self.Rest_time, 2, 0)

        self.IEPE = QtWidgets.QTextBrowser()
        self.IEPE.setMaximumSize(113, 27)
        self.IEPE.setObjectName("IEPE")
        self.data_listlayout.addWidget(self.IEPE, 3, 0)

        self.Channel = QtWidgets.QTextBrowser()
        self.Channel.setMaximumSize(113, 27)
        self.Channel.setObjectName("Channel")
        self.data_listlayout.addWidget(self.Channel, 4, 0)

        self.Sensitivity = QtWidgets.QTextBrowser()
        self.Sensitivity.setMaximumSize(113, 27)
        self.Sensitivity.setObjectName("Sensitivity")
        self.data_listlayout.addWidget(self.Sensitivity, 5, 0)

        self.Sensitivity2 = QtWidgets.QTextBrowser()
        self.Sensitivity2.setMaximumSize(113, 27)
        self.Sensitivity2.setObjectName("Sensitivity_view")
        self.data_listlayout.addWidget(self.Sensitivity2, 6, 0)

        self.Sample_rate_view = QtWidgets.QTextBrowser()
        self.Sample_rate_view.setMaximumSize(113, 27)
        self.Sample_rate_view.setObjectName("Sample_rate_view")
        self.data_listlayout.addWidget(self.Sample_rate_view, 0, 1)

        self.Duration_view = QtWidgets.QTextBrowser()
        self.Duration_view.setMaximumSize(113, 27)
        self.Duration_view.setObjectName("Duration_view")
        self.data_listlayout.addWidget(self.Duration_view, 1, 1)

        self.Rest_time_view = QtWidgets.QTextBrowser()
        self.Rest_time_view.setMaximumSize(113, 27)
        self.Rest_time_view.setObjectName("Rest_time_view")
        self.data_listlayout.addWidget(self.Rest_time_view, 2, 1)

        self.Channel_view = QtWidgets.QTextBrowser()
        self.Channel_view.setMaximumSize(113, 27)
        self.Channel_view.setObjectName("Channel_view")
        self.data_listlayout.addWidget(self.Channel_view, 4, 1)

        self.IEPE_view = QtWidgets.QTextBrowser()
        self.IEPE_view.setMaximumSize(113, 27)
        self.IEPE_view.setObjectName("IEPE_view")
        self.data_listlayout.addWidget(self.IEPE_view, 3, 1)

        self.Sensitivity_view = QtWidgets.QTextBrowser()
        self.Sensitivity_view.setMaximumSize(113, 27)
        self.Sensitivity_view.setObjectName("Sensitivity_view")
        self.data_listlayout.addWidget(self.Sensitivity_view, 5, 1)

        self.Sensitivity_edit = QtWidgets.QLineEdit()
        self.Sensitivity_edit.setMaximumSize(113, 27)
        self.Sensitivity_edit.setObjectName("Sensitivity_view")
        self.Sensitivity_edit.setPlaceholderText("Edit Sensitivity")
        self.Sensitivity_edit.setStyleSheet("""background-color: lightgray;color: black;""")
        self.data_listlayout.addWidget(self.Sensitivity_edit, 6, 1)

        self.Sensitivity_edit.returnPressed.connect(self.save_Sensitivity)
        self.Sensitivity_edit.returnPressed.connect(self.update_filtered_files)

        self.data_listlayout.setContentsMargins(0, 0, 0, 0)
        self.data_listlayout.setSpacing(0)
        self.data_listlayout.setRowStretch(0, 1)
        self.data_listlayout.setRowStretch(1, 1)
        self.data_listlayout.setColumnStretch(0, 1)
        self.data_listlayout.setColumnStretch(1, 1)

        self.data_center_layout = QtWidgets.QGridLayout()
        self.data_center_layout.addLayout(self.data_listlayout, 0, 0)
        self.data_center_layout.setRowStretch(0, 0)
        self.data_center_layout.setContentsMargins(0, 0, 0, 0)
        self.data_center_layout.setSpacing(0)

        self.optin_layout = QtWidgets.QGridLayout()

        self.Plot_Options = QtWidgets.QTextBrowser()
        self.Plot_Options.setMaximumSize(136, 27)
        self.Plot_Options.setObjectName("FFT Option")
        self.optin_layout.addWidget(self.Plot_Options, 0, 0)

        # self.options_layout = QtWidgets.QGridLayout()
        self.textBrowser_15 = QtWidgets.QTextBrowser()
        self.textBrowser_15.setMaximumSize(136, 27)
        self.textBrowser_15.setObjectName("textBrowser_15")
        self.optin_layout.addWidget(self.textBrowser_15, 1, 0)

        self.Hz = QtWidgets.QTextEdit()
        self.Hz.setPlaceholderText("")
        self.Hz.setObjectName("Hz")
        self.Hz.setStyleSheet("""background-color: lightgray;color: black;""")
        self.Hz.setMaximumSize(136, 27)
        self.optin_layout.addWidget(self.Hz, 1, 1)

        self.textBrowser_16 = QtWidgets.QTextBrowser()
        self.textBrowser_16.setObjectName("textBrowser_16")
        self.textBrowser_16.setMaximumSize(136, 27)
        self.optin_layout.addWidget(self.textBrowser_16, 2, 0)

        self.Function = QtWidgets.QComboBox()
        self.Function.setObjectName("Function")
        self.Function.setStyleSheet("""background-color: lightgray;color: black;""")
        self.Function.addItem("Rectangular")
        self.Function.addItem("Hanning")
        self.Function.addItem("Flattop")

        self.Function.setMaximumSize(136, 27)
        self.optin_layout.addWidget(self.Function, 2, 1)

        self.textBrowser_17 = QtWidgets.QTextBrowser()
        self.textBrowser_17.setGeometry(QtCore.QRect(430, 10, 151, 31))
        self.textBrowser_17.setObjectName("textBrowser_17")
        self.textBrowser_17.setMaximumSize(136, 27)
        self.optin_layout.addWidget(self.textBrowser_17, 3, 0)

        self.Overlap_Factor = QtWidgets.QComboBox()
        self.Overlap_Factor.setGeometry(QtCore.QRect(590, 10, 111, 26))
        self.Overlap_Factor.setObjectName("Overlap_Factor")
        self.Overlap_Factor.setStyleSheet("""background-color: lightgray;color: black;""")
        self.Overlap_Factor.addItem("0%")
        self.Overlap_Factor.addItem("25%")
        self.Overlap_Factor.addItem("50%")
        self.Overlap_Factor.addItem("75%")
        self.Overlap_Factor.setMaximumSize(136, 27)
        self.optin_layout.addWidget(self.Overlap_Factor, 3, 1)

        self.select_type_convert = QtWidgets.QTextBrowser()
        self.select_type_convert.setObjectName("Convert")
        self.select_type_convert.setMaximumSize(136, 27)
        self.optin_layout.addWidget(self.select_type_convert, 4, 0)

        self.select_pytpe = QtWidgets.QComboBox()
        self.select_pytpe.setObjectName("select_pytpe")
        self.select_pytpe.setStyleSheet("""background-color: lightgray;color: black;""")
        self.select_pytpe.addItem("ACC", 1)  # "ACC" 표시, 내부 값은 1
        self.select_pytpe.addItem("VEL", 2)  # "VEL" 표시, 내부 값은 2
        self.select_pytpe.addItem("DIS", 3)  # "DIS" 표시, 내부 값은 3
        self.select_pytpe.setMaximumSize(136, 27)

        self.optin_layout.addWidget(self.select_pytpe, 4, 1)

        self.plot_button = QtWidgets.QPushButton("Plot")
        self.plot_button.setMaximumSize(136, 27)
        self.plot_button.clicked.connect(self.clear_marker)
        self.plot_button.clicked.connect(self.plot_signal_data)
        self.plot_button.clicked.connect(self.set_x_axis)
        self.plot_button.clicked.connect(self.set_y_axis)
        self.plot_button.clicked.connect(self.set_wave_x_axis)
        self.plot_button.clicked.connect(self.set_wave_y_axis)
        self.optin_layout.addWidget(self.plot_button, 5, 0)
        self.plot_button.setStyleSheet("""background-color: lightgray;color: black;""")

        self.next_button = QtWidgets.QPushButton("Next")
        self.next_button.setMaximumSize(136, 27)
        self.optin_layout.addWidget(self.next_button, 5, 1)
        self.next_button.setStyleSheet("""background-color: lightgray;color: black;""")
        self.next_button.clicked.connect(self.plot_next_file)
        self.next_button.clicked.connect(self.set_x_axis)
        self.next_button.clicked.connect(self.set_y_axis)
        self.next_button.clicked.connect(self.set_wave_x_axis)
        self.next_button.clicked.connect(self.set_wave_y_axis)
        # self.optin_layout.addLayout(self.options_layout, 1, 0, 1,1)

        self.optin_layout.setContentsMargins(0, 0, 0, 0)
        self.optin_layout.setSpacing(0)
        self.optin_layout.setRowStretch(0, 1)
        self.optin_layout.setRowStretch(1, 1)
        self.optin_layout.setColumnStretch(0, 1)
        self.optin_layout.setColumnStretch(1, 1)

        self.data_center_layout2 = QtWidgets.QGridLayout()
        self.data_center_layout2.addLayout(self.optin_layout, 0, 0)
        self.data_center_layout2.setRowStretch(0, 0)
        self.data_center_layout2.setContentsMargins(0, 0, 0, 0)
        self.data_center_layout2.setSpacing(0)

        # self.tab3_layout.addLayout(self.scale_layout, 1, 1, 1, 8,  alignment=QtCore.Qt.AlignLeft)
        self.checkBox.stateChanged.connect(self.update_filtered_files)
        self.checkBox_2.stateChanged.connect(self.update_filtered_files)
        self.checkBox_3.stateChanged.connect(self.update_filtered_files)
        self.checkBox_4.stateChanged.connect(self.update_filtered_files)
        self.checkBox_5.stateChanged.connect(self.update_filtered_files)
        self.checkBox_6.stateChanged.connect(self.update_filtered_files)

        self.data_center_allin = QtWidgets.QGridLayout()
        self.data_center_allin.addLayout(self.data_center_layout, 0, 0, alignment=QtCore.Qt.AlignTop)
        self.data_center_allin.addLayout(self.data_center_layout2, 0, 1, alignment=QtCore.Qt.AlignTop)
        # self.data_center_allin.setRowStretch(0, 0)
        self.data_center_allin.setContentsMargins(0, 0, 0, 0)
        self.data_center_allin.setSpacing(0)

        # ▶ Waveform 그래프
        # ✅ 수정 코드
        dpi = QtWidgets.QApplication.primaryScreen().logicalDotsPerInch()
        self.waveform_figure = Figure(figsize=(10, 4), dpi=dpi)
        self.waveform_figure.set_tight_layout({'rect': [0, 0, 0.88, 1]})  # 범례 공간 12%
        self.wavecanvas = FigureCanvas(self.waveform_figure)
        self.wavecanvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.waveax = self.waveform_figure.add_subplot(111)
        self.waveax.set_title("Waveform", fontsize=7, fontname='Malgun Gothic')
        self.wavecanvas.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.wavecanvas.setFocus()

        # ▶ Spectrum 그래프
        # ✅ 수정 코드
        dpi = QtWidgets.QApplication.primaryScreen().logicalDotsPerInch()
        self.figure = Figure(figsize=(10, 4), dpi=dpi)
        self.figure.set_tight_layout({'rect': [0, 0, 0.88, 1]})
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Vibration Spectrum", fontsize=7, fontname='Malgun Gothic')
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        self.canvas.setFocus()

        self.wave_scale_layout = QtWidgets.QVBoxLayout()
        self.wave_scale_layout.setContentsMargins(0, 20, 0, 20)
        self.wave_scale_layout.addStretch(2)

        self.wave_x_layout = QtWidgets.QHBoxLayout()
        self.wave_x_layout2 = QtWidgets.QHBoxLayout()
        self.wave_y_layout = QtWidgets.QHBoxLayout()
        self.wave_y_layout2 = QtWidgets.QHBoxLayout()

        self.wave_x_layout.addStretch()  # 왼쪽에 공간을 먼저 넣음
        self.wave_x_layout2.addStretch()  # 왼쪽에 공간을 먼저 넣음
        self.wave_y_layout.addStretch()  # 왼쪽에 공간을 먼저 넣음
        self.wave_y_layout2.addStretch()  # 왼쪽에 공간을 먼저 넣음
        # ✅ X축, Y축 Limit 설정 UI 추가
        self.auto_wave_x = QtWidgets.QCheckBox("Auto X")
        self.auto_wave_x.setChecked(True)  # 기본값 Auto
        self.wave_x_layout.addWidget(self.auto_wave_x)

        self.wave_x_autoscale = QtWidgets.QPushButton("Auto Scale")
        self.wave_x_autoscale.setMaximumSize(100, 31)
        self.wave_x_layout.addWidget(self.wave_x_autoscale)

        self.auto_wave_y = QtWidgets.QCheckBox("Auto Y")
        self.auto_wave_y.setChecked(True)
        self.wave_y_layout.addWidget(self.auto_wave_y)

        self.wave_y_autoscale = QtWidgets.QPushButton("Auto Scale")
        self.wave_y_autoscale.setMaximumSize(100, 31)
        self.wave_y_layout.addWidget(self.wave_y_autoscale)

        self.x_min_input = QtWidgets.QLineEdit()
        self.x_min_input.setPlaceholderText("X min")
        self.x_min_input.setMaximumSize(70, 31)
        self.x_min_input.setStyleSheet("""background-color: lightgray;color: black;""")
        self.wave_x_layout2.addWidget(self.x_min_input)

        self.x_max_input = QtWidgets.QLineEdit()
        self.x_max_input.setPlaceholderText("X max")
        self.x_max_input.setMaximumSize(70, 31)
        self.x_max_input.setStyleSheet("""background-color: lightgray;color: black;""")
        self.wave_x_layout2.addWidget(self.x_max_input)

        self.wave_x_set = QtWidgets.QPushButton("Set")
        self.wave_x_set.setMaximumSize(70, 31)
        self.wave_x_layout2.addWidget(self.wave_x_set)

        self.y_min_wave_input = QtWidgets.QLineEdit()
        self.y_min_wave_input.setPlaceholderText("Y min")
        self.y_min_wave_input.setMaximumSize(70, 31)
        self.y_min_wave_input.setStyleSheet("""background-color: lightgray;color: black;""")
        self.wave_y_layout2.addWidget(self.y_min_wave_input)

        self.y_max_wave_input = QtWidgets.QLineEdit()
        self.y_max_wave_input.setPlaceholderText("Y max")
        self.y_max_wave_input.setMaximumSize(70, 31)
        self.y_max_wave_input.setStyleSheet("""background-color: lightgray;color: black;""")
        self.wave_y_layout2.addWidget(self.y_max_wave_input)

        self.wave_y_set = QtWidgets.QPushButton("Set")
        self.wave_y_set.setMaximumSize(70, 31)
        self.wave_y_layout2.addWidget(self.wave_y_set)

        self.wave_x_set.clicked.connect(self.set_wave_x_axis)
        self.wave_y_set.clicked.connect(self.set_wave_y_axis)
        self.wave_x_autoscale.clicked.connect(self.auto_wave_scale_x)
        self.wave_y_autoscale.clicked.connect(self.auto_wave_scale_y)

        # self.wave_x_layout.addStretch()
        # self.wave_y_layout.addStretch()
        # self.wave_x_layout2.addStretch()
        # self.wave_y_layout2.addStretch()
        self.wave_scale_layout.addLayout(self.wave_x_layout)
        self.wave_scale_layout.addLayout(self.wave_x_layout2)
        self.wave_scale_layout.addLayout(self.wave_y_layout)
        self.wave_scale_layout.addLayout(self.wave_y_layout2)
        self.wave_scale_layout.addStretch(2)

        #spectrum
        self.spectrum_scale_layout = QtWidgets.QVBoxLayout()
        self.spectrum_scale_layout.setContentsMargins(0, 5, 0, 10)
        self.spectrum_scale_layout.addStretch(2)

        self.spectrum_x_layout = QtWidgets.QHBoxLayout()
        self.spectrum_x_layout2 = QtWidgets.QHBoxLayout()
        self.spectrum_y_layout = QtWidgets.QHBoxLayout()
        self.spectrum_y_layout2 = QtWidgets.QHBoxLayout()

        self.spectrum_x_layout.addStretch()
        self.spectrum_x_layout2.addStretch()
        self.spectrum_y_layout.addStretch()
        self.spectrum_y_layout2.addStretch()

        # ✅ X축, Y축 Limit 설정 UI 추가
        self.auto_spectrum_x = QtWidgets.QCheckBox("Auto X")
        self.auto_spectrum_x.setChecked(True)  # 기본값 Auto
        self.spectrum_x_layout.addWidget(self.auto_spectrum_x)

        self.spectrum_x_autoscale = QtWidgets.QPushButton("Auto Scale")
        self.spectrum_x_autoscale.setMaximumSize(100, 31)
        self.spectrum_x_layout.addWidget(self.spectrum_x_autoscale)

        self.auto_spectrum_y = QtWidgets.QCheckBox("Auto Y")
        self.auto_spectrum_y.setChecked(True)
        self.spectrum_y_layout.addWidget(self.auto_spectrum_y)

        self.spectrum_y_autoscale = QtWidgets.QPushButton("Auto Scale")
        self.spectrum_y_autoscale.setMaximumSize(100, 31)
        self.spectrum_y_layout.addWidget(self.spectrum_y_autoscale)

        self.spectrum_x_min_input = QtWidgets.QLineEdit()
        self.spectrum_x_min_input.setPlaceholderText("X min")
        self.spectrum_x_min_input.setMaximumSize(70, 31)
        self.spectrum_x_min_input.setStyleSheet("""background-color: lightgray;color: black;""")
        self.spectrum_x_layout2.addWidget(self.spectrum_x_min_input)

        self.spectrum_x_max_input = QtWidgets.QLineEdit()
        self.spectrum_x_max_input.setPlaceholderText("X max")
        self.spectrum_x_max_input.setMaximumSize(70, 31)
        self.spectrum_x_max_input.setStyleSheet("""background-color: lightgray;color: black;""")
        self.spectrum_x_layout2.addWidget(self.spectrum_x_max_input)

        self.spectrum_x_set = QtWidgets.QPushButton("Set")
        self.spectrum_x_set.setMaximumSize(70, 31)
        self.spectrum_x_layout2.addWidget(self.spectrum_x_set)

        self.spectrum_y_min_input = QtWidgets.QLineEdit()
        self.spectrum_y_min_input.setPlaceholderText("Y min")
        self.spectrum_y_min_input.setMaximumSize(70, 31)
        self.spectrum_y_min_input.setStyleSheet("""background-color: lightgray;color: black;""")
        self.spectrum_y_layout2.addWidget(self.spectrum_y_min_input)

        self.spectrum_y_max_input = QtWidgets.QLineEdit()
        self.spectrum_y_max_input.setPlaceholderText("Y max")
        self.spectrum_y_max_input.setMaximumSize(70, 31)
        self.spectrum_y_max_input.setStyleSheet("""background-color: lightgray;color: black;""")
        self.spectrum_y_layout2.addWidget(self.spectrum_y_max_input)

        self.spectrum_y_set = QtWidgets.QPushButton("Set")
        self.spectrum_y_set.setMaximumSize(70, 31)
        self.spectrum_y_layout2.addWidget(self.spectrum_y_set)

        self.spectrum_x_set.clicked.connect(self.set_x_axis)
        self.spectrum_y_set.clicked.connect(self.set_y_axis)
        self.spectrum_x_autoscale.clicked.connect(self.auto_scale_x)
        self.spectrum_y_autoscale.clicked.connect(self.auto_scale_y)

        self.save_button = QtWidgets.QPushButton("Data Extraction")
        # self.save_button.setGeometry(QtCore.QRect(1750, 205, 80, 30))
        self.save_button.clicked.connect(self.on_save_button_clicked)

        self.spectrum_scale_layout.addLayout(self.spectrum_x_layout)
        self.spectrum_scale_layout.addLayout(self.spectrum_x_layout2)
        self.spectrum_scale_layout.addLayout(self.spectrum_y_layout)
        self.spectrum_scale_layout.addLayout(self.spectrum_y_layout2)
        self.spectrum_scale_layout.addWidget(self.save_button)
        self.spectrum_scale_layout.addStretch(2)
        self.scale_spectrum_widget = QtWidgets.QWidget()
        self.scale_spectrum_widget.setLayout(self.spectrum_scale_layout)

        self.wave_scale_widget = QtWidgets.QWidget()
        self.wave_scale_widget.setLayout(self.wave_scale_layout)

        # # 그래프를 표시할 수직 Splitter 생성
        # self.graph_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        # self.graph_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 수평 Splitter - Wave
        self.wave_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.wave_splitter.addWidget(self.wavecanvas)
        self.wave_splitter.addWidget(self.wave_scale_widget)

        # 수평 Splitter - Spec
        self.spec_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.spec_splitter.addWidget(self.canvas)
        self.spec_splitter.addWidget(self.scale_spectrum_widget)

        # 수직 Splitter - 상단: Wave / 하단: Spec
        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.main_splitter.addWidget(self.wave_splitter)
        self.main_splitter.addWidget(self.spec_splitter)

        self.tab3_layout.addWidget(self.main_splitter, 1, 1, 1, 9)

        # Stretch 비율 조정 (선택사항)
        self.main_splitter.setStretchFactor(0, 1)  # wave 영역
        self.main_splitter.setStretchFactor(1, 1)  # spec 영역

        self.wave_splitter.setStretchFactor(0, 5)  # wave canvas
        self.wave_splitter.setStretchFactor(1, 1)  # wave scale

        self.spec_splitter.setStretchFactor(0, 5)  # spec canvas
        self.spec_splitter.setStretchFactor(1, 1)  # spec scale

        self.tab3_layout.addLayout(self.data_center_allin, 0, 1, alignment=QtCore.Qt.AlignTop)
        # self.tab3_layout.addLayout(self.data_center_layout2, 0,  2,   alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        # self.tab3_layout.setRowStretch(1, 1)  # 그래프 splitter가 포함된 줄
        # ▶ tab3_layout에 splitter 추가 (GridLayout 기준 위치는 조절 가능)

        #trendtab
        self.tab_4 = QtWidgets.QWidget()
        self.tabWidget.addTab(self.tab_4, "")
        self.tab_4.setObjectName("tab_4")

        self.tab4_layout = QtWidgets.QGridLayout(self.tab_4)

        self.alloption_layout = QtWidgets.QGridLayout()
        self.Plot_Options_3 = QtWidgets.QTextBrowser()
        self.Plot_Options_3.setMaximumSize(129, 27)
        self.Plot_Options_3.setObjectName("Plot_Options_3")
        self.alloption_layout.addWidget(self.Plot_Options_3, 0, 0)

        self.option1_layout = QtWidgets.QGridLayout()

        self.textBrowser_30 = QtWidgets.QTextBrowser()
        self.textBrowser_30.setObjectName("textBrowser_18")
        self.textBrowser_30.setMaximumSize(129, 27)
        self.option1_layout.addWidget(self.textBrowser_30, 0, 0)

        self.Hz_3 = QtWidgets.QTextEdit()
        self.Hz_3.setPlaceholderText("Hz")
        self.Hz_3.setObjectName("Hz_2")
        self.Hz_3.setStyleSheet("""background-color: lightgray;color: black;""")
        self.Hz_3.setMaximumSize(129, 27)
        self.option1_layout.addWidget(self.Hz_3, 0, 1)

        self.textBrowser_31 = QtWidgets.QTextBrowser()
        self.textBrowser_31.setObjectName("textBrowser_19")
        self.textBrowser_31.setMaximumSize(129, 27)
        self.option1_layout.addWidget(self.textBrowser_31, 1, 0)

        self.Function_3 = QtWidgets.QComboBox()
        self.Function_3.setObjectName("Function_3")
        self.Function_3.setMaximumSize(129, 27)
        self.Function_3.setStyleSheet("""background-color: lightgray;color: black;""")
        self.option1_layout.addWidget(self.Function_3, 1, 1)

        self.Function_3.addItem("")
        self.Function_3.addItem("")
        self.Function_3.addItem("")

        self.plot_button = QtWidgets.QPushButton("Calculation && Plot")
        self.plot_button.setMaximumSize(129, 27)
        self.plot_button.setStyleSheet("""background-color: lightgray;color: black;""")
        self.plot_button.clicked.connect(self.delite)
        self.plot_button.clicked.connect(self.plot_trend)
        self.option1_layout.addWidget(self.plot_button, 1, 2)

        self.textBrowser_32 = QtWidgets.QTextBrowser()
        self.textBrowser_32.setObjectName("textBrowser_20")
        self.textBrowser_32.setMaximumSize(129, 27)
        self.option1_layout.addWidget(self.textBrowser_32, 2, 0)

        self.Overlap_Factor_3 = QtWidgets.QComboBox()
        self.Overlap_Factor_3.setObjectName("Overlap_Factor_2")
        self.Overlap_Factor_3.setMaximumSize(129, 27)
        self.Overlap_Factor_3.setStyleSheet("""background-color: lightgray;color: black;""")
        self.option1_layout.addWidget(self.Overlap_Factor_3, 2, 1)

        self.Overlap_Factor_3.addItem("0%")
        self.Overlap_Factor_3.addItem("25%")
        self.Overlap_Factor_3.addItem("50%")
        self.Overlap_Factor_3.addItem("75%")

        self.call_button = QtWidgets.QPushButton("Load Data && Plot")
        self.call_button.setMaximumSize(129, 27)
        self.call_button.setStyleSheet("""background-color: lightgray;color: black;""")
        self.call_button.clicked.connect(self.delite)
        self.call_button.clicked.connect(self.load_trend_data_and_plot)
        self.option1_layout.addWidget(self.call_button, 2, 2)

        self.select_type_convert3 = QtWidgets.QTextBrowser()
        self.select_type_convert3.setObjectName("Convert")
        self.select_type_convert3.setMaximumSize(129, 27)
        self.option1_layout.addWidget(self.select_type_convert3, 3, 0)

        self.select_pytpe3 = QtWidgets.QComboBox()
        self.select_pytpe3.setObjectName("select_pytpe")
        self.select_pytpe3.setMaximumSize(129, 27)
        self.select_pytpe3.setStyleSheet("""background-color: lightgray;color: black;""")
        self.select_pytpe3.addItem("ACC", 1)  # "ACC" 표시, 내부 값은 1
        self.select_pytpe3.addItem("VEL", 2)  # "VEL" 표시, 내부 값은 2
        self.select_pytpe3.addItem("DIS", 3)  # "DIS" 표시, 내부 값은 3
        self.option1_layout.addWidget(self.select_pytpe3, 3, 1)

        self.save_button = QtWidgets.QPushButton("Data Extraction")
        self.save_button.setMaximumSize(129, 27)
        self.save_button.setStyleSheet("""background-color: lightgray;color: black;""")
        self.save_button.clicked.connect(self.on_save_button_clicked2)
        self.option1_layout.addWidget(self.save_button, 3, 2)

        self.freq_range_label = QtWidgets.QTextBrowser()
        self.freq_range_label.setObjectName("Band Limit (Hz):")
        self.freq_range_label.setMaximumSize(129, 27)
        self.freq_range_label.setObjectName("freq_range_label")
        self.option1_layout.addWidget(self.freq_range_label, 4, 0)

        self.freq_range_inputmin = QtWidgets.QLineEdit("")
        self.freq_range_inputmin.setMaximumSize(129, 27)
        self.freq_range_inputmin.setPlaceholderText("MIN")
        self.freq_range_inputmin.setStyleSheet("""background-color: lightgray;color: black;""")
        self.freq_range_inputmin.setObjectName("freq_range_inputmin")
        self.option1_layout.addWidget(self.freq_range_inputmin, 4, 1)

        self.freq_range_inputmax = QtWidgets.QLineEdit("")
        self.freq_range_inputmax.setMaximumSize(129, 27)
        self.freq_range_inputmax.setPlaceholderText("MAX")
        self.freq_range_inputmax.setStyleSheet("""background-color: lightgray;color: black;""")
        self.freq_range_inputmax.setObjectName("freq_range_inputmax")
        self.option1_layout.addWidget(self.freq_range_inputmax, 4, 2)

        self.option1_layout.setContentsMargins(0, 0, 0, 0)
        self.option1_layout.setSpacing(0)
        self.option1_layout.setRowStretch(0, 1)
        self.option1_layout.setRowStretch(1, 1)
        self.option1_layout.setColumnStretch(0, 1)
        self.option1_layout.setColumnStretch(1, 1)

        self.alloption_layout.addLayout(self.option1_layout, 1, 0, )
        self.alloption_layout.setSpacing(0)
        self.alloption_layout.setRowStretch(0, 0)
        self.alloption_layout.setContentsMargins(0, 0, 0, 0)
        self.tab4_layout.addLayout(self.alloption_layout, 0, 1, alignment=QtCore.Qt.AlignLeft)  # 왼쪽 옵션 레이아웃 추가

        self.data_layout = QtWidgets.QGridLayout()

        self.buttonall_layout = QtWidgets.QHBoxLayout()

        self.select_all_btn3 = QtWidgets.QPushButton("Select All")
        # self.select_all_btn3.setGeometry(QtCore.QRect(10, 150, 100, 30))
        self.select_all_btn3.setObjectName("select_all_btn")
        self.select_all_btn3.clicked.connect(self.select_all_items3)
        self.buttonall_layout.addWidget(self.select_all_btn3)

        self.deselect_all_btn3 = QtWidgets.QPushButton("Deselect All")
        # self.deselect_all_btn3.setGeometry(QtCore.QRect(110, 150, 100, 30))
        self.deselect_all_btn3.setObjectName("deselect_all_btn")
        self.deselect_all_btn3.clicked.connect(self.deselect_all_items3)
        self.buttonall_layout.addWidget(self.deselect_all_btn3)

        self.Querry_list3 = QtWidgets.QListWidget()
        self.Querry_list3.setObjectName("Querry_list2")
        self.Querry_list3.setMinimumWidth(300)
        self.Querry_list3.setMaximumWidth(300)
        self.Querry_list3.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.Querry_list3.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.checksBox2 = QtWidgets.QGridLayout()

        self.checkBox_13 = QtWidgets.QCheckBox()
        self.checkBox_13.setObjectName("checkBox_7")
        self.checksBox2.addWidget(self.checkBox_13, 0, 0)

        self.checkBox_14 = QtWidgets.QCheckBox()
        self.checkBox_14.setObjectName("checkBox_8")
        self.checksBox2.addWidget(self.checkBox_14, 0, 1)

        self.checkBox_15 = QtWidgets.QCheckBox()
        self.checkBox_15.setObjectName("checkBox_9")
        self.checksBox2.addWidget(self.checkBox_15, 0, 2)

        self.checkBox_16 = QtWidgets.QCheckBox()
        self.checkBox_16.setObjectName("checkBox_10")
        self.checksBox2.addWidget(self.checkBox_16, 1, 0)

        self.checkBox_17 = QtWidgets.QCheckBox()
        self.checkBox_17.setObjectName("checkBox_11")
        self.checksBox2.addWidget(self.checkBox_17, 1, 1)

        self.checkBox_18 = QtWidgets.QCheckBox()
        self.checkBox_18.setObjectName("checkBox_12")
        self.checksBox2.addWidget(self.checkBox_18, 1, 2)

        self.data_layout.addLayout(self.checksBox2, 0, 0)
        self.data_layout.addLayout(self.buttonall_layout, 1, 0)
        self.data_layout.addWidget(self.Querry_list3, 2, 0)
        self.tab4_layout.addLayout(self.data_layout, 0, 0, 2, 1, alignment=QtCore.Qt.AlignTop)  # 왼쪽 콘텐츠 레이아웃 추가
        self.tab4_layout.setColumnStretch(1, 4)  # 왼쪽 콘텐츠용

        self.trend_section_layout = QtWidgets.QHBoxLayout()

        # ✅ trend 그래프를 표시할 위젯 추가
        self.trend_graph_layout = QtWidgets.QVBoxLayout()

        # trend 생성
        # ✅ 수정 코드
        dpi = QtWidgets.QApplication.primaryScreen().logicalDotsPerInch()
        self.trend_figure = Figure(figsize=(10, 4), dpi=dpi)
        self.trend_figure.set_tight_layout({'rect': [0, 0, 0.88, 1]})
        self.trend_canvas = FigureCanvas(self.trend_figure)
        self.trend_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.trend_ax = self.trend_figure.add_subplot(111)
        # FigureCanvas를 생성하여 trend 그래프 위젯에 추가

        self.trend_canvas.setFocusPolicy(Qt.ClickFocus)
        self.trend_canvas.setFocus()

        self.trend_graph_layout.addWidget(self.trend_canvas)

        # trend 그래프를 그릴 Axes 생성
        self.trend_ax.set_title("Overall RMS Trend", fontsize=7, fontname='Malgun Gothic')

        self.data_list_layout = QtWidgets.QVBoxLayout()

        self.data_list_label = QtWidgets.QTextBrowser()
        self.data_list_label.setObjectName("Pick Data List")
        self.data_list_label.setMaximumSize(175, 31)
        self.data_list_label.setObjectName("data_list_label")

        self.data_list_text = QtWidgets.QTextEdit()
        self.data_list_text.setMaximumSize(175, 900)
        self.data_list_text.setReadOnly(True)

        # 채널 헤더만 미리 입력해 둡니다
        initial_text = "\n".join(["Ch1", "-", "Ch2", "-", "Ch3", "-", "Ch4", "-", "Ch5", "-", "Ch6", "-"])
        self.data_list_text.setText(initial_text)
        self.data_list_save_btn = QtWidgets.QPushButton("List Save")
        self.data_list_save_btn.setMaximumSize(175, 31)
        self.data_list_save_btn.clicked.connect(self.on_list_save_btn_clicked)
        self.data_list_layout.addWidget(self.data_list_label, 1)
        self.data_list_layout.addWidget(self.data_list_text, 2)
        self.data_list_layout.addWidget(self.data_list_save_btn, 1)
        self.trend_section_layout.addLayout(self.trend_graph_layout, 3)  # 왼쪽: 리스트
        self.trend_section_layout.addLayout(self.data_list_layout, 1)  # 오른쪽: 그래프
        self.tab4_layout.addLayout(self.trend_section_layout, 1, 1, 1, 8, alignment=QtCore.Qt.AlignLeft)

        #banpeaktab
        self.tab_5 = QtWidgets.QWidget()
        self.tabWidget.addTab(self.tab_5, "")
        self.tab_5.setObjectName("tab_5")
        self.tab5_layout = QtWidgets.QGridLayout(self.tab_5)
        self.alloption2_layout = QtWidgets.QGridLayout()
        self.Plot_Options_4 = QtWidgets.QTextBrowser()
        self.Plot_Options_4.setMaximumSize(129, 27)
        self.Plot_Options_4.setObjectName("Plot_Options_4")
        self.alloption2_layout.addWidget(self.Plot_Options_4, 0, 0)
        self.option2_layout = QtWidgets.QGridLayout()
        self.textBrowser_33 = QtWidgets.QTextBrowser()
        self.textBrowser_33.setMaximumSize(129, 27)
        self.textBrowser_33.setObjectName("textBrowser_18")
        self.option2_layout.addWidget(self.textBrowser_33, 0, 0)

        self.Hz_4 = QtWidgets.QTextEdit()
        self.Hz_4.setMaximumSize(129, 27)
        self.Hz_4.setPlaceholderText("Hz")
        self.Hz_4.setObjectName("Hz_2")
        self.Hz_4.setStyleSheet("""background-color: lightgray;color: black;""")
        self.option2_layout.addWidget(self.Hz_4, 0, 1)

        self.textBrowser_34 = QtWidgets.QTextBrowser()
        self.textBrowser_34.setMaximumSize(129, 27)
        self.textBrowser_34.setObjectName("textBrowser_19")
        self.option2_layout.addWidget(self.textBrowser_34, 1, 0)

        self.Function_4 = QtWidgets.QComboBox()
        self.Function_4.setMaximumSize(129, 27)
        self.Function_4.setObjectName("Function_3")
        self.Function_4.setStyleSheet("""background-color: lightgray;color: black;""")
        self.option2_layout.addWidget(self.Function_4, 1, 1)

        self.Function_4.addItem("")
        self.Function_4.addItem("")
        self.Function_4.addItem("")

        self.textBrowser_35 = QtWidgets.QTextBrowser()
        self.textBrowser_35.setMaximumSize(129, 27)
        self.textBrowser_35.setObjectName("textBrowser_20")
        self.option2_layout.addWidget(self.textBrowser_35, 2, 0)

        self.Overlap_Factor_4 = QtWidgets.QComboBox()
        self.Overlap_Factor_4.setMaximumSize(129, 27)
        self.Overlap_Factor_4.setStyleSheet("""background-color: lightgray;color: black;""")
        self.Overlap_Factor_4.setObjectName("Overlap_Factor_2")
        self.option2_layout.addWidget(self.Overlap_Factor_4, 2, 1)

        self.Overlap_Factor_4.addItem("0%")
        self.Overlap_Factor_4.addItem("25%")
        self.Overlap_Factor_4.addItem("50%")
        self.Overlap_Factor_4.addItem("75%")
        # Plot Button
        self.plot_button2 = QtWidgets.QPushButton("Plot")
        self.plot_button2.setMaximumSize(129, 27)
        self.plot_button2.setStyleSheet("""background-color: lightgray;color: black;""")
        self.plot_button2.clicked.connect(self.plot_peak)
        self.option2_layout.addWidget(self.plot_button2, 2, 2)

        self.select_type_convert4 = QtWidgets.QTextBrowser()
        self.select_type_convert4.setObjectName("Convert")
        self.select_type_convert4.setMaximumSize(129, 27)
        self.option2_layout.addWidget(self.select_type_convert4, 3, 0)

        self.select_pytpe4 = QtWidgets.QComboBox()
        self.select_pytpe4.setObjectName("select_pytpe")
        self.select_pytpe4.setMaximumSize(129, 27)
        self.select_pytpe4.setStyleSheet("""background-color: lightgray;color: black;""")
        self.select_pytpe4.addItem("ACC", 1)  # "ACC" 표시, 내부 값은 1
        self.select_pytpe4.addItem("VEL", 2)  # "VEL" 표시, 내부 값은 2
        self.select_pytpe4.addItem("DIS", 3)  # "DIS" 표시, 내부 값은 3
        self.option2_layout.addWidget(self.select_pytpe4, 3, 1)

        # save_button
        self.save2_button = QtWidgets.QPushButton("Save")
        self.save2_button.setMaximumSize(129, 27)
        self.save2_button.setStyleSheet("""background-color: lightgray;color: black;""")
        self.save2_button.clicked.connect(self.on_save_button_clicked3)
        self.option2_layout.addWidget(self.save2_button, 3, 2)

        self.freq_range_label2 = QtWidgets.QTextBrowser()
        self.freq_range_label2.setMaximumSize(129, 27)
        self.freq_range_label2.setObjectName("Band Limit (Hz):")
        self.option2_layout.addWidget(self.freq_range_label2, 4, 0)

        self.freq_range_inputmin2 = QtWidgets.QLineEdit("")
        self.freq_range_inputmin2.setMaximumSize(129, 27)
        self.freq_range_inputmin2.setPlaceholderText("MIN")
        self.freq_range_inputmin2.setStyleSheet("""background-color: lightgray;color: black;""")
        self.freq_range_inputmin2.setObjectName("freq_range_inputmin")
        self.option2_layout.addWidget(self.freq_range_inputmin2, 4, 1)

        self.freq_range_inputmax2 = QtWidgets.QLineEdit("")
        self.freq_range_inputmax2.setMaximumSize(129, 27)
        self.freq_range_inputmax2.setPlaceholderText("MAX")
        self.freq_range_inputmax2.setStyleSheet("""background-color: lightgray;color: black;""")
        self.freq_range_inputmax2.setObjectName("freq_range_inputmax")
        self.option2_layout.addWidget(self.freq_range_inputmax2, 4, 2)

        self.alloption2_layout.addLayout(self.option2_layout, 1, 0, 1, 1)
        self.alloption2_layout.setSpacing(0)

        self.tab5_layout.addLayout(self.alloption2_layout, 0, 1, 1, 1, alignment=QtCore.Qt.AlignLeft)
        self.tab5_layout.setColumnStretch(1, 4)  # 왼쪽 콘텐츠용

        self.data2_layout = QtWidgets.QVBoxLayout()

        self.buttonall2_layout = QtWidgets.QHBoxLayout()

        self.select_all_btn4 = QtWidgets.QPushButton("Select All")
        self.select_all_btn4.setGeometry(QtCore.QRect(10, 150, 100, 30))
        self.select_all_btn4.setObjectName("select_all_btn")
        self.select_all_btn4.clicked.connect(self.select_all_items4)
        self.buttonall2_layout.addWidget(self.select_all_btn4)

        self.deselect_all_btn4 = QtWidgets.QPushButton("Deselect All")
        self.deselect_all_btn4.setGeometry(QtCore.QRect(110, 150, 100, 30))
        self.deselect_all_btn4.setObjectName("deselect_all_btn")
        self.deselect_all_btn4.clicked.connect(self.deselect_all_items4)
        self.buttonall2_layout.addWidget(self.deselect_all_btn4)

        self.Querry_list4 = QtWidgets.QListWidget()
        self.Querry_list4.setMinimumWidth(360)
        self.Querry_list4.setObjectName("Querry_list4")
        self.Querry_list4.setMinimumWidth(300)
        self.Querry_list4.setMaximumWidth(300)
        # Querry_list3 다중 선택 가능하도록 설정 추가

        self.Querry_list4.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.Querry_list4.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.checksBox3 = QtWidgets.QGridLayout()

        self.checkBox_19 = QtWidgets.QCheckBox()
        self.checkBox_19.setObjectName("checkBox_7")
        self.checksBox3.addWidget(self.checkBox_19, 0, 0)

        self.checkBox_20 = QtWidgets.QCheckBox()
        self.checkBox_20.setObjectName("checkBox_8")
        self.checksBox3.addWidget(self.checkBox_20, 0, 1)

        self.checkBox_21 = QtWidgets.QCheckBox()
        self.checkBox_21.setObjectName("checkBox_9")
        self.checksBox3.addWidget(self.checkBox_21, 0, 2)

        self.checkBox_22 = QtWidgets.QCheckBox()
        self.checkBox_22.setObjectName("checkBox_10")
        self.checksBox3.addWidget(self.checkBox_22, 1, 0)

        self.checkBox_23 = QtWidgets.QCheckBox()
        self.checkBox_23.setObjectName("checkBox_11")
        self.checksBox3.addWidget(self.checkBox_23, 1, 1)

        self.checkBox_24 = QtWidgets.QCheckBox()
        self.checkBox_24.setObjectName("checkBox_12")
        self.checksBox3.addWidget(self.checkBox_24, 1, 2)

        self.data2_layout.addLayout(self.checksBox3)
        self.data2_layout.addLayout(self.buttonall2_layout)
        self.data2_layout.addWidget(self.Querry_list4)
        self.tab5_layout.addLayout(self.data2_layout, 0, 0, 2, 1)
        self.tab5_layout.setColumnStretch(1, 4)  # 왼쪽 콘텐츠용

        self.peak_graph_layout = QtWidgets.QVBoxLayout()

        # peak 생성
        # ✅ 수정 코드
        dpi = QtWidgets.QApplication.primaryScreen().logicalDotsPerInch()
        self.peak_figure = Figure(figsize=(10, 4), dpi=dpi)
        self.peak_figure.set_tight_layout({'rect': [0, 0, 0.88, 1]})
        self.peak_canvas = FigureCanvas(self.peak_figure)
        self.peak_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.peak_ax = self.peak_figure.add_subplot(111)

        self.peak_graph_layout.addWidget(self.peak_canvas)

        self.peak_canvas.setFocusPolicy(Qt.ClickFocus)
        self.peak_canvas.setFocus()

        # peak 그래프를 그릴 Axes 생성
        self.peak_ax.set_title("Band Peak Trend", fontsize=7, fontname='Malgun Gothic')

        self.tab5_layout.addLayout(self.peak_graph_layout, 1, 1, 1, 3, alignment=QtCore.Qt.AlignLeft)  # 그래프 위젯 추가

        #Waterfalltab

        # ⭐ Waterfall 캐시 변수 추가
        self.waterfall_cache = {
            'computed': False,
            'frequency': None,
            'spectra': [],  # [(file_name, f, P, timestamp), ...]
            'params': {}  # delta_f, overlap, window_type 저장
        }


        self.tab_2 = QtWidgets.QWidget()
        self.tabWidget.addTab(self.tab_2, "")
        self.tab_2.setObjectName("tab_2")

        self.tab2_layout = QtWidgets.QGridLayout(self.tab_2)

        self.button2_leftlayout = QtWidgets.QHBoxLayout()

        self.select_all_btn2 = QtWidgets.QPushButton("Select All")
        self.select_all_btn2.setGeometry(QtCore.QRect(10, 150, 100, 30))
        self.select_all_btn2.setObjectName("select_all_btn")
        self.select_all_btn2.clicked.connect(self.select_all_items2)

        self.deselect_all_btn2 = QtWidgets.QPushButton("Deselect All")
        self.deselect_all_btn2.setGeometry(QtCore.QRect(110, 150, 100, 30))
        self.deselect_all_btn2.setObjectName("deselect_all_btn")
        self.deselect_all_btn2.clicked.connect(self.deselect_all_items2)
        self.button2_leftlayout.addWidget(self.select_all_btn2)
        self.button2_leftlayout.addWidget(self.deselect_all_btn2)

        self.Qurry_layout2 = QtWidgets.QHBoxLayout()
        self.Querry_list2 = QtWidgets.QListWidget()
        self.Querry_list2.setObjectName("Querry_list2")
        self.Querry_list2.setMinimumWidth(300)
        self.Querry_list2.setMaximumWidth(300)
        self.Querry_list2.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.Querry_list2.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.Qurry_layout2.addWidget(self.Querry_list2)

        self.checkboxs_layout = QtWidgets.QGridLayout()

        self.checkBox_7 = QtWidgets.QCheckBox()
        self.checkBox_7.setObjectName("checkBox_7")
        self.checkboxs_layout.addWidget(self.checkBox_7, 0, 0)

        self.checkBox_8 = QtWidgets.QCheckBox()
        self.checkBox_8.setObjectName("checkBox_8")
        self.checkboxs_layout.addWidget(self.checkBox_8, 0, 1)

        self.checkBox_9 = QtWidgets.QCheckBox()
        self.checkBox_9.setObjectName("checkBox_9")
        self.checkboxs_layout.addWidget(self.checkBox_9, 0, 2)

        self.checkBox_10 = QtWidgets.QCheckBox()
        self.checkBox_10.setObjectName("checkBox_10")
        self.checkboxs_layout.addWidget(self.checkBox_10, 1, 0)

        self.checkBox_11 = QtWidgets.QCheckBox()
        self.checkBox_11.setObjectName("checkBox_11")
        self.checkboxs_layout.addWidget(self.checkBox_11, 1, 1)

        self.checkBox_12 = QtWidgets.QCheckBox()
        self.checkBox_12.setObjectName("checkBox_12")
        self.checkboxs_layout.addWidget(self.checkBox_12, 1, 2)
        self.data2_listlayout = QtWidgets.QVBoxLayout()
        self.data2_listlayout.addLayout(self.checkboxs_layout)
        self.data2_listlayout.addLayout(self.button2_leftlayout)
        self.data2_listlayout.addLayout(self.Qurry_layout2)
        self.tab2_layout.addLayout(self.data2_listlayout, 0, 0, 2, 1, alignment=QtCore.Qt.AlignTop)
        self.tab2_layout.setColumnStretch(1, 4)

        self.left_layout = QtWidgets.QGridLayout()

        self.options2_layout = QtWidgets.QGridLayout()

        self.Plot_Options_2 = QtWidgets.QTextBrowser()
        # self.Plot_Options_2.setGeometry(QtCore.QRect(10, 10, 101, 31))
        self.Plot_Options_2.setMaximumSize(129, 27)
        self.Plot_Options_2.setObjectName("Plot_Options_2")
        self.options2_layout.addWidget(self.Plot_Options_2, 0, 0)

        self.textBrowser_18 = QtWidgets.QTextBrowser()
        self.textBrowser_18.setMaximumSize(129, 27)
        self.textBrowser_18.setObjectName("textBrowser_18")
        self.options2_layout.addWidget(self.textBrowser_18, 1, 0)

        self.Hz_2 = QtWidgets.QTextEdit()
        self.Hz_2.setMaximumSize(129, 27)
        self.Hz_2.setPlaceholderText("Hz")
        self.Hz_2.setObjectName("Hz_2")
        self.Hz_2.setStyleSheet("""background-color: lightgray;color: black;""")
        self.options2_layout.addWidget(self.Hz_2, 1, 1)

        self.textBrowser_19 = QtWidgets.QTextBrowser()
        self.textBrowser_19.setMaximumSize(129, 27)
        self.textBrowser_19.setObjectName("textBrowser_19")
        self.options2_layout.addWidget(self.textBrowser_19, 2, 0)

        self.Function_2 = QtWidgets.QComboBox()
        self.Function_2.setMaximumSize(129, 27)
        self.Function_2.setObjectName("Function_2")
        self.Function_2.setStyleSheet("""background-color: lightgray;color: black;""")
        self.Function_2.addItem("")
        self.Function_2.addItem("")
        self.Function_2.addItem("")
        self.options2_layout.addWidget(self.Function_2, 2, 1)

        self.textBrowser_20 = QtWidgets.QTextBrowser()
        self.textBrowser_20.setMaximumSize(129, 27)
        self.textBrowser_20.setObjectName("textBrowser_20")
        self.options2_layout.addWidget(self.textBrowser_20, 3, 0)

        self.Overlap_Factor_2 = QtWidgets.QComboBox()
        self.Overlap_Factor_2.setMaximumSize(129, 27)
        self.Overlap_Factor_2.setObjectName("Overlap_Factor_2")
        self.Overlap_Factor_2.setStyleSheet("""background-color: lightgray;color: black;""")
        self.Overlap_Factor_2.addItem("0%")
        self.Overlap_Factor_2.addItem("25%")
        self.Overlap_Factor_2.addItem("50%")
        self.Overlap_Factor_2.addItem("75%")
        self.options2_layout.addWidget(self.Overlap_Factor_2, 3, 1)

        self.select_type_convert2 = QtWidgets.QTextBrowser()
        self.select_type_convert2.setObjectName("Convert")
        self.select_type_convert2.setMaximumSize(129, 27)
        self.options2_layout.addWidget(self.select_type_convert2, 4, 0)

        self.select_pytpe2 = QtWidgets.QComboBox()
        self.select_pytpe2.setObjectName("select_pytpe")
        self.select_pytpe2.setMaximumSize(129, 27)
        self.select_pytpe2.setStyleSheet("""background-color: lightgray;color: black;""")
        self.select_pytpe2.addItem("ACC", 1)  # "ACC" 표시, 내부 값은 1
        self.select_pytpe2.addItem("VEL", 2)  # "VEL" 표시, 내부 값은 2
        self.select_pytpe2.addItem("DIS", 3)  # "DIS" 표시, 내부 값은 3
        self.options2_layout.addWidget(self.select_pytpe2, 4, 1)

        self.input_angle = QtWidgets.QTextBrowser()
        self.input_angle.setObjectName("angle")
        self.input_angle.setMaximumSize(129, 27)
        self.options2_layout.addWidget(self.input_angle, 5, 0)

        self.angle_input = QtWidgets.QLineEdit()
        self.angle_input.setPlaceholderText("각도 (30)")
        self.angle_input.setStyleSheet("""background-color: lightgray;color: black;""")
        self.angle_input.setMaximumSize(129, 27)
        self.options2_layout.addWidget(self.angle_input, 5, 1)

        # ⭐ 각도 변경 이벤트 연결 추가 (새로 추가할 코드)
        self.angle_input.returnPressed.connect(self.update_waterfall_angle)

        self.plot_waterfall_button = QtWidgets.QPushButton("Plot Waterfall")
        self.plot_waterfall_button.setMaximumSize(129, 27)
        # self.plot_waterfall_button.setGeometry(QtCore.QRect(450, 95, 150, 30))
        self.plot_waterfall_button.clicked.connect(lambda: self.plot_waterfall_spectrum(force_recalculate=True))
        self.options2_layout.addWidget(self.plot_waterfall_button)
        self.options2_layout.setContentsMargins(0, 0, 0, 0)
        self.options2_layout.setSpacing(0)
        self.options2_layout.setRowStretch(0, 1)
        self.options2_layout.setRowStretch(1, 1)
        self.options2_layout.setColumnStretch(1, 1)

        self.left_layout.addLayout(self.options2_layout, 1, 0, 1, 1)

        self.waterfall_scale_layout = QtWidgets.QVBoxLayout()
        self.waterfall_scale_layout.addStretch

        self.x_scale_layout = QtWidgets.QHBoxLayout()
        self.x_scale_layout2 = QtWidgets.QHBoxLayout()
        self.y_scale_layout = QtWidgets.QHBoxLayout()
        self.y_scale_layout2 = QtWidgets.QHBoxLayout()
        self.z_scale_layout = QtWidgets.QHBoxLayout()
        self.z_scale_layout2 = QtWidgets.QHBoxLayout()

        # ✅ X축, Y축 Limit 설정 UI 추가
        self.auto_scale_x_2 = QtWidgets.QCheckBox("Auto X")
        self.auto_scale_x_2.setChecked(True)  # 기본값 Auto
        self.x_scale_layout.addWidget(self.auto_scale_x_2)

        self.water_x_autoscale = QtWidgets.QPushButton("Auto Scale")
        self.water_x_autoscale.setMaximumSize(100, 31)
        self.x_scale_layout.addWidget(self.water_x_autoscale)

        self.auto_scale_z = QtWidgets.QCheckBox("Auto z")
        self.auto_scale_z.setChecked(True)
        self.z_scale_layout.addWidget(self.auto_scale_z)

        self.water_z_autoscale = QtWidgets.QPushButton("Auto Scale")
        self.water_z_autoscale.setMaximumSize(100, 31)
        self.z_scale_layout.addWidget(self.water_z_autoscale)

        self.x_min_input2 = QtWidgets.QLineEdit()
        self.x_min_input2.setMaximumSize(70, 31)
        self.x_min_input2.setPlaceholderText("X min")
        self.x_min_input2.setStyleSheet("""background-color: lightgray;color: black;""")
        self.x_scale_layout2.addWidget(self.x_min_input2)

        self.x_max_input2 = QtWidgets.QLineEdit()
        self.x_max_input2.setMaximumSize(70, 31)
        self.x_max_input2.setPlaceholderText("X max")
        self.x_max_input2.setStyleSheet("""background-color: lightgray;color: black;""")
        self.x_scale_layout2.addWidget(self.x_max_input2)

        self.water_x_set = QtWidgets.QPushButton("Set")
        self.water_x_set.setMaximumSize(70, 31)
        self.x_scale_layout2.addWidget(self.water_x_set)

        self.z_min_input = QtWidgets.QLineEdit()
        self.z_min_input.setMaximumSize(70, 31)
        self.z_min_input.setPlaceholderText("z min")
        self.z_min_input.setStyleSheet("""background-color: lightgray;color: black;""")
        self.z_scale_layout2.addWidget(self.z_min_input)

        self.z_max_input = QtWidgets.QLineEdit()
        self.z_max_input.setMaximumSize(70, 31)
        self.z_max_input.setPlaceholderText("z max")
        self.z_max_input.setStyleSheet("""background-color: lightgray;color: black;""")
        self.z_scale_layout2.addWidget(self.z_max_input)

        self.water_z_set = QtWidgets.QPushButton("Set")
        self.water_z_set.setMaximumSize(70, 31)
        self.z_scale_layout2.addWidget(self.water_z_set)

        self.water_x_set.clicked.connect(self.set_x_axis2)
        self.water_z_set.clicked.connect(self.set_z_axis)
        self.water_x_autoscale.clicked.connect(self.show_full_view_x)
        self.water_z_autoscale.clicked.connect(self.show_full_view_z)
        self.waterfall_scale_layout.addLayout(self.x_scale_layout)
        self.waterfall_scale_layout.addLayout(self.x_scale_layout2)
        self.waterfall_scale_layout.addLayout(self.y_scale_layout)
        self.waterfall_scale_layout.addLayout(self.y_scale_layout2)
        self.waterfall_scale_layout.addLayout(self.z_scale_layout)
        self.waterfall_scale_layout.addLayout(self.z_scale_layout2)
        self.tab2_layout.addLayout(self.left_layout, 0, 1)
        self.tab2_layout.addLayout(self.waterfall_scale_layout, 0, 2, 1, 1, alignment=QtCore.Qt.AlignRight)
        self.tab2_layout.setColumnStretch(1, 4)  # 왼쪽 콘텐츠용

        # ✅ Waterfall 그래프를 표시할 위젯 추가
        self.waterfall_graph_layout = QtWidgets.QVBoxLayout()

        # Figure 생성
        # ✅ 수정 코드
        dpi = QtWidgets.QApplication.primaryScreen().logicalDotsPerInch()
        self.waterfall_figure = plt.Figure(figsize=(10, 4), dpi=dpi)
        self.waterfall_canvas = FigureCanvas(self.waterfall_figure)
        self.waterfall_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.waterfall_ax = self.waterfall_figure.add_subplot(111)

        # FigureCanvas를 생성하여 Waterfall 그래프 위젯에 추가
        self.waterfall_graph_layout.addWidget(self.waterfall_canvas)
        # self.waterfall_toolbar = NavigationToolbar(self.waterfall_canvas, MainWindow)
        # self.waterfall_graph_layout.addWidget(self.waterfall_toolbar)

        # Waterfall 그래프를 그릴 Axes 생성
        # self.waterfall_ax.set_title("Waterfall")
        self.waterfall_ax.set_title("Waterfall Spectrum", fontsize=7, fontname='Malgun Gothic')
        self.tab2_layout.addLayout(self.waterfall_graph_layout, 1, 1, 1, 8,
                                   alignment=QtCore.Qt.AlignLeft)  # 그래프 위젯 추가

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)

        self.menubar.setGeometry(QtCore.QRect(0, 0, 1920, 24))
        self.menubar.setObjectName("menubar")

        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")

        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.selected_checkbox = None
        self.directory_path = None
        self.sensitivity = None
        self.signal_data = None

        self.x_data = None
        self.y_data = None

        item = QtWidgets.QTableWidgetItem()
        self.Data_list.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.Data_list.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.Data_list.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.Data_list.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.Data_list.setHorizontalHeaderItem(4, item)

        # ✅ 채널 체크박스 변경 시 Details에도 반영
        self.checkBox_7.stateChanged.connect(self.update_querry_list2)
        self.checkBox_8.stateChanged.connect(self.update_querry_list2)
        self.checkBox_9.stateChanged.connect(self.update_querry_list2)
        self.checkBox_10.stateChanged.connect(self.update_querry_list2)
        self.checkBox_11.stateChanged.connect(self.update_querry_list2)
        self.checkBox_12.stateChanged.connect(self.update_querry_list2)

        # ✅ 채널 체크박스가 변경될 때마다 `update_querry_list3()` 실행
        self.checkBox_13.stateChanged.connect(self.update_querry_list3)
        self.checkBox_14.stateChanged.connect(self.update_querry_list3)
        self.checkBox_15.stateChanged.connect(self.update_querry_list3)
        self.checkBox_16.stateChanged.connect(self.update_querry_list3)
        self.checkBox_17.stateChanged.connect(self.update_querry_list3)
        self.checkBox_18.stateChanged.connect(self.update_querry_list3)

        # ✅ 채널 체크박스가 변경될 때마다 `update_querry_list3()` 실행
        self.checkBox_19.stateChanged.connect(self.update_querry_list4)
        self.checkBox_20.stateChanged.connect(self.update_querry_list4)
        self.checkBox_21.stateChanged.connect(self.update_querry_list4)
        self.checkBox_22.stateChanged.connect(self.update_querry_list4)
        self.checkBox_23.stateChanged.connect(self.update_querry_list4)
        self.checkBox_24.stateChanged.connect(self.update_querry_list4)

        self.Data_list.horizontalHeader().sectionClicked.connect(self.handle_header_click)
        self.select_all_toggle = False  # 토글 상태 저장 변수
        self.trend_marker_filenames = []
        self.peak_marker_filenames = []
        self.marker_filenames = []
        self.marker_list = []
        self.marker_infos = []
        self.markers = []  # 마커와 텍스트를 저장할 리스트
        self.trend_markers = []  # 마커 핸들 저장
        self.peak_markers = []  # 마커 핸들 저장

        self.trend_markers2 = []
        self.trend_annotations = []  # 텍스트 박스 핸들 저장
        self.annotations = []  # 텍스트 박스 핸들 저장
        self.peak_markers = []  # 피크 그래프의 마커 저장
        self.peak_annotations = []  # 피크 그래프의 텍스트 박스 저장
        self.cursor_circles = []
        self.markers = []  # 마커 저장 리스트
        self.current_x = 0
        self.x_step = 0.1
        self.hover_pos = [None, None]  # 현재 hover_dot 위치 저장 (float x, y)
        self.hover_pos2 = [None, None]  # 현재 hover_dot 위치 저장 (float x, y) spectrum
        self.hover_pos_peak = [None, None]
        self.hover_step = [0.01, 0.01]  # 키보드 이동 단위 (x, y 방향)
        self.mouse_tracking_enabled = True  # 기본값은 True로 설정

        # ⭐ Waterfall 캐시 초기화
        self.waterfall_cache = {
            'computed': False,
            'spectra': [],
            'params': {}
        }

        # 클래스 초기화 부분에 추가할 변수
        self.current_x_min = None
        self.current_x_max = None
        self.current_z_min = None
        self.current_z_max = None

    def _init_optimization_if_needed(self):
        """최적화 시스템 지연 초기화 (directory_path 설정 후 호출)"""
        if self._optimization_initialized:
            return

        try:
            # 캐시 디렉토리 설정
            if hasattr(self, 'directory_path') and self.directory_path:
                cache_dir = os.path.join(self.directory_path, '.cache')
            else:
                cache_dir = 'cache'

            # 파일 캐시 및 배치 프로세서 초기화
            self.file_cache = FileCache(cache_dir=cache_dir)
            self.batch_processor = BatchProcessor(self.file_cache)

            self._optimization_initialized = True
            perf_logger.log_info("✅ Level 1 최적화 활성화: 빠른 파일 로딩 & 캐싱")
        except Exception as e:
            perf_logger.log_warning(f"⚠️ 최적화 초기화 실패: {e}")

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.Select_button.setText(_translate("MainWindow", "Select Directory: 📂"))
        self.Data_button.setText(_translate("MainWindow", "Data Query:          💾"))
        item = self.Data_list.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Data"))
        item = self.Data_list.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Time"))
        item = self.Data_list.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Total Files"))
        item = self.Data_list.horizontalHeaderItem(3)
        item.setText(_translate("MainWindow", "Files"))
        item = self.Data_list.horizontalHeaderItem(4)
        item.setText(_translate("MainWindow", "Select"))
        self.Choose_button.setText(_translate("MainWindow", "Choose"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Data Query"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), _translate("MainWindow", "Time / Spectrum"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4), _translate("MainWindow", "Overall RMS Trend"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_5), _translate("MainWindow", "Band Peak Trend"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Waterfall"))
        self.Sample_rate.setHtml(_translate("MainWindow", "Sampling:"))
        self.select_type_convert.setHtml(_translate("Mainwindow", "Convert"))
        self.select_type_convert4.setHtml(_translate("Mainwindow", "Convert"))
        self.select_type_convert2.setHtml(_translate("Mainwindow", "Convert"))
        self.input_angle.setHtml(_translate("Mainwindow", "Angle"))
        self.freq_range_label.setHtml(_translate("Mainwindow", "BandLimit"))
        self.freq_range_label2.setHtml(_translate("Mainwindow", "BandLimit"))
        self.select_type_convert3.setHtml(_translate("MainWindow", "Convert"))
        self.data_list_label.setHtml(_translate("MainWindow", "Pick Data List"))
        self.Duration.setHtml(_translate("MainWindow", "Record Length:"))
        self.Rest_time.setHtml(_translate("MainWindow", "Rest time:"))
        self.IEPE.setHtml(_translate("MainWindow", "IEPE enable:"))
        self.Channel.setHtml(_translate("MainWindow", "Channel:"))
        self.Sensitivity.setHtml(_translate("MainWindow", "Sensitivity:"))
        self.Sensitivity2.setHtml(_translate("MainWindow", "Sensitivity_edit:"))
        self.Sample_rate_view.setHtml(_translate("MainWindow", ""))
        self.Duration_view.setHtml(_translate("MainWindow", ""))
        self.Rest_time_view.setHtml(_translate("MainWindow", ""))
        self.Channel_view.setHtml(_translate("MainWindow", ""))
        self.IEPE_view.setHtml(_translate("MainWindow", ""))
        self.Sensitivity_view.setHtml(_translate("MainWindow", ""))
        self.Plot_Options.setHtml(_translate("MainWindow", "FFT Options"))
        self.textBrowser_15.setHtml(_translate("MainWindow", "\u0394f:"))
        self.Hz.setHtml(_translate("MainWindow", ""))
        self.textBrowser_16.setHtml(_translate("MainWindow", "Windown Function:"))
        self.Function.setItemText(0, _translate("MainWindow", "Rectangular"))
        self.Function.setItemText(1, _translate("MainWindow", "Hanning"))
        self.Function.setItemText(2, _translate("MainWindow", "Flattop"))
        self.textBrowser_17.setHtml(_translate("MainWindow", "Overlap Factor:"))
        self.Overlap_Factor.setItemText(0, _translate("MainWindow", "0%"))
        self.Overlap_Factor.setItemText(1, _translate("MainWindow", "25%"))
        self.Overlap_Factor.setItemText(2, _translate("MainWindow", "50%"))
        self.Overlap_Factor.setItemText(3, _translate("MainWindow", "75%"))
        self.checkBox.setText(_translate("MainWindow", "1CH"))
        self.checkBox_2.setText(_translate("MainWindow", "2CH"))
        self.checkBox_3.setText(_translate("MainWindow", "3CH"))
        self.checkBox_4.setText(_translate("MainWindow", "4CH"))
        self.checkBox_5.setText(_translate("MainWindow", "5CH"))
        self.checkBox_6.setText(_translate("MainWindow", "6CH"))
        self.Plot_Options_2.setHtml(_translate("MainWindow", "FFT Options"))
        self.Plot_Options_3.setHtml(_translate("MainWindow", "FFT Options"))
        self.Plot_Options_4.setHtml(_translate("MainWindow", "FFT Options"))
        self.textBrowser_18.setHtml(_translate("MainWindow", "\u0394f:"))
        self.textBrowser_30.setHtml(_translate("MainWindow", "\u0394f:"))
        self.textBrowser_33.setHtml(_translate("MainWindow", "\u0394f:"))
        self.Hz_2.setHtml(_translate("MainWindow", ""))
        self.Hz_3.setHtml(_translate("MainWindow", ""))
        self.Hz_4.setHtml(_translate("MainWindow", ""))
        self.textBrowser_19.setHtml(_translate("MainWindow", "Windown Function:"))
        self.textBrowser_31.setHtml(_translate("MainWindow", "Windown Function:"))
        self.textBrowser_34.setHtml(_translate("MainWindow", "Windown Function:"))
        self.Function_2.setItemText(0, _translate("MainWindow", "Rectangular"))
        self.Function_2.setItemText(1, _translate("MainWindow", "Hanning"))
        self.Function_2.setItemText(2, _translate("MainWindow", "Flattop"))
        self.Function_3.setItemText(0, _translate("MainWindow", "Rectangular"))
        self.Function_3.setItemText(1, _translate("MainWindow", "Hanning"))
        self.Function_3.setItemText(2, _translate("MainWindow", "Flattop"))
        self.Function_4.setItemText(0, _translate("MainWindow", "Rectangular"))
        self.Function_4.setItemText(1, _translate("MainWindow", "Hanning"))
        self.Function_4.setItemText(2, _translate("MainWindow", "Flattop"))
        self.textBrowser_20.setHtml(_translate("MainWindow", "Overlap Factor:"))
        self.textBrowser_32.setHtml(_translate("MainWindow", "Overlap Factor:"))
        self.textBrowser_35.setHtml(_translate("MainWindow", "Overlap Factor:"))
        self.Overlap_Factor_2.setItemText(0, _translate("MainWindow", "0%"))
        self.Overlap_Factor_2.setItemText(1, _translate("MainWindow", "25%"))
        self.Overlap_Factor_2.setItemText(2, _translate("MainWindow", "50%"))
        self.Overlap_Factor_2.setItemText(3, _translate("MainWindow", "75%"))
        self.Overlap_Factor_3.setItemText(0, _translate("MainWindow", "0%"))
        self.Overlap_Factor_3.setItemText(1, _translate("MainWindow", "25%"))
        self.Overlap_Factor_3.setItemText(2, _translate("MainWindow", "50%"))
        self.Overlap_Factor_3.setItemText(3, _translate("MainWindow", "75%"))
        self.checkBox_7.setText(_translate("MainWindow", "1CH"))
        self.checkBox_8.setText(_translate("MainWindow", "2CH"))
        self.checkBox_9.setText(_translate("MainWindow", "3CH"))
        self.checkBox_10.setText(_translate("MainWindow", "4CH"))
        self.checkBox_11.setText(_translate("MainWindow", "5CH"))
        self.checkBox_12.setText(_translate("MainWindow", "6CH"))
        self.checkBox_13.setText(_translate("MainWindow", "1CH"))
        self.checkBox_14.setText(_translate("MainWindow", "2CH"))
        self.checkBox_15.setText(_translate("MainWindow", "3CH"))
        self.checkBox_16.setText(_translate("MainWindow", "4CH"))
        self.checkBox_17.setText(_translate("MainWindow", "5CH"))
        self.checkBox_18.setText(_translate("MainWindow", "6CH"))
        self.checkBox_19.setText(_translate("MainWindow", "1CH"))
        self.checkBox_20.setText(_translate("MainWindow", "2CH"))
        self.checkBox_21.setText(_translate("MainWindow", "3CH"))
        self.checkBox_22.setText(_translate("MainWindow", "4CH"))
        self.checkBox_23.setText(_translate("MainWindow", "5CH"))
        self.checkBox_24.setText(_translate("MainWindow", "6CH"))
        self.directory_path = ""  # 선택한 디렉토리 저장 변수

    def select_directory(self):
        """ 폴더 선택 """
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(None, "Select Directory", "",
                                                              QtWidgets.QFileDialog.ShowDirsOnly)
        if dir_path:
            self.directory_path = dir_path
            self.Directory.setText(dir_path)

    def handle_header_click(self, logicalIndex):
        # "Select" 열이 몇 번째인지 확인 (보통 마지막 열, 여기선 3번째)
        if logicalIndex == 4:  # "Select" 열
            row_count = self.Data_list.rowCount()
            new_state = QtCore.Qt.Checked if not self.select_all_toggle else QtCore.Qt.Unchecked

            for row in range(row_count):
                item = self.Data_list.item(row, 4)
                if item is not None:
                    item.setCheckState(new_state)

            self.select_all_toggle = not self.select_all_toggle

    def load_data(self):
        """ 선택한 폴더의 파일을 불러와 1분 단위로 그룹화 """
        if not self.directory_path:
            QtWidgets.QMessageBox.warning(None, "Warning", "Please select a directory first.")
            return

        file_dict = defaultdict(list)
        files = os.listdir(self.directory_path)

        self.all_files = [f for f in files if f.endswith(".txt")]

        for filename in self.all_files:
            parts = filename.split("_")
            if len(parts) >= 2:
                date_part = parts[0]  # '2025-04-10'
                time_part = parts[1]  # '13-36-13'
                time_parts = time_part.split("-")
                if len(time_parts) == 3:
                    formatted_time = f"{time_parts[0]}:{time_parts[1]}:{time_parts[2]}"  # '13:36:13'
                    key = (date_part, formatted_time)
                    file_dict[key].append(filename)

        # 테이블 업데이트
        # 테이블 업데이트
        self.Data_list.setRowCount(0)  # 기존 데이터 초기화
        for idx, ((date, time), files) in enumerate(sorted(file_dict.items())):
            self.Data_list.insertRow(idx)
            self.Data_list.setItem(idx, 0, QtWidgets.QTableWidgetItem(date))  # 날짜
            self.Data_list.setItem(idx, 1, QtWidgets.QTableWidgetItem(time))  # 시간
            self.Data_list.setItem(idx, 2, QtWidgets.QTableWidgetItem(str(len(files))))  # 파일 개수
            self.Data_list.setItem(idx, 3, QtWidgets.QTableWidgetItem(", ".join(files)))  # 파일 목록

            # 체크박스 추가
            checkbox_item = QtWidgets.QTableWidgetItem()
            checkbox_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            checkbox_item.setCheckState(QtCore.Qt.Unchecked)
            self.Data_list.setItem(idx, 4, checkbox_item)

        # 테이블 컬럼 이름 설정
        self.Data_list.setHorizontalHeaderLabels(['Date', 'Time', 'Total Files', 'Files', 'Select'])

        # 파일이 없을 경우 경고 메시지
        if not file_dict:
            QtWidgets.QMessageBox.information(None, "No Data", "선택한 폴더에 적절한 형식의 .txt 파일이 없습니다.")

        self.Data_list.show()

    def on_choose_button_clicked(self):
        """Data Query 탭에서 선택된 파일을 저장하고 Details 탭으로 이동"""
        selected_files = []
        for row in range(self.Data_list.rowCount()):
            checkbox_item = self.Data_list.item(row, 4)
            if checkbox_item.checkState() == QtCore.Qt.Checked:  # 체크된 파일 가져오기
                files = self.Data_list.item(row, 3).text().split(", ")
                selected_files.extend(files)

        if selected_files:
            self.selected_files = sorted(selected_files, reverse=False)  # ✅ 전체 선택 파일 저장
            self.Querry_list.clear()
            self.Querry_list2.clear()
            self.Querry_list3.clear()
            self.Querry_list4.clear()
            self.Querry_list.addItems(self.selected_files)  # ✅ 초기에는 전체 선택 파일 표시
            self.Querry_list2.addItems(self.selected_files)
            self.Querry_list3.addItems(self.selected_files)
            self.Querry_list4.addItems(self.selected_files)
            self.tabWidget.setCurrentIndex(1)  # ✅ Details 탭으로 이동
        else:
            QtWidgets.QMessageBox.warning(None, "No Files Selected", "선택된 파일이 없습니다.")

    def on_querry_list_item_clicked(self, item):
        """Querry_list에서 선택한 파일 내용을 읽어 UI에 채움"""
        file_name = item.text()  # 선택한 파일명 가져오기
        file_path = os.path.join(self.directory_path, file_name)  # 전체 경로

        if not os.path.exists(file_path):
            QtWidgets.QMessageBox.warning(None, "File Error", f"파일을 찾을 수 없습니다: {file_name}")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 예제 데이터 파싱 (파일 형식에 따라 수정 필요)
            parsed_data = self.parse_file_data(lines)

            # ✅ UI에 데이터 채우기
            self.sample_rate = self.Sample_rate_view.setText(parsed_data.get("D.Sampling Freq.", ""))
            self.Duration = self.Duration_view.setText(parsed_data.get("Record Length", ""))
            self.Rest_time = self.Rest_time_view.setText(parsed_data.get("rest_time", ""))
            self.Channel_view.setText(parsed_data.get("channel", ""))
            self.IEPE = self.IEPE_view.setText(parsed_data.get("iepe", ""))
            self.Sensitivity = self.Sensitivity_view.setText(parsed_data.get("sensitivity", ""))


        except Exception as e:
            QtWidgets.QMessageBox.warning(None, "Read Error", f"파일을 읽는 중 오류 발생: {str(e)}")

    def select_all_items(self):
        """전체 항목 선택"""
        for i in range(self.Querry_list.count()):
            item = self.Querry_list.item(i)
            item.setSelected(True)

    def deselect_all_items(self):
        """전체 선택 해제"""
        for i in range(self.Querry_list.count()):
            item = self.Querry_list.item(i)
            item.setSelected(False)

    def select_all_items2(self):
        """전체 항목 선택"""
        for i in range(self.Querry_list2.count()):
            item = self.Querry_list2.item(i)
            item.setSelected(True)

    def deselect_all_items2(self):
        """전체 선택 해제"""
        for i in range(self.Querry_list2.count()):
            item = self.Querry_list2.item(i)
            item.setSelected(False)

    def select_all_items3(self):
        """전체 항목 선택"""
        for i in range(self.Querry_list3.count()):
            item = self.Querry_list3.item(i)
            item.setSelected(True)

    def deselect_all_items3(self):
        """전체 선택 해제"""
        for i in range(self.Querry_list3.count()):
            item = self.Querry_list3.item(i)
            item.setSelected(False)

    def select_all_items4(self):
        """전체 항목 선택"""
        for i in range(self.Querry_list4.count()):
            item = self.Querry_list4.item(i)
            item.setSelected(True)

    def deselect_all_items4(self):
        """전체 선택 해제"""
        for i in range(self.Querry_list4.count()):
            item = self.Querry_list4.item(i)
            item.setSelected(False)

    def save_Sensitivity(self):
        """선택된 파일들의 Sensitivity를 업데이트하고 기존 값은 b.Sensitivity로 보존"""
        new_sensitivity = self.Sensitivity_edit.text().strip()
        selected_files = [item.text() for item in self.Querry_list.selectedItems()]

        if not new_sensitivity:
            QtWidgets.QMessageBox.warning(None, "경고", "유효한 Sensitivity 값을 입력해주세요.")
            return

        if not selected_files:
            QtWidgets.QMessageBox.warning(None, "경고", "파일을 선택해주세요.")
            return

        for file_name in selected_files:
            file_path = os.path.join(self.directory_path, file_name)
            # 파일 이름만 있다면 경로를 합쳐줌

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                new_lines = []
                sensitivity_found = False

                for line in lines:
                    if line.strip().startswith("Sensitivity") and not line.strip().startswith("b.Sensitivity"):
                        new_lines.append("b." + line)
                        new_lines.append(f"Sensitivity              : {new_sensitivity} mv/unit\n")
                        sensitivity_found = True
                    else:
                        new_lines.append(line)

                if not sensitivity_found:
                    new_lines.append(f"Sensitivity              : {new_sensitivity} mv/unit\n")

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)

            except Exception as e:
                QtWidgets.QMessageBox.critical(None, "오류", f"{file_name} 처리 중 오류 발생: {str(e)}")
                continue

        QtWidgets.QMessageBox.information(None, "성공", "선택된 파일들의 Sensitivity가 성공적으로 업데이트되었습니다.")

    def parse_file_data(self, lines):
        """파일 내용을 파싱하여 필요한 데이터 추출"""
        data = {
            "D.Sampling Freq.": "",
            "Record Length": "",
            "rest_time": "",
            "channel": "",
            "iepe": "",
            "sensitivity": "",
            "starting_time": "",
            "repetition": "",
            "b.Sensitivity": "",
        }

        for line in lines:
            parts = line.strip().split(":")
            if len(parts) < 2:
                continue

            key = parts[0].strip()
            value = parts[1].strip()

            if "D.Sampling Freq." in key:
                data["D.Sampling Freq."] = value
            elif "Starting time" in key:
                data["starting_time"] = value
            elif "Record Length" in key:
                data["Record Length"] = value
            elif "Rest time" in key:
                data["rest_time"] = value
            elif "Repetition" in key:
                data["repetition"] = value
            elif "Channel" in key:
                data["channel"] = value
            elif "IEPE enable" in key:
                data["iepe"] = value
            elif "Sensitivity" in key:
                data["sensitivity"] = value
            elif "b.Sensitivity" in key:
                data["b.Sensitivity"] = value

        return data

    def mdl_FFT_N(self, type_flag, tfs, X, res, ovrl, win, sgnl, conv2sgnl, Zpadding):
        """
                FFT Analyze Module (Number)

                Parameters:
                type_flag : 1 for time vector input, 2 for sampling frequency input.
                tfs       : Time vector (if type_flag==1) or Sampling frequency (if type_flag==2).
                X         : Time signal vector or matrix (shape: (L, Ch)).
                res       : Frequency Resolution.
                ovrl      : Overlapping percentage. (0, 25, 50, 75)
                win       : Window type (0: rectangular, 1: hanning, 2: flattop)
                sgnl      : Input signal type (1: Acc, 2: Vel, 3: Disp)
                conv2sgnl : Convert to (1: Acc, 2: Vel, 3: Disp)
                Zpadding  : Zero padding frequency threshold (Hz). If nonzero, frequencies < (Zpadding+0.01) set to zero.

                Returns:
                f   : Frequency vector.
                P   : FFT spectrum (averaged) for each channel.
                ACF : Amplitude Correction Factor.
                ECF : Energy Correction Factor.
                """
        X = np.atleast_2d(X)  # ensure X is 2D: (L, Ch)
        L, Ch = X.shape
        if type_flag == 1:
            t = np.asarray(tfs).flatten()
            dt = t[1] - t[0]
            Fs = 1 / dt
        elif type_flag == 2:
            Fs = tfs
            dt = 1 / Fs
            t = np.arange(L) * dt
        else:
            raise ValueError("type_flag must be 1 or 2.")

        # Segment length based on frequency resolution: l = floor(Fs/res)
        l = int(np.floor(Fs / res))
        if Fs / res > L:
            raise ValueError(f"Frequency Resolution should be larger than {Fs / L:.2f}.")

        # Determine step size based on overlapping percentage
        if ovrl == 0:
            step = l
        elif ovrl == 25:
            step = int(np.ceil(l * 3 / 4))
        elif ovrl == 50:
            step = int(np.ceil(l / 2))
        elif ovrl == 75:
            step = int(np.ceil(l / 4))
        else:
            raise ValueError("ovrl must be one of: 0, 25, 50, 75.")

        # Compute number of segments (per channel)
        num_segments = 1 + (L - l) // step
        segments = {}
        t_segments = []

        for seg in range(num_segments):
            start = seg * step
            end = start + l
            if end > L:
                break  # safety check
            t_seg = t[start:end]
            t_segments.append(t_seg)
            for ch in range(Ch):
                if ch not in segments:
                    segments[ch] = []
                segments[ch].append(X[start:end, ch])
        # Convert lists to arrays: each becomes shape (num_segments, l)
        for ch in range(Ch):
            segments[ch] = np.array(segments[ch])
        # For time segments, shape (num_segments, l)
        t_segments = np.array(t_segments)

        # Window selection: create window vector of length l.
        if win == 0:  # Rectangular
            w = np.ones(l)
        elif win == 1:  # Hanning, periodic window
            w = hann(l, sym=False)
        elif win == 2:  # Flattop, periodic window
            w = flattop(l, sym=False)
        else:
            raise ValueError("win must be 0, 1, or 2.")

        fft_segments = {}
        for ch in range(Ch):
            seg_win = segments[ch] * w[None, :]
            Y = fft(seg_win, axis=1)
            Y = Y / l
            n_oneside = l // 2 + 1
            Y = Y[:, :n_oneside]
            if n_oneside > 1:
                Y[:, 1:-1] = 2 * Y[:, 1:-1]
            fft_segments[ch] = Y

        # Average FFT spectrum over segments for each channel
        P = []
        for ch in range(Ch):
            # Mean over segments (axis=0), result shape: (n_oneside,)
            P_ch = np.mean(abs(fft_segments[ch]), axis=0)
            P.append(P_ch)
        P = np.column_stack(P)  # shape: (n_oneside, Ch)

        # Frequency vector
        f = Fs * np.arange(n_oneside) / l

        iomega = 1j * 2 * np.pi * f
        if sgnl == 1:  # Input: Acceleration
            if conv2sgnl == 2:  # Convert to Velocity
                # Avoid f==0 division: perform conversion on f>0 indices only.
                P_conv = np.empty_like(P, dtype=complex)
                P_conv[0, :] = 0
                P_conv[1:, :] = P[1:, :] / iomega[1:, None]
                P_conv = np.abs(P_conv) * 1000
                P = P_conv

            elif conv2sgnl == 3:  # Convert to Displacement
                P_conv = np.empty_like(P, dtype=complex)
                P_conv[0, :] = 0
                # For f>0: divide twice by iomega
                P_conv[1:, :] = P[1:, :] / (iomega[1:, None] ** 2)
                P_conv = np.abs(P_conv) * 1000
                P = P_conv
                # Else, no conversion if conv2sgnl==1.
        elif sgnl == 2:  # Input: Velocity
            if conv2sgnl == 1:  # Convert to Acceleration
                P_conv = P * iomega[:, None]
                P_conv = np.abs(P_conv) / 1000
                P = P_conv
            elif conv2sgnl == 3:  # Convert to Displacement
                P_conv = np.empty_like(P, dtype=complex)
                P_conv[0, :] = 0
                P_conv[1:, :] = P[1:, :] / iomega[1:, None]
                P_conv = np.abs(P_conv)
                P = P_conv
        elif sgnl == 3:  # Input: Displacement
            if conv2sgnl == 1:  # Convert to Acceleration
                P_conv = P * (iomega[:, None] ** 2)
                P_conv = np.abs(P_conv) / 1000
                P = P_conv
            elif conv2sgnl == 2:  # Convert to Velocity
                P_conv = P * iomega[:, None]
                P_conv = np.abs(P_conv)
                P = P_conv
        else:
            raise ValueError("sgnl must be 1, 2, or 3.")

        # Ensure DC component is zero as in MATLAB code
        P[0, :] = 0

        # Zero Padding: if Zpadding is nonzero, set spectrum values to zero for frequencies < (Zpadding+0.01)
        if Zpadding != 0:
            idx = np.where(f < (Zpadding + 0.01))[0]
            P[idx, :] = 0

        # Correction Factors
        ACF = 1 / (np.mean(w) * np.sqrt(2))
        rms_w = np.sqrt(np.mean(w ** 2))
        ECF = 1 / (rms_w * np.sqrt(2))

        # Power Spectral Density (Sxx) 추가
        Sxx = (P ** 2) / (Fs / l)

        return w, f, P, ACF, ECF, rms_w, Sxx

    def plot_signal_data(self):
        """
        ⭐ Level 5 최적화: 병렬 Spectrum 분석
        - 100개: 2-4초 → 0.5초
        - 1000개: 20초+ → 3-5초
        """
        from PyQt5.QtWidgets import QMessageBox, QApplication
        from PyQt5.QtCore import Qt
        from OPTIMIZATION_PATCH_LEVEL5_SPECTRUM import SpectrumParallelProcessor

        perf_logger.log_info("🚀 plot_signal_data 시작 (Level 5)")
        start_total = perf_logger.start_timer("전체 Spectrum 분석")

        try:
            # ===== 1. 파라미터 준비 =====
            if not self.Querry_list.count():
                perf_logger.end_timer("전체 Spectrum 분석", start_total)
                return

            selected_files = [item.text() for item in self.Querry_list.selectedItems()]

            MAX_FILES = 30
            if len(selected_files) > MAX_FILES:
                reply = QMessageBox.question(
                    None, "경고",
                    f"선택한 파일이 {len(selected_files)}개입니다.\n"
                    f"처음 {MAX_FILES}개만 처리하시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    selected_files = selected_files[:MAX_FILES]
                else:
                    perf_logger.log_warning(f"⚠️ {len(selected_files)}개 파일 처리 시도")

            if not selected_files:
                QMessageBox.critical(None, "오류", "파일을 선택하세요")
                return

            try:
                delta_f = float(self.Hz.toPlainText())
                overlap = float(self.Overlap_Factor.currentText().replace('%', ''))
                window_type = self.Function.currentText()
                view_type = self.select_pytpe.currentData()
            except ValueError as e:
                QMessageBox.critical(None, "입력 오류", str(e))
                return

            # ===== 2. 그래프 초기화 =====
            self.ax.clear()
            self.waveax.clear()

            # ===== 3. 진행률 다이얼로그 =====
            self.progress_dialog = ProgressDialog(len(selected_files), self.main_window)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.show()

            def progress_update(current, total):
                self.progress_dialog.update_progress(current)
                self.progress_dialog.label.setText(f"처리 중... {current}/{total}")
                QApplication.processEvents()

            # ===== 4. 파일 경로 리스트 =====
            file_paths = [
                os.path.join(self.directory_path, fname)
                for fname in selected_files
            ]

            # ===== 5. 병렬 처리 =====
            processor = SpectrumParallelProcessor(max_workers=6)

            perf_logger.log_info(f"🔥 병렬 처리 시작 ({len(file_paths)}개, {processor.max_workers} 워커)")
            start_parallel = perf_logger.start_timer("병렬 Spectrum 처리")

            results = processor.process_batch(
                file_paths=file_paths,
                delta_f=delta_f,
                overlap=overlap,
                window_type=window_type,
                view_type=view_type,
                progress_callback=progress_update
            )

            perf_logger.end_timer("병렬 Spectrum 처리", start_parallel)

            # ===== 6. 성공/실패 집계 =====
            success_results = [r for r in results if r.success]
            failed_count = len(results) - len(success_results)

            perf_logger.log_info(f"✓ 성공: {len(success_results)}, ✗ 실패: {failed_count}")

            if not success_results:
                QMessageBox.warning(None, "경고", "처리된 데이터가 없습니다.")
                self.progress_dialog.close()
                return

            # ===== 7. 배치 렌더링 =====
            perf_logger.log_info("🎨 그래프 렌더링 시작")
            start_render = perf_logger.start_timer("그래프 렌더링")

            colors = ["b", "g", "r", "c", "m", "y"]

            # Spectrum 렌더링
            for i, result in enumerate(success_results):
                color = colors[i % len(colors)]
                self.ax.plot(
                    result.frequency,
                    result.spectrum,
                    color=color,
                    linewidth=0.5,
                    label=result.file_name,
                    alpha=0.8
                )

            # Waveform 렌더링
            for i, result in enumerate(success_results):
                color = colors[i % len(colors)]
                self.waveax.plot(
                    result.time,
                    result.waveform,
                    color=color,
                    linewidth=0.5,
                    label=result.file_name,
                    alpha=0.8
                )

            perf_logger.end_timer("그래프 렌더링", start_render)

            # ===== 8. 그래프 설정 =====
            self.ax.set_title("Vibration Spectrum", fontsize=7, fontname=DEFAULT_FONT)
            self.waveax.set_title("Waveform", fontsize=7, fontname=DEFAULT_FONT)

            view_type_map = {1: "ACC", 2: "VEL", 3: "DIS"}
            view_type_str = view_type_map.get(view_type, "ACC")

            labels = {
                "ACC": "Vibration Acceleration\n(m/s², RMS)",
                "VEL": "Vibration Velocity\n(mm/s, RMS)",
                "DIS": "Vibration Displacement\n(μm, RMS)"
            }
            ylabel = labels.get(view_type_str, "Vibration (mm/s, RMS)")

            self.ax.set_xlabel("Frequency (Hz)", fontsize=7, fontname=DEFAULT_FONT)
            self.ax.set_ylabel(ylabel, fontsize=7, fontname=DEFAULT_FONT)
            self.waveax.set_xlabel("Time (s)", fontsize=7, fontname=DEFAULT_FONT)
            self.waveax.set_ylabel(ylabel, fontsize=7, fontname=DEFAULT_FONT)

            self.ax.grid(True)
            self.waveax.grid(True)

            # ⭐ 범례 업데이트 추가
            self.update_legend_position(self.ax, max_items=15)
            self.update_legend_position(self.waveax, max_items=15)

            # ⭐ tight_layout 재적용
            try:
                self.figure.tight_layout(rect=[0, 0, 0.88, 1])
                self.waveform_figure.tight_layout(rect=[0, 0, 0.88, 1])
            except:
                pass

            # ⭐ Legend 샘플링 (30개 → 10개)
            for ax in [self.ax, self.waveax]:
                handles, legend_labels = ax.get_legend_handles_labels()
                if len(handles) > 10:
                    step = len(handles) // 10
                    handles = handles[::step]
                    legend_labels = legend_labels[::step]
                ax.legend(handles, legend_labels, loc="upper left",
                          bbox_to_anchor=(1, 1), fontsize=7)

            # ⭐ 비동기 렌더링
            self.canvas.draw_idle()
            self.wavecanvas.draw_idle()
            QApplication.processEvents()
            self.canvas.flush_events()
            self.wavecanvas.flush_events()

            # ===== 9. 데이터 저장 =====
            self.spectrum_data_dict1 = {}
            self.file_names_used1 = []
            self.sample_rate1 = {}
            self.data_dict = {}

            for result in success_results:
                if result.success:
                    self.spectrum_data_dict1[result.file_name] = result.spectrum
                    self.file_names_used1.append(result.file_name)
                    self.sample_rate1[result.file_name] = result.sampling_rate
                    self.data_dict[result.file_name] = (result.frequency, result.spectrum)

            if success_results:
                first = success_results[0]
                self.frequency_array1 = first.frequency
                self.delta_f1 = delta_f
                self.window_type1 = window_type
                self.overlap1 = overlap
                self.view_type = view_type_str

                # 메타데이터
                self.dt1 = first.metadata.get('dt', '')
                self.start_time1 = first.metadata.get('start_time', '')
                self.Duration1 = first.metadata.get('duration', '')
                self.Rest_time1 = first.metadata.get('rest_time', '')
                self.repetition1 = first.metadata.get('repetition', '')
                self.IEPE1 = first.metadata.get('iepe', '')
                self.Sensitivity1 = first.metadata.get('sens', '')
                self.b_Sensitivity1 = first.metadata.get('b_sens', '')
                self.channel_info1 = first.metadata.get('channel', '')
                self.channel_infos1 = [r.file_name.split('_')[0] for r in success_results]

            # ===== 10. 마우스 이벤트 =====
            try:
                if hasattr(self, 'cid_move') and self.cid_move:
                    self.canvas.mpl_disconnect(self.cid_move)
                if hasattr(self, 'cid_click') and self.cid_click:
                    self.canvas.mpl_disconnect(self.cid_click)
                if hasattr(self, 'cid_key') and self.cid_key:
                    self.canvas.mpl_disconnect(self.cid_key)

                self.cid_move = self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
                self.cid_click = self.canvas.mpl_connect("button_press_event", self.on_mouse_click)
                self.cid_key = self.canvas.mpl_connect("key_press_event", self.on_key_press)
                self.hover_dot2 = self.ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
            except:
                pass

            # ===== 11. 정리 =====
            self.progress_dialog.close()

            import gc
            gc.collect()

            perf_logger.end_timer("전체 Spectrum 분석", start_total)
            perf_logger.log_info("✅ plot_signal_data 완료")

        except Exception as e:
            perf_logger.end_timer("전체 Spectrum 분석", start_total)
            perf_logger.log_warning(f"❌ 오류 발생: {e}")
            import gc
            gc.collect()
            raise

    def plot_next_file(self):
        current_items = self.Querry_list.selectedItems()
        if not current_items:
            return

        current_index = self.Querry_list.row(current_items[-1])
        total_count = self.Querry_list.count()

        if current_index < total_count - 1:
            next_index = current_index + 1

            # 다음 항목도 선택 상태로 만들기 (기존 선택 유지)
            self.Querry_list.item(next_index).setSelected(True)

            # ✅ 기존 함수 호출
            self.plot_signal_data()
        else:
            QMessageBox.critical(None, "안내", "ℹ️ 마지막 파일입니다.")

    def on_save_button_clicked(self):
        # Spectrum이 아닌 경우 저장하지 않음
        if not hasattr(self, 'spectrum_data_dict1') or not self.spectrum_data_dict1:
            return

        self.save_spectrum_to_csv(
            self.spectrum_data_dict1,
            # self.metadata_dict,
            self.frequency_array1,
            self.file_names_used1,
            self.delta_f1,
            self.window_type1,
            self.overlap1,
            self.channel_info1,
            self.sample_rate1,
            self.dt1,
            self.start_time1,
            self.Duration1,
            self.Rest_time1,
            self.repetition1,
            self.IEPE1,
            self.Sensitivity1,
            self.b_Sensitivity1,
            self.channel_infos1,
            self.view_type,
        )

    def save_spectrum_to_csv(self, spectrum_data1, frequencies1, file_names1, delta_f1, window_type1, overlap1,
                             channel_info1, sampling_rates1, dt1, start_time1, Duration1, Rest_time1, repetition1,
                             IEPE1, Sensitivity1, b_Sensitivity1, channel_infos1, view_type):
        # ✅ 저장 경로 선택
        save_path, _ = QFileDialog.getSaveFileName(None, "CSV 파일 저장", "", "CSV Files (*.csv)")
        if not save_path:
            return
        if not save_path.endswith(".csv"):
            save_path += ".csv"

        with open(save_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            # ✅ 헤더 정보 작성
            writer.writerow(["Δf", delta_f1])
            writer.writerow(["Window", window_type1])
            writer.writerow(["Overlap", f"{overlap1}%"])
            writer.writerow(["Record Length", Duration1])
            writer.writerow(["Sampling", sampling_rates1.get(file_names1[0], "N/A")])
            writer.writerow(["Rest Time", Rest_time1])
            writer.writerow(["IEPE", IEPE1])
            writer.writerow(["Sensitivity", Sensitivity1])
            writer.writerow(["b.Sensitivity", b_Sensitivity1])
            writer.writerow(["Starting Time", start_time1])
            writer.writerow(["Repetition", repetition1])
            writer.writerow(["Time Resolution(dt)", dt1])
            writer.writerow(["view_type", view_type])
            writer.writerow([])  # 빈 줄 삽입

            # ✅ 채널명 라인 (6번째 줄)
            channel_row = ["", *[
                re.search(r'_(\d+)\.txt$', fn).group(1) if re.search(r'_(\d+)\.txt$', fn) else "?"
                for fn in file_names1
            ]]
            writer.writerow(["Channel"] + channel_row[1:])

            # ✅ 열 제목 (주파수 + 파일 이름)
            writer.writerow(["Frequency (Hz)", *file_names1])

            # ✅ 데이터 라인 작성
            for i, freq in enumerate(frequencies1):
                row = [freq]
                for file_name1 in file_names1:
                    spectrum = spectrum_data1.get(file_name1)
                    value = float(spectrum[i]) if spectrum is not None and i < len(spectrum) else ""
                    row.append(value)
                writer.writerow(row)

    def set_x_axis(self):
        # ✅ Auto Scale이 활성화되어 있으면 입력값 무시
        if self.auto_spectrum_x.isChecked():
            return
        # ⭐ 안전한 마커 제거
        for marker, label in self.markers:
            try:
                marker.remove()
            except (NotImplementedError, ValueError, AttributeError):
                try:
                    marker.set_data([], [])
                except:
                    pass
            try:
                label.remove()
            except (NotImplementedError, ValueError, AttributeError):
                try:
                    label.set_visible(False)
                except:
                    pass
        self.markers.clear()

        try:

            ax = self.canvas.figure.axes[0]  # matplotlib 축 객체
            lines = ax.get_lines()  # 그래프 라인들

            x_min = float(self.spectrum_x_min_input.text())
            x_max = float(self.spectrum_x_max_input.text())
            if x_min >= x_max:
                raise ValueError

            self.auto_spectrum_x.setChecked(False)
            self.ax.set_xlim(x_min, x_max)

            y_data_in_x_range = []
            for line in lines:
                x_data = line.get_xdata()  # 현재 라인의 X 데이터
                y_data = line.get_ydata()  # 현재 라인의 Y 데이터

                # x_data가 list라면 NumPy 배열로 변환
                x_data = np.array(x_data)
                y_data = np.array(y_data)  # y_data도 NumPy 배열로 변환

                # X 범위에 해당하는 값들만 필터링
                mask = (x_data >= x_min) & (x_data <= x_max)  # X 범위에 해당하는 값들만 필터링
                y_filtered = y_data[mask]  # 해당 범위의 Y값만 추출
                y_data_in_x_range.extend(y_filtered)  # Y 데이터 모은 리스트에 추가

            if y_data_in_x_range:  # 데이터가 있을 경우만
                y_min = min(y_data_in_x_range)
                y_max = max(y_data_in_x_range)
                ax.set_ylim(y_min, y_max)  # Y축 범위 설정

            self.auto_spectrum_y.setChecked(False)  # Y축 자동 스케일 해제

            self.canvas.draw()
        except ValueError:
            print("")

    def set_y_axis(self):
        # ✅ Auto Scale이 활성화되어 있으면 입력값 무시
        if self.auto_spectrum_y.isChecked():
            return
        # ⭐ 안전한 마커 제거
        for marker, label in self.markers:
            try:
                marker.remove()
            except (NotImplementedError, ValueError, AttributeError):
                try:
                    marker.set_data([], [])
                except:
                    pass
            try:
                label.remove()
            except (NotImplementedError, ValueError, AttributeError):
                try:
                    label.set_visible(False)
                except:
                    pass
        self.markers.clear()
        try:
            y_min = float(self.spectrum_y_min_input.text())
            y_max = float(self.spectrum_y_max_input.text())
            if y_min >= y_max:
                raise ValueError
            self.auto_spectrum_y.setChecked(False)
            self.ax.set_ylim(y_min, y_max)
            self.canvas.draw()
        except ValueError:
            print("")

    def auto_scale_x(self):
        # ⭐ 안전한 마커 제거
        for marker, label in self.markers:
            try:
                marker.remove()
            except (NotImplementedError, ValueError, AttributeError):
                try:
                    marker.set_data([], [])
                except:
                    pass
            try:
                label.remove()
            except (NotImplementedError, ValueError, AttributeError):
                try:
                    label.set_visible(False)
                except:
                    pass
        self.markers.clear()
        ax = self.canvas.figure.axes[0]  # matplotlib 축 객체
        self.auto_spectrum_x.setChecked(True)
        self.auto_spectrum_y.setChecked(True)
        ax.autoscale(enable=True, axis='x')
        self.canvas.draw()

    def auto_scale_y(self):
        # ⭐ 안전한 마커 제거
        for marker, label in self.markers:
            try:
                marker.remove()
            except (NotImplementedError, ValueError, AttributeError):
                try:
                    marker.set_data([], [])
                except:
                    pass
            try:
                label.remove()
            except (NotImplementedError, ValueError, AttributeError):
                try:
                    label.set_visible(False)
                except:
                    pass
        self.markers.clear()
        ax = self.canvas.figure.axes[0]  # matplotlib 축 객체
        self.auto_spectrum_y.setChecked(True)
        ax.autoscale(enable=True, axis='y')
        self.canvas.draw()

    def set_wave_x_axis(self):
        # ✅ Auto Scale이 활성화되어 있으면 입력값 무시
        if self.auto_wave_x.isChecked():
            return
        try:
            # 현재 그래프의 첫 번째 축 객체와 그 안의 라인 객체들
            ax = self.wavecanvas.figure.axes[0]  # matplotlib 축 객체
            lines = ax.get_lines()  # 그래프 라인들

            x_min = float(self.x_min_input.text())
            x_max = float(self.x_max_input.text())
            if x_min >= x_max:
                raise ValueError

            self.auto_wave_x.setChecked(False)
            self.waveax.set_xlim(x_min, x_max)

            y_data_in_x_range = []
            for line in lines:
                x_data = line.get_xdata()  # 현재 라인의 X 데이터
                y_data = line.get_ydata()  # 현재 라인의 Y 데이터
                mask = (x_data >= x_min) & (x_data <= x_max)  # X 범위에 해당하는 값들만 필터링
                y_filtered = y_data[mask]  # 해당 범위의 Y값만 추출
                y_data_in_x_range.extend(y_filtered)  # Y 데이터 모은 리스트에 추가

            if y_data_in_x_range:  # 데이터가 있을 경우만
                y_min = min(y_data_in_x_range)
                y_max = max(y_data_in_x_range)
                ax.set_ylim(y_min, y_max)  # Y축 범위 설정

            self.auto_wave_y.setChecked(False)  # Y축 자동 스케일 해제

            self.wavecanvas.draw()
        except ValueError:
            print("")

    def set_wave_y_axis(self):
        # ✅ Auto Scale이 활성화되어 있으면 입력값 무시
        if self.auto_wave_y.isChecked():
            return
        try:
            y_min = float(self.y_min_wave_input.text())
            y_max = float(self.y_max_wave_input.text())
            if y_min >= y_max:
                raise ValueError
            self.auto_wave_y.setChecked(False)
            self.waveax.set_ylim(y_min, y_max)
            self.wavecanvas.draw()
        except ValueError:
            print("")

    def auto_wave_scale_x(self):
        ax = self.wavecanvas.figure.axes[0]  # matplotlib 축 객체
        self.auto_wave_x.setChecked(True)
        self.auto_wave_y.setChecked(True)
        ax.autoscale(enable=True, axis='x')
        self.wavecanvas.draw()

    def auto_wave_scale_y(self):
        ax = self.wavecanvas.figure.axes[0]  # matplotlib 축 객체
        self.auto_wave_y.setChecked(True)
        ax.autoscale(enable=True, axis='y')
        self.wavecanvas.draw()

    def on_mouse_move(self, event):
        if not self.mouse_tracking_enabled:  # X축 범위 설정 중에는 마우스 이벤트 무시
            return
        """마우스가 그래프 위를 움직일 때 가장 가까운 점을 찾아서 점 표시"""
        if not event.inaxes:
            if self.hover_pos2 is not None:  # hover_pos가 None이 아니면 점을 지우기
                self.hover_dot2.set_data([], [])
                self.hover_pos2 = None
                self.canvas.draw()
            return

        closest_x, closest_y, min_dist = None, None, np.inf  # np.inf로 수정

        # 모든 라인에서 가장 가까운 점 찾기
        for line in self.ax.get_lines():
            x_data_move, y_data_move = line.get_xdata(), line.get_ydata()

            # 데이터가 없으면 건너뛴다
            if len(x_data_move) == 0 or len(y_data_move) == 0:
                continue

            # datetime 타입이면 float(ordinal)로 변환
            if isinstance(x_data_move[0], datetime):
                x_data_move = mdates.date2num(x_data_move)
                self.initialize_hover_step(x_data_move, y_data_move)  # datetime 처리 후 호출

            for x, y in zip(x_data_move, y_data_move):
                dist = np.hypot(event.xdata - x, event.ydata - y)
                if dist < min_dist:
                    min_dist = dist
                    closest_x, closest_y = x, y

        # 가장 가까운 점이 존재하면 해당 점을 표시
        if closest_x is not None:
            self.hover_dot2.set_data([closest_x], [closest_y])
            self.hover_pos2 = [closest_x, closest_y]  # 현재 좌표 저장
            self.canvas.draw()

    def clear_marker(self):
        """마커와 주석을 안전하게 제거"""
        for marker, label in self.markers:
            try:
                marker.remove()
            except (NotImplementedError, ValueError, AttributeError):
                # remove()가 지원되지 않으면 set_data로 초기화
                try:
                    marker.set_data([], [])
                except:
                    pass

            try:
                label.remove()
            except (NotImplementedError, ValueError, AttributeError):
                try:
                    label.set_visible(False)
                except:
                    pass

        self.markers.clear()

        # 캔버스 강제 업데이트
        try:
            self.canvas.draw_idle()
        except:
            pass

    def on_mouse_click(self, event):
        """마우스를 클릭했을 때 가장 가까운 점을 고정된 마커로 표시"""
        if not event.inaxes:
            return

        # hover_dot 위치를 가져와서 마커로 고정
        x, y = self.hover_dot2.get_data()

        if x and y:
            self.add_marker(x, y)

        if event.button == 3:  # 오른쪽 클릭
            for marker, label in self.markers:
                marker.remove()
                label.remove()
            self.markers.clear()

            # for annotation in self.annotations:
            #         annotation.remove()
            # self.annotations.clear()
            # for filename in self.marker_filenames:
            #         self.remove_marker_filename_from_list(filename)
            # self.marker_filenames.clear()

            self.canvas.draw()
            return

    def initialize_hover_step2(self, x_data, y_data):
        x_spacing = np.mean(np.diff(x_data))
        y_spacing = np.mean(np.diff(y_data))
        self.hover_step = [x_spacing, y_spacing]

    def on_key_press(self, event):
        """키보드 입력 처리 (방향키로 점 이동, 엔터로 마커 고정)"""
        x, y = self.hover_dot2.get_data()

        # 모든 라인에서 x, y 데이터를 가져옵니다.
        all_x_data = []
        all_y_data = []
        for line in self.ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()
            if len(x_data) == 0 or len(y_data) == 0:
                continue
            if isinstance(x_data[0], datetime):
                x_data = mdates.date2num(x_data)
            all_x_data.extend(x_data)
            all_y_data.extend(y_data)
            self.initialize_hover_step2(x_data, y_data)

        # 현재 x, y를 기준으로 가장 가까운 점을 찾기
        closest_index = None
        current_index = None
        min_dist = np.inf
        for idx, (x_val, y_val) in enumerate(zip(all_x_data, all_y_data)):
            dist = np.hypot(x - x_val, y - y_val)
            if dist < min_dist:
                min_dist = dist
                current_index = idx

        if current_index is None:
            return  # 아무 데이터도 없으면 종료

        # 이동할 다음 데이터 찾기
        candidates = []
        if event.key == 'left':
            # x값이 작아지는 방향으로 이동
            candidates = [(i, abs(all_x_data[i] - x)) for i in range(len(all_x_data)) if all_x_data[i] < x]
        elif event.key == 'right':
            # x값이 커지는 방향으로 이동
            candidates = [(i, abs(all_x_data[i] - x)) for i in range(len(all_x_data)) if all_x_data[i] > x]
        elif event.key == 'up':
            candidates = [
                (i, abs(all_y_data[i] - y))
                for i in range(len(all_y_data))
                if abs(all_x_data[i] - x) < 1e-6 and all_y_data[i] > y
            ]
        elif event.key == 'down':
            candidates = [
                (i, abs(all_y_data[i] - y))
                for i in range(len(all_y_data))
                if abs(all_x_data[i] - x) < 1e-6 and all_y_data[i] < y
            ]
        elif event.key == 'enter':
            self.add_marker(all_x_data[current_index], all_y_data[current_index])
            return
        if candidates:
            # 가장 가까운 x 또는 y를 가진 index 선택
            candidates.sort(key=lambda t: t[1])  # 거리 기준 정렬
            current_index = candidates[0][0]

        # 이동된 위치로 hover_dot 위치 업데이트
        new_x = all_x_data[current_index]
        new_y = all_y_data[current_index]
        self.hover_pos2 = [new_x, new_y]
        self.hover_dot2.set_data([new_x], [new_y])
        self.canvas.draw()

    def add_marker(self, x, y):
        """마커 점과 텍스트를 동시에 추가"""

        min_distance = float('inf')
        closest_file = None
        closest_x = closest_y = None
        closest_index = None

        for file_name, (data_x, data_y) in self.data_dict.items():
            x_array = np.array(data_x)
            y_array = np.array(data_y)
            idx = (np.abs(x_array - x)).argmin()
            x_val = x_array[idx]
            y_val = y_array[idx]

            # y_input이 있으면 마우스 클릭 거리로, 없으면 x 거리만
            if y is not None:
                dist = np.hypot(x_val - x, y_val - y)
            else:
                dist = abs(x_val - x)

            dist = np.hypot(x_val - x, y_val - y)

            if dist < min_distance:
                min_distance = dist
                closest_file = file_name
                closest_x, closest_y = x_val, y_val
                matched_index = idx

        if closest_file is not None:
            x_list, y_list = self.data_dict[closest_file]
            if (
                    matched_index is not None
                    and matched_index < len(x_list)
                    and x_list[matched_index] == closest_x
                    and y_list[matched_index] == closest_y
            ):
                marker = \
                self.ax.plot(np.round(closest_x, 4), np.round(closest_y, 4), marker='o', color='red', markersize=7)[0]

            label = self.ax.text(
                float(closest_x), float(closest_y) + 0.001,
                f"file: {closest_file}\nX: {float(closest_x):.4f}, Y: {float(closest_y):.4f}",
                fontsize=7, fontweight='bold', color='black',
                ha='center', va='bottom'
            )
            self.markers.append((marker, label))
            # self.annotations.append(annotation)
            self.canvas.draw()

    def update_filtered_files(self):
        if not hasattr(self, "selected_files"):  # Data Query에서 선택한 파일 목록이 없으면 return
            return

        # ✅ 체크박스 그룹을 리스트로 관리
        checkboxes = [
            self.checkBox, self.checkBox_2, self.checkBox_3, self.checkBox_4, self.checkBox_5, self.checkBox_6
        ]

        suffixes = ["1", "2", "3", "4", "5", "6"]

        # ✅ 체크된 채널 번호만 리스트로 수집
        selected_suffixes = [suffixes[i % 6] for i, cb in enumerate(checkboxes) if cb.isChecked()]

        # ✅ 체크 해제 시 전체 파일을 표시하도록 처리
        if not selected_suffixes:
            self.Querry_list.clear()
            self.Querry_list.addItems(self.selected_files)

            return  # ✅ 체크 해제 시 전체 파일을 표시하고 함수 종료

        # 선택된 채널 번호가 포함된 파일만 필터링
        filtered_files = [f for f in self.selected_files if any(f.endswith(f"_{s}.txt") for s in selected_suffixes)]

        # ✅ 필터링된 결과를 리스트에 반영
        self.Querry_list.clear()
        self.Querry_list.addItems(filtered_files)

        # ✅ UI 강제 업데이트 (필요할 경우)
        self.Querry_list.repaint()

        # ✅ 채널 선택이 변경될 때마다 그래프 자동 업데이트
        # self.plot_signal_data()

    def load_file_data(self, file_name):
        file_path = os.path.join(self.directory_path, file_name)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # ✅ 'Record Length' 값 추출 (예: 30 from "Record Length : 30 s")
            record_length = None
            for line in lines:
                if "Record Length" in line:
                    match = re.search(r"Record Length\s*:\s*(\d+(?:\.\d+)?)", line)
                    if match:
                        record_length = float(match.group(1))
                    break  # 찾았으면 반복 중지

            # ✅ 숫자가 포함된 줄만 필터링 (텍스트 제거)
            numeric_lines = [line for line in lines if re.match(r"^\s*[-+]?\d*\.?\d+", line)]

            # ✅ 한 줄씩 처리하여 numpy 배열로 변환
            data = []
            for line in numeric_lines:
                # 각 줄을 공백 기준으로 분리하여 숫자 배열로 변환
                data.append(list(map(float, line.split())))

            data = np.array(data)

            return data, record_length

        except Exception as e:
            return np.array([])  # 오류 발생 시 빈 배열 반환

    def update_overlap_factor(self):
        """ 사용자가 선택한 Overlap Factor 값을 적용 """
        overlap_text = self.Overlap_Factor.currentText()  # UI에서 선택한 값 가져오기
        overlap_mapping = {"0%": 0, "25%": 0.25, "50%": 0.5, "75%": 0.75}

        self.overlap_factor = overlap_mapping.get(overlap_text, 0.5)  # 기본값 50%

        # UI 이벤트 연결 (사용자가 선택하면 update_overlap_factor 실행됨)
        self.Overlap_Factor.currentIndexChanged.connect(self.update_overlap_factor)

    def plot_waterfall_spectrum(self, x_min=None, x_max=None, z_min=None, z_max=None, force_recalculate=False):
        """
        3D Waterfall 스펙트럼 그래프
        force_recalculate=True: FFT 재계산
        force_recalculate=False: 캐시 사용 (축 조정/각도 변경 시)
        """

        selected_items = self.Querry_list2.selectedItems()
        if not selected_items:
            QMessageBox.critical(None, "오류", "파일을 선택하세요")
            return

        # ===== 파라미터 읽기 =====
        try:
            delta_f = float(self.Hz_2.toPlainText())
            overlap = float(self.Overlap_Factor_2.currentText().replace('%', ''))
            window_type = self.Function_2.currentText().lower()
            view_type = self.select_pytpe2.currentData()
            angle = float(self.angle_input.text()) if self.angle_input.text().strip() else 270.0
        except ValueError as e:
            QMessageBox.critical(None, "입력 오류", str(e))
            return

        # ===== 캐시 유효성 검사 =====
        current_params = {
            'delta_f': delta_f,
            'overlap': overlap,
            'window_type': window_type,
            'view_type': view_type,
            'file_count': len(selected_items),
            'file_names': tuple(item.text() for item in selected_items)
        }

        cache_valid = (
                hasattr(self, 'waterfall_cache') and
                self.waterfall_cache.get('computed', False) and
                self.waterfall_cache.get('params') == current_params and
                not force_recalculate
        )

        # ===== FFT 계산 (필요시에만) =====
        if not cache_valid:
            print("🔄 Waterfall FFT 재계산 중...")

            # 캐시 초기화
            if not hasattr(self, 'waterfall_cache'):
                self.waterfall_cache = {}

            self.waterfall_cache['spectra'] = []

            self.progress_dialog = ProgressDialog(len(selected_items), self.main_window)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.show()

            # 시간 정렬
            items_with_time = []
            for item in selected_items:
                file_name = item.text()
                try:
                    timestamp = self.extract_timestamp_from_filename(file_name)
                except Exception:
                    timestamp = datetime.datetime.max
                items_with_time.append((item, timestamp))

            sorted_items = sorted(items_with_time, key=lambda x: x[1], reverse=False)

            for draw_idx, (item, timestamp) in enumerate(sorted_items):
                file_name = item.text()
                file_path = os.path.join(self.directory_path, file_name)

                self.progress_dialog.label.setText(f"{file_name} 처리 중...")

                # 데이터 로드
                data, record_length = self.load_file_data(file_name)

                if data is None or len(data) == 0:
                    self.progress_dialog.update_progress(draw_idx + 1)
                    continue

                # 메타데이터 읽기
                sampling_rate = None
                b_sensitivity = None
                sensitivity = None

                try:
                    with open(file_path, 'r') as file:
                        for line in file:
                            if "D.Sampling Freq. " in line:
                                sampling_rate_str = line.split(":")[1].strip()
                                sampling_rate = float(sampling_rate_str.replace("Hz", "").strip())
                            elif "b.Sensitivity" in line and b_sensitivity is None:
                                b_sensitivity = line.split(":")[1].strip().split()[0]
                            elif "Sensitivity" in line:
                                sensitivity = line.split(":")[1].strip()
                except Exception as e:
                    print(f"⚠ {file_name} - 메타데이터 파싱 오류: {e}")

                if sampling_rate is None or sampling_rate <= 0:
                    self.progress_dialog.update_progress(draw_idx + 1)
                    continue

                # 민감도 보정
                def extract_numeric_value(s):
                    if s is None:
                        return None
                    match = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
                    return float(match.group()) if match else None

                try:
                    if b_sensitivity is not None and sensitivity is not None:
                        b_sens = extract_numeric_value(b_sensitivity)
                        sens = extract_numeric_value(sensitivity)
                        if b_sens is not None and sens is not None and sens != 0:
                            scaled_data = (b_sens / sens) * data
                        else:
                            scaled_data = data
                    else:
                        scaled_data = data
                except Exception as e:
                    scaled_data = data

                # Delta_f 보정
                if record_length:
                    duration = float(record_length)
                    hz_value = round(1 / duration + 0.01, 2)
                    delta_f = max(delta_f, hz_value)

                # FFT 계산
                try:
                    win_flag = {"rectangular": 0, "hanning": 1, "flattop": 2}.get(window_type, 1)
                    w, f, P, ACF, ECF, rms_w, Sxx = self.mdl_FFT_N(
                        2, sampling_rate, scaled_data, delta_f, overlap,
                        win_flag, 1, view_type, 0
                    )
                except Exception as e:
                    print(f"❌ FFT 계산 실패: {e}")
                    self.progress_dialog.update_progress(draw_idx + 1)
                    continue

                P_magnitude = np.round(np.mean(ACF * np.abs(P), axis=1), 4)

                # X축 라벨 생성
                try:
                    name_only = os.path.splitext(file_name)[0]
                    parts = name_only.split("_")
                    if len(parts) >= 3:
                        date = parts[0]
                        time = parts[1]
                        rest = '_'.join(parts[2:])
                        x_label = f"{date}\n{time}_{rest}"
                    else:
                        x_label = file_name
                except:
                    x_label = file_name

                # ⭐ 결과 캐싱
                self.waterfall_cache['spectra'].append({
                    'file_name': file_name,
                    'frequency': f,
                    'spectrum': P_magnitude,
                    'timestamp': timestamp,
                    'x_label': x_label,
                    'sampling_rate': sampling_rate
                })

                self.progress_dialog.update_progress(draw_idx + 1)

            self.progress_dialog.close()

            # ⭐ 캐시 상태 업데이트
            self.waterfall_cache['computed'] = True
            self.waterfall_cache['params'] = current_params

            print(f"✅ Waterfall 캐시 생성 완료 ({len(self.waterfall_cache['spectra'])}개 파일)")

        else:
            print("✅ 캐시된 Waterfall 데이터 사용")

        # ===== 그래프 렌더링 (항상 실행) =====
        self.waterfall_figure.clf()
        self.waterfall_ax = self.waterfall_figure.add_subplot(111)
        self.waterfall_ax.set_title("Waterfall Spectrum", fontsize=7, fontname='Malgun Gothic')

        # X/Z 범위 결정
        if len(self.waterfall_cache['spectra']) == 0:
            print("❌ 표시할 데이터가 없습니다")
            return

        # 전역 범위 계산
        all_frequencies = []
        all_spectra = []
        for cached in self.waterfall_cache['spectra']:
            all_frequencies.extend(cached['frequency'])
            all_spectra.extend(cached['spectrum'])

        global_xmin = np.min(all_frequencies)
        global_xmax = np.max(all_frequencies)
        global_zmin = np.min(all_spectra)
        global_zmax = np.max(all_spectra)

        if x_min is None:
            x_min = global_xmin
        if x_max is None:
            x_max = global_xmax
        if z_min is None:
            z_min = global_zmin
        if z_max is None:
            z_max = global_zmax

        # 각도 설정
        angle_deg = angle
        angle_rad = np.deg2rad(angle_deg)

        # Y축 고정 범위
        fixed_ymin, fixed_ymax = 0, 130
        num_files = len(self.waterfall_cache['spectra'])
        offset_range = fixed_ymax - fixed_ymin
        offset_distance = offset_range / num_files
        dx = offset_distance * np.cos(angle_rad)
        dy = offset_distance * np.sin(angle_rad)

        # 라벨 위치 계산
        max_labels = 5
        total_files = len(self.waterfall_cache['spectra'])
        label_indices = list(range(total_files)) if total_files <= max_labels else \
            np.linspace(0, total_files - 1, max_labels, dtype=int)

        yticks_for_labels = []
        labels_for_ticks = []

        # 그래프 그리기
        for draw_idx, cached_data in enumerate(self.waterfall_cache['spectra']):
            f = cached_data['frequency']
            P_magnitude = cached_data['spectrum']
            file_name = cached_data['file_name']
            x_label = cached_data['x_label']

            # X축 필터링
            mask_freq = (f >= x_min) & (f <= x_max)
            f_filtered = f[mask_freq]
            p_filtered = P_magnitude[mask_freq]

            # X 정규화
            x_range = x_max - x_min
            f_normalized = (f_filtered - x_min) / x_range
            x_scale = 530

            # Y 정규화
            global_max = np.max(all_spectra)
            if z_min is not None and z_max is not None and z_max > z_min:
                p_clipped = np.clip(p_filtered, z_min, z_max)
                y_normalized = (p_clipped - z_min) / (z_max - z_min)
            else:
                y_normalized = p_filtered / global_max

            scale_factor = (fixed_ymax - fixed_ymin) * 1
            y_scaled = y_normalized * scale_factor

            # Offset 적용
            base_x = draw_idx * dx
            base_y = draw_idx * dy
            offset_x = f_normalized * x_scale + base_x
            offset_y = y_scaled + base_y

            # 그래프 그리기
            self.waterfall_ax.plot(offset_x, offset_y, alpha=0.6, label=file_name)

            # 첫 번째 그래프에만 X/Y축 tick 표시
            if draw_idx == 0:
                if len(offset_x) >= 2:
                    xticks = np.linspace(offset_x[0], offset_x[-1], 7)
                    xtick_labels = np.linspace(x_min, x_max, 7)
                    self.waterfall_ax.set_xticks(xticks)
                    self.waterfall_ax.set_xticklabels([f"{val:.1f}" for val in xtick_labels])

                if z_min is not None and z_max is not None and len(offset_y) >= 2:
                    self.waterfall_ax.yaxis.set_ticks_position('left')
                    ymin = min(offset_y)
                    ymax = max(offset_y)
                    yticks = np.linspace(ymin, ymax, 7)
                    ytick_labels = np.linspace(z_min, z_max, 7)
                    self.waterfall_ax.set_yticks(yticks)
                    self.waterfall_ax.set_yticklabels([f"{val:.4f}" for val in ytick_labels], fontsize=7)
                    self.waterfall_ax.tick_params(axis='y', labelleft=True)
                    self.waterfall_ax.set_ylim(0, 150)

            # 라벨 저장
            if draw_idx in label_indices:
                center_y = np.min(offset_y)
                base_name = file_name.replace(".txt", "")
                parts = base_name.split("_")
                if len(parts) >= 2:
                    label_text = parts[0] + "_" + parts[1] + "\n" + "_".join(parts[2:])
                else:
                    label_text = base_name

                yticks_for_labels.append(center_y)
                labels_for_ticks.append(label_text)

        # 오른쪽 Y축 라벨
        ax_right = self.waterfall_ax.twinx()
        ax_right.set_ylim(self.waterfall_ax.get_ylim())
        ax_right.set_yticks([])
        ax_right.tick_params(right=False)

        for y, label in zip(yticks_for_labels, labels_for_ticks):
            ax_right.text(1.02, y, label, transform=ax_right.get_yaxis_transform(),
                          fontsize=7, va='center', ha='left')

        # Y축 라벨
        view_type_map = {1: "ACC", 2: "VEL", 3: "DIS"}
        view_type_str = view_type_map.get(view_type, "ACC")
        labels = {
            "ACC": "Vibration Acceleration \n (m/s^2, RMS)",
            "VEL": "Vibration Velocity \n (mm/s, RMS)",
            "DIS": "Vibration Displacement \n (μm , RMS)"
        }
        zlabel = labels.get(view_type_str, "RMS Vibration (mm/s, RMS)")
        self.waterfall_ax.set_ylabel(zlabel, fontsize=7, fontname='Malgun Gothic')
        self.waterfall_ax.set_xlabel("Frequency (Hz)", fontsize=7)

        # ⭐ 폰트 크기 동적 조정
        font_size = self.get_dynamic_font_size(10)
        self.waterfall_ax.xaxis.label.set_fontsize(font_size - 2)
        self.waterfall_ax.yaxis.label.set_fontsize(font_size - 2)
        self.waterfall_ax.tick_params(labelsize=font_size - 3)

        # 배경 설정
        self.waterfall_figure.patch.set_facecolor('white')
        self.waterfall_ax.set_facecolor('white')
        self.waterfall_ax.tick_params(axis='y', labelrotation=0)
        self.waterfall_ax.tick_params(axis='x', labelsize=7)
        self.waterfall_ax.tick_params(axis='y', labelsize=7)

        # ⭐ X축 그리드 추가 (등간격 기준)
        x_range = x_max - x_min
        if x_range <= 100:
            interval = 10
        elif x_range <= 200:
            interval = 20
        elif x_range <= 500:
            interval = 50
        elif x_range <= 1000:
            interval = 100
        elif x_range <= 2000:
            interval = 200
        elif x_range <= 5000:
            interval = 500
        else:
            interval = 1000

        grid_ticks = np.arange(
            int(x_min / interval) * interval,
            x_max + interval,
            interval
        )

        # 그리드 그리기 (첫 번째 그래프 기준으로 변환)
        if len(self.waterfall_cache['spectra']) > 0:
            first_f = self.waterfall_cache['spectra'][0]['frequency']
            mask = (first_f >= x_min) & (first_f <= x_max)
            f_filtered = first_f[mask]

            if len(f_filtered) >= 2:
                f_normalized = (f_filtered - x_min) / x_range
                offset_x_first = f_normalized * x_scale

                for tick_val in grid_ticks:
                    if x_min <= tick_val <= x_max:
                        # tick_val을 offset_x 좌표로 변환
                        normalized = (tick_val - x_min) / x_range
                        x_pos = normalized * x_scale
                        self.waterfall_ax.axvline(x=x_pos, color='gray', linestyle='--',
                                                  linewidth=0.5, alpha=0.3)

        self.waterfall_canvas.draw()

    def show_full_view_x(self):
        try:
            x_min = None
            x_max = None
            self.current_x_min = x_min
            self.current_x_max = x_max

            self.auto_scale_x_2.setChecked(True)

            # ⭐ force_recalculate=False
            self.plot_waterfall_spectrum(
                x_min=x_min,
                x_max=x_max,
                z_min=self.current_z_min,
                z_max=self.current_z_max,
                force_recalculate=False
            )

        except ValueError:
            print("")

    def show_full_view_z(self):
        try:
            z_min = None
            z_max = None
            self.current_z_min = z_min
            self.current_z_max = z_max

            self.auto_scale_z.setChecked(True)

            # ⭐ force_recalculate=False
            self.plot_waterfall_spectrum(
                x_min=self.current_x_min,
                x_max=self.current_x_max,
                z_min=z_min,
                z_max=z_max,
                force_recalculate=False
            )

        except ValueError:
            print("")

    def set_x_axis2(self):
        """X축 조정 - 재계산 없이 View만 변경"""
        try:
            x_min = float(self.x_min_input2.text())
            x_max = float(self.x_max_input2.text())
            if x_min >= x_max:
                raise ValueError

            self.current_x_min = x_min
            self.current_x_max = x_max
            self.auto_scale_x_2.setChecked(False)

            # ⭐ force_recalculate=False (재계산 안 함)
            self.plot_waterfall_spectrum(
                x_min=x_min,
                x_max=x_max,
                z_min=self.current_z_min,
                z_max=self.current_z_max,
                force_recalculate=False  # ← 핵심!
            )

        except ValueError:
            print("")


    def set_z_axis(self):
        """Z축 조정 - 재계산 없이 View만 변경"""
        try:
            z_min = float(self.z_min_input.text())
            z_max = float(self.z_max_input.text())
            if z_min >= z_max:
                raise ValueError

            self.current_z_min = z_min
            self.current_z_max = z_max
            self.auto_scale_z.setChecked(False)

            # ⭐ force_recalculate=False
            self.plot_waterfall_spectrum(
                x_min=self.current_x_min,
                x_max=self.current_x_max,
                z_min=z_min,
                z_max=z_max,
                force_recalculate=False
            )

        except ValueError:
            print("")

    def extract_timestamp_from_filename(self, filename):
        """
                파일 이름에서 날짜 및 시간을 추출하는 함수.
                파일 이름이 'YYYY-MM-DD_HH-MM-SS' 형식이어야 합니다.
                예외가 발생할 경우 현재 시간으로 대체합니다.
                """

        # 파일 이름에서 'YYYY-MM-DD_HH-MM-SS' 부분만 추출하는 정규 표현식
        match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)

        if match:
            timestamp_str = match.group(1)

            # '_'를 ' '로 변환하고, '-'는 시간 부분에서만 ':'로 변환
            timestamp_str = timestamp_str.replace('_', ' ')  # 날짜와 시간을 공백으로 구분
            timestamp_str = timestamp_str[:10] + ' ' + timestamp_str[11:].replace('-', ':')  # 시간 부분만 변경

            try:
                # datetime 형식으로 변환
                file_timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d \n %H:%M:%S")
                return file_timestamp

            except ValueError:
                return datetime.now()  # 잘못된 형식일 경우 현재 시간으로 대체
        else:
            return datetime.now()  # 시간 정보를 찾을 수 없을 경우 현재 시간으로 대체

    def update_querry_list2(self):
        """✅ 선택한 채널에 해당하는 파일만 `Querry_list2`에 표시하고, 선택이 해제되면 전체 파일 표시"""

        if not hasattr(self, "selected_files"):  # 선택된 파일이 없으면 리턴
            return

        # ✅ **사용자가 체크한 채널 (1CH ~ 6CH) 확인**
        selected_channels = []
        checkboxes = [
            self.checkBox_7, self.checkBox_8, self.checkBox_9,
            self.checkBox_10, self.checkBox_11, self.checkBox_12
        ]
        for idx, checkbox in enumerate(checkboxes, start=1):
            if checkbox.isChecked():
                selected_channels.append(str(idx))  # 선택된 채널 번호 저장 (예: "1", "2", ...)

        # ✅ **채널이 선택되지 않았다면 전체 파일 다시 표시**
        if not selected_channels:
            self.Querry_list2.clear()
            self.Querry_list2.addItems(self.selected_files)
            return

        # ✅ **선택한 채널과 일치하는 파일만 필터링**
        filtered_files = [f for f in self.selected_files if any(f.endswith(f"_{ch}.txt") for ch in selected_channels)]

        # ✅ `Querry_list2` 업데이트
        self.Querry_list2.clear()
        self.Querry_list2.addItems(filtered_files)

    def update_querry_list3(self):
        """✅ 선택한 채널에 해당하는 파일만 `Querry_list3`에 표시하고, 선택이 해제되면 전체 파일 표시"""

        if not hasattr(self, "selected_files"):  # 선택된 파일이 없으면 리턴
            return

        # ✅ **사용자가 체크한 채널 (1CH ~ 6CH) 확인**
        selected_channels = []
        checkboxes = [
            self.checkBox_13, self.checkBox_14, self.checkBox_15,
            self.checkBox_16, self.checkBox_17, self.checkBox_18
        ]
        for idx, checkbox in enumerate(checkboxes, start=1):
            if checkbox.isChecked():
                selected_channels.append(str(idx))  # 선택된 채널 번호 저장 (예: "1", "2", ...)

        # ✅ **채널이 선택되지 않았다면 전체 파일 다시 표시**
        if not selected_channels:
            self.Querry_list3.clear()
            self.Querry_list3.addItems(self.selected_files)
            return

        # ✅ **선택한 채널과 일치하는 파일만 필터링**
        filtered_files = [f for f in self.selected_files if any(f.endswith(f"_{ch}.txt") for ch in selected_channels)]

        # ✅ `Querry_list3` 업데이트
        self.Querry_list3.clear()
        self.Querry_list3.addItems(filtered_files)

    def update_querry_list4(self):
        """✅ 선택한 채널에 해당하는 파일만 `Querry_list3`에 표시하고, 선택이 해제되면 전체 파일 표시"""

        if not hasattr(self, "selected_files"):  # 선택된 파일이 없으면 리턴
            return

        # ✅ **사용자가 체크한 채널 (1CH ~ 6CH) 확인**
        selected_channels = []
        checkboxes = [
            self.checkBox_19, self.checkBox_20, self.checkBox_21,
            self.checkBox_22, self.checkBox_23, self.checkBox_24
        ]
        for idx, checkbox in enumerate(checkboxes, start=1):
            if checkbox.isChecked():
                selected_channels.append(str(idx))  # 선택된 채널 번호 저장 (예: "1", "2", ...)

        # ✅ **채널이 선택되지 않았다면 전체 파일 다시 표시**
        if not selected_channels:
            self.Querry_list4.clear()
            self.Querry_list4.addItems(self.selected_files)
            return

        # ✅ **선택한 채널과 일치하는 파일만 필터링**
        filtered_files = [f for f in self.selected_files if any(f.endswith(f"_{ch}.txt") for ch in selected_channels)]

        # ✅ `Querry_list3` 업데이트
        self.Querry_list4.clear()
        self.Querry_list4.addItems(filtered_files)

    def delite(self):
        for marker in self.trend_markers:
            marker.remove()
        self.trend_markers.clear()

        for annotation in self.trend_annotations:
            annotation.remove()
        self.trend_annotations.clear()

        for filename in self.trend_marker_filenames:
            self.remove_marker_filename_from_list(filename)
        self.trend_marker_filenames.clear()

    def plot_trend(self):
        """
        ⭐ Level 5 최적화: 병렬 Trend 분석
        - 1000개: 18분 → 2-3분
        - 10000개: 3시간 → 20-30분
        """
        from OPTIMIZATION_PATCH_LEVEL5_TREND import TrendParallelProcessor
        from PyQt5.QtWidgets import QMessageBox, QApplication
        from PyQt5.QtCore import Qt
        import matplotlib.dates as mdates

        perf_logger.log_info("🚀 plot_trend 시작 (Level 5)")
        start_total = perf_logger.start_timer("전체 Trend 분석")

        # ===== 1. 파라미터 준비 =====
        selected_items = self.Querry_list3.selectedItems()
        if not selected_items:
            QMessageBox.critical(None, "오류", "파일을 선택하세요")
            return

        try:
            delta_f = float(self.Hz_3.toPlainText().strip())
            overlap = float(self.Overlap_Factor_3.currentText().replace('%', '').strip())
            window_type = self.Function_3.currentText()
            view_type = self.select_pytpe3.currentData()
            band_min = float(self.freq_range_inputmin.text().strip())
            band_max = float(self.freq_range_inputmax.text().strip())
        except ValueError as e:
            QMessageBox.critical(None, "입력 오류", f"파라미터 오류: {e}")
            return

        # ===== 2. 파일 경로 리스트 =====
        file_paths = [
            os.path.join(self.directory_path, item.text())
            for item in selected_items
        ]

        perf_logger.log_info(f"📁 파일 수: {len(file_paths)}")

        # ===== 3. 진행률 다이얼로그 =====
        self.progress_dialog = ProgressDialog(len(file_paths), self.main_window)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()

        def progress_update(current, total):
            self.progress_dialog.update_progress(current)
            self.progress_dialog.label.setText(f"처리 중... {current}/{total}")
            QApplication.processEvents()

        # ===== 4. 병렬 처리 =====
        processor = TrendParallelProcessor(max_workers=6)  # 6코어 활용

        perf_logger.log_info(f"🔥 병렬 처리 시작 ({processor.max_workers} 워커)")
        start_parallel = perf_logger.start_timer("병렬 Trend 처리")

        results = processor.process_batch(
            file_paths=file_paths,
            delta_f=delta_f,
            overlap=overlap,
            window_type=window_type,
            view_type=view_type,
            band_min=band_min,
            band_max=band_max,
            progress_callback=progress_update
        )

        perf_logger.end_timer("병렬 Trend 처리", start_parallel)

        # ===== 5. 성공/실패 집계 =====
        success_results = [r for r in results if r.success]
        failed_count = len(results) - len(success_results)

        perf_logger.log_info(f"✓ 성공: {len(success_results)}, ✗ 실패: {failed_count}")

        if not success_results:
            QMessageBox.warning(None, "경고", "처리된 데이터가 없습니다.")
            self.progress_dialog.close()
            return

        # ===== 6. 그래프 데이터 준비 =====
        self.trend_ax.clear()
        self.trend_ax.set_title("Overall RMS Trend", fontsize=7, fontname=DEFAULT_FONT)

        channel_data = {}
        x_labels = []
        trend_x_data = []
        trend_rms_values = []
        trend_file_names = []

        for result in success_results:
            # 채널 번호 추출
            channel_num = result.file_name.split('_')[-1].replace('.txt', '')

            if channel_num not in channel_data:
                channel_data[channel_num] = {"x": [], "y": [], "label": []}

            # 타임스탬프 추출
            try:
                timestamp = self.extract_timestamp_from_filename(result.file_name)
                x_value = timestamp
                x_label = timestamp.strftime("%Y-%m-%d\n%H:%M:%S")
            except:
                x_value = len(channel_data[channel_num]["x"])
                x_label = result.file_name

            channel_data[channel_num]["x"].append(x_value)
            channel_data[channel_num]["y"].append(result.rms_value)
            channel_data[channel_num]["label"].append(result.file_name)

            # 전체 데이터 저장
            trend_x_data.append(x_value)
            trend_rms_values.append(result.rms_value)
            trend_file_names.append(result.file_name)
            x_labels.append(x_label)

        # ===== 7. 그래프 렌더링 =====
        colors = ["r", "g", "b", "c", "m", "y"]

        for i, (ch, data) in enumerate(channel_data.items()):
            self.trend_ax.plot(
                data["x"], data["y"],
                label=f"Channel {ch}",
                color=colors[i % len(colors)],
                marker='o', markersize=2, linewidth=0.5
            )

        # ===== 8. X축 눈금 설정 =====
        sorted_pairs = sorted(zip(trend_x_data, x_labels))
        sorted_x, sorted_labels = zip(*sorted_pairs) if sorted_pairs else ([], [])

        num_ticks = min(10, len(sorted_x))
        if num_ticks > 0:
            tick_indices = np.linspace(0, len(sorted_x) - 1, num_ticks, dtype=int)
            tick_positions = [sorted_x[i] for i in tick_indices]
            tick_labels = [sorted_labels[i] for i in tick_indices]

            self.trend_ax.set_xticks(tick_positions)
            self.trend_ax.set_xticklabels(tick_labels, rotation=0, ha="right",
                                          fontsize=7, fontname=DEFAULT_FONT)

        # ===== 9. Y축 라벨 =====
        view_type_map = {1: "ACC", 2: "VEL", 3: "DIS"}
        view_type_str = view_type_map.get(view_type, "ACC")

        labels = {
            "ACC": "Vibration Acceleration\n(m/s², RMS)",
            "VEL": "Vibration Velocity\n(mm/s, RMS)",
            "DIS": "Vibration Displacement\n(μm, RMS)"
        }
        ylabel = labels.get(view_type_str, "Vibration (mm/s, RMS)")

        self.trend_ax.set_xlabel("Date & Time", fontsize=7, fontname=DEFAULT_FONT)
        self.trend_ax.set_ylabel(ylabel, fontsize=7, fontname=DEFAULT_FONT)
        self.trend_ax.set_facecolor('white')
        self.trend_ax.grid(True, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
        self.trend_ax.tick_params(axis='x', labelsize=7)
        self.trend_ax.tick_params(axis='y', labelsize=7)

        # ⭐ 범례 업데이트 추가
        self.update_legend_position(self.trend_ax, max_items=10)

        # ⭐ tight_layout 재적용
        try:
            self.trend_figure.tight_layout(rect=[0, 0, 0.88, 1])
        except:
            pass

        # 범례
        # handles, legend_labels = self.trend_ax.get_legend_handles_labels()
        # unique = dict()
        # for h, l in zip(handles, legend_labels):
        #     if l not in unique:
        #         unique[l] = h
        # self.trend_ax.legend(unique.values(), unique.keys(), fontsize=7)

        # ===== 10. 캔버스 그리기 =====
        self.trend_canvas.draw_idle()
        self.trend_canvas.flush_events()

        # ===== 11. JSON 저장 (병렬) =====
        perf_logger.log_info("💾 JSON 저장 시작")
        start_save = perf_logger.start_timer("JSON 배치 저장")

        from OPTIMIZATION_PATCH_LEVEL4_RENDERING import ParallelTrendSaver

        save_tasks = []
        for result in success_results:
            if result.success:
                save_tasks.append({
                    'file_name': result.file_name,
                    'rms_value': result.rms_value,
                    'delta_f': delta_f,
                    'window_type': window_type,
                    'overlap': overlap,
                    'band_min': band_min,
                    'band_max': band_max,
                    'sampling_rate': result.sampling_rate,
                    'start_time': result.metadata.get('start_time', ''),
                    'dt': '',
                    'duration': result.metadata.get('duration', ''),
                    'rest_time': '',
                    'repetition': '',
                    'iepe': '',
                    'sensitivity': result.metadata.get('sens', ''),
                    'b_sensitivity': result.metadata.get('b_sens', ''),
                    'channel_num': result.file_name.split('_')[-1].replace('.txt', ''),
                    'view_type': view_type_str,
                    'directory_path': self.directory_path
                })

        saver = ParallelTrendSaver(max_workers=6)
        save_result = saver.save_batch(save_tasks)

        perf_logger.end_timer("JSON 배치 저장", start_save)
        perf_logger.log_info(f"✓ JSON 저장: {save_result['success']}/{save_result['total']}")

        # ===== 12. 마우스 이벤트 연결 =====
        try:
            if hasattr(self, 'cid_move'):
                self.trend_canvas.mpl_disconnect(self.cid_move)
            if hasattr(self, 'cid_click'):
                self.trend_canvas.mpl_disconnect(self.cid_click)
            if hasattr(self, 'cid_key'):
                self.trend_canvas.mpl_disconnect(self.cid_key)

            self.cid_move = self.trend_canvas.mpl_connect("motion_notify_event", self.on_move2)
            self.cid_click = self.trend_canvas.mpl_connect("button_press_event", self.on_click2)
            self.cid_key = self.trend_canvas.mpl_connect("key_press_event", self.on_key_press2)

            self.hover_dot = self.trend_ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
        except:
            pass

        # ===== 13. 데이터 저장 (CSV 저장용) =====
        # ⭐ 채널별로 분리된 데이터 저장 (마우스 이벤트용)
        self.trend_data_by_channel = {}  # 신규: 채널별 데이터
        for ch, data in channel_data.items():
            self.trend_data_by_channel[ch] = {
                'x': data["x"],  # datetime 또는 index
                'y': data["y"],  # RMS 값들
                'labels': data["label"]  # 파일명들
            }

        self.trend_file_names = trend_file_names
        self.file_name_used = trend_file_names
        self.trend_rms_values = trend_rms_values
        self.trend_delta_f = delta_f
        self.trend_window = window_type
        self.trend_overlap = overlap
        self.trend_band_min = band_min
        self.trend_band_max = band_max
        self.trend_x_value = trend_x_data
        self.view_type = view_type_str

        # 추가 메타데이터
        if success_results:
            first_result = success_results[0]
            self.sample_rate = first_result.sampling_rate
            self.dt = first_result.metadata.get('dt', '')
            self.start_time = first_result.metadata.get('start_time', '')
            self.Duration = first_result.metadata.get('duration', '')
            self.Rest_time = ''
            self.repetition = ''
            self.IEPE = ''
            self.Sensitivity = first_result.metadata.get('sens', '')
            self.b_Sensitivity = first_result.metadata.get('b_sens', '')
            self.channel = []

        # ===== 14. 마우스 이벤트 연결 =====
        try:
            if hasattr(self, 'cid_move') and self.cid_move:
                self.trend_canvas.mpl_disconnect(self.cid_move)
            if hasattr(self, 'cid_click') and self.cid_click:
                self.trend_canvas.mpl_disconnect(self.cid_click)
            if hasattr(self, 'cid_key') and self.cid_key:
                self.trend_canvas.mpl_disconnect(self.cid_key)

            self.cid_move = self.trend_canvas.mpl_connect("motion_notify_event", self.on_move2)
            self.cid_click = self.trend_canvas.mpl_connect("button_press_event", self.on_click2)
            self.cid_key = self.trend_canvas.mpl_connect("key_press_event", self.on_key_press2)
            self.hover_dot = self.trend_ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
        except:
            pass

        # ===== 14. 정리 =====
        self.progress_dialog.close()

        import gc
        gc.collect()

        perf_logger.end_timer("전체 Trend 분석", start_total)
        perf_logger.log_info("✅ plot_trend 완료")

    def load_trend_data_and_plot(self):  #잠시대기
        selected_items = self.Querry_list3.selectedItems()
        if not selected_items:
            print("❌ 선택된 항목이 없습니다.")
            return

        trend_x_data = []
        self.trend_data = []  # y 값 (RMS 값)
        self.trend_file_names = []  # x 라벨 (파일 이름)
        self.channel_num = []  # 채널 번호
        self.trend_markers_load = []  # 마커 저장용
        self.trend_annotations_load = []
        self.trend_marker_filenames_load = []  # 주석 저장용
        channel_data = {}  # 채널별 x, y 데이터 저장
        x_labels = []
        x_data = []
        y_data = []
        labels = []
        offset_step = 20  # y축 간격
        start_time = None

        # 🔍 현재 UI 설정값 읽기
        try:
            view_type_map = {
                1: "ACC",
                2: "VEL",
                3: "DIS"
            }

            view_type_code = self.select_pytpe3.currentData()  # 선택된 데이터 코드 가져오기
            view_type = view_type_map.get(view_type_code, "ACC")  # 기본값은 "ACC"로 설정

            current_options = {
                "window": self.Function_3.currentText().lower(),
                "view_type": view_type,
                "band_min": float(self.freq_range_inputmin.text().strip()),
                "band_max": float(self.freq_range_inputmax.text().strip()),
                "delta_f": float(self.Hz_3.toPlainText().strip()) if self.Hz_3.toPlainText().strip() else 1.0,
                "overlap": float(self.Overlap_Factor_3.currentText().replace('%',
                                                                             '').strip()) if self.Overlap_Factor_3.currentText().strip() else 50.0
            }
        except Exception as e:
            QMessageBox.warning(self, "옵션 읽기 오류", f"옵션 값을 불러오는 중 오류가 발생했습니다: {e}")
            return

        for idx, item in enumerate(selected_items):
            file_name = item.text()
            json_path = os.path.join(self.directory_path, 'trend_data', file_name.replace(".txt", ".json"))

            try:
                file_timestamp = self.extract_timestamp_from_filename(file_name)
                x_labels.append(file_timestamp.strftime("%Y-%m-%d""\n""%H:%M:%S"))  # "날짜_시간" 포맷으로 저장
            except Exception as e:
                #print(f"⚠ {file_name} - 시간 추출 실패: {e}")
                x_labels.append(file_name)

            if not os.path.exists(json_path):
                # print(f"⚠ {file_name} - 저장된 트렌드 데이터가 없습니다.")
                continue

            try:
                trend_data = load_json(json_path)
                rms = trend_data["rms_value"]
                window = trend_data.get("window", "").lower()
                view_type_json = trend_data.get("view_type", "")
                band_min_json = float(trend_data.get("band_min", -1))
                band_max_json = float(trend_data.get("band_max", -1))
                delta_f_json = float(trend_data.get("delta_f", -1))
                overlap_json = float(trend_data.get("overlap", -1))

                trend_options = {
                    "window": trend_data.get("window", "").lower(),
                    "view_type": trend_data.get("view_type", ""),  # 예: "VEL"
                    "band_min": float(trend_data.get("band_min", -1)),
                    "band_max": float(trend_data.get("band_max", -1)),
                    "delta_f": float(trend_data.get("delta_f", -1)),
                    "overlap": float(trend_data.get("overlap", -1)),
                }
            except Exception as e:
                perf_logger.log_warning(f"⚠️ JSON 로드 실패: {json_path}, {e}")
                continue

            # ⚠ 옵션 불일치 검사
            mismatch_keys = []
            for key in current_options:
                cur = current_options[key]
                saved = trend_options.get(key)
                if isinstance(cur, float) or isinstance(saved, float):
                    if abs(cur - float(saved)) > 1e-3:  # float 비교
                        mismatch_keys.append(f"{key} (저장: {saved}, 현재: {cur})")
                else:
                    if cur != saved:
                        mismatch_keys.append(f"{key} (저장: {saved}, 현재: {cur})")

            if mismatch_keys:
                QMessageBox.warning(None, "옵션 불일치", f"{file_name} 의 설정이 현재 설정과 다릅니다:\n" + "\n".join(mismatch_keys))
                return
            # 채널 번호를 기준으로 데이터 저장
            channel = trend_data["channel_num"]
            if channel not in channel_data:
                channel_data[channel] = {"x_data": [], "y_data": [], "labels": []}

            if start_time is None:
                start_time = file_timestamp if file_timestamp else datetime.datetime.now()

            if file_timestamp:
                time_offset = (file_timestamp - start_time).total_seconds()
            else:
                time_offset += offset_step

            if file_timestamp:
                x_value = self.extract_timestamp_from_filename(file_name)
                x_value_2 = file_name.rsplit('.', 1)[0]
            else:
                x_value = start_time.timestamp() + offset_step * idx

            channel_data[channel]["x_data"].append(x_value)
            channel_data[channel]["y_data"].append(rms)
            channel_data[channel]["labels"].append(file_name)

            x_data.append(x_value)
            y_data.append(rms)
            labels.append(file_name)
            trend_x_data.append(x_value)

            self.trend_data.append(rms)
            self.trend_file_names.append(file_name)

        # 그래프 다시 그림
        self.trend_ax.clear()
        self.trend_ax.set_title("Overall RMS Trend \n (Loaded Data)", fontsize=7, fontname='Malgun Gothic')
        colors = ["r", "g", "b", "c", "m", "y"]

        for i, (ch, data) in enumerate(channel_data.items()):
            self.trend_ax.plot(data["x_data"], data["y_data"], label=f"Channel {ch}", color=colors[i % len(colors)],
                               marker='o', markersize=3, linewidth=1.5)

        sorted_pairs = sorted(zip(x_data, x_labels))
        sorted_x, sorted_labels = zip(*sorted_pairs)

        # 평균적으로 5개만 tick 표시
        num_ticks = 10
        total = len(sorted_x)
        if total <= num_ticks:
            tick_indices = list(range(total))
        else:
            tick_indices = [int(i) for i in np.linspace(0, total - 1, num_ticks)]
        # tick 위치 설정
        # 추출한 인덱스 기반으로 tick 설정
        tick_positions = [sorted_x[i] for i in tick_indices]
        tick_labels = [sorted_labels[i] for i in tick_indices]
        self.trend_ax.set_xticks(tick_positions)
        self.trend_ax.set_xticklabels(tick_labels, rotation=0, ha="right", fontsize=7, fontname='Malgun Gothic')
        self.trend_ax.set_xlabel("data&time", fontsize=7, fontname='Malgun Gothic')

        view_type_map = {
            1: "ACC",
            2: "VEL",
            3: "DIS"
        }

        view_type_code = self.select_pytpe3.currentData()
        view_type = view_type_map.get(view_type_code, "ACC")  # 기본값은 "ACC"로 설정

        labels = {
            "ACC": "Vibration Acceleration \n (m/s^2, RMS)",
            "VEL": "Vibration Velocity \n (mm/s, RMS)",
            "DIS": "Vibration Displacement \n (μm , RMS)"
        }
        ylabel = labels.get(view_type, "Vibration (mm/s, RMS)")
        self.trend_ax.set_ylabel(ylabel, fontsize=7, fontname='Malgun Gothic')
        self.trend_ax.set_facecolor('white')

        self.trend_canvas.flush_events()
        # self.trend_ax.set_position([0.1, 0.1, 0.7, 0.8])  # [left, bottom, width, height] 형식으로 설정
        self.trend_ax.grid(True, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
        handles, labels = self.trend_ax.get_legend_handles_labels()
        unique = dict()
        for h, l in zip(handles, labels):
            if l not in unique:
                unique[l] = h
            self.trend_ax.legend(unique.values(), unique.keys())
        self.trend_ax.tick_params(axis='x', labelsize=7)
        self.trend_ax.tick_params(axis='y', labelsize=7)
        self.trend_canvas.draw()
        self.cid_move = self.trend_canvas.mpl_connect("motion_notify_event", self.on_move_load)
        self.cid_click = self.trend_canvas.mpl_connect("button_press_event", self.on_click_load)
        self.cid_key = self.trend_canvas.mpl_connect("key_press_event", self.on_key_press_load)

        self.hover_dot_load = self.trend_ax.plot([], [], 'ko', markersize=3, alpha=0.5)[0]

        self.trend_x_value = trend_x_data
        self.trend_rms_values = y_data

    def save_trend_data_per_file(self, file_name, rms_value, delta_f, window_type, overlap, band_min, band_max, channel,
                                 sampling_rate, dt, start_time, duration, rest_time, repetition, iepe, sensitivity,
                                 b_sensitivity, channel_num, view_type, time, data2, freq, P, ACF):
        base_name = os.path.splitext(os.path.basename(file_name))[0]
        save_folder = os.path.join(self.directory_path, 'trend_data')
        os.makedirs(save_folder, exist_ok=True)

        save_path = os.path.join(save_folder, f"{base_name}.json")
        view_type_map = {
            1: "ACC",
            2: "VEL",
            3: "DIS"
        }
        view_type_str = view_type_map.get(view_type, "UNKNOWN")  # 기본값은 "UNKNOWN"

        trend_data = {
            "rms_value": rms_value,
            "delta_f": delta_f,
            "window": window_type,
            "overlap": overlap,
            "band_min": band_min,
            "band_max": band_max,
            "sampling_rate": sampling_rate,
            "start_time": str(start_time),
            "dt": dt,
            "filename": file_name,
            "duration": duration,
            "rest_time": rest_time,
            "repetition": repetition,
            "iepe": iepe,
            "sensitivity": sensitivity,
            "b_sensitivity": b_sensitivity,
            "channel_num": channel_num,
            "view_type": view_type_str,

        }
        try:
            # ⭐ 수정: save_json 함수 사용 (파일 경로 전달)
            save_json(trend_data, save_path, indent=4)
            perf_logger.log_info(f"✓ 트렌드 데이터 저장: {save_path}")
        except Exception as e:
            perf_logger.log_warning(f"⚠️ {save_path} 저장 실패: {e}")
            print(f"⚠️ {save_path} 저장 실패: {e}")

    def on_save_button_clicked2(self):

        # 필수 정보가 다 있을 경우에만 저장
        if hasattr(self, 'trend_file_names') and hasattr(self, 'trend_rms_values'):
            self.save_trend_to_csv(
                file_names=self.trend_file_names,
                file_name_used=self.file_name_used,
                rms_values=self.trend_rms_values,
                delta_f=self.trend_delta_f,
                window=self.trend_window,
                overlap=self.trend_overlap,
                band_min=self.trend_band_min,
                band_max=self.trend_band_max,
                channel=self.channel,
                sampling_rates=self.sample_rate,
                dt=self.dt,
                start_time=self.start_time,
                duration=self.Duration,
                rest_time=self.Rest_time,
                repetition=self.repetition,
                iepe=self.IEPE,
                sensitivity=self.Sensitivity,
                b_sensitivity=self.b_Sensitivity,
                channel_infos=self.channel_infos,
                view_type=self.view_type,

            )
        else:
            print("❗ 먼저 트렌드를 분석해주세요. (plot_trend 실행 필요)")

    def save_trend_to_csv(self, file_names, file_name_used, rms_values, delta_f, window, overlap,
                          band_min, band_max, channel, sampling_rates, dt, start_time, duration,
                          rest_time, repetition, iepe, sensitivity, b_sensitivity, channel_infos, view_type):
        """트렌드 데이터를 CSV 파일로 저장하는 함수"""

        # 저장 경로 지정
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save CSV File", "", "CSV Files (*.csv)")
        if not save_path:
            return
        if not save_path.endswith(".csv"):
            save_path += ".csv"

        with open(save_path, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # 상단 정보 작성
            writer.writerow(['delta f', delta_f])
            writer.writerow(['window', window])
            writer.writerow(['overlap (%)', overlap])
            writer.writerow(['Band Limit (Hz)', f"{band_min} ~ {band_max}"])
            writer.writerow(['Channel', ', '.join(map(str, channel))])
            writer.writerow(['Sampling', sampling_rates])
            writer.writerow(['Record Length', duration])
            writer.writerow(['Rest Time (s)', rest_time])
            writer.writerow(['IEPE', iepe])
            writer.writerow(['Sensitivity (mV/g)', sensitivity])
            writer.writerow(['Start Time', start_time])
            writer.writerow(['Repetition', repetition])
            writer.writerow(['Time Resolution', dt])
            writer.writerow(['B.Sensitivity', b_sensitivity])
            writer.writerow(['View_type', ', '.join(view_type) if isinstance(view_type, list) else view_type])
            writer.writerow([])  # 빈 줄

            # 데이터 컬럼 헤더
            writer.writerow(['CH', 'File Name', 'Band Limited Overal RMS Value (mm/s, RMS)'])

            # 데이터 작성
            for name, rms in zip(file_names, rms_values):
                match = re.findall(r'\d+', name)
                ch = f"CH{match[-1]}" if match else "CH"
                writer.writerow([ch, name, rms])

        print(f"✅ 트렌드 CSV 저장 완료: {save_path}")

    def on_move2(self, event):
        """마우스가 그래프 위를 움직일 때 가장 가까운 점을 찾아서 점 표시"""
        if not event.inaxes:
            if self.hover_pos is not None:  # hover_pos가 None이 아니면 점을 지우기
                self.hover_dot.set_data([], [])
                self.hover_pos = None
                self.trend_canvas.draw()
            return

        closest_x, closest_y, min_dist = None, None, np.inf  # np.inf로 수정

        # 모든 라인에서 가장 가까운 점 찾기
        for line in self.trend_ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()

            # 데이터가 없으면 건너뛴다
            if len(x_data) == 0 or len(y_data) == 0:
                continue

            # datetime 타입이면 float(ordinal)로 변환
            if isinstance(x_data[0], datetime):
                x_data = mdates.date2num(x_data)
                self.initialize_hover_step(x_data, y_data)  # datetime 처리 후 호출

            for x, y in zip(x_data, y_data):
                dist = np.hypot(event.xdata - x, event.ydata - y)
                if dist < min_dist:
                    min_dist = dist
                    closest_x, closest_y = x, y

        # 가장 가까운 점이 존재하면 해당 점을 표시
        if closest_x is not None:
            self.hover_dot.set_data([closest_x], [closest_y])
            self.hover_pos = [closest_x, closest_y]  # 현재 좌표 저장
            self.trend_canvas.draw()

    def on_click2(self, event):
        """마우스를 클릭했을 때 가장 가까운 점을 고정된 마커로 표시"""

        if not event.inaxes:
            return

        if event.inaxes == self.trend_ax:
            self.add_marker2(event.xdata, event.ydata)

        # hover_dot 위치를 가져와서 마커로 고정
        x, y = self.hover_dot.get_data()

        if x and y:
            self.add_marker2(x, y)

        if event.button == 3:  # 오른쪽 클릭
            for marker in self.trend_markers:
                marker.remove()
            self.trend_markers.clear()

            for annotation in self.trend_annotations:
                annotation.remove()
            self.trend_annotations.clear()
            for filename in self.trend_marker_filenames:
                self.remove_marker_filename_from_list(filename)
            self.trend_marker_filenames.clear()

            self.trend_canvas.draw()
            return

    def initialize_hover_step(self, x_data, y_data):
        x_spacing = np.mean(np.diff(x_data))
        y_spacing = np.mean(np.diff(y_data))
        self.hover_step = [x_spacing, y_spacing]

    def on_key_press2(self, event):
        """키보드 입력 처리 (방향키로 점 이동, 엔터로 마커 고정)"""
        x, y = self.hover_dot.get_data()

        # 모든 라인에서 x, y 데이터를 가져옵니다.
        all_x_data = []
        all_y_data = []
        for line in self.trend_ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()
            if len(x_data) == 0 or len(y_data) == 0:
                continue
            if isinstance(x_data[0], datetime):
                x_data = mdates.date2num(x_data)
            all_x_data.extend(x_data)
            all_y_data.extend(y_data)
            self.initialize_hover_step(x_data, y_data)

        # 현재 x, y를 기준으로 가장 가까운 점을 찾기
        closest_index = None
        current_index = None
        min_dist = np.inf
        for idx, (x_val, y_val) in enumerate(zip(all_x_data, all_y_data)):
            dist = np.hypot(x - x_val, y - y_val)
            if dist < min_dist:
                min_dist = dist
                current_index = idx

        if current_index is None:
            return  # 아무 데이터도 없으면 종료

        # 이동할 다음 데이터 찾기
        candidates = []
        if event.key == 'left':
            # x값이 작아지는 방향으로 이동
            candidates = [(i, abs(all_x_data[i] - x)) for i in range(len(all_x_data)) if all_x_data[i] < x]
        elif event.key == 'right':
            # x값이 커지는 방향으로 이동
            candidates = [(i, abs(all_x_data[i] - x)) for i in range(len(all_x_data)) if all_x_data[i] > x]
        elif event.key == 'up':
            candidates = [
                (i, abs(all_y_data[i] - y))
                for i in range(len(all_y_data))
                if abs(all_x_data[i] - x) < 1e-6 and all_y_data[i] > y
            ]
        elif event.key == 'down':
            candidates = [
                (i, abs(all_y_data[i] - y))
                for i in range(len(all_y_data))
                if abs(all_x_data[i] - x) < 1e-6 and all_y_data[i] < y
            ]
        elif event.key == 'enter':
            self.add_marker2(all_x_data[current_index], all_y_data[current_index])
            return
        if candidates:
            # 가장 가까운 x 또는 y를 가진 index 선택
            candidates.sort(key=lambda t: t[1])  # 거리 기준 정렬
            current_index = candidates[0][0]

        # 이동된 위치로 hover_dot 위치 업데이트
        new_x = all_x_data[current_index]
        new_y = all_y_data[current_index]
        self.hover_pos = [new_x, new_y]
        self.hover_dot.set_data([new_x], [new_y])
        self.trend_canvas.draw()

    def add_marker2(self, x, y):
        """
        Overall RMS Trend 그래프에 마커 추가 (기존 로직 복원)
        """
        try:
            # ===== 0. x, y가 리스트인 경우 첫 번째 값 추출 =====
            if isinstance(x, (list, np.ndarray)):
                if len(x) == 0:
                    print("⚠️ x 데이터가 비어있습니다")
                    return
                x = x[0]

            if isinstance(y, (list, np.ndarray)):
                if len(y) == 0:
                    print("⚠️ y 데이터가 비어있습니다")
                    return
                y = y[0]

            # ===== 1. 데이터 존재 확인 =====
            if not hasattr(self, 'trend_x_value') or not hasattr(self, 'trend_rms_values'):
                print("⚠️ Trend 데이터가 없습니다")
                return

            # ===== 2. 가장 가까운 데이터 포인트 찾기 =====
            from datetime import datetime
            import matplotlib.dates as mdates

            min_distance = float('inf')
            closest_index = -1

            # 전체 데이터에서 검색 (기존 방식)
            for i, (data_x, data_y) in enumerate(zip(self.trend_x_value, self.trend_rms_values)):
                # datetime을 float로 변환
                if isinstance(data_x, datetime):
                    data_x_float = mdates.date2num(data_x)
                else:
                    data_x_float = data_x

                # x도 datetime이면 변환
                if isinstance(x, datetime):
                    x_float = mdates.date2num(x)
                else:
                    x_float = x

                # y 값 변환
                if isinstance(y, list) and len(y) > 0:
                    y_val = float(y[0])
                else:
                    y_val = float(y)

                dx = abs(x_float - data_x_float)
                dy = abs(y_val - data_y)

                # 우선순위: x가 같으면 y 차이만, 아니면 전체 거리
                if dx == 0:
                    dist = dy
                else:
                    dist = np.hypot(dx, dy)

                if dist < min_distance:
                    min_distance = dist
                    closest_index = i

            # ===== 3. 클릭 범위 검증 (기존보다 관대하게) =====
            if closest_index == -1:
                print("ℹ️ 가까운 데이터 포인트를 찾을 수 없습니다")
                return

            # ===== 4. 기존 마커 제거 =====
            if hasattr(self, 'trend_marker') and self.trend_marker:
                try:
                    self.trend_marker.remove()
                except:
                    pass

            if hasattr(self, 'trend_annotation') and self.trend_annotation:
                try:
                    self.trend_annotation.remove()
                except:
                    pass

            # ===== 5. 새 마커 추가 =====
            file_name = self.trend_file_names[closest_index]
            x_val = self.trend_x_value[closest_index]
            y_val = self.trend_rms_values[closest_index]

            self.trend_marker = self.trend_ax.plot(
                x_val, y_val,
                marker='o', color='red', markersize=7
            )[0]

            # ===== 6. 주석 추가 =====
            annotation_text = f"{file_name}\nX: {x_val}\nY: {y_val:.4f}"

            self.trend_annotation = self.trend_ax.annotate(
                annotation_text,
                (x_val, y_val),
                textcoords="offset points",
                xytext=(10, 10),
                ha='left',
                fontsize=7,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="black",
                          facecolor="lightyellow", alpha=0.8)
            )

            self.trend_canvas.draw()

            print(f"📍 마커 추가: 파일={file_name}, RMS={y_val:.4f}")

            # ===== 7. Pick Data List 추가 =====
            if hasattr(self, 'data_list_text'):
                try:
                    self.add_marker_filename_to_list(file_name)
                except Exception as e:
                    print(f"⚠️ Pick Data List 추가 실패: {e}")

        except Exception as e:
            print(f"⚠️ add_marker2 오류: {e}")
            import traceback
            traceback.print_exc()

    def on_move_load(self, event):
        """마우스가 그래프 위를 움직일 때 가장 가까운 점을 찾아서 점 표시"""
        if not event.inaxes:
            if self.hover_pos is not None:  # hover_pos가 None이 아니면 점을 지우기
                self.hover_dot_load.set_data([], [])
                self.hover_pos = None
                self.trend_canvas.draw()
            return

        closest_x, closest_y, min_dist = None, None, np.inf  # np.inf로 수정

        # 모든 라인에서 가장 가까운 점 찾기
        for line in self.trend_ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()

            # 데이터가 없으면 건너뛴다
            if len(x_data) == 0 or len(y_data) == 0:
                continue

            # datetime 타입이면 float(ordinal)로 변환
            if isinstance(x_data[0], datetime):
                x_data = mdates.date2num(x_data)
                self.initialize_hover_step_load(x_data, y_data)  # datetime 처리 후 호출

            for x, y in zip(x_data, y_data):
                dist = np.hypot(event.xdata - x, event.ydata - y)
                if dist < min_dist:
                    min_dist = dist
                    closest_x, closest_y = x, y

        # 가장 가까운 점이 존재하면 해당 점을 표시
        if closest_x is not None:
            self.hover_dot_load.set_data([closest_x], [closest_y])
            self.hover_pos = [closest_x, closest_y]  # 현재 좌표 저장
            self.trend_canvas.draw()

    def on_click_load(self, event):
        """마우스를 클릭했을 때 가장 가까운 점을 고정된 마커로 표시"""
        if not event.inaxes:
            return

        # hover_dot 위치를 가져와서 마커로 고정
        x, y = self.hover_dot_load.get_data()

        if x and y:
            self.add_marker_load(x, y)

        if event.button == 3:  # 오른쪽 클릭
            for marker in self.trend_markers_load:
                marker.remove()
            self.trend_markers_load.clear()

            for annotation in self.trend_annotations_load:
                annotation.remove()
            self.trend_annotations_load.clear()
            for filename in self.trend_marker_filenames_load:
                self.remove_marker_filename_from_list(filename)
            self.trend_marker_filenames_load.clear()

            self.trend_canvas.draw()
            return

    def initialize_hover_step_load(self, x_data, y_data):
        x_spacing = np.mean(np.diff(x_data))
        y_spacing = np.mean(np.diff(y_data))
        self.hover_step = [x_spacing, y_spacing]

    def on_key_press_load(self, event):
        """키보드 입력 처리 (방향키로 점 이동, 엔터로 마커 고정)"""
        x, y = self.hover_dot_load.get_data()

        # 모든 라인에서 x, y 데이터를 가져옵니다.
        all_x_data = []
        all_y_data = []
        for line in self.trend_ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()
            if len(x_data) == 0 or len(y_data) == 0:
                continue
            if isinstance(x_data[0], datetime):
                x_data = mdates.date2num(x_data)
            all_x_data.extend(x_data)
            all_y_data.extend(y_data)
            self.initialize_hover_step_load(x_data, y_data)

        # 현재 x, y를 기준으로 가장 가까운 점을 찾기
        closest_index = None
        current_index = None
        min_dist = np.inf
        for idx, (x_val, y_val) in enumerate(zip(all_x_data, all_y_data)):
            dist = np.hypot(x - x_val, y - y_val)
            if dist < min_dist:
                min_dist = dist
                current_index = idx

        if current_index is None:
            return  # 아무 데이터도 없으면 종료

        # 이동할 다음 데이터 찾기
        candidates = []
        if event.key == 'left':
            # x값이 작아지는 방향으로 이동
            candidates = [(i, abs(all_x_data[i] - x)) for i in range(len(all_x_data)) if all_x_data[i] < x]
        elif event.key == 'right':
            # x값이 커지는 방향으로 이동
            candidates = [(i, abs(all_x_data[i] - x)) for i in range(len(all_x_data)) if all_x_data[i] > x]
        elif event.key == 'up':
            candidates = [
                (i, abs(all_y_data[i] - y))
                for i in range(len(all_y_data))
                if abs(all_x_data[i] - x) < 1e-6 and all_y_data[i] > y
            ]
        elif event.key == 'down':
            candidates = [
                (i, abs(all_y_data[i] - y))
                for i in range(len(all_y_data))
                if abs(all_x_data[i] - x) < 1e-6 and all_y_data[i] < y
            ]
        elif event.key == 'enter':
            self.add_marker_load(all_x_data[current_index], all_y_data[current_index])
            return
        if candidates:
            # 가장 가까운 x 또는 y를 가진 index 선택
            candidates.sort(key=lambda t: t[1])  # 거리 기준 정렬
            current_index = candidates[0][0]

        # 이동된 위치로 hover_dot 위치 업데이트
        new_x = all_x_data[current_index]
        new_y = all_y_data[current_index]
        self.hover_pos = [new_x, new_y]
        self.hover_dot_load.set_data([new_x], [new_y])
        self.trend_canvas.draw()

    def add_marker_load(self, x, y):
        """마커 점과 텍스트를 동시에 추가"""
        # 가장 가까운 데이터 포인트 찾기
        min_distance = float('inf')
        closest_index = -1
        for i, (data_x, data_y) in enumerate(zip(self.trend_x_value, self.trend_rms_values)):
            # x가 datetime일 경우 float로 변환
            if isinstance(data_x, datetime):
                data_x_float = mdates.date2num(data_x)
            else:
                data_x_float = data_x
            if isinstance(y, list) and len(y) > 0:
                y_val = float(y[0])  # np.float64 → float 변환
            else:
                y_val = float(y)

            dx = abs(x - data_x_float)
            dy = abs(y_val - data_y)

            # 우선순위 조건 적용
            if dx == 0:
                dist = dy  # x가 같으면 y 차이만 고려
            else:
                dist = np.hypot(dx, dy)  # 그 외는 전체 거리 기준

            if dist < min_distance:
                min_distance = dist
                closest_index = i

        if closest_index != -1:
            file_name = self.trend_file_names[closest_index]
            x_val = self.trend_x_value[closest_index]  # 실제 x 값
            y_val = self.trend_rms_values[closest_index]  # 실제 y 값

            # 마커 추가
            marker = self.trend_ax.plot(x_val, y_val, marker='o', color='red', markersize=7)[0]
            self.trend_markers_load.append(marker)
            self.trend_marker_filenames.append(file_name)  # ⬅️ 파일명 저장
            self.add_marker_filename_to_list(file_name)

            # 텍스트 추가 (파일 이름, x, y 값 표시)
            label = f"{file_name}\nX: {x_val}\nY: {y_val:.4f}"
            annotation = self.trend_ax.annotate(
                label,
                (x_val, y_val),
                textcoords="offset points",
                xytext=(10, 10),
                ha='left',
                fontsize=7,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightyellow", alpha=0.8)
            )
            self.trend_annotations_load.append(annotation)

            # marked_points 리스트에 추가 (파일명, x, y, 라벨 정보 저장)
            #self.marked_points.append((file_name, x_val, y_val, label))

            self.trend_canvas.draw()

    def on_list_save_btn_clicked(self):
        try:
            text_lines = self.data_list_text.toPlainText().split("\n")

            channel_files = {f"Ch{i}": [] for i in range(1, 7)}  # Ch1 ~ Ch6 초기화

            for line in text_lines:
                line = line.strip()
                if not line or line.startswith("Ch") or line == "-":
                    continue

                # 파일명에서 채널 번호 추출: 마지막 언더스코어 다음의 숫자
                try:
                    channel_num = int(line.split("_")[-1].split(".")[0])  # 마지막 숫자
                    if 1 <= channel_num <= 6:
                        channel_key = f"Ch{channel_num}"
                        channel_files[channel_key].append(line)
                except Exception as e:
                    print(f"파일 파싱 오류: {line}, 에러: {e}")

            dialog = ListSaveDialog(
                channel_files,
                self.main_window,
                directory_path=self.directory_path  # ✅ 폴더 경로 같이 넘기기
            )

            # ⭐ 모달 다이얼로그로 실행 (블로킹)
            dialog.setWindowModality(QtCore.Qt.ApplicationModal)

            # ⭐ 창 크기 및 위치 설정
            dialog.resize(1600, 900)

            # ⭐ exec_() 대신 show() 사용하면 논블로킹
            # result = dialog.exec_()  # 블로킹 (창 닫을 때까지 대기)
            dialog.show()  # 논블로킹 (창 띄우고 바로 반환)

            # ⭐ 다이얼로그 참조 저장 (GC 방지)
            self.detail_analysis_dialog = dialog
            # if dialog.exec_() == QtWidgets.QDialog.Accepted:
            #     selected_files = dialog.get_selected_files()
            #     # if selected_files:
            #     #         self.save_selected_files(selected_files)
        except Exception as e:
            print(f"❌ on_list_save_btn_clicked 오류: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(None, "오류", f"Detail Analysis 실행 중 오류 발생:\n{e}")
    def add_marker_filename_to_list(self, filename):
        # 예: filename = "data_example_3.txt"

        # 파일명 끝의 숫자 추출
        match = re.search(r"_([1-6])\.txt$", filename)
        if not match:
            print(f"채널 숫자 추출 실패: {filename}")
            return

        ch_num = int(match.group(1))

        current_text = self.data_list_text.toPlainText()
        lines = current_text.split("\n")

        ch_header = f"Ch{ch_num}"
        insert_idx = -1
        for i, line in enumerate(lines):
            if line.strip() == ch_header:
                insert_idx = i
                break

        if insert_idx == -1:
            print("채널 헤더 찾기 실패")
            return

        # 채널 바로 아래에 삽입 (중복 방지 포함)
        i = insert_idx + 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("Ch"):
            if lines[i].strip() == filename.strip():  # 중복이면 종료
                return
            i += 1

        lines.insert(i, filename)
        self.data_list_text.setText("\n".join(lines))

    def remove_marker_filename_from_list(self, filename):
        # 현재 QTextEdit 텍스트 가져오기
        current_text = self.data_list_text.toPlainText()
        lines = current_text.split("\n")

        # 파일명 일치하는 줄 삭제
        new_lines = [line for line in lines if line.strip() != filename.strip()]

        # 다시 설정
        self.data_list_text.setText("\n".join(new_lines))

    def plot_peak(self):
        """
        ⭐ Level 5 최적화: 병렬 Band Peak 분석
        - 1000개: 18분 → 0.08초 수준
        - 10000개: 3시간 → 수 초 수준
        """
        from PyQt5.QtWidgets import QMessageBox
        from PyQt5.QtCore import Qt
        import os
        from OPTIMIZATION_PATCH_LEVEL5_TREND import PeakParallelProcessor

        perf_logger.log_info("🚀 plot_peak 시작 (Level 5)")
        start_total = perf_logger.start_timer("전체 Peak 분석")

        # ===== 1. 파라미터 준비 =====
        selected_items = self.Querry_list4.selectedItems()
        if not selected_items:
            QMessageBox.critical(None, "오류", "파일을 선택하세요")
            return

        try:
            delta_f = float(self.Hz_4.toPlainText().strip())
            overlap = float(self.Overlap_Factor_4.currentText().replace('%', '').strip())
            window_type = self.Function_4.currentText()
            view_type = self.select_pytpe4.currentData()
            band_min = float(self.freq_range_inputmin2.text().strip())
            band_max = float(self.freq_range_inputmax2.text().strip())
        except ValueError as e:
            QMessageBox.critical(None, "입력 오류", f"파라미터 오류: {e}")
            return

        # ===== 2. 파일 경로 리스트 =====
        file_paths = [
            os.path.join(self.directory_path, item.text())
            for item in selected_items
        ]

        perf_logger.log_info(f"📁 파일 수: {len(file_paths)}")

        # ===== 3. 진행률 다이얼로그 =====
        self.progress_dialog = ProgressDialog(len(file_paths), self.main_window)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()

        def progress_update(current, total):
            self.progress_dialog.update_progress(current)
            self.progress_dialog.label.setText(f"처리 중... {current}/{total}")
            QApplication.processEvents()

        # ===== 4. 병렬 처리 =====
        processor = PeakParallelProcessor(max_workers=6)

        perf_logger.log_info(f"🔥 병렬 처리 시작 ({processor.processor.max_workers} 워커)")
        start_parallel = perf_logger.start_timer("병렬 Peak 처리")

        results = processor.process_batch(
            file_paths=file_paths,
            delta_f=delta_f,
            overlap=overlap,
            window_type=window_type,
            view_type=view_type,
            band_min=band_min,
            band_max=band_max,
            progress_callback=progress_update
        )

        perf_logger.end_timer("병렬 Peak 처리", start_parallel)

        # ===== 5. 성공/실패 집계 =====
        success_results = [r for r in results if r.success]
        failed_count = len(results) - len(success_results)

        perf_logger.log_info(f"✓ 성공: {len(success_results)}, ✗ 실패: {failed_count}")

        if not success_results:
            QMessageBox.warning(None, "경고", "처리된 데이터가 없습니다.")
            self.progress_dialog.close()
            return

        # ===== 6. 그래프 데이터 준비 =====
        self.peak_ax.clear()
        self.peak_ax.set_title("Band Peak Trend", fontsize=7, fontname=DEFAULT_FONT)

        channel_data = {}
        x_labels = []
        peak_x_data = []
        peak_values = []  # ⭐ Peak 값 (RMS 대신)
        peak_file_names = []

        for result in success_results:
            # 채널 번호 추출
            channel_num = result.file_name.split('_')[-1].replace('.txt', '')

            if channel_num not in channel_data:
                channel_data[channel_num] = {"x": [], "y": [], "label": []}

            # 타임스탬프 추출
            try:
                timestamp = self.extract_timestamp_from_filename(result.file_name)
                x_value = timestamp
                x_label = timestamp.strftime("%Y-%m-%d\n%H:%M:%S")
            except:
                x_value = len(channel_data[channel_num]["x"])
                x_label = result.file_name

            # ⭐ Peak 값 사용 (RMS 대신)
            channel_data[channel_num]["x"].append(x_value)
            channel_data[channel_num]["y"].append(result.peak_value)
            channel_data[channel_num]["label"].append(result.file_name)

            # 전체 데이터 저장
            peak_x_data.append(x_value)
            peak_values.append(result.peak_value)
            peak_file_names.append(result.file_name)
            x_labels.append(x_label)

        # ===== 7. 그래프 렌더링 =====
        colors = ["r", "g", "b", "c", "m", "y"]

        for i, (ch, data) in enumerate(channel_data.items()):
            self.peak_ax.plot(
                data["x"], data["y"],
                label=f"Channel {ch}",
                color=colors[i % len(colors)],
                marker='o', markersize=2, linewidth=0.5
            )

        # ===== 8. X축 눈금 설정 =====
        sorted_pairs = sorted(zip(peak_x_data, x_labels))
        sorted_x, sorted_labels = zip(*sorted_pairs) if sorted_pairs else ([], [])

        num_ticks = min(10, len(sorted_x))
        if num_ticks > 0:
            tick_indices = np.linspace(0, len(sorted_x) - 1, num_ticks, dtype=int)
            tick_positions = [sorted_x[i] for i in tick_indices]
            tick_labels = [sorted_labels[i] for i in tick_indices]

            self.peak_ax.set_xticks(tick_positions)
            self.peak_ax.set_xticklabels(tick_labels, rotation=0, ha="right",
                                         fontsize=7, fontname=DEFAULT_FONT)

        # ===== 9. Y축 라벨 =====
        view_type_map = {1: "ACC", 2: "VEL", 3: "DIS"}
        view_type_str = view_type_map.get(view_type, "ACC")

        labels = {
            "ACC": "Peak Acceleration\n(m/s², RMS)",
            "VEL": "Peak Velocity\n(mm/s, RMS)",
            "DIS": "Peak Displacement\n(μm, RMS)"
        }
        ylabel = labels.get(view_type_str, "Peak Vibration (mm/s, RMS)")

        self.peak_ax.set_xlabel("Date & Time", fontsize=7, fontname=DEFAULT_FONT)
        self.peak_ax.set_ylabel(ylabel, fontsize=7, fontname=DEFAULT_FONT)
        self.peak_ax.set_facecolor('white')
        self.peak_ax.grid(True, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
        self.peak_ax.tick_params(axis='x', labelsize=7)
        self.peak_ax.tick_params(axis='y', labelsize=7)

        # ⭐ 범례 업데이트 추가
        self.update_legend_position(self.peak_ax, max_items=10)

        # ⭐ tight_layout 재적용
        try:
            self.peak_figure.tight_layout(rect=[0, 0, 0.88, 1])
        except:
            pass

        # 범례
        # handles, legend_labels = self.peak_ax.get_legend_handles_labels()
        # unique = dict()
        # for h, l in zip(handles, legend_labels):
        #     if l not in unique:
        #         unique[l] = h
        # self.peak_ax.legend(unique.values(), unique.keys(), fontsize=7)

        # ===== 10. 캔버스 그리기 =====
        self.peak_canvas.draw_idle()
        self.peak_canvas.flush_events()

        # ===== 11. JSON 저장 (병렬) - 선택사항 =====
        # Peak도 JSON 저장이 필요하면 RMS와 동일하게 구현
        # (생략 가능)

        # ===== 12. 마우스 이벤트 연결 =====
        try:
            if hasattr(self, 'cid_move_peak'):
                self.peak_canvas.mpl_disconnect(self.cid_move_peak)
            if hasattr(self, 'cid_click_peak'):
                self.peak_canvas.mpl_disconnect(self.cid_click_peak)
            if hasattr(self, 'cid_key_peak'):
                self.peak_canvas.mpl_disconnect(self.cid_key_peak)

            self.cid_move_peak = self.peak_canvas.mpl_connect("motion_notify_event", self.on_move_peak)
            self.cid_click_peak = self.peak_canvas.mpl_connect("button_press_event", self.on_click_peak)
            self.cid_key_peak = self.peak_canvas.mpl_connect("key_press_event", self.on_key_press_peak)

            self.hover_dot_peak = self.peak_ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
        except:
            pass

        # ===== 13. 데이터 저장 (CSV 저장용) =====

        # ⭐ 채널별로 분리된 데이터 저장 (마우스 이벤트용)
        self.peak_data_by_channel = {}  # 신규: 채널별 데이터

        for ch, data in channel_data.items():
            self.peak_data_by_channel[ch] = {
                'x': data["x"],
                'y': data["y"],
                'labels': data["label"]
            }

        self.peak_file_names = peak_file_names
        self.peak_value = peak_values
        self.peak_delta_f = delta_f
        self.peak_overlap = overlap
        self.peak_window = window_type
        self.peak_band_min = band_min
        self.peak_band_max = band_max
        self.peak_x_value = peak_x_data
        self.view_type = view_type_str

        # 추가 메타데이터
        if success_results:
            first_result = success_results[0]
            self.sample_rate = first_result.sampling_rate
            self.dt = first_result.metadata.get('dt', '')
            self.start_time = first_result.metadata.get('start_time', '')
            self.Duration = first_result.metadata.get('duration', '')
            self.Rest_time = ''
            self.repetition = ''
            self.IEPE = ''
            self.Sensitivity = first_result.metadata.get('sens', '')
            self.b_Sensitivity = first_result.metadata.get('b_sens', '')
            self.channel = []

        try:
            if hasattr(self, 'peak_cid_move') and self.peak_cid_move:
                self.peak_canvas.mpl_disconnect(self.peak_cid_move)
            if hasattr(self, 'peak_cid_click') and self.peak_cid_click:
                self.peak_canvas.mpl_disconnect(self.peak_cid_click)
            if hasattr(self, 'peak_cid_key') and self.peak_cid_key:
                self.peak_canvas.mpl_disconnect(self.peak_cid_key)

            self.peak_cid_move = self.peak_canvas.mpl_connect("motion_notify_event", self.on_move_peak)
            self.peak_cid_click = self.peak_canvas.mpl_connect("button_press_event", self.on_click_peak)
            self.peak_cid_key = self.peak_canvas.mpl_connect("key_press_event", self.on_key_press_peak)
            self.hover_dot_peak = self.peak_ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
        except:
            pass

        # ===== 14. 정리 =====
        self.progress_dialog.close()

        import gc
        gc.collect()

        perf_logger.end_timer("전체 Peak 분석", start_total)
        perf_logger.log_info("✅ plot_peak 완료")

    def on_save_button_clicked3(self):
        # 필수 정보가 다 있을 경우에만 저장
        if hasattr(self, 'peak_file_names') and hasattr(self, 'peak_value'):
            self.save_peak_to_csv(
                file_names=self.peak_file_names,
                peak_value=self.peak_value,  # ✅ RMS 값 리스트
                delta_f=self.peak_delta_f,
                window=self.peak_window,
                overlap=self.peak_overlap,
                band_min=self.peak_band_min,
                band_max=self.peak_band_max,
                channel=self.channel,
                sampling_rates=self.sample_rate,
                dt=self.dt,
                start_time=self.start_time,
                duration=self.Duration,
                rest_time=self.Rest_time,
                repetition=self.repetition,
                iepe=self.IEPE,
                sensitivity=self.Sensitivity,
                b_sensitivity=self.b_Sensitivity,
                view_type=self.view_type
            )
        else:
            print("❗ 먼저 트렌드를 분석해주세요. (plot_peak 실행 필요)")

    def save_peak_to_csv(self, file_names, peak_value, delta_f, window, overlap, band_min, band_max,
                         channel, sampling_rates, dt, start_time, duration, rest_time, repetition,
                         iepe, sensitivity, b_sensitivity, view_type):

        # 저장 경로 선택
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(None, "Save CSV File", "", "CSV Files (*.csv)")
        if not save_path:
            return
        if not save_path.endswith(".csv"):
            save_path += ".csv"

        with open(save_path, mode='w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # 상단 정보 (헤더)
            writer.writerow(['delta f', delta_f])
            writer.writerow(['window', window])
            writer.writerow(['overlap (%)', overlap])
            writer.writerow(['Band Limit (Hz)', f"{band_min} ~ {band_max}"])
            writer.writerow(['Channel', ', '.join(map(str, channel))])
            writer.writerow(['Sampling Rate (Hz)', sampling_rates])
            writer.writerow(['time resolution', dt])
            writer.writerow(['Record Length (s)', duration])
            writer.writerow(['Rest Time (s)', rest_time])
            writer.writerow(['IEPE', iepe])
            writer.writerow(['Repetition', repetition])
            writer.writerow(['Start Time', start_time])
            writer.writerow(['Sensitivity (mV/g)', sensitivity])
            writer.writerow(['B.Sensitivity', b_sensitivity])
            writer.writerow(['view_type', view_type])
            writer.writerow([])  # 빈 줄 삽입

            # 데이터 헤더
            writer.writerow(['CH', 'File name', 'Band Limited Overall RMS Value (mm/s, RMS)'])

            # 데이터 작성
            for name, rms in zip(file_names, peak_value):
                match = re.findall(r'\d+', name)
                ch = f"CH{match[-1]}" if match else "CH"
                writer.writerow([ch, name, rms])

    def on_move_peak(self, event):
        """마우스가 그래프 위를 움직일 때 가장 가까운 점을 찾아서 점 표시"""
        if not event.inaxes:
            if self.hover_pos_peak is not None:  # hover_pos가 None이 아니면 점을 지우기
                self.hover_dot_peak.set_data([], [])
                self.hover_pos_peak = None
                self.peak_canvas.draw()
            return

        closest_x, closest_y, min_dist = None, None, np.inf  # np.inf로 수정

        # 모든 라인에서 가장 가까운 점 찾기
        for line in self.peak_ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()

            # 데이터가 없으면 건너뛴다
            if len(x_data) == 0 or len(y_data) == 0:
                continue

            # datetime 타입이면 float(ordinal)로 변환
            if isinstance(x_data[0], datetime):
                x_data = mdates.date2num(x_data)
                self.initialize_hover_step(x_data, y_data)  # datetime 처리 후 호출

            for x, y in zip(x_data, y_data):
                dist = np.hypot(event.xdata - x, event.ydata - y)
                if dist < min_dist:
                    min_dist = dist
                    closest_x, closest_y = x, y

        # 가장 가까운 점이 존재하면 해당 점을 표시
        if closest_x is not None:
            self.hover_dot_peak.set_data([closest_x], [closest_y])
            self.hover_pos_peak = [closest_x, closest_y]  # 현재 좌표 저장
            self.peak_canvas.draw()

    def on_click_peak(self, event):
        """마우스를 클릭했을 때 가장 가까운 점을 고정된 마커로 표시"""
        if not event.inaxes:
            return

        if event.inaxes == self.peak_ax:
            self.add_marker_peak(event.xdata, event.ydata)
        # hover_dot 위치를 가져와서 마커로 고정
        x, y = self.hover_dot_peak.get_data()

        if x and y:
            self.add_marker_peak(x, y)

        if event.button == 3:  # 오른쪽 클릭
            for marker in self.peak_markers:
                marker.remove()
            self.peak_markers.clear()

            for annotation in self.peak_annotations:
                annotation.remove()
            self.peak_annotations.clear()

            self.peak_canvas.draw()
            return

    def on_key_press_peak(self, event):
        """키보드 입력 처리 (방향키로 점 이동, 엔터로 마커 고정)"""
        x, y = self.hover_dot_peak.get_data()

        # 모든 라인에서 x, y 데이터를 가져옵니다.
        all_x_data = []
        all_y_data = []
        for line in self.peak_ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()
            if len(x_data) == 0 or len(y_data) == 0:
                continue
            if isinstance(x_data[0], datetime):
                x_data = mdates.date2num(x_data)
            all_x_data.extend(x_data)
            all_y_data.extend(y_data)
            self.initialize_hover_step(x_data, y_data)

        # 현재 x, y를 기준으로 가장 가까운 점을 찾기
        closest_index = None
        current_index = None
        min_dist = np.inf
        for idx, (x_val, y_val) in enumerate(zip(all_x_data, all_y_data)):
            dist = np.hypot(x - x_val, y - y_val)
            if dist < min_dist:
                min_dist = dist
                current_index = idx

        if current_index is None:
            return  # 아무 데이터도 없으면 종료

        # 이동할 다음 데이터 찾기
        candidates = []
        if event.key == 'left':
            # x값이 작아지는 방향으로 이동
            candidates = [(i, abs(all_x_data[i] - x)) for i in range(len(all_x_data)) if all_x_data[i] < x]
        elif event.key == 'right':
            # x값이 커지는 방향으로 이동
            candidates = [(i, abs(all_x_data[i] - x)) for i in range(len(all_x_data)) if all_x_data[i] > x]
        elif event.key == 'up':
            candidates = [
                (i, abs(all_y_data[i] - y))
                for i in range(len(all_y_data))
                if abs(all_x_data[i] - x) < 1e-6 and all_y_data[i] > y
            ]
        elif event.key == 'down':
            candidates = [
                (i, abs(all_y_data[i] - y))
                for i in range(len(all_y_data))
                if abs(all_x_data[i] - x) < 1e-6 and all_y_data[i] < y
            ]
        elif event.key == 'enter':
            self.add_marker_peak(all_x_data[current_index], all_y_data[current_index])
            return
        if candidates:
            # 가장 가까운 x 또는 y를 가진 index 선택
            candidates.sort(key=lambda t: t[1])  # 거리 기준 정렬
            current_index = candidates[0][0]

        # 이동된 위치로 hover_dot 위치 업데이트
        new_x = all_x_data[current_index]
        new_y = all_y_data[current_index]
        self.hover_pos_peak = [new_x, new_y]
        self.hover_dot_peak.set_data([new_x], [new_y])
        self.peak_canvas.draw()


    def add_marker_peak(self, x, y):
        """
        Band Peak Trend 그래프에 마커 추가 (기존 로직 복원)
        """
        try:
            # ===== 0. x, y가 리스트인 경우 첫 번째 값 추출 =====
            if isinstance(x, (list, np.ndarray)):
                if len(x) == 0:
                    print("⚠️ x 데이터가 비어있습니다")
                    return
                x = x[0]

            if isinstance(y, (list, np.ndarray)):
                if len(y) == 0:
                    print("⚠️ y 데이터가 비어있습니다")
                    return
                y = y[0]

            # ===== 1. 데이터 존재 확인 =====
            if not hasattr(self, 'peak_x_value') or not hasattr(self, 'peak_value'):
                print("⚠️ Peak 데이터가 없습니다")
                return

            # ===== 2. 가장 가까운 데이터 포인트 찾기 =====
            from datetime import datetime
            import matplotlib.dates as mdates

            min_distance = float('inf')
            closest_index = -1

            # 전체 데이터에서 검색 (기존 방식)
            for i, (data_x, data_y) in enumerate(zip(self.peak_x_value, self.peak_value)):
                # datetime을 float로 변환
                if isinstance(data_x, datetime):
                    data_x_float = mdates.date2num(data_x)
                else:
                    data_x_float = data_x

                # x도 datetime이면 변환
                if isinstance(x, datetime):
                    x_float = mdates.date2num(x)
                else:
                    x_float = x

                # y 값 변환
                if isinstance(y, list) and len(y) > 0:
                    y_val = float(y[0])
                else:
                    y_val = float(y)

                dx = abs(x_float - data_x_float)
                dy = abs(y_val - data_y)

                # 우선순위: x가 같으면 y 차이만, 아니면 전체 거리
                if dx == 0:
                    dist = dy
                else:
                    dist = np.hypot(dx, dy)

                if dist < min_distance:
                    min_distance = dist
                    closest_index = i

            # ===== 3. 클릭 범위 검증 =====
            if closest_index == -1:
                print("ℹ️ 가까운 데이터 포인트를 찾을 수 없습니다")
                return

            # ===== 4. 기존 마커 제거 =====
            if hasattr(self, 'peak_marker') and self.peak_marker:
                try:
                    self.peak_marker.remove()
                except:
                    pass

            if hasattr(self, 'peak_annotation') and self.peak_annotation:
                try:
                    self.peak_annotation.remove()
                except:
                    pass

            # ===== 5. 새 마커 추가 =====
            file_name = self.peak_file_names[closest_index]
            x_val = self.peak_x_value[closest_index]
            y_val = self.peak_value[closest_index]

            self.peak_marker = self.peak_ax.plot(
                x_val, y_val,
                marker='o', color='red', markersize=7
            )[0]

            # ===== 6. 주석 추가 =====
            annotation_text = f"{file_name}\nX: {x_val}\nY: {y_val:.4f}"

            self.peak_annotation = self.peak_ax.annotate(
                annotation_text,
                (x_val, y_val),
                textcoords="offset points",
                xytext=(10, 10),
                ha='left',
                fontsize=7,
                bbox=dict(boxstyle="round,pad=0.3", edgecolor="black",
                          facecolor="lightyellow", alpha=0.8)
            )

            self.peak_canvas.draw()

            print(f"📍 Peak 마커 추가: 파일={file_name}, Peak={y_val:.4f}")

            # ===== 7. Pick Data List 추가 =====
            if hasattr(self, 'data_list_text'):
                try:
                    self.add_marker_filename_to_list(file_name)
                except Exception as e:
                    print(f"⚠️ Pick Data List 추가 실패: {e}")

        except Exception as e:
            print(f"⚠️ add_marker_peak 오류: {e}")
            import traceback
            traceback.print_exc()


"""
cn_3F_trend_optimized.py의 if __name__ == "__main__": 부분 완전 교체
(임포트 문제 없음, 모든 코드 포함)
"""

if __name__ == "__main__":
    import faulthandler
    faulthandler.enable()

    # ===== 스플래시 스크린 클래스 (임포트 불필요) =====
    class ModernSplashScreen(QtWidgets.QWidget):
        """CNAVE 스플래시 스크린"""

        def __init__(self, version="v1.0.0", parent=None):
            super().__init__(parent)
            self.version = version

            # 창 설정
            self.setWindowFlags(
                QtCore.Qt.WindowStaysOnTopHint |
                QtCore.Qt.FramelessWindowHint |
                QtCore.Qt.Tool
            )
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            self.setFixedSize(600, 450)

            # 화면 중앙 배치
            screen = QtWidgets.QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)

            # UI 구성
            self.setup_ui()

            # 자동 닫기 타이머 (3초)
            self.close_timer = QtCore.QTimer()
            self.close_timer.setSingleShot(True)
            self.close_timer.timeout.connect(self.close)
            self.close_timer.start(10000)

        def setup_ui(self):
            """UI 구성"""
            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)

            # 메인 프레임
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

            # 로고
            logo_label = QtWidgets.QLabel()
            try:
                pixmap = QtGui.QPixmap("icn.ico")
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(128, 128, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    logo_label.setPixmap(pixmap)
                else:
                    raise Exception("로고 로드 실패")
            except:
                logo_label.setText("🚀")
                logo_label.setStyleSheet("font-size: 64px;")
            logo_label.setAlignment(QtCore.Qt.AlignCenter)
            frame_layout.addWidget(logo_label)

            # 회사명
            company_label = QtWidgets.QLabel("CNAVE")
            company_label.setStyleSheet("""
                QLabel {
                    font-size: 32px;
                    font-weight: bold;
                    color: #003366;
                    font-family: 'Arial';
                }
            """)
            company_label.setAlignment(QtCore.Qt.AlignCenter)
            frame_layout.addWidget(company_label)

            # 프로그램명
            app_label = QtWidgets.QLabel("CNXMW Post Processor")
            app_label.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    color: #666666;
                    font-family: 'Arial';
                }
            """)
            app_label.setAlignment(QtCore.Qt.AlignCenter)
            frame_layout.addWidget(app_label)

            # 버전
            version_label = QtWidgets.QLabel(self.version)
            version_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #999999;
                    font-family: 'Arial';
                }
            """)
            version_label.setAlignment(QtCore.Qt.AlignCenter)
            frame_layout.addWidget(version_label)

            # 프로그레스 바
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

            # 로딩 메시지
            self.status_label = QtWidgets.QLabel("Starting...")
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #666666;
                    font-family: 'Arial';
                }
            """)
            self.status_label.setAlignment(QtCore.Qt.AlignCenter)
            frame_layout.addWidget(self.status_label)

            frame_layout.addStretch()

            # 저작권
            copyright_label = QtWidgets.QLabel("© 2024-2026 CNAVE. All rights reserved.")
            copyright_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #999999;
                    font-family: 'Arial';
                }
            """)
            copyright_label.setAlignment(QtCore.Qt.AlignCenter)
            frame_layout.addWidget(copyright_label)

            layout.addWidget(frame)

            # 애니메이션 시작
            self.start_progress_animation()

        def start_progress_animation(self):
            """프로그레스 바 애니메이션"""
            self.progress_value = 0
            self.progress_timer = QtCore.QTimer()
            self.progress_timer.timeout.connect(self.update_progress)
            self.progress_timer.start(30)

        def update_progress(self):
            """진행률 업데이트"""
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

        def set_progress(self, value, message=None):
            """진행률 설정"""
            self.progress_bar.setValue(value)
            if message:
                self.status_label.setText(message)
            QtWidgets.QApplication.processEvents()

    # ===== 프로그램 정보 =====
    VERSION = "v1.0.0"
    APP_NAME = "CNAVE CNXMW Post Processor"

    # ⭐ High DPI 지원
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    # Windows DPI 설정
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = QtWidgets.QApplication(sys.argv)

    # ===== 1. 스플래시 스크린 표시 =====
    splash = ModernSplashScreen(version=VERSION)
    splash.show()
    splash.set_progress(10, "Loading libraries...")
    QtWidgets.QApplication.processEvents()

    # ===== 2. 폰트 설정 =====
    screen = app.primaryScreen()
    dpi = screen.logicalDotsPerInch()
    scale_factor = dpi / 96.0
    font_size = max(9, int(10 * scale_factor))
    font = QtGui.QFont("Malgun Gothic", font_size)
    app.setFont(font)
    app.setWindowIcon(QtGui.QIcon("icn.ico"))

    splash.set_progress(30, "Initializing UI...")
    QtWidgets.QApplication.processEvents()

    # ===== 3. 메인 윈도우 생성 =====
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()

    splash.set_progress(60, "Setting up components...")
    QtWidgets.QApplication.processEvents()

    ui.setupUi(MainWindow)
    ui.retranslateUi(MainWindow)

    MainWindow.setWindowTitle(APP_NAME)
    MainWindow.setWindowIcon(QtGui.QIcon("icn.ico"))

    splash.set_progress(80, "Finalizing...")
    QtWidgets.QApplication.processEvents()

    # 창 크기 설정
    screen_geometry = screen.availableGeometry()
    window_width = int(screen_geometry.width() * 0.9)
    window_height = int(screen_geometry.height() * 0.9)
    MainWindow.resize(window_width, window_height)
    MainWindow.move(
        (screen_geometry.width() - window_width) // 2,
        (screen_geometry.height() - window_height) // 2
    )

    splash.set_progress(100, "Ready!")
    QtWidgets.QApplication.processEvents()

    # ===== 4. 스플래시 닫고 메인 윈도우 표시 =====
    def show_main_window():
        splash.close()
        MainWindow.show()

    QtCore.QTimer.singleShot(500, show_main_window)

    # ===== 5. 프로그램 실행 =====
    try:
        exit_code = app.exec_()
        import gc
        gc.collect()

        perf_logger.log_info("프로그램 종료")
        try:
            perf_logger.generate_summary()
            perf_logger.save_json_report()
            print("\n✅ 성능 리포트 저장 완료")
        except Exception as e:
            print(f"⚠️ 리포트 저장 실패: {e}")

        sys.exit(exit_code)

    except Exception as e:
        import gc
        gc.collect()
        print(f"\n❌ 프로그램 오류: {e}")

        try:
            perf_logger.generate_summary()
            perf_logger.save_json_report()
        except:
            pass

        sys.exit(1)

