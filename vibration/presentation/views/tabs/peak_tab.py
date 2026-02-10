"""
밴드 피크 트렌드 탭 뷰 - 레거시 tab_5의 정확한 복제.

cn_3F_trend_optimized.py 1810-2100 라인과 동일한 픽셀 완벽 UI 호환.
"""
from typing import List, Optional
import re
import numpy as np
from datetime import datetime
import matplotlib.dates as mdates

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QGridLayout, QVBoxLayout, QComboBox, QPushButton,
    QListWidget, QAbstractItemView, QCheckBox, QTextBrowser,
    QTextEdit, QLineEdit, QSizePolicy, QApplication
)
from PyQt5.QtCore import pyqtSignal, Qt, QEvent

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from vibration.presentation.views.dialogs.responsive_layout_utils import WidgetSizes, PlotFontSizes


VIEW_TYPE_LABELS = {
    'ACC': 'Peak Acceleration\n(m/s², RMS)',
    'VEL': 'Peak Velocity\n(mm/s, RMS)',
    'DIS': 'Peak Displacement\n(μm, RMS)'
}

CHANNEL_COLORS = ['r', 'g', 'b', 'c', 'm', 'y']


class PeakTabView(QWidget):
    """
    밴드 피크 트렌드 탭 뷰 - 레거시 정확 복제.
    
    레거시 tab_5 레이아웃 구조:
    - 좌측: 체크박스 (1CH-6CH), Select All/Deselect All 버튼, 파일 목록
    - 우측 상단: FFT 옵션 (Δf, Window, Overlap, Convert, BandLimit), Plot/Save 버튼
    - 하단: 피크 트렌드 그래프
    """
    
    compute_requested = pyqtSignal()
    save_requested = pyqtSignal()
    list_save_requested = pyqtSignal(dict, str)
    view_type_changed = pyqtSignal(int)
    channel_filter_changed = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_view_type = 'ACC'
        self.hover_dot = None
        self.hover_pos = None
        self.peak_marker = None
        self.peak_annotation = None
        self.peak_x_value = []
        self.peak_values = []
        self.peak_file_names = []
        self._all_files: List[str] = []
        self._original_limits: dict = {}
        self._setup_ui()
        self._connect_signals()
        self._init_mouse_events()
    
    def _setup_ui(self):
        self.tab5_layout = QGridLayout(self)
        
        self._create_left_panel()
        self._create_top_right_controls()
        self._create_plot_area()
        
        # Create horizontal section: graph + Pick Data List
        peak_controls_layout = QVBoxLayout()
        peak_controls_layout.addStretch(2)
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()
        self.reset_zoom_button = QPushButton("Reset Zoom")
        self.reset_zoom_button.setMaximumSize(*WidgetSizes.axis_button())
        reset_layout.addWidget(self.reset_zoom_button)
        peak_controls_layout.addLayout(reset_layout)
        peak_controls_layout.addStretch(2)
        peak_controls_widget = QWidget()
        peak_controls_widget.setLayout(peak_controls_layout)
        
        peak_section_layout = QHBoxLayout()
        peak_section_layout.addLayout(self.peak_graph_layout, 3)
        peak_section_layout.addWidget(peak_controls_widget, 0)
        data_list_layout = self._create_data_list_panel()
        peak_section_layout.addLayout(data_list_layout, 1)
        
        self.tab5_layout.addLayout(self.data2_layout, 0, 0, 2, 1)
        self.tab5_layout.addLayout(self.alloption2_layout, 0, 1, 1, 1, Qt.AlignLeft)
        self.tab5_layout.addLayout(peak_section_layout, 1, 1, 1, 8, Qt.AlignLeft)
        
        self.tab5_layout.setColumnStretch(1, 4)
    
    def _create_left_panel(self):
        self.data2_layout = QVBoxLayout()
        
        checksBox3 = QGridLayout()
        self.checkBox_19 = QCheckBox("1CH")
        checksBox3.addWidget(self.checkBox_19, 0, 0)
        self.checkBox_20 = QCheckBox("2CH")
        checksBox3.addWidget(self.checkBox_20, 0, 1)
        self.checkBox_21 = QCheckBox("3CH")
        checksBox3.addWidget(self.checkBox_21, 0, 2)
        self.checkBox_22 = QCheckBox("4CH")
        checksBox3.addWidget(self.checkBox_22, 1, 0)
        self.checkBox_23 = QCheckBox("5CH")
        checksBox3.addWidget(self.checkBox_23, 1, 1)
        self.checkBox_24 = QCheckBox("6CH")
        checksBox3.addWidget(self.checkBox_24, 1, 2)
        
        buttonall2_layout = QHBoxLayout()
        self.select_all_btn4 = QPushButton("Select All")
        buttonall2_layout.addWidget(self.select_all_btn4)
        self.deselect_all_btn4 = QPushButton("Deselect All")
        buttonall2_layout.addWidget(self.deselect_all_btn4)
        
        self.Querry_list4 = QListWidget()
        self.Querry_list4.setMinimumWidth(WidgetSizes.file_list_width())
        self.Querry_list4.setMaximumWidth(WidgetSizes.file_list_width())
        self.Querry_list4.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        self.data2_layout.addLayout(checksBox3)
        self.data2_layout.addLayout(buttonall2_layout)
        self.data2_layout.addWidget(self.Querry_list4)
        
        self.file_list = self.Querry_list4
    
    def _create_top_right_controls(self):
        self.alloption2_layout = QGridLayout()
        self.alloption2_layout.setSpacing(0)
        self.alloption2_layout.setContentsMargins(0, 0, 0, 0)
        
        self.Plot_Options_4 = QTextBrowser()
        self.Plot_Options_4.setMaximumSize(*WidgetSizes.option_control())
        self.Plot_Options_4.setHtml("FFT Options")
        self.alloption2_layout.addWidget(self.Plot_Options_4, 0, 0)
        
        option2_layout = self._create_fft_options()
        self.alloption2_layout.addLayout(option2_layout, 1, 0)
    
    def _create_fft_options(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.textBrowser_33 = QTextBrowser()
        self.textBrowser_33.setMaximumSize(*WidgetSizes.option_control())
        self.textBrowser_33.setHtml("Δf:")
        layout.addWidget(self.textBrowser_33, 0, 0)
        
        self.Hz_4 = QTextEdit()
        self.Hz_4.setPlaceholderText("Hz")
        self.Hz_4.setStyleSheet("background-color: lightgray;color: black;")
        self.Hz_4.setMaximumSize(*WidgetSizes.option_control())
        layout.addWidget(self.Hz_4, 0, 1)
        
        self.textBrowser_34 = QTextBrowser()
        self.textBrowser_34.setMaximumSize(*WidgetSizes.option_control())
        self.textBrowser_34.setHtml("Windown Function:")
        layout.addWidget(self.textBrowser_34, 1, 0)
        
        self.Function_4 = QComboBox()
        self.Function_4.setStyleSheet("background-color: lightgray;color: black;")
        self.Function_4.addItem("Rectangular")
        self.Function_4.addItem("Hanning")
        self.Function_4.addItem("Flattop")
        self.Function_4.setMaximumSize(*WidgetSizes.option_control())
        layout.addWidget(self.Function_4, 1, 1)
        
        self.textBrowser_35 = QTextBrowser()
        self.textBrowser_35.setMaximumSize(*WidgetSizes.option_control())
        self.textBrowser_35.setHtml("Overlap Factor:")
        layout.addWidget(self.textBrowser_35, 2, 0)
        
        self.Overlap_Factor_4 = QComboBox()
        self.Overlap_Factor_4.setStyleSheet("background-color: lightgray;color: black;")
        self.Overlap_Factor_4.addItem("0%")
        self.Overlap_Factor_4.addItem("25%")
        self.Overlap_Factor_4.addItem("50%")
        self.Overlap_Factor_4.addItem("75%")
        self.Overlap_Factor_4.setMaximumSize(*WidgetSizes.option_control())
        layout.addWidget(self.Overlap_Factor_4, 2, 1)
        
        self.plot_button2 = QPushButton("Plot")
        self.plot_button2.setMaximumSize(*WidgetSizes.option_control())
        self.plot_button2.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.plot_button2, 2, 2)
        
        self.select_type_convert4 = QTextBrowser()
        self.select_type_convert4.setMaximumSize(*WidgetSizes.option_control())
        self.select_type_convert4.setHtml("Convert")
        layout.addWidget(self.select_type_convert4, 3, 0)
        
        self.select_pytpe4 = QComboBox()
        self.select_pytpe4.setStyleSheet("background-color: lightgray;color: black;")
        self.select_pytpe4.addItem("ACC", 1)
        self.select_pytpe4.addItem("VEL", 2)
        self.select_pytpe4.addItem("DIS", 3)
        self.select_pytpe4.setMaximumSize(*WidgetSizes.option_control())
        layout.addWidget(self.select_pytpe4, 3, 1)
        
        self.save2_button = QPushButton("Save")
        self.save2_button.setMaximumSize(*WidgetSizes.option_control())
        self.save2_button.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.save2_button, 3, 2)
        
        self.freq_range_label2 = QTextBrowser()
        self.freq_range_label2.setMaximumSize(*WidgetSizes.option_control())
        self.freq_range_label2.setHtml("Band Limit (Hz):")
        layout.addWidget(self.freq_range_label2, 4, 0)
        
        self.freq_range_inputmin2 = QLineEdit("")
        self.freq_range_inputmin2.setMaximumSize(*WidgetSizes.option_control())
        self.freq_range_inputmin2.setPlaceholderText("MIN")
        self.freq_range_inputmin2.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.freq_range_inputmin2, 4, 1)
        
        self.freq_range_inputmax2 = QLineEdit("")
        self.freq_range_inputmax2.setMaximumSize(*WidgetSizes.option_control())
        self.freq_range_inputmax2.setPlaceholderText("MAX")
        self.freq_range_inputmax2.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.freq_range_inputmax2, 4, 2)
        
        self.window_combo = self.Function_4
        self.overlap_combo = self.Overlap_Factor_4
        self.view_type_combo = self.select_pytpe4
        self.delta_f_input = self.Hz_4
        
        return layout
    
    def _create_plot_area(self):
        self.peak_graph_layout = QVBoxLayout()
        
        dpi = QApplication.primaryScreen().logicalDotsPerInch()
        self.peak_figure = Figure(figsize=(10, 4), dpi=dpi)
        self.peak_figure.set_tight_layout({'rect': [0, 0, 0.88, 1]})
        self.peak_canvas = FigureCanvas(self.peak_figure)
        self.peak_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.peak_ax = self.peak_figure.add_subplot(111)
        self.peak_ax.set_title("Band Peak Trend", fontsize=PlotFontSizes.TITLE)
        self.peak_canvas.setFocusPolicy(Qt.ClickFocus)
        
        self.peak_graph_layout.addWidget(self.peak_canvas)
        
        self.plot_widget = self.peak_canvas
    
    def _create_data_list_panel(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        
        self.data_list_label = QTextBrowser()
        self.data_list_label.setMaximumSize(*WidgetSizes.data_list_label())
        self.data_list_label.setHtml("Pick Data List")
        
        self.data_list_text = QTextEdit()
        self.data_list_text.setMaximumSize(*WidgetSizes.data_list_text())
        self.data_list_text.setReadOnly(True)
        initial_text = "\n".join(["Ch1", "-", "Ch2", "-", "Ch3", "-", "Ch4", "-", "Ch5", "-", "Ch6", "-"])
        self.data_list_text.setText(initial_text)
        
        self.data_list_save_btn = QPushButton("List Save")
        self.data_list_save_btn.setMaximumSize(*WidgetSizes.data_list_label())
        
        layout.addWidget(self.data_list_label, 1)
        layout.addWidget(self.data_list_text, 2)
        layout.addWidget(self.data_list_save_btn, 1)
        
        return layout
    
    def _connect_signals(self):
        self.plot_button2.clicked.connect(self.compute_requested)
        self.save2_button.clicked.connect(self.save_requested)
        self.data_list_save_btn.clicked.connect(self._on_list_save_clicked)
        self.reset_zoom_button.clicked.connect(self._reset_zoom)
        self.select_pytpe4.currentIndexChanged.connect(
            lambda: self.view_type_changed.emit(self.select_pytpe4.currentData())
        )
        self.select_all_btn4.clicked.connect(self.Querry_list4.selectAll)
        self.deselect_all_btn4.clicked.connect(self.Querry_list4.clearSelection)
        
        # 채널 체크박스 - 파일 목록 필터
        self.checkBox_19.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_20.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_21.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_22.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_23.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_24.stateChanged.connect(self._on_channel_filter_changed)
    
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
            self.checkBox_19, self.checkBox_20, self.checkBox_21,
            self.checkBox_22, self.checkBox_23, self.checkBox_24
        ]
        for idx, checkbox in enumerate(checkboxes, start=1):
            if checkbox.isChecked():
                selected_channels.append(str(idx))
        
        if not selected_channels:
            self.Querry_list4.clear()
            self.Querry_list4.addItems(self._all_files)
            return
        
        filtered_files = [
            f for f in self._all_files
            if any(f.endswith(f"_{ch}.txt") for ch in selected_channels)
        ]
        self.Querry_list4.clear()
        self.Querry_list4.addItems(filtered_files)
    
    def _init_mouse_events(self):
        self.peak_canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.peak_canvas.mpl_connect('button_press_event', self._on_mouse_click)
        self.peak_canvas.mpl_connect('key_press_event', self._on_key_press)
        self.peak_canvas.mpl_connect('scroll_event', self._on_scroll)
    
    def _save_original_limits(self):
        self._original_limits['peak'] = (self.peak_ax.get_xlim(), self.peak_ax.get_ylim())
    
    def _reset_zoom(self):
        if 'peak' in self._original_limits:
            xlim, ylim = self._original_limits['peak']
            self.peak_ax.set_xlim(xlim)
            self.peak_ax.set_ylim(ylim)
            self.peak_canvas.draw_idle()
    
    def _on_scroll(self, event):
        if event.inaxes != self.peak_ax:
            return
        
        if 'peak' not in self._original_limits:
            self._save_original_limits()
        
        xlim = self.peak_ax.get_xlim()
        ylim = self.peak_ax.get_ylim()
        
        modifiers = QApplication.keyboardModifiers()
        
        if modifiers & Qt.ControlModifier:
            shift = (xlim[1] - xlim[0]) * (0.1 if event.button == 'up' else -0.1)
            self.peak_ax.set_xlim(xlim[0] + shift, xlim[1] + shift)
            self.peak_canvas.draw_idle()
            return
        
        if modifiers & Qt.ShiftModifier:
            shift = (ylim[1] - ylim[0]) * (0.1 if event.button == 'up' else -0.1)
            self.peak_ax.set_ylim(ylim[0] + shift, ylim[1] + shift)
            self.peak_canvas.draw_idle()
            return
        
        scale_factor = 0.85 if event.button == 'up' else 1.15
        xdata, ydata = event.xdata, event.ydata
        
        self.peak_ax.set_xlim(xdata - (xdata - xlim[0]) * scale_factor,
                              xdata + (xlim[1] - xdata) * scale_factor)
        self.peak_ax.set_ylim(ydata - (ydata - ylim[0]) * scale_factor,
                              ydata + (ylim[1] - ydata) * scale_factor)
        self.peak_canvas.draw_idle()
    
    def get_parameters(self) -> dict:
        try:
            delta_f = float(self.Hz_4.toPlainText().strip())
        except (ValueError, AttributeError):
            delta_f = 1.0
        
        try:
            band_min = float(self.freq_range_inputmin2.text().strip())
        except (ValueError, AttributeError):
            band_min = 0.0
        
        try:
            band_max = float(self.freq_range_inputmax2.text().strip())
        except (ValueError, AttributeError):
            band_max = 10000.0
        
        return {
            'delta_f': delta_f,
            'window_type': self.Function_4.currentText(),
            'overlap': float(self.Overlap_Factor_4.currentText().replace('%', '')),
            'view_type': self.select_pytpe4.currentData(),
            'band_min': band_min,
            'band_max': band_max
        }
    
    def plot_peak_trend(self, channel_data: dict, clear: bool = True):
        if clear:
            self.peak_ax.clear()
            self.peak_ax.set_title("Band Peak Trend", fontsize=PlotFontSizes.TITLE)
        
        for idx, (ch, data) in enumerate(sorted(channel_data.items())):
            color = CHANNEL_COLORS[idx % len(CHANNEL_COLORS)]
            self.peak_ax.plot(data['x'], data['y'], 
                             label=f"Channel {ch}", color=color,
                             marker='o', markersize=2, linewidth=0.5)
        
        self.peak_ax.set_xlabel('Date & Time', fontsize=PlotFontSizes.LABEL)
        self.peak_ax.set_ylabel(VIEW_TYPE_LABELS.get(self._current_view_type, ''), fontsize=PlotFontSizes.LABEL)
        self.peak_ax.set_facecolor('white')
        self.peak_ax.grid(True, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
        self.peak_ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), 
                           fontsize=PlotFontSizes.LEGEND, frameon=True, fancybox=True, shadow=True)
        self.peak_canvas.draw_idle()
        self._save_original_limits()
    
    def set_view_type(self, view_type: str):
        self._current_view_type = view_type
    
    def clear_plot(self):
        self.peak_ax.clear()
        self.peak_ax.set_title("Band Peak Trend", fontsize=PlotFontSizes.TITLE)
        self.peak_canvas.draw()
    
    def set_files(self, files: List[str]):
        self._all_files = list(files)
        self.Querry_list4.clear()
        self.Querry_list4.addItems(files)
    
    def get_selected_files(self) -> List[str]:
        return [item.text() for item in self.Querry_list4.selectedItems()]
    
    def _on_mouse_move(self, event):
        if not event.inaxes:
            if self.hover_pos is not None:
                if self.hover_dot:
                    self.hover_dot.set_data([], [])
                self.hover_pos = None
                self.peak_canvas.draw_idle()
            return
        
        closest_x, closest_y, min_dist = None, None, np.inf
        
        for line in self.peak_ax.get_lines():
            x_data, y_data = line.get_xdata(), line.get_ydata()
            
            if len(x_data) == 0 or len(y_data) == 0:
                continue
            
            if isinstance(x_data[0], datetime):
                x_data = mdates.date2num(x_data)
            
            for x, y in zip(x_data, y_data):
                dist = np.hypot(event.xdata - x, event.ydata - y)
                if dist < min_dist:
                    min_dist = dist
                    closest_x, closest_y = x, y
        
        if closest_x is not None:
            if self.hover_dot is None:
                self.hover_dot = self.peak_ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
            self.hover_dot.set_data([closest_x], [closest_y])
            self.hover_pos = [closest_x, closest_y]
            self.peak_canvas.draw_idle()
    
    def _on_mouse_click(self, event):
        if not event.inaxes:
            return
        
        if event.button == 1:
            x, y = self.hover_dot.get_data() if self.hover_dot else (None, None)
            if x is not None and len(x) > 0:
                self._add_marker(x[0], y[0])
        elif event.button == 3:
            self._clear_markers()
    
    def _on_key_press(self, event):
        if event.key == 'escape':
            self._clear_markers()
        elif event.key == 'enter' and self.hover_pos:
            self._add_marker(self.hover_pos[0], self.hover_pos[1])
    
    def _add_marker(self, x, y):
        if not self.peak_x_value or not self.peak_values:
            return
        
        min_distance = float('inf')
        closest_index = -1
        
        for i, (data_x, data_y) in enumerate(zip(self.peak_x_value, self.peak_values)):
            if isinstance(data_x, datetime):
                data_x_float = mdates.date2num(data_x)
            else:
                data_x_float = data_x
            
            if isinstance(x, datetime):
                x_float = mdates.date2num(x)
            else:
                x_float = x
            
            dx = abs(x_float - data_x_float)
            dy = abs(float(y) - data_y)
            dist = np.hypot(dx, dy) if dx != 0 else dy
            
            if dist < min_distance:
                min_distance = dist
                closest_index = i
        
        if closest_index == -1:
            return
        
        if self.peak_marker:
            try:
                self.peak_marker.remove()
            except:
                pass
        
        if self.peak_annotation:
            try:
                self.peak_annotation.remove()
            except:
                pass
        
        file_name = self.peak_file_names[closest_index]
        x_val = self.peak_x_value[closest_index]
        y_val = self.peak_values[closest_index]
        
        self.peak_marker = self.peak_ax.plot(
            x_val, y_val,
            marker='o', color='red', markersize=7
        )[0]
        
        annotation_text = f"{file_name}\nX: {x_val}\nY: {y_val:.4f}"
        
        self.peak_annotation = self.peak_ax.annotate(
            annotation_text,
            (x_val, y_val),
            textcoords="offset points",
            xytext=(10, 10),
            ha='left',
            fontsize=PlotFontSizes.ANNOTATION,
            bbox=dict(boxstyle="round,pad=0.3", edgecolor="black",
                     facecolor="lightyellow", alpha=0.8)
        )
        
        self.peak_canvas.draw_idle()
        self._add_filename_to_list(file_name)
    
    def _clear_markers(self):
        if self.peak_marker:
            try:
                self.peak_marker.remove()
                self.peak_marker = None
            except:
                pass
        
        if self.peak_annotation:
            try:
                self.peak_annotation.remove()
                self.peak_annotation = None
            except:
                pass
        
        self.peak_canvas.draw_idle()
    
    def _add_filename_to_list(self, filename: str):
        print(f"✅ Pick Data List: Adding '{filename}'")
        
        match = re.search(r"_([1-6])\.txt$", filename)
        if not match:
            print(f"⚠️ Pick Data List: Filename pattern not matched: {filename}")
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
            print(f"⚠️ Pick Data List: Channel header '{ch_header}' not found")
            return
        
        i = insert_idx + 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("Ch"):
            if lines[i].strip() == filename.strip():
                print(f"ℹ️ Pick Data List: '{filename}' already exists in Ch{ch_num}")
                return
            i += 1
        
        lines.insert(i, filename)
        self.data_list_text.setText("\n".join(lines))
        print(f"✅ Pick Data List: '{filename}' added to Ch{ch_num}")
    
    def set_peak_data(self, x_values: List, peak_values: List, file_names: List):
        print(f"✅ Set peak data: {len(file_names)} files")
        self.peak_x_value = x_values
        self.peak_values = peak_values
        self.peak_file_names = file_names
    
    def set_directory_path(self, directory_path: str):
        self._directory_path = directory_path
    
    def _on_list_save_clicked(self):
        try:
            text_lines = self.data_list_text.toPlainText().split("\n")
            channel_files = {f"Ch{i}": [] for i in range(1, 7)}
            
            for line in text_lines:
                line = line.strip()
                if not line or line.startswith("Ch") or line == "-":
                    continue
                
                try:
                    channel_num = int(line.split("_")[-1].split(".")[0])
                    if 1 <= channel_num <= 6:
                        channel_key = f"Ch{channel_num}"
                        channel_files[channel_key].append(line)
                except Exception as e:
                    print(f"파일 파싱 오류: {line}, 에러: {e}")
            
            directory_path = getattr(self, '_directory_path', '')
            self.list_save_requested.emit(channel_files, directory_path)
            
        except Exception as e:
            print(f"❌ List Save 오류: {e}")
            import traceback
            traceback.print_exc()
