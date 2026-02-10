"""
스펙트럼 분석 탭 뷰 - 레거시 tab_3의 정확한 복제.

cn_3F_trend_optimized.py 1095-1650 라인과 동일한 픽셀 완벽 UI 호환.
"""
from typing import List, Optional

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QGridLayout, QVBoxLayout, QComboBox, QPushButton,
    QSplitter, QLabel, QListWidget, QAbstractItemView, QCheckBox, QTextBrowser,
    QTextEdit, QLineEdit, QSizePolicy, QApplication, QDateEdit, QInputDialog,
    QDialog, QDialogButtonBox, QFormLayout, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt, QDate

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.widgets import SpanSelector

from vibration.presentation.views.dialogs.responsive_layout_utils import WidgetSizes, PlotFontSizes


VIEW_TYPE_LABELS = {
    'ACC': 'Vibration Acceleration\n(m/s², RMS)',
    'VEL': 'Vibration Velocity\n(mm/s, RMS)',
    'DIS': 'Vibration Displacement\n(μm, RMS)'
}

WAVEFORM_Y_LABELS = {
    'ACC': 'Acceleration (m/s²)',
    'VEL': 'Velocity (mm/s)',
    'DIS': 'Displacement (μm)'
}

PLOT_COLORS = ['b', 'g', 'r', 'c', 'm', 'y']


class SpectrumTabView(QWidget):
    """
    시간/스펙트럼 탭 뷰 - 레거시 정확 복제.
    
    레거시 tab_3 레이아웃 구조:
    - 좌측: 체크박스, 파일 목록, 메타데이터
    - 우측 상단: FFT 옵션, Plot/Next 버튼
    - 하단: 파형 + 스펙트럼 플롯과 축 컨트롤
    """
    
    compute_requested = pyqtSignal()
    next_file_requested = pyqtSignal()
    view_type_changed = pyqtSignal(int)
    window_type_changed = pyqtSignal(str)
    file_clicked = pyqtSignal(str)
    date_filter_changed = pyqtSignal(str, str)
    refresh_requested = pyqtSignal()
    close_all_windows_requested = pyqtSignal()
    axis_range_changed = pyqtSignal(str, str, float, float)
    time_range_selected = pyqtSignal(float, float)
    channel_filter_changed = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_view_type = 'ACC'
        self.markers = []
        self.hover_dot = None
        self.hover_pos = None
        self.data_dict = {}
        self.mouse_tracking_enabled = True
        self._all_files: List[str] = []
        self._span_selector = None
        self._batch_mode = False
        self._original_limits: dict = {}
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        self.tab3_layout = QGridLayout(self)
        
        self._create_left_panel()
        self._create_top_right_controls()
        self._create_plot_area()
        
        self.tab3_layout.addLayout(self.lift_layout, 0, 0, 2, 1, Qt.AlignTop)
        self.tab3_layout.addLayout(self.data_center_allin, 0, 1, Qt.AlignTop)
        self.tab3_layout.addWidget(self.main_splitter, 1, 1, 1, 9)
        
        self.tab3_layout.setColumnStretch(1, 4)
    
    def _create_left_panel(self):
        """좌측 패널 생성 — 체크박스, 날짜 필터, 파일 목록."""
        self.lift_layout = QGridLayout()
        
        checksBox = QGridLayout()
        self.checkBox = QCheckBox("1CH")
        checksBox.addWidget(self.checkBox, 0, 0)
        self.checkBox_2 = QCheckBox("2CH")
        checksBox.addWidget(self.checkBox_2, 0, 1)
        self.checkBox_3 = QCheckBox("3CH")
        checksBox.addWidget(self.checkBox_3, 0, 2)
        self.checkBox_4 = QCheckBox("4CH")
        checksBox.addWidget(self.checkBox_4, 1, 0)
        self.checkBox_5 = QCheckBox("5CH")
        checksBox.addWidget(self.checkBox_5, 1, 1)
        self.checkBox_6 = QCheckBox("6CH")
        checksBox.addWidget(self.checkBox_6, 1, 2)
        
        button_layout2 = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        button_layout2.addWidget(self.select_all_btn)
        self.deselect_all_btn = QPushButton("Deselect All")
        button_layout2.addWidget(self.deselect_all_btn)
        
        date_filter_layout = QHBoxLayout()
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate(2000, 1, 1))
        date_filter_layout.addWidget(QLabel("From:"))
        date_filter_layout.addWidget(self.date_from)
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        date_filter_layout.addWidget(QLabel("To:"))
        date_filter_layout.addWidget(self.date_to)
        
        self.date_filter_btn = QPushButton("Filter")
        self.date_filter_btn.setStyleSheet("background-color: lightgray;color: black;")
        date_filter_layout.addWidget(self.date_filter_btn)
        
        self.Querry_list = QListWidget()
        self.Querry_list.setMinimumWidth(WidgetSizes.file_list_width())
        self.Querry_list.setMaximumWidth(WidgetSizes.file_list_width())
        self.Querry_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        self.lift_layout.addLayout(checksBox, 0, 0)
        self.lift_layout.addLayout(button_layout2, 1, 0)
        self.lift_layout.addLayout(date_filter_layout, 2, 0)
        self.lift_layout.addWidget(self.Querry_list, 3, 0)
        
        self.file_list = self.Querry_list
    
    def _create_top_right_controls(self):
        self.data_center_allin = QGridLayout()
        self.data_center_allin.setContentsMargins(0, 0, 0, 0)
        self.data_center_allin.setSpacing(0)
        
        data_center_layout = QGridLayout()
        data_listlayout = self._create_metadata_section()
        data_center_layout.addLayout(data_listlayout, 0, 0)
        data_center_layout.setRowStretch(0, 0)
        data_center_layout.setContentsMargins(0, 0, 0, 0)
        data_center_layout.setSpacing(0)
        
        data_center_layout2 = QGridLayout()
        optin_layout = self._create_fft_options()
        data_center_layout2.addLayout(optin_layout, 0, 0)
        data_center_layout2.setRowStretch(0, 0)
        data_center_layout2.setContentsMargins(0, 0, 0, 0)
        data_center_layout2.setSpacing(0)
        
        self.data_center_allin.addLayout(data_center_layout, 0, 0, Qt.AlignTop)
        self.data_center_allin.addLayout(data_center_layout2, 0, 1, Qt.AlignTop)
        self.data_center_allin.setContentsMargins(0, 0, 0, 0)
        self.data_center_allin.setSpacing(0)
    
    def _create_metadata_section(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.Sample_rate = QTextBrowser()
        self.Sample_rate.setMaximumSize(*WidgetSizes.meta_label())
        self.Sample_rate.setHtml("Sampling:")
        layout.addWidget(self.Sample_rate, 0, 0)
        
        self.Duration = QTextBrowser()
        self.Duration.setMaximumSize(*WidgetSizes.meta_label())
        self.Duration.setHtml("Record Length:")
        layout.addWidget(self.Duration, 1, 0)
        
        self.Rest_time = QTextBrowser()
        self.Rest_time.setMaximumSize(*WidgetSizes.meta_label())
        self.Rest_time.setHtml("Rest time:")
        layout.addWidget(self.Rest_time, 2, 0)
        
        self.IEPE = QTextBrowser()
        self.IEPE.setMaximumSize(*WidgetSizes.meta_label())
        self.IEPE.setHtml("IEPE enable:")
        layout.addWidget(self.IEPE, 3, 0)
        
        self.Channel = QTextBrowser()
        self.Channel.setMaximumSize(*WidgetSizes.meta_label())
        self.Channel.setHtml("Channel:")
        layout.addWidget(self.Channel, 4, 0)
        
        self.Sensitivity = QTextBrowser()
        self.Sensitivity.setMaximumSize(*WidgetSizes.meta_label())
        self.Sensitivity.setHtml("Sensitivity:")
        layout.addWidget(self.Sensitivity, 5, 0)
        
        self.Sensitivity2 = QTextBrowser()
        self.Sensitivity2.setMaximumSize(*WidgetSizes.meta_label())
        self.Sensitivity2.setHtml("Sensitivity_edit:")
        layout.addWidget(self.Sensitivity2, 6, 0)
        
        self.Sample_rate_view = QTextBrowser()
        self.Sample_rate_view.setMaximumSize(*WidgetSizes.meta_label())
        self.Sample_rate_view.setHtml("")
        layout.addWidget(self.Sample_rate_view, 0, 1)
        
        self.Duration_view = QTextBrowser()
        self.Duration_view.setMaximumSize(*WidgetSizes.meta_label())
        self.Duration_view.setHtml("")
        layout.addWidget(self.Duration_view, 1, 1)
        
        self.Rest_time_view = QTextBrowser()
        self.Rest_time_view.setMaximumSize(*WidgetSizes.meta_label())
        self.Rest_time_view.setHtml("")
        layout.addWidget(self.Rest_time_view, 2, 1)
        
        self.IEPE_view = QTextBrowser()
        self.IEPE_view.setMaximumSize(*WidgetSizes.meta_label())
        self.IEPE_view.setHtml("")
        layout.addWidget(self.IEPE_view, 3, 1)
        
        self.Channel_view = QTextBrowser()
        self.Channel_view.setMaximumSize(*WidgetSizes.meta_label())
        self.Channel_view.setHtml("")
        layout.addWidget(self.Channel_view, 4, 1)
        
        self.Sensitivity_view = QTextBrowser()
        self.Sensitivity_view.setMaximumSize(*WidgetSizes.meta_label())
        self.Sensitivity_view.setHtml("")
        layout.addWidget(self.Sensitivity_view, 5, 1)
        
        self.Sensitivity_edit = QLineEdit()
        self.Sensitivity_edit.setMaximumSize(*WidgetSizes.meta_label())
        self.Sensitivity_edit.setPlaceholderText("Edit Sensitivity")
        self.Sensitivity_edit.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.Sensitivity_edit, 6, 1)
        
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        
        return layout
    
    def _create_fft_options(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        self.Plot_Options = QTextBrowser()
        self.Plot_Options.setMaximumSize(*WidgetSizes.spec_control())
        self.Plot_Options.setHtml("FFT Options")
        layout.addWidget(self.Plot_Options, 0, 0)
        
        self.textBrowser_15 = QTextBrowser()
        self.textBrowser_15.setMaximumSize(*WidgetSizes.spec_control())
        self.textBrowser_15.setHtml("Δf:")
        layout.addWidget(self.textBrowser_15, 1, 0)
        
        self.Hz = QTextEdit()
        self.Hz.setPlaceholderText("")
        self.Hz.setStyleSheet("background-color: lightgray;color: black;")
        self.Hz.setMaximumSize(*WidgetSizes.spec_control())
        layout.addWidget(self.Hz, 1, 1)
        
        self.textBrowser_16 = QTextBrowser()
        self.textBrowser_16.setMaximumSize(*WidgetSizes.spec_control())
        self.textBrowser_16.setHtml("Windown Function:")
        layout.addWidget(self.textBrowser_16, 2, 0)
        
        self.Function = QComboBox()
        self.Function.setStyleSheet("background-color: lightgray;color: black;")
        self.Function.addItem("Rectangular")
        self.Function.addItem("Hanning")
        self.Function.addItem("Flattop")
        self.Function.setMaximumSize(*WidgetSizes.spec_control())
        layout.addWidget(self.Function, 2, 1)
        
        self.textBrowser_17 = QTextBrowser()
        self.textBrowser_17.setMaximumSize(*WidgetSizes.spec_control())
        self.textBrowser_17.setHtml("Overlap Factor:")
        layout.addWidget(self.textBrowser_17, 3, 0)
        
        self.Overlap_Factor = QComboBox()
        self.Overlap_Factor.setStyleSheet("background-color: lightgray;color: black;")
        self.Overlap_Factor.addItem("0%")
        self.Overlap_Factor.addItem("25%")
        self.Overlap_Factor.addItem("50%")
        self.Overlap_Factor.addItem("75%")
        self.Overlap_Factor.setMaximumSize(*WidgetSizes.spec_control())
        layout.addWidget(self.Overlap_Factor, 3, 1)
        
        self.select_type_convert = QTextBrowser()
        self.select_type_convert.setMaximumSize(*WidgetSizes.spec_control())
        self.select_type_convert.setHtml("Convert")
        layout.addWidget(self.select_type_convert, 4, 0)
        
        self.select_pytpe = QComboBox()
        self.select_pytpe.setStyleSheet("background-color: lightgray;color: black;")
        self.select_pytpe.addItem("ACC", 1)
        self.select_pytpe.addItem("VEL", 2)
        self.select_pytpe.addItem("DIS", 3)
        self.select_pytpe.setMaximumSize(*WidgetSizes.spec_control())
        layout.addWidget(self.select_pytpe, 4, 1)
        
        btn_style = "background-color: lightgray;color: black;"
        
        self.plot_button = QPushButton("Plot")
        self.plot_button.setFixedSize(*WidgetSizes.spec_control())
        self.plot_button.setStyleSheet(btn_style)
        layout.addWidget(self.plot_button, 5, 0)
        
        self.next_button = QPushButton("Next")
        self.next_button.setFixedSize(*WidgetSizes.spec_control())
        self.next_button.setStyleSheet(btn_style)
        layout.addWidget(self.next_button, 5, 1)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setFixedSize(*WidgetSizes.spec_control())
        self.refresh_button.setStyleSheet(btn_style)
        layout.addWidget(self.refresh_button, 6, 0)
        
        self.close_all_button = QPushButton("Close All")
        self.close_all_button.setFixedSize(*WidgetSizes.spec_control())
        self.close_all_button.setStyleSheet(btn_style)
        layout.addWidget(self.close_all_button, 6, 1)
        
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        
        self.window_combo = self.Function
        self.overlap_combo = self.Overlap_Factor
        self.view_type_combo = self.select_pytpe
        self.plot_btn = self.plot_button
        self.next_btn = self.next_button
        
        return layout
    
    def _create_plot_area(self):
        dpi = QApplication.primaryScreen().logicalDotsPerInch()
        
        self.waveform_figure = Figure(figsize=(10, 4), dpi=dpi)
        self.waveform_figure.set_tight_layout({'rect': [0, 0, 0.88, 1]})
        self.wavecanvas = FigureCanvas(self.waveform_figure)
        self.wavecanvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.waveax = self.waveform_figure.add_subplot(111)
        self.waveax.set_title("Waveform", fontsize=PlotFontSizes.TITLE)
        self.wavecanvas.setFocusPolicy(Qt.StrongFocus)
        
        self.figure = Figure(figsize=(10, 4), dpi=dpi)
        self.figure.set_tight_layout({'rect': [0, 0, 0.88, 1]})
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Vibration Spectrum", fontsize=PlotFontSizes.TITLE)
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        
        self._connect_picking_events()
        
        wave_scale_widget = self._create_axis_controls('wave')
        spec_scale_widget = self._create_axis_controls('spec')
        
        wave_splitter = QSplitter(Qt.Horizontal)
        wave_splitter.addWidget(self.wavecanvas)
        wave_splitter.addWidget(wave_scale_widget)
        wave_splitter.setStretchFactor(0, 5)
        wave_splitter.setStretchFactor(1, 1)
        
        spec_splitter = QSplitter(Qt.Horizontal)
        spec_splitter.addWidget(self.canvas)
        spec_splitter.addWidget(spec_scale_widget)
        spec_splitter.setStretchFactor(0, 5)
        spec_splitter.setStretchFactor(1, 1)
        
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.addWidget(wave_splitter)
        self.main_splitter.addWidget(spec_splitter)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)
        
        self.waveform_plot = self.wavecanvas
        self.spectrum_plot = self.canvas
    
    def _create_axis_controls(self, plot_type: str) -> QWidget:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 20 if plot_type == 'wave' else 5, 0, 20 if plot_type == 'wave' else 10)
        layout.addStretch(2)
        
        if plot_type == 'spec':
            reset_layout = QHBoxLayout()
            reset_layout.addStretch()
            self.reset_zoom_button = QPushButton("Reset Zoom")
            self.reset_zoom_button.setMaximumSize(*WidgetSizes.axis_button())
            reset_layout.addWidget(self.reset_zoom_button)
            layout.addLayout(reset_layout)
        
        x_layout = QHBoxLayout()
        x_layout2 = QHBoxLayout()
        y_layout = QHBoxLayout()
        y_layout2 = QHBoxLayout()
        
        x_layout.addStretch()
        x_layout2.addStretch()
        y_layout.addStretch()
        y_layout2.addStretch()
        
        auto_x = QCheckBox("Auto X")
        auto_x.setChecked(True)
        x_layout.addWidget(auto_x)
        
        x_autoscale = QPushButton("Auto Scale")
        x_autoscale.setMaximumSize(*WidgetSizes.axis_button())
        x_layout.addWidget(x_autoscale)
        
        auto_y = QCheckBox("Auto Y")
        auto_y.setChecked(True)
        y_layout.addWidget(auto_y)
        
        y_autoscale = QPushButton("Auto Scale")
        y_autoscale.setMaximumSize(*WidgetSizes.axis_button())
        y_layout.addWidget(y_autoscale)
        
        x_min_input = QLineEdit()
        x_min_input.setPlaceholderText("X min")
        x_min_input.setMaximumSize(*WidgetSizes.axis_input())
        x_min_input.setStyleSheet("background-color: lightgray;color: black;")
        x_layout2.addWidget(x_min_input)
        
        x_max_input = QLineEdit()
        x_max_input.setPlaceholderText("X max")
        x_max_input.setMaximumSize(*WidgetSizes.axis_input())
        x_max_input.setStyleSheet("background-color: lightgray;color: black;")
        x_layout2.addWidget(x_max_input)
        
        x_set = QPushButton("Set")
        x_set.setMaximumSize(*WidgetSizes.axis_input())
        x_layout2.addWidget(x_set)
        
        y_min_input = QLineEdit()
        y_min_input.setPlaceholderText("Y min")
        y_min_input.setMaximumSize(*WidgetSizes.axis_input())
        y_min_input.setStyleSheet("background-color: lightgray;color: black;")
        y_layout2.addWidget(y_min_input)
        
        y_max_input = QLineEdit()
        y_max_input.setPlaceholderText("Y max")
        y_max_input.setMaximumSize(*WidgetSizes.axis_input())
        y_max_input.setStyleSheet("background-color: lightgray;color: black;")
        y_layout2.addWidget(y_max_input)
        
        y_set = QPushButton("Set")
        y_set.setMaximumSize(*WidgetSizes.axis_input())
        y_layout2.addWidget(y_set)
        
        layout.addLayout(x_layout)
        layout.addLayout(x_layout2)
        layout.addLayout(y_layout)
        layout.addLayout(y_layout2)
        
        if plot_type == 'spec':
            save_button = QPushButton("Data Extraction")
            layout.addWidget(save_button)
        
        layout.addStretch(2)
        
        if plot_type == 'wave':
            self.wave_auto_x = auto_x
            self.wave_auto_y = auto_y
            self.wave_x_min = x_min_input
            self.wave_x_max = x_max_input
            self.wave_x_set = x_set
            self.wave_y_min = y_min_input
            self.wave_y_max = y_max_input
            self.wave_y_set = y_set
            self.wave_x_autoscale = x_autoscale
            self.wave_y_autoscale = y_autoscale
        elif plot_type == 'spec':
            self.spec_auto_x = auto_x
            self.spec_auto_y = auto_y
            self.spec_x_min = x_min_input
            self.spec_x_max = x_max_input
            self.spec_x_set = x_set
            self.spec_y_min = y_min_input
            self.spec_y_max = y_max_input
            self.spec_y_set = y_set
            self.spec_x_autoscale = x_autoscale
            self.spec_y_autoscale = y_autoscale
        
        x_set.clicked.connect(lambda: self._on_axis_set_clicked(plot_type, 'x', x_min_input, x_max_input))
        y_set.clicked.connect(lambda: self._on_axis_set_clicked(plot_type, 'y', y_min_input, y_max_input))
        x_autoscale.clicked.connect(lambda: self._on_auto_scale_clicked(plot_type, 'x'))
        y_autoscale.clicked.connect(lambda: self._on_auto_scale_clicked(plot_type, 'y'))
        
        widget = QWidget()
        widget.setLayout(layout)
        return widget
    
    def _on_axis_set_clicked(self, plot_type: str, axis: str,
                              min_input: QLineEdit, max_input: QLineEdit):
        """Set 버튼 클릭 시 축 범위 변경 시그널 발생."""
        try:
            val_min = float(min_input.text())
            val_max = float(max_input.text())
            if val_min < val_max:
                self.axis_range_changed.emit(plot_type, axis, val_min, val_max)
        except ValueError:
            pass
    
    def _on_auto_scale_clicked(self, plot_type: str, axis: str):
        """Auto Scale 버튼 클릭 시 자동 범위 적용."""
        if plot_type == 'wave':
            ax = self.waveax
            canvas = self.wavecanvas
        else:
            ax = self.ax
            canvas = self.canvas
        
        if axis == 'x':
            ax.autoscale(enable=True, axis='x')
        else:
            ax.autoscale(enable=True, axis='y')
        canvas.draw_idle()
    
    def _on_canvas_click(self, event, plot_type: str):
        """캔버스 외곽 클릭 시 축 범위 입력 팝업 표시."""
        if event.inaxes is not None:
            return
        
        if plot_type == 'wave':
            ax = self.waveax
            fig = self.waveform_figure
            canvas = self.wavecanvas
        else:
            ax = self.ax
            fig = self.figure
            canvas = self.canvas
        
        bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
        click_x_inch = event.x / fig.dpi
        click_y_inch = event.y / fig.dpi
        
        if click_y_inch < bbox.y0:
            result = self._show_axis_range_dialog("X axis range")
            if result is not None:
                val_min, val_max = result
                if val_min < val_max:
                    ax.set_xlim(val_min, val_max)
                    canvas.draw_idle()
        elif click_x_inch < bbox.x0:
            result = self._show_axis_range_dialog("Y axis range")
            if result is not None:
                val_min, val_max = result
                if val_min < val_max:
                    ax.set_ylim(val_min, val_max)
                    canvas.draw_idle()
    
    def _show_axis_range_dialog(self, title: str):
        """축 범위 입력 다이얼로그 — Min/Max 개별 입력 필드."""
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        form = QFormLayout(dlg)
        
        min_input = QLineEdit()
        min_input.setPlaceholderText("Min")
        min_input.setStyleSheet("background-color: lightgray; color: black;")
        form.addRow("Min:", min_input)
        
        max_input = QLineEdit()
        max_input.setPlaceholderText("Max")
        max_input.setStyleSheet("background-color: lightgray; color: black;")
        form.addRow("Max:", max_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)
        
        if dlg.exec_() == QDialog.Accepted:
            try:
                return float(min_input.text()), float(max_input.text())
            except ValueError:
                return None
        return None
    
    def _on_date_filter_clicked(self):
        """날짜 필터 버튼 클릭 처리."""
        from_str = self.date_from.date().toString("yyyy-MM-dd")
        to_str = self.date_to.date().toString("yyyy-MM-dd")
        self.date_filter_changed.emit(from_str, to_str)
    
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
            self.checkBox, self.checkBox_2, self.checkBox_3,
            self.checkBox_4, self.checkBox_5, self.checkBox_6
        ]
        for idx, checkbox in enumerate(checkboxes, start=1):
            if checkbox.isChecked():
                selected_channels.append(str(idx))
        
        if not selected_channels:
            self.Querry_list.clear()
            self.Querry_list.addItems(self._all_files)
            return
        
        filtered_files = [
            f for f in self._all_files
            if any(f.endswith(f"_{ch}.txt") for ch in selected_channels)
        ]
        self.Querry_list.clear()
        self.Querry_list.addItems(filtered_files)
    
    def _on_span_selected(self, t_start: float, t_end: float):
        """SpanSelector 시간 범위 선택 처리."""
        if abs(t_end - t_start) > 0.001:
            self.time_range_selected.emit(t_start, t_end)
    
    def _save_original_limits(self, ax, key: str):
        self._original_limits[key] = (ax.get_xlim(), ax.get_ylim())
    
    def _reset_zoom(self):
        for key, (xlim, ylim) in self._original_limits.items():
            ax = self.ax if key == 'spec' else self.waveax
            canvas = self.canvas if key == 'spec' else self.wavecanvas
            ax.set_xlim(xlim)
            ax.set_ylim(ylim)
            canvas.draw_idle()
    
    def _on_scroll(self, event, ax, canvas):
        if event.inaxes != ax:
            return
        
        key = 'spec' if ax == self.ax else 'wave'
        if key not in self._original_limits:
            self._save_original_limits(ax, key)
        
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        modifiers = QApplication.keyboardModifiers()
        
        if modifiers & Qt.ControlModifier:
            shift = (xlim[1] - xlim[0]) * (0.1 if event.button == 'up' else -0.1)
            ax.set_xlim(xlim[0] + shift, xlim[1] + shift)
            canvas.draw_idle()
            return
        
        if modifiers & Qt.ShiftModifier:
            shift = (ylim[1] - ylim[0]) * (0.1 if event.button == 'up' else -0.1)
            ax.set_ylim(ylim[0] + shift, ylim[1] + shift)
            canvas.draw_idle()
            return
        
        scale_factor = 0.85 if event.button == 'up' else 1.15
        xdata, ydata = event.xdata, event.ydata
        
        ax.set_xlim(xdata - (xdata - xlim[0]) * scale_factor,
                     xdata + (xlim[1] - xdata) * scale_factor)
        ax.set_ylim(ydata - (ydata - ylim[0]) * scale_factor,
                     ydata + (ylim[1] - ydata) * scale_factor)
        canvas.draw_idle()
    
    def _connect_signals(self):
        self.plot_btn.clicked.connect(self.compute_requested)
        self.next_btn.clicked.connect(self.next_file_requested)
        self.select_pytpe.currentIndexChanged.connect(
            lambda: self.view_type_changed.emit(self.select_pytpe.currentData())
        )
        self.Function.currentTextChanged.connect(self.window_type_changed)
        self.select_all_btn.clicked.connect(self.Querry_list.selectAll)
        self.deselect_all_btn.clicked.connect(self.Querry_list.clearSelection)
        self.Querry_list.itemClicked.connect(lambda item: self.file_clicked.emit(item.text()))
        
        self.date_filter_btn.clicked.connect(self._on_date_filter_clicked)
        self.refresh_button.clicked.connect(self.refresh_requested)
        self.close_all_button.clicked.connect(self.close_all_windows_requested)
        self.reset_zoom_button.clicked.connect(self._reset_zoom)
        
        # 채널 체크박스 - 파일 목록 필터
        self.checkBox.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_2.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_3.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_4.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_5.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_6.stateChanged.connect(self._on_channel_filter_changed)
        
        self.wavecanvas.mpl_connect("button_press_event",
                                     lambda event: self._on_canvas_click(event, 'wave'))
        self.canvas.mpl_connect("button_press_event",
                                 lambda event: self._on_canvas_click(event, 'spec'))
        
        self.canvas.mpl_connect('scroll_event', lambda e: self._on_scroll(e, self.ax, self.canvas))
        self.wavecanvas.mpl_connect('scroll_event', lambda e: self._on_scroll(e, self.waveax, self.wavecanvas))
    
    def _connect_picking_events(self):
        self.cid_move = self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self.cid_click = self.canvas.mpl_connect("button_press_event", self._on_mouse_click)
        self.cid_key = self.canvas.mpl_connect("key_press_event", self._on_key_press)
        self.hover_dot = self.ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
    
    def _reconnect_picking_events(self):
        if hasattr(self, 'cid_move') and self.cid_move:
            self.canvas.mpl_disconnect(self.cid_move)
        if hasattr(self, 'cid_click') and self.cid_click:
            self.canvas.mpl_disconnect(self.cid_click)
        if hasattr(self, 'cid_key') and self.cid_key:
            self.canvas.mpl_disconnect(self.cid_key)
        self.cid_move = self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self.cid_click = self.canvas.mpl_connect("button_press_event", self._on_mouse_click)
        self.cid_key = self.canvas.mpl_connect("key_press_event", self._on_key_press)
        self.hover_dot = self.ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
        self.hover_pos = None
    
    def get_parameters(self) -> dict:
        return {
            'window_type': self.Function.currentText(),
            'overlap': float(self.Overlap_Factor.currentText().replace('%', '')),
            'view_type': self.select_pytpe.currentData()
        }
    
    _MAX_LEGEND_ITEMS = 15
    
    def plot_spectrum(self, frequencies: List[float], spectrum: List[float],
                      label: str = '', color_index: int = 0, clear: bool = True):
        if clear:
            self.ax.clear()
            self.ax.set_title("Vibration Spectrum", fontsize=PlotFontSizes.TITLE)
            self.data_dict.clear()
            self.markers.clear()
            self._reconnect_picking_events()
        
        color = PLOT_COLORS[color_index % len(PLOT_COLORS)]
        self.ax.plot(frequencies, spectrum, color=color, linewidth=0.5, label=label, alpha=0.8)
        
        if label:
            self.data_dict[label] = (frequencies, spectrum)
        
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel(VIEW_TYPE_LABELS.get(self._current_view_type, ''))
        self.ax.grid(True)
        self._update_legend(self.ax, self.figure, self.canvas)
    
    def plot_waveform(self, time: List[float], amplitude: List[float],
                      label: str = '', color_index: int = 0, clear: bool = True):
        if clear:
            self.waveax.clear()
            self.waveax.set_title("Waveform", fontsize=PlotFontSizes.TITLE)
        
        color = PLOT_COLORS[color_index % len(PLOT_COLORS)]
        self.waveax.plot(time, amplitude, color=color, linewidth=0.5, label=label, alpha=0.8)
        self.waveax.set_xlabel('Time (s)')
        self.waveax.set_ylabel(WAVEFORM_Y_LABELS.get(self._current_view_type, ''))
        self.waveax.grid(True)
        self._update_legend(self.waveax, self.waveform_figure, self.wavecanvas)
        
        if not self._batch_mode:
            self._span_selector = SpanSelector(
                self.waveax, self._on_span_selected, 'horizontal',
                useblit=True, props=dict(alpha=0.3, facecolor='yellow'),
                interactive=True, drag_from_anywhere=True
            )
    
    def begin_batch(self):
        self._batch_mode = True
    
    def end_batch(self):
        self._batch_mode = False
        self._update_legend(self.ax, self.figure, self.canvas)
        self._update_legend(self.waveax, self.waveform_figure, self.wavecanvas)
        self._save_original_limits(self.ax, 'spec')
        self._save_original_limits(self.waveax, 'wave')
        self._span_selector = SpanSelector(
            self.waveax, self._on_span_selected, 'horizontal',
            useblit=True, props=dict(alpha=0.3, facecolor='yellow'),
            interactive=True, drag_from_anywhere=True
        )
    
    def _update_legend(self, ax, figure, canvas):
        handles, labels = ax.get_legend_handles_labels()
        if not labels:
            if not self._batch_mode:
                canvas.draw_idle()
            return
        
        if len(labels) <= self._MAX_LEGEND_ITEMS:
            ax.legend(
                loc='upper left', bbox_to_anchor=(1.02, 1),
                fontsize=PlotFontSizes.LEGEND,
                frameon=True, fancybox=True, shadow=True
            )
            figure.set_tight_layout({'rect': [0, 0, 0.88, 1]})
        else:
            legend = ax.get_legend()
            if legend:
                legend.remove()
            figure.set_tight_layout({'rect': [0, 0, 0.98, 1]})
        if not self._batch_mode:
            canvas.draw_idle()
    
    def set_view_type(self, view_type: str):
        self._current_view_type = view_type
    
    def clear_plots(self):
        self.ax.clear()
        self.ax.set_title("Vibration Spectrum", fontsize=PlotFontSizes.TITLE)
        self.markers.clear()
        self.data_dict.clear()
        self._reconnect_picking_events()
        self.canvas.draw()
        self.waveax.clear()
        self.waveax.set_title("Waveform", fontsize=PlotFontSizes.TITLE)
        self.wavecanvas.draw()
    
    def show_warning(self, title: str, message: str):
        QMessageBox.warning(self, title, message)
    
    def set_files(self, files: List[str]):
        self._all_files = list(files)
        self.Querry_list.clear()
        self.Querry_list.addItems(files)
    
    def get_selected_files(self) -> List[str]:
        return [item.text() for item in self.Querry_list.selectedItems()]
    
    def set_file_metadata(self, metadata: dict):
        self.Sample_rate_view.setHtml(metadata.get('D.Sampling Freq.', ''))
        self.Duration_view.setHtml(metadata.get('Record Length', ''))
        self.Rest_time_view.setHtml(metadata.get('rest_time', ''))
        self.Channel_view.setHtml(metadata.get('channel', ''))
        self.IEPE_view.setHtml(metadata.get('iepe', ''))
        self.Sensitivity_view.setHtml(metadata.get('sensitivity', ''))
    
    def _on_mouse_move(self, event):
        if not self.mouse_tracking_enabled or not event.inaxes:
            if self.hover_pos is not None:
                self.hover_dot.set_data([], [])
                self.hover_pos = None
                self.canvas.draw_idle()
            return
        
        import numpy as np
        closest_x, closest_y, min_dist = None, None, np.inf
        
        for line in self.ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()
            if len(x_data) == 0 or len(y_data) == 0:
                continue
            
            for x, y in zip(x_data, y_data):
                dist = np.hypot(event.xdata - x, event.ydata - y)
                if dist < min_dist:
                    min_dist = dist
                    closest_x, closest_y = x, y
        
        if closest_x is not None:
            self.hover_dot.set_data([closest_x], [closest_y])
            self.hover_pos = [closest_x, closest_y]
            self.canvas.draw_idle()
    
    def _on_mouse_click(self, event):
        if not event.inaxes:
            return
        
        if event.button == 1:
            x, y = self.hover_dot.get_data()
            if x is not None and len(x) > 0 and y is not None and len(y) > 0:
                self._add_marker(float(x[0]), float(y[0]))
        elif event.button == 3:
            self.clear_markers()
    
    def _on_key_press(self, event):
        import numpy as np
        x, y = self.hover_dot.get_data()
        if x is None or len(x) == 0:
            return
        
        x, y = float(x[0]), float(y[0])
        
        all_x_data = []
        all_y_data = []
        for line in self.ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()
            if len(x_data) == 0 or len(y_data) == 0:
                continue
            all_x_data.extend(x_data)
            all_y_data.extend(y_data)
        
        if not all_x_data:
            return
        
        current_index = None
        min_dist = np.inf
        for idx, (x_val, y_val) in enumerate(zip(all_x_data, all_y_data)):
            dist = np.hypot(x - x_val, y - y_val)
            if dist < min_dist:
                min_dist = dist
                current_index = idx
        
        if current_index is None:
            return
        
        candidates = []
        if event.key == 'left':
            candidates = [(i, abs(all_x_data[i] - x)) for i in range(len(all_x_data)) if all_x_data[i] < x]
        elif event.key == 'right':
            candidates = [(i, abs(all_x_data[i] - x)) for i in range(len(all_x_data)) if all_x_data[i] > x]
        elif event.key == 'up':
            candidates = [(i, abs(all_y_data[i] - y)) for i in range(len(all_y_data)) 
                          if abs(all_x_data[i] - x) < 1e-6 and all_y_data[i] > y]
        elif event.key == 'down':
            candidates = [(i, abs(all_y_data[i] - y)) for i in range(len(all_y_data)) 
                          if abs(all_x_data[i] - x) < 1e-6 and all_y_data[i] < y]
        elif event.key == 'enter':
            self._add_marker(all_x_data[current_index], all_y_data[current_index])
            return
        
        if candidates:
            candidates.sort(key=lambda t: t[1])
            current_index = candidates[0][0]
        
        new_x = all_x_data[current_index]
        new_y = all_y_data[current_index]
        self.hover_pos = [new_x, new_y]
        self.hover_dot.set_data([new_x], [new_y])
        self.canvas.draw_idle()
    
    def _add_marker(self, x: float, y: float):
        marker, = self.ax.plot([x], [y], 'ro', markersize=8, zorder=10)
        label = self.ax.text(x, y, f'  ({x:.2f}, {y:.2e})', 
                            fontsize=PlotFontSizes.MARKER_LABEL, color='red', 
                            verticalalignment='bottom')
        self.markers.append((marker, label))
        self.canvas.draw_idle()
    
    def clear_markers(self):
        for marker, label in self.markers:
            marker.remove()
            label.remove()
        self.markers.clear()
        self.canvas.draw_idle()
