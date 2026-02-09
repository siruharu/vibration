"""
전체 RMS 트렌드 탭 뷰 - 레거시 tab_4의 정확한 복제.

cn_3F_trend_optimized.py 1585-1810 라인과 동일한 픽셀 완벽 UI 호환.
"""
from typing import List, Optional
import re
import numpy as np
from datetime import datetime
import matplotlib.dates as mdates

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QGridLayout, QVBoxLayout, QComboBox, QPushButton,
    QLabel, QListWidget, QAbstractItemView, QCheckBox, QTextBrowser,
    QTextEdit, QLineEdit, QSizePolicy, QApplication
)
from PyQt5.QtCore import pyqtSignal, Qt

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from vibration.presentation.views.dialogs.responsive_layout_utils import WidgetSizes, PlotFontSizes


VIEW_TYPE_LABELS = {
    'ACC': 'Vibration Acceleration\n(m/s², RMS)',
    'VEL': 'Vibration Velocity\n(mm/s, RMS)',
    'DIS': 'Vibration Displacement\n(μm, RMS)'
}

CHANNEL_COLORS = ['r', 'g', 'b', 'c', 'm', 'y']


class TrendTabView(QWidget):
    """
    전체 RMS 트렌드 탭 뷰 - 레거시 정확 복제.
    
    레거시 tab_4 레이아웃 구조:
    - 좌측: 체크박스, 파일 목록
    - 우측 상단: FFT 옵션, 버튼 (Calculation & Plot, Load Data & Plot, Data Extraction)
    - 하단: 트렌드 그래프 + Pick Data List 패널
    """
    
    compute_requested = pyqtSignal()
    load_data_requested = pyqtSignal()
    save_requested = pyqtSignal()
    list_save_requested = pyqtSignal(dict, str)
    view_type_changed = pyqtSignal(int)
    channel_filter_changed = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_view_type = 'ACC'
        self.hover_dot = None
        self.hover_pos = None
        self.trend_marker = None
        self.trend_annotation = None
        self.trend_x_value = []
        self.trend_rms_values = []
        self.trend_file_names = []
        self._all_files: List[str] = []
        self._setup_ui()
        self._connect_signals()
        self._init_mouse_events()
    
    def _setup_ui(self):
        self.tab4_layout = QGridLayout(self)
        
        self._create_left_panel()
        self._create_top_right_controls()
        self._create_plot_area()
        
        self.tab4_layout.addLayout(self.data_layout, 0, 0, 2, 1, Qt.AlignTop)
        self.tab4_layout.addLayout(self.alloption_layout, 0, 1, Qt.AlignLeft)
        self.tab4_layout.addLayout(self.trend_section_layout, 1, 1, 1, 8, Qt.AlignLeft)
        
        self.tab4_layout.setColumnStretch(1, 4)
    
    def _create_left_panel(self):
        self.data_layout = QGridLayout()
        
        checksBox2 = QGridLayout()
        self.checkBox_13 = QCheckBox("1CH")
        checksBox2.addWidget(self.checkBox_13, 0, 0)
        self.checkBox_14 = QCheckBox("2CH")
        checksBox2.addWidget(self.checkBox_14, 0, 1)
        self.checkBox_15 = QCheckBox("3CH")
        checksBox2.addWidget(self.checkBox_15, 0, 2)
        self.checkBox_16 = QCheckBox("4CH")
        checksBox2.addWidget(self.checkBox_16, 1, 0)
        self.checkBox_17 = QCheckBox("5CH")
        checksBox2.addWidget(self.checkBox_17, 1, 1)
        self.checkBox_18 = QCheckBox("6CH")
        checksBox2.addWidget(self.checkBox_18, 1, 2)
        
        buttonall_layout = QHBoxLayout()
        self.select_all_btn3 = QPushButton("Select All")
        buttonall_layout.addWidget(self.select_all_btn3)
        self.deselect_all_btn3 = QPushButton("Deselect All")
        buttonall_layout.addWidget(self.deselect_all_btn3)
        
        self.Querry_list3 = QListWidget()
        self.Querry_list3.setMinimumWidth(WidgetSizes.file_list_width())
        self.Querry_list3.setMaximumWidth(WidgetSizes.file_list_width())
        self.Querry_list3.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        self.data_layout.addLayout(checksBox2, 0, 0)
        self.data_layout.addLayout(buttonall_layout, 1, 0)
        self.data_layout.addWidget(self.Querry_list3, 2, 0)
        
        self.file_list = self.Querry_list3
    
    def _create_top_right_controls(self):
        self.alloption_layout = QGridLayout()
        self.alloption_layout.setSpacing(0)
        self.alloption_layout.setContentsMargins(0, 0, 0, 0)
        
        self.Plot_Options_3 = QTextBrowser()
        self.Plot_Options_3.setMaximumSize(*WidgetSizes.option_control())
        self.Plot_Options_3.setHtml("FFT Options")
        self.alloption_layout.addWidget(self.Plot_Options_3, 0, 0)
        
        option1_layout = self._create_fft_options()
        self.alloption_layout.addLayout(option1_layout, 1, 0)
        self.alloption_layout.setRowStretch(0, 0)
    
    def _create_fft_options(self) -> QGridLayout:
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.textBrowser_30 = QTextBrowser()
        self.textBrowser_30.setMaximumSize(*WidgetSizes.option_control())
        self.textBrowser_30.setHtml("Δf:")
        layout.addWidget(self.textBrowser_30, 0, 0)
        
        self.Hz_3 = QTextEdit()
        self.Hz_3.setPlaceholderText("Hz")
        self.Hz_3.setStyleSheet("background-color: lightgray;color: black;")
        self.Hz_3.setMaximumSize(*WidgetSizes.option_control())
        layout.addWidget(self.Hz_3, 0, 1)
        
        self.textBrowser_31 = QTextBrowser()
        self.textBrowser_31.setMaximumSize(*WidgetSizes.option_control())
        self.textBrowser_31.setHtml("Windown Function:")
        layout.addWidget(self.textBrowser_31, 1, 0)
        
        self.Function_3 = QComboBox()
        self.Function_3.setStyleSheet("background-color: lightgray;color: black;")
        self.Function_3.addItem("Rectangular")
        self.Function_3.addItem("Hanning")
        self.Function_3.addItem("Flattop")
        self.Function_3.setMaximumSize(*WidgetSizes.option_control())
        layout.addWidget(self.Function_3, 1, 1)
        
        self.plot_button = QPushButton("Calculation && Plot")
        self.plot_button.setMaximumSize(*WidgetSizes.option_control())
        self.plot_button.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.plot_button, 1, 2)
        
        self.textBrowser_32 = QTextBrowser()
        self.textBrowser_32.setMaximumSize(*WidgetSizes.option_control())
        self.textBrowser_32.setHtml("Overlap Factor:")
        layout.addWidget(self.textBrowser_32, 2, 0)
        
        self.Overlap_Factor_3 = QComboBox()
        self.Overlap_Factor_3.setStyleSheet("background-color: lightgray;color: black;")
        self.Overlap_Factor_3.addItem("0%")
        self.Overlap_Factor_3.addItem("25%")
        self.Overlap_Factor_3.addItem("50%")
        self.Overlap_Factor_3.addItem("75%")
        self.Overlap_Factor_3.setMaximumSize(*WidgetSizes.option_control())
        layout.addWidget(self.Overlap_Factor_3, 2, 1)
        
        self.call_button = QPushButton("Load Data && Plot")
        self.call_button.setMaximumSize(*WidgetSizes.option_control())
        self.call_button.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.call_button, 2, 2)
        
        self.select_type_convert3 = QTextBrowser()
        self.select_type_convert3.setMaximumSize(*WidgetSizes.option_control())
        self.select_type_convert3.setHtml("Convert")
        layout.addWidget(self.select_type_convert3, 3, 0)
        
        self.select_pytpe3 = QComboBox()
        self.select_pytpe3.setStyleSheet("background-color: lightgray;color: black;")
        self.select_pytpe3.addItem("ACC", 1)
        self.select_pytpe3.addItem("VEL", 2)
        self.select_pytpe3.addItem("DIS", 3)
        self.select_pytpe3.setMaximumSize(*WidgetSizes.option_control())
        layout.addWidget(self.select_pytpe3, 3, 1)
        
        self.save_button = QPushButton("Data Extraction")
        self.save_button.setMaximumSize(*WidgetSizes.option_control())
        self.save_button.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.save_button, 3, 2)
        
        self.freq_range_label = QTextBrowser()
        self.freq_range_label.setMaximumSize(*WidgetSizes.option_control())
        self.freq_range_label.setHtml("BandLimit")
        layout.addWidget(self.freq_range_label, 4, 0)
        
        self.freq_range_inputmin = QLineEdit("")
        self.freq_range_inputmin.setMaximumSize(*WidgetSizes.option_control())
        self.freq_range_inputmin.setPlaceholderText("MIN")
        self.freq_range_inputmin.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.freq_range_inputmin, 4, 1)
        
        self.freq_range_inputmax = QLineEdit("")
        self.freq_range_inputmax.setMaximumSize(*WidgetSizes.option_control())
        self.freq_range_inputmax.setPlaceholderText("MAX")
        self.freq_range_inputmax.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.freq_range_inputmax, 4, 2)
        
        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        
        self.window_combo = self.Function_3
        self.overlap_combo = self.Overlap_Factor_3
        self.view_type_combo = self.select_pytpe3
        self.delta_f_input = self.Hz_3
        
        return layout
    
    def _create_plot_area(self):
        self.trend_section_layout = QHBoxLayout()
        
        trend_graph_layout = QVBoxLayout()
        
        dpi = QApplication.primaryScreen().logicalDotsPerInch()
        self.trend_figure = Figure(figsize=(10, 4), dpi=dpi)
        self.trend_figure.set_tight_layout({'rect': [0, 0, 0.88, 1]})
        self.trend_canvas = FigureCanvas(self.trend_figure)
        self.trend_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.trend_ax = self.trend_figure.add_subplot(111)
        self.trend_ax.set_title("Overall RMS Trend", fontsize=PlotFontSizes.TITLE)
        self.trend_canvas.setFocusPolicy(Qt.ClickFocus)
        
        trend_graph_layout.addWidget(self.trend_canvas)
        
        data_list_layout = self._create_data_list_panel()
        
        self.trend_section_layout.addLayout(trend_graph_layout, 3)
        self.trend_section_layout.addLayout(data_list_layout, 1)
        
        self.plot_widget = self.trend_canvas
    
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
        self.plot_button.clicked.connect(self.compute_requested)
        self.call_button.clicked.connect(self.load_data_requested)
        self.save_button.clicked.connect(self.save_requested)
        self.data_list_save_btn.clicked.connect(self._on_list_save_clicked)
        self.select_pytpe3.currentIndexChanged.connect(
            lambda: self.view_type_changed.emit(self.select_pytpe3.currentData())
        )
        self.select_all_btn3.clicked.connect(self.Querry_list3.selectAll)
        self.deselect_all_btn3.clicked.connect(self.Querry_list3.clearSelection)
        
        # 채널 체크박스 - 파일 목록 필터
        self.checkBox_13.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_14.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_15.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_16.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_17.stateChanged.connect(self._on_channel_filter_changed)
        self.checkBox_18.stateChanged.connect(self._on_channel_filter_changed)
    
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
            self.checkBox_13, self.checkBox_14, self.checkBox_15,
            self.checkBox_16, self.checkBox_17, self.checkBox_18
        ]
        for idx, checkbox in enumerate(checkboxes, start=1):
            if checkbox.isChecked():
                selected_channels.append(str(idx))
        
        if not selected_channels:
            self.Querry_list3.clear()
            self.Querry_list3.addItems(self._all_files)
            return
        
        filtered_files = [
            f for f in self._all_files
            if any(f.endswith(f"_{ch}.txt") for ch in selected_channels)
        ]
        self.Querry_list3.clear()
        self.Querry_list3.addItems(filtered_files)
    
    def get_parameters(self) -> dict:
        try:
            delta_f = float(self.Hz_3.toPlainText().strip())
        except (ValueError, AttributeError):
            delta_f = 1.0
        
        try:
            band_min = float(self.freq_range_inputmin.text().strip())
        except (ValueError, AttributeError):
            band_min = 0.0
        
        try:
            band_max = float(self.freq_range_inputmax.text().strip())
        except (ValueError, AttributeError):
            band_max = 10000.0
        
        return {
            'delta_f': delta_f,
            'window_type': self.Function_3.currentText(),
            'overlap': float(self.Overlap_Factor_3.currentText().replace('%', '')),
            'view_type': self.select_pytpe3.currentData(),
            'band_min': band_min,
            'band_max': band_max
        }
    
    def plot_trend(self, channel_data: dict, clear: bool = True):
        if clear:
            self.trend_ax.clear()
            self.trend_ax.set_title("Overall RMS Trend", fontsize=PlotFontSizes.TITLE)
        
        for idx, (ch, data) in enumerate(sorted(channel_data.items())):
            color = CHANNEL_COLORS[idx % len(CHANNEL_COLORS)]
            self.trend_ax.plot(data['x'], data['y'], 
                             label=f"Channel {ch}", color=color,
                             marker='o', markersize=2, linewidth=0.5)
        
        self.trend_ax.set_xlabel('Date & Time', fontsize=PlotFontSizes.LABEL)
        self.trend_ax.set_ylabel(VIEW_TYPE_LABELS.get(self._current_view_type, ''), fontsize=PlotFontSizes.LABEL)
        self.trend_ax.set_facecolor('white')
        self.trend_ax.grid(True, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
        self.trend_ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), 
                           fontsize=PlotFontSizes.LEGEND, frameon=True, fancybox=True, shadow=True)
        self.trend_canvas.draw_idle()
    
    def set_view_type(self, view_type: str):
        self._current_view_type = view_type
    
    def clear_plot(self):
        self.trend_ax.clear()
        self.trend_ax.set_title("Overall RMS Trend", fontsize=PlotFontSizes.TITLE)
        self.trend_canvas.draw()
    
    def set_files(self, files: List[str]):
        self._all_files = list(files)
        self.Querry_list3.clear()
        self.Querry_list3.addItems(files)
    
    def get_selected_files(self) -> List[str]:
        return [item.text() for item in self.Querry_list3.selectedItems()]
    
    def update_data_list(self, data_text: str):
        self.data_list_text.setText(data_text)
    
    def _init_mouse_events(self):
        self.trend_canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.trend_canvas.mpl_connect('button_press_event', self._on_mouse_click)
        self.trend_canvas.mpl_connect('key_press_event', self._on_key_press)
        self.trend_canvas.mpl_connect('scroll_event', self._on_scroll)
    
    def _on_scroll(self, event):
        if event.inaxes != self.trend_ax:
            return
        
        scale_factor = 0.85 if event.button == 'up' else 1.15
        
        xlim = self.trend_ax.get_xlim()
        ylim = self.trend_ax.get_ylim()
        xdata, ydata = event.xdata, event.ydata
        
        x_left = xdata - (xdata - xlim[0]) * scale_factor
        x_right = xdata + (xlim[1] - xdata) * scale_factor
        self.trend_ax.set_xlim(x_left, x_right)
        
        y_bottom = ydata - (ydata - ylim[0]) * scale_factor
        y_top = ydata + (ylim[1] - ydata) * scale_factor
        self.trend_ax.set_ylim(y_bottom, y_top)
        
        self.trend_canvas.draw_idle()
    
    def _on_mouse_move(self, event):
        if not event.inaxes:
            if self.hover_pos is not None:
                if self.hover_dot:
                    self.hover_dot.set_data([], [])
                self.hover_pos = None
                self.trend_canvas.draw_idle()
            return
        
        closest_x, closest_y, min_dist = None, None, np.inf
        
        for line in self.trend_ax.get_lines():
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
                self.hover_dot = self.trend_ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
            self.hover_dot.set_data([closest_x], [closest_y])
            self.hover_pos = [closest_x, closest_y]
            self.trend_canvas.draw_idle()
    
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
        if not self.trend_x_value or not self.trend_rms_values:
            return
        
        min_distance = float('inf')
        closest_index = -1
        
        for i, (data_x, data_y) in enumerate(zip(self.trend_x_value, self.trend_rms_values)):
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
        
        if self.trend_marker:
            try:
                self.trend_marker.remove()
            except:
                pass
        
        if self.trend_annotation:
            try:
                self.trend_annotation.remove()
            except:
                pass
        
        file_name = self.trend_file_names[closest_index]
        x_val = self.trend_x_value[closest_index]
        y_val = self.trend_rms_values[closest_index]
        
        self.trend_marker = self.trend_ax.plot(
            x_val, y_val,
            marker='o', color='red', markersize=7
        )[0]
        
        annotation_text = f"{file_name}\nX: {x_val}\nY: {y_val:.4f}"
        
        self.trend_annotation = self.trend_ax.annotate(
            annotation_text,
            (x_val, y_val),
            textcoords="offset points",
            xytext=(10, 10),
            ha='left',
            fontsize=PlotFontSizes.ANNOTATION,
            bbox=dict(boxstyle="round,pad=0.3", edgecolor="black",
                     facecolor="lightyellow", alpha=0.8)
        )
        
        self.trend_canvas.draw_idle()
        self._add_filename_to_list(file_name)
    
    def _clear_markers(self):
        if self.trend_marker:
            try:
                self.trend_marker.remove()
                self.trend_marker = None
            except:
                pass
        
        if self.trend_annotation:
            try:
                self.trend_annotation.remove()
                self.trend_annotation = None
            except:
                pass
        
        self.trend_canvas.draw_idle()
    
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
    
    def set_trend_data(self, x_values: List, rms_values: List, file_names: List):
        self.trend_x_value = x_values
        self.trend_rms_values = rms_values
        self.trend_file_names = file_names
    
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
    
    def set_directory_path(self, directory_path: str):
        self._directory_path = directory_path
