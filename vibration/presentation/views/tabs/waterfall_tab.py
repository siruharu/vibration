"""
워터폴 분석 탭 뷰 - 레거시 tab_2의 정확한 복제.

cn_3F_trend_optimized.py 2009-2350 라인과 동일한 픽셀 완벽 UI 호환.
FFT 옵션과 축 컨트롤이 포함된 시간-주파수 워터폴 3D 플롯을 표시합니다.
"""
from typing import Optional, List

from typing import Tuple

from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QAbstractItemView, QCheckBox, QTextBrowser,
    QTextEdit, QComboBox, QLineEdit, QSizePolicy, QApplication, QDateEdit, QMenu
)
from PyQt5.QtCore import pyqtSignal, Qt, QDate
from PyQt5.QtGui import QScreen, QColor, QFont, QCursor

import numpy as np

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from vibration.presentation.views.dialogs.responsive_layout_utils import WidgetSizes, PlotFontSizes


VIEW_TYPE_LABELS = {
    'ACC': 'Vibration Acceleration\n(m/s², RMS)',
    'VEL': 'Vibration Velocity\n(mm/s, RMS)',
    'DIS': 'Vibration Displacement\n(μm, RMS)'
}

CHANNEL_COLORS = {
    '1': QColor(31, 119, 180),
    '2': QColor(44, 160, 44),
    '3': QColor(214, 39, 40),
    '4': QColor(148, 103, 189),
    '5': QColor(255, 127, 14),
    '6': QColor(140, 86, 75),
}


class WaterfallTabView(QWidget):
    """
    워터폴 분석 탭 뷰 - 레거시 정확 복제.
    
    레거시 tab_2 레이아웃 구조:
    - 좌측: 6개 채널 체크박스 (checkBox_7-12), Select All/Deselect All, 파일 목록 (Querry_list2)
    - 중앙: FFT 옵션 (Δf, Window, Overlap, Convert, Angle), Plot Waterfall 버튼
    - 우측: X/Z 축 컨트롤 (Auto 체크박스, Min/Max 입력, Set/Auto Scale 버튼)
    - 하단: 워터폴 3D 플롯용 Matplotlib figure
    
    연산 처리를 위해 프레젠터에 시그널을 발행합니다.
    """
    
    # 프레젠터용 시그널
    compute_requested = pyqtSignal(bool)  # force_recalculate flag
    set_x_axis_requested = pyqtSignal()
    set_z_axis_requested = pyqtSignal()
    auto_scale_x_requested = pyqtSignal()
    auto_scale_z_requested = pyqtSignal()
    angle_changed = pyqtSignal()
    channel_filter_changed = pyqtSignal()
    date_filter_changed = pyqtSignal(str, str)
    band_trend_requested = pyqtSignal(float)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """워터폴 탭 뷰를 초기화합니다."""
        super().__init__(parent)
        self._all_files: List[str] = []
        self._original_limits: dict = {}
        self.hover_dot = None
        self.hover_pos = None
        self.waterfall_marker = None
        self.waterfall_annotation = None
        self._picking_data: List[tuple[float, float, float, float, str]] = []
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """레거시 tab_2와 정확히 일치하는 UI 레이아웃을 설정합니다."""
        self.tab2_layout = QGridLayout(self)
        
        # 메인 섹션 생성
        self._create_left_panel()
        self._create_middle_panel()
        self._create_right_panel()
        self._create_plot_area()
        
        self.tab2_layout.addLayout(self.data2_listlayout, 0, 0, 2, 1, Qt.AlignmentFlag.AlignTop)
        self.tab2_layout.addLayout(self.left_layout, 0, 1)
        self.tab2_layout.addLayout(self.waterfall_scale_layout, 0, 2, 1, 1, Qt.AlignmentFlag.AlignRight)
        self.tab2_layout.addLayout(self.waterfall_graph_layout, 1, 1, 1, 8, Qt.AlignmentFlag.AlignLeft)
        
        self.tab2_layout.setColumnStretch(1, 4)
     
    def _create_left_panel(self):
        """체크박스, 버튼, 파일 목록이 포함된 좌측 패널을 생성합니다."""
        self.data2_listlayout = QVBoxLayout()
        
        # 채널 체크박스 - 레거시 명명 그대로
        self.checkboxs_layout = QGridLayout()
        
        self.checkBox_7 = QCheckBox("1CH")
        self.checkBox_7.setObjectName("checkBox_7")
        self.checkboxs_layout.addWidget(self.checkBox_7, 0, 0)
        
        self.checkBox_8 = QCheckBox("2CH")
        self.checkBox_8.setObjectName("checkBox_8")
        self.checkboxs_layout.addWidget(self.checkBox_8, 0, 1)
        
        self.checkBox_9 = QCheckBox("3CH")
        self.checkBox_9.setObjectName("checkBox_9")
        self.checkboxs_layout.addWidget(self.checkBox_9, 0, 2)
        
        self.checkBox_10 = QCheckBox("4CH")
        self.checkBox_10.setObjectName("checkBox_10")
        self.checkboxs_layout.addWidget(self.checkBox_10, 1, 0)
        
        self.checkBox_11 = QCheckBox("5CH")
        self.checkBox_11.setObjectName("checkBox_11")
        self.checkboxs_layout.addWidget(self.checkBox_11, 1, 1)
        
        self.checkBox_12 = QCheckBox("6CH")
        self.checkBox_12.setObjectName("checkBox_12")
        self.checkboxs_layout.addWidget(self.checkBox_12, 1, 2)
        
        # 전체 선택 / 전체 해제 버튼
        self.button2_leftlayout = QHBoxLayout()
        
        self.select_all_btn2 = QPushButton("Select All")
        self.select_all_btn2.setObjectName("select_all_btn")
        self.button2_leftlayout.addWidget(self.select_all_btn2)
        
        self.deselect_all_btn2 = QPushButton("Deselect All")
        self.deselect_all_btn2.setObjectName("deselect_all_btn")
        self.button2_leftlayout.addWidget(self.deselect_all_btn2)
        
        # 날짜 필터
        date_filter_layout = QHBoxLayout()
        self.date_from2 = QDateEdit()
        self.date_from2.setCalendarPopup(True)
        self.date_from2.setDisplayFormat("yyyy-MM-dd")
        self.date_from2.setDate(QDate(2000, 1, 1))
        date_filter_layout.addWidget(QLabel("From:"))
        date_filter_layout.addWidget(self.date_from2)

        self.date_to2 = QDateEdit()
        self.date_to2.setCalendarPopup(True)
        self.date_to2.setDisplayFormat("yyyy-MM-dd")
        self.date_to2.setDate(QDate.currentDate())
        date_filter_layout.addWidget(QLabel("To:"))
        date_filter_layout.addWidget(self.date_to2)

        self.date_filter_btn2 = QPushButton("Filter")
        self.date_filter_btn2.setStyleSheet("background-color: lightgray;color: black;")
        date_filter_layout.addWidget(self.date_filter_btn2)

        # 파일 목록 - 레거시 명명 그대로
        self.Qurry_layout2 = QHBoxLayout()
        self.Querry_list2 = QListWidget()
        self.Querry_list2.setObjectName("Querry_list2")
        self.Querry_list2.setMinimumWidth(WidgetSizes.file_list_width())
        self.Querry_list2.setMaximumWidth(WidgetSizes.file_list_width())
        self.Querry_list2.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.Querry_list2.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.Qurry_layout2.addWidget(self.Querry_list2)
        
        # 데이터 레이아웃으로 결합
        self.data2_listlayout.addLayout(self.checkboxs_layout)
        self.data2_listlayout.addLayout(self.button2_leftlayout)
        self.data2_listlayout.addLayout(date_filter_layout)
        self.data2_listlayout.addLayout(self.Qurry_layout2)
        
        # 다른 탭과의 일관성을 위한 별칭
        self.file_list = self.Querry_list2
    
    def _create_middle_panel(self):
        """FFT 옵션과 Plot Waterfall 버튼이 포함된 중앙 패널을 생성합니다."""
        self.left_layout = QGridLayout()
        self.options2_layout = QGridLayout()
        
        # FFT 옵션 라벨
        self.Plot_Options_2 = QTextBrowser()
        self.Plot_Options_2.setMaximumSize(*WidgetSizes.option_control())
        self.Plot_Options_2.setObjectName("Plot_Options_2")
        self.Plot_Options_2.setHtml("FFT Options")
        self.options2_layout.addWidget(self.Plot_Options_2, 0, 0)
        
        # Δf label
        self.textBrowser_18 = QTextBrowser()
        self.textBrowser_18.setMaximumSize(*WidgetSizes.option_control())
        self.textBrowser_18.setObjectName("textBrowser_18")
        self.textBrowser_18.setHtml("Δf:")
        self.options2_layout.addWidget(self.textBrowser_18, 1, 0)
        
        # Δf input - exact legacy naming: Hz_2
        self.Hz_2 = QTextEdit()
        self.Hz_2.setMaximumSize(*WidgetSizes.option_control())
        self.Hz_2.setPlaceholderText("Hz")
        self.Hz_2.setObjectName("Hz_2")
        self.Hz_2.setStyleSheet("background-color: lightgray; color: black;")
        self.options2_layout.addWidget(self.Hz_2, 1, 1)
        
        # Window Function label
        self.textBrowser_19 = QTextBrowser()
        self.textBrowser_19.setMaximumSize(*WidgetSizes.option_control())
        self.textBrowser_19.setObjectName("textBrowser_19")
        self.textBrowser_19.setHtml("Window Function:")
        self.options2_layout.addWidget(self.textBrowser_19, 2, 0)
        
        # Window Function combo - exact legacy naming: Function_2
        self.Function_2 = QComboBox()
        self.Function_2.setMaximumSize(*WidgetSizes.option_control())
        self.Function_2.setObjectName("Function_2")
        self.Function_2.setStyleSheet("background-color: lightgray; color: black;")
        self.Function_2.addItem("Rectangular")
        self.Function_2.addItem("Hanning")
        self.Function_2.addItem("Flattop")
        self.options2_layout.addWidget(self.Function_2, 2, 1)
        
        # Overlap Factor label
        self.textBrowser_20 = QTextBrowser()
        self.textBrowser_20.setMaximumSize(*WidgetSizes.option_control())
        self.textBrowser_20.setObjectName("textBrowser_20")
        self.textBrowser_20.setHtml("Overlap Factor:")
        self.options2_layout.addWidget(self.textBrowser_20, 3, 0)
        
        # Overlap Factor combo - exact legacy naming: Overlap_Factor_2
        self.Overlap_Factor_2 = QComboBox()
        self.Overlap_Factor_2.setMaximumSize(*WidgetSizes.option_control())
        self.Overlap_Factor_2.setObjectName("Overlap_Factor_2")
        self.Overlap_Factor_2.setStyleSheet("background-color: lightgray; color: black;")
        self.Overlap_Factor_2.addItem("0%")
        self.Overlap_Factor_2.addItem("25%")
        self.Overlap_Factor_2.addItem("50%")
        self.Overlap_Factor_2.addItem("75%")
        self.options2_layout.addWidget(self.Overlap_Factor_2, 3, 1)
        
        # Convert label
        self.select_type_convert2 = QTextBrowser()
        self.select_type_convert2.setObjectName("Convert")
        self.select_type_convert2.setMaximumSize(*WidgetSizes.option_control())
        self.select_type_convert2.setHtml("Convert")
        self.options2_layout.addWidget(self.select_type_convert2, 4, 0)
        
        # Convert combo - exact legacy naming: select_pytpe2
        self.select_pytpe2 = QComboBox()
        self.select_pytpe2.setObjectName("select_pytpe")
        self.select_pytpe2.setMaximumSize(*WidgetSizes.option_control())
        self.select_pytpe2.setStyleSheet("background-color: lightgray; color: black;")
        self.select_pytpe2.addItem("ACC", 1)
        self.select_pytpe2.addItem("VEL", 2)
        self.select_pytpe2.addItem("DIS", 3)
        self.options2_layout.addWidget(self.select_pytpe2, 4, 1)
        
        # Angle label
        self.input_angle = QTextBrowser()
        self.input_angle.setObjectName("angle")
        self.input_angle.setMaximumSize(*WidgetSizes.option_control())
        self.input_angle.setHtml("Angle")
        self.options2_layout.addWidget(self.input_angle, 5, 0)
        
        # Angle input - exact legacy naming: angle_input
        self.angle_input = QLineEdit()
        self.angle_input.setPlaceholderText("각도 (30)")
        self.angle_input.setStyleSheet("background-color: lightgray; color: black;")
        self.angle_input.setMaximumSize(*WidgetSizes.option_control())
        self.options2_layout.addWidget(self.angle_input, 5, 1)
        
        # Plot Waterfall button
        self.plot_waterfall_button = QPushButton("Plot Waterfall")
        self.plot_waterfall_button.setMaximumSize(*WidgetSizes.option_control())
        self.options2_layout.addWidget(self.plot_waterfall_button)
        
        self.band_trend_button = QPushButton("Band Trend")
        self.band_trend_button.setMaximumSize(*WidgetSizes.option_control())
        self.options2_layout.addWidget(self.band_trend_button)
        
        # 레이아웃 설정
        self.options2_layout.setContentsMargins(0, 0, 0, 0)
        self.options2_layout.setSpacing(0)
        self.options2_layout.setRowStretch(0, 1)
        self.options2_layout.setRowStretch(1, 1)
        self.options2_layout.setColumnStretch(1, 1)
        
        self.left_layout.addLayout(self.options2_layout, 1, 0, 1, 1)
        
        # 일관성을 위한 별칭
        self.delta_f_input = self.Hz_2
        self.window_combo = self.Function_2
        self.overlap_combo = self.Overlap_Factor_2
        self.view_type_combo = self.select_pytpe2
    
    def _create_right_panel(self):
        """X/Z 축 스케일 컨트롤이 포함된 우측 패널을 생성합니다."""
        self.waterfall_scale_layout = QVBoxLayout()
        
        # X축 컨트롤
        self.x_scale_layout = QHBoxLayout()
        self.x_scale_layout2 = QHBoxLayout()
        
        # Auto X checkbox and Auto Scale button
        self.auto_scale_x_2 = QCheckBox("Auto X")
        self.auto_scale_x_2.setChecked(True)
        self.x_scale_layout.addWidget(self.auto_scale_x_2)
        
        self.water_x_autoscale = QPushButton("Auto Scale")
        self.water_x_autoscale.setMaximumSize(*WidgetSizes.axis_button())
        self.x_scale_layout.addWidget(self.water_x_autoscale)
        
        # X Min/Max inputs and Set button
        self.x_min_input2 = QLineEdit()
        self.x_min_input2.setMaximumSize(*WidgetSizes.axis_input())
        self.x_min_input2.setPlaceholderText("X min")
        self.x_min_input2.setStyleSheet("background-color: lightgray; color: black;")
        self.x_scale_layout2.addWidget(self.x_min_input2)
        
        self.x_max_input2 = QLineEdit()
        self.x_max_input2.setMaximumSize(*WidgetSizes.axis_input())
        self.x_max_input2.setPlaceholderText("X max")
        self.x_max_input2.setStyleSheet("background-color: lightgray; color: black;")
        self.x_scale_layout2.addWidget(self.x_max_input2)
        
        self.water_x_set = QPushButton("Set")
        self.water_x_set.setMaximumSize(*WidgetSizes.axis_input())
        self.x_scale_layout2.addWidget(self.water_x_set)
        
        # Z축 컨트롤
        self.z_scale_layout = QHBoxLayout()
        self.z_scale_layout2 = QHBoxLayout()
        
        # Auto Z checkbox and Auto Scale button
        self.auto_scale_z = QCheckBox("Auto Z")
        self.auto_scale_z.setChecked(True)
        self.z_scale_layout.addWidget(self.auto_scale_z)
        
        self.water_z_autoscale = QPushButton("Auto Scale")
        self.water_z_autoscale.setMaximumSize(*WidgetSizes.axis_button())
        self.z_scale_layout.addWidget(self.water_z_autoscale)
        
        # Z Min/Max inputs and Set button
        self.z_min_input = QLineEdit()
        self.z_min_input.setMaximumSize(*WidgetSizes.axis_input())
        self.z_min_input.setPlaceholderText("Z min")
        self.z_min_input.setStyleSheet("background-color: lightgray; color: black;")
        self.z_scale_layout2.addWidget(self.z_min_input)
        
        self.z_max_input = QLineEdit()
        self.z_max_input.setMaximumSize(*WidgetSizes.axis_input())
        self.z_max_input.setPlaceholderText("Z max")
        self.z_max_input.setStyleSheet("background-color: lightgray; color: black;")
        self.z_scale_layout2.addWidget(self.z_max_input)
        
        self.water_z_set = QPushButton("Set")
        self.water_z_set.setMaximumSize(*WidgetSizes.axis_input())
        self.z_scale_layout2.addWidget(self.water_z_set)
        
        # 모든 스케일 레이아웃 추가
        self.waterfall_scale_layout.addLayout(self.x_scale_layout)
        self.waterfall_scale_layout.addLayout(self.x_scale_layout2)
        self.waterfall_scale_layout.addLayout(self.z_scale_layout)
        self.waterfall_scale_layout.addLayout(self.z_scale_layout2)
    
    def _create_plot_area(self):
        """워터폴 3D 플롯용 matplotlib figure를 생성합니다."""
        self.waterfall_graph_layout = QVBoxLayout()
        
        screen: Optional[QScreen] = QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch() if screen else 96.0
        self.waterfall_figure = Figure(figsize=(10, 4), dpi=dpi)
        self.waterfall_canvas = FigureCanvas(self.waterfall_figure)
        self.waterfall_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.waterfall_ax = self.waterfall_figure.add_subplot(111)
        self.waterfall_ax.set_title("Waterfall Spectrum", fontsize=PlotFontSizes.TITLE)
        
        self.waterfall_graph_layout.addWidget(self.waterfall_canvas)
        self._init_mouse_events()
    
    def _connect_signals(self):
        """프레젠터를 위해 버튼 시그널을 뷰 시그널에 연결합니다."""
        # 플롯 버튼 - 강제 재계산
        self.plot_waterfall_button.clicked.connect(lambda: self.compute_requested.emit(True))
        
        # 축 컨트롤
        self.water_x_set.clicked.connect(self.set_x_axis_requested.emit)
        self.water_z_set.clicked.connect(self.set_z_axis_requested.emit)
        self.water_x_autoscale.clicked.connect(self.auto_scale_x_requested.emit)
        self.water_z_autoscale.clicked.connect(self.auto_scale_z_requested.emit)
        
        # 각도 입력 - Enter 시 발행
        self.angle_input.returnPressed.connect(self.angle_changed.emit)
        
        # 전체 선택 / 전체 해제 버튼
        self.select_all_btn2.clicked.connect(self.Querry_list2.selectAll)
        self.deselect_all_btn2.clicked.connect(self.Querry_list2.clearSelection)
        
        # 채널 체크박스 - 파일 목록 필터
        self.checkBox_7.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_8.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_9.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_10.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_11.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_12.stateChanged.connect(self._on_channel_filter_changed)
        
        self.date_filter_btn2.clicked.connect(self._on_date_filter_clicked)
        self.band_trend_button.clicked.connect(self._on_band_trend_clicked)

    
    def _on_channel_filter_changed(self):
        """채널 체크박스 상태 변경을 처리 - 파일 목록을 필터링합니다."""
        self._update_filtered_file_list()
        self.channel_filter_changed.emit()
    
    def _update_filtered_file_list(self):
        """선택된 채널 체크박스에 따라 파일 목록을 업데이트합니다."""
        if not self._all_files:
            return
        
        selected_channels = []
        checkboxes = [
            self.checkBox_7, self.checkBox_8, self.checkBox_9,
            self.checkBox_10, self.checkBox_11, self.checkBox_12
        ]
        for idx, checkbox in enumerate(checkboxes, start=1):
            if checkbox.isChecked():
                selected_channels.append(str(idx))
        
        if not selected_channels:
            self._populate_file_list_grouped(self._all_files)
            return
        
        filtered_files = [
            f for f in self._all_files
            if any(f.endswith(f"_{ch}.txt") for ch in selected_channels)
        ]
        self._populate_file_list_grouped(filtered_files)
    
    @staticmethod
    def _extract_channel(filename: str) -> str:
        try:
            return filename.rsplit('_', 1)[-1].replace('.txt', '')
        except (IndexError, ValueError):
            return '0'
    
    def _populate_file_list_grouped(self, files: List[str]):
        self.Querry_list2.clear()
        
        grouped: dict[str, list[str]] = {}
        for f in files:
            ch = self._extract_channel(f)
            grouped.setdefault(ch, []).append(f)
        
        for ch_key in sorted(grouped.keys()):
            header = QListWidgetItem(f"── CH{ch_key} ({len(grouped[ch_key])}) ──")
            header.setFlags(Qt.ItemFlag.NoItemFlags)
            header_font = QFont()
            header_font.setBold(True)
            header.setFont(header_font)
            color = CHANNEL_COLORS.get(ch_key, QColor(100, 100, 100))
            header.setForeground(color)
            self.Querry_list2.addItem(header)
            
            for filename in grouped[ch_key]:
                item = QListWidgetItem(filename)
                item.setForeground(color)
                self.Querry_list2.addItem(item)
    
    def get_parameters(self) -> dict[str, object]:
        """UI 입력에서 현재 FFT 파라미터를 가져옵니다."""
        try:
            delta_f = float(self.Hz_2.toPlainText().strip())
        except (ValueError, AttributeError):
            delta_f = 1.0
        
        try:
            angle = float(self.angle_input.text().strip()) if self.angle_input.text().strip() else 270.0
        except ValueError:
            angle = 270.0
        
        return {
            'delta_f': delta_f,
            'window_type': self.Function_2.currentText().lower(),
            'overlap': float(self.Overlap_Factor_2.currentText().replace('%', '')),
            'view_type': self.select_pytpe2.currentData(),
            'angle': angle
        }
    
    def get_x_axis_limits(self) -> Tuple[Optional[float], Optional[float]]:
        """입력에서 X축 범위를 가져옵니다."""
        try:
            x_min = float(self.x_min_input2.text())
            x_max = float(self.x_max_input2.text())
            if x_min >= x_max:
                return None, None
            return x_min, x_max
        except ValueError:
            return None, None
    
    def get_z_axis_limits(self) -> Tuple[Optional[float], Optional[float]]:
        """입력에서 Z축 범위를 가져옵니다."""
        try:
            z_min = float(self.z_min_input.text())
            z_max = float(self.z_max_input.text())
            if z_min >= z_max:
                return None, None
            return z_min, z_max
        except ValueError:
            return None, None
    
    def set_auto_x_checked(self, checked: bool):
        """Auto X 체크박스 상태를 설정합니다."""
        self.auto_scale_x_2.setChecked(checked)
    
    def set_auto_z_checked(self, checked: bool):
        """Auto Z 체크박스 상태를 설정합니다."""
        self.auto_scale_z.setChecked(checked)
    
    def clear_plot(self):
        """워터폴 플롯을 초기화합니다."""
        self.waterfall_ax.clear()
        self.waterfall_ax.set_title("Waterfall Spectrum", fontsize=PlotFontSizes.TITLE)
        self.waterfall_canvas.draw()
    
    def set_files(self, files: List[str]):
        """Data Query 탭에서 파일 목록을 업데이트합니다."""
        self._all_files = files.copy()
        self._populate_file_list_grouped(files)
    
    def get_selected_files(self) -> List[str]:
        """현재 선택된 파일 목록을 반환합니다."""
        return [item.text() for item in self.Querry_list2.selectedItems()]
    
    def get_figure(self) -> Figure:
        """직접 플로팅을 위한 matplotlib figure를 반환합니다."""
        return self.waterfall_figure
    
    def get_axes(self):
        """직접 플로팅을 위한 matplotlib axes를 반환합니다."""
        return self.waterfall_ax
    
    def set_axes(self, ax):
        """figure 초기화 후 matplotlib axes 참조를 설정합니다."""
        self.waterfall_ax = ax
    
    def draw(self):
        """캔버스를 다시 그립니다."""
        self.waterfall_canvas.draw()
    
    def _on_date_filter_clicked(self):
        from_str = self.date_from2.date().toString("yyyy-MM-dd")
        to_str = self.date_to2.date().toString("yyyy-MM-dd")
        self.date_filter_changed.emit(from_str, to_str)
    
    def _on_band_trend_clicked(self):
        from PyQt5.QtWidgets import QInputDialog
        freq, ok = QInputDialog.getDouble(
            self, "Band Trend", "Frequency (Hz):", value=100.0, min=0.0, max=50000.0, decimals=1
        )
        if ok:
            self.band_trend_requested.emit(freq)
    
    def _init_mouse_events(self):
        self.waterfall_canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.waterfall_canvas.mpl_connect('button_press_event', self._on_mouse_click)
        self.waterfall_canvas.mpl_connect('scroll_event', self._on_scroll)
    
    def _save_original_limits(self):
        self._original_limits['waterfall'] = (self.waterfall_ax.get_xlim(), self.waterfall_ax.get_ylim())
    
    def _reset_zoom(self):
        if 'waterfall' in self._original_limits:
            xlim, ylim = self._original_limits['waterfall']
            self.waterfall_ax.set_xlim(xlim)
            self.waterfall_ax.set_ylim(ylim)
            self.waterfall_canvas.draw_idle()
    
    def _on_scroll(self, event):
        if event.inaxes != self.waterfall_ax:
            return
        
        if 'waterfall' not in self._original_limits:
            self._save_original_limits()
        
        xlim = self.waterfall_ax.get_xlim()
        
        modifiers = QApplication.keyboardModifiers()
        
        if modifiers & Qt.ControlModifier:
            shift = (xlim[1] - xlim[0]) * (0.1 if event.button == 'up' else -0.1)
            self.waterfall_ax.set_xlim(xlim[0] + shift, xlim[1] + shift)
            self.waterfall_canvas.draw_idle()
            return
        
        scale_factor = 0.85 if event.button == 'up' else 1.15
        xdata = event.xdata
        
        self.waterfall_ax.set_xlim(xdata - (xdata - xlim[0]) * scale_factor,
                                   xdata + (xlim[1] - xdata) * scale_factor)
        self.waterfall_canvas.draw_idle()
    
    def set_picking_data(self, data: List[tuple[float, float, float, float, str]]):
        self._picking_data = data
    
    def _on_mouse_move(self, event):
        if not event.inaxes:
            if self.hover_pos is not None:
                if self.hover_dot:
                    self.hover_dot.set_data([], [])
                self.hover_pos = None
                self.waterfall_canvas.draw_idle()
            return
        
        if not self._picking_data:
            return
        
        closest = None
        min_dist = np.inf
        
        for entry in self._picking_data:
            plot_x, plot_y = entry[0], entry[1]
            dist = np.hypot(event.xdata - plot_x, event.ydata - plot_y)
            if dist < min_dist:
                min_dist = dist
                closest = entry
        
        if closest is not None:
            if self.hover_dot is None:
                self.hover_dot = self.waterfall_ax.plot([], [], 'ko', markersize=5, alpha=0.5)[0]
            self.hover_dot.set_data([closest[0]], [closest[1]])
            self.hover_pos = closest
            self.waterfall_canvas.draw_idle()
    
    def _on_mouse_click(self, event):
        if not event.inaxes:
            return
        if event.button == 1 and self.hover_pos is not None:
            self._add_picking_marker(self.hover_pos)
        elif event.button == 3:
            menu = QMenu(self)
            reset_action = menu.addAction("Reset Zoom")
            clear_action = menu.addAction("Clear Picking")
            action = menu.exec_(QCursor.pos())
            if action == reset_action:
                self._reset_zoom()
            elif action == clear_action:
                self._clear_picking_markers()
    
    def _add_picking_marker(self, data):
        plot_x, plot_y, freq, amp, fname = data[0], data[1], data[2], data[3], data[4]
        
        if self.waterfall_marker:
            try:
                self.waterfall_marker.remove()
            except Exception:
                pass
        if self.waterfall_annotation:
            try:
                self.waterfall_annotation.remove()
            except Exception:
                pass
        
        self.waterfall_marker = self.waterfall_ax.plot(
            plot_x, plot_y, marker='o', color='red', markersize=7
        )[0]
        
        annotation_text = f"{fname}\nFreq: {freq:.1f} Hz\nAmp: {amp:.4f}"
        self.waterfall_annotation = self.waterfall_ax.annotate(
            annotation_text,
            (plot_x, plot_y),
            textcoords="offset points",
            xytext=(10, 10),
            ha='left',
            fontsize=PlotFontSizes.ANNOTATION,
            bbox=dict(boxstyle="round,pad=0.3", edgecolor="black",
                     facecolor="lightyellow", alpha=0.8)
        )
        self.waterfall_canvas.draw_idle()
    
    def _clear_picking_markers(self):
        if self.waterfall_marker:
            try:
                self.waterfall_marker.remove()
                self.waterfall_marker = None
            except Exception:
                pass
        if self.waterfall_annotation:
            try:
                self.waterfall_annotation.remove()
                self.waterfall_annotation = None
            except Exception:
                pass
        self.waterfall_canvas.draw_idle()
