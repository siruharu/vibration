"""
Spectrum analysis tab view - exact replication of legacy tab_3.

Matches cn_3F_trend_optimized.py lines 1095-1650 for pixel-perfect UI compatibility.
"""
from typing import List, Optional

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QGridLayout, QVBoxLayout, QComboBox, QPushButton,
    QSplitter, QLabel, QListWidget, QAbstractItemView, QCheckBox, QTextBrowser,
    QTextEdit, QLineEdit, QSizePolicy, QApplication
)
from PyQt5.QtCore import pyqtSignal, Qt

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


VIEW_TYPE_LABELS = {
    'ACC': 'Vibration Acceleration\n(m/s², RMS)',
    'VEL': 'Vibration Velocity\n(mm/s, RMS)',
    'DIS': 'Vibration Displacement\n(μm, RMS)'
}

PLOT_COLORS = ['b', 'g', 'r', 'c', 'm', 'y']


class SpectrumTabView(QWidget):
    """
    Time/Spectrum tab view - exact legacy replication.
    
    Layout structure matches legacy tab_3:
    - Left: checkboxes, file list, metadata
    - Top right: FFT options, Plot/Next buttons
    - Bottom: waveform + spectrum plots with axis controls
    """
    
    compute_requested = pyqtSignal()
    next_file_requested = pyqtSignal()
    view_type_changed = pyqtSignal(int)
    window_type_changed = pyqtSignal(str)
    file_clicked = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_view_type = 'ACC'
        self.markers = []
        self.hover_dot = None
        self.hover_pos = None
        self.data_dict = {}
        self.mouse_tracking_enabled = True
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
        
        self.Querry_list = QListWidget()
        self.Querry_list.setMinimumWidth(300)
        self.Querry_list.setMaximumWidth(300)
        self.Querry_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        self.lift_layout.addLayout(checksBox, 0, 0)
        self.lift_layout.addLayout(button_layout2, 1, 0)
        self.lift_layout.addWidget(self.Querry_list, 2, 0)
        
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
        self.Sample_rate.setMaximumSize(113, 27)
        self.Sample_rate.setHtml("Sampling:")
        layout.addWidget(self.Sample_rate, 0, 0)
        
        self.Duration = QTextBrowser()
        self.Duration.setMaximumSize(113, 27)
        self.Duration.setHtml("Record Length:")
        layout.addWidget(self.Duration, 1, 0)
        
        self.Rest_time = QTextBrowser()
        self.Rest_time.setMaximumSize(113, 27)
        self.Rest_time.setHtml("Rest time:")
        layout.addWidget(self.Rest_time, 2, 0)
        
        self.IEPE = QTextBrowser()
        self.IEPE.setMaximumSize(113, 27)
        self.IEPE.setHtml("IEPE enable:")
        layout.addWidget(self.IEPE, 3, 0)
        
        self.Channel = QTextBrowser()
        self.Channel.setMaximumSize(113, 27)
        self.Channel.setHtml("Channel:")
        layout.addWidget(self.Channel, 4, 0)
        
        self.Sensitivity = QTextBrowser()
        self.Sensitivity.setMaximumSize(113, 27)
        self.Sensitivity.setHtml("Sensitivity:")
        layout.addWidget(self.Sensitivity, 5, 0)
        
        self.Sensitivity2 = QTextBrowser()
        self.Sensitivity2.setMaximumSize(113, 27)
        self.Sensitivity2.setHtml("Sensitivity_edit:")
        layout.addWidget(self.Sensitivity2, 6, 0)
        
        self.Sample_rate_view = QTextBrowser()
        self.Sample_rate_view.setMaximumSize(113, 27)
        self.Sample_rate_view.setHtml("")
        layout.addWidget(self.Sample_rate_view, 0, 1)
        
        self.Duration_view = QTextBrowser()
        self.Duration_view.setMaximumSize(113, 27)
        self.Duration_view.setHtml("")
        layout.addWidget(self.Duration_view, 1, 1)
        
        self.Rest_time_view = QTextBrowser()
        self.Rest_time_view.setMaximumSize(113, 27)
        self.Rest_time_view.setHtml("")
        layout.addWidget(self.Rest_time_view, 2, 1)
        
        self.IEPE_view = QTextBrowser()
        self.IEPE_view.setMaximumSize(113, 27)
        self.IEPE_view.setHtml("")
        layout.addWidget(self.IEPE_view, 3, 1)
        
        self.Channel_view = QTextBrowser()
        self.Channel_view.setMaximumSize(113, 27)
        self.Channel_view.setHtml("")
        layout.addWidget(self.Channel_view, 4, 1)
        
        self.Sensitivity_view = QTextBrowser()
        self.Sensitivity_view.setMaximumSize(113, 27)
        self.Sensitivity_view.setHtml("")
        layout.addWidget(self.Sensitivity_view, 5, 1)
        
        self.Sensitivity_edit = QLineEdit()
        self.Sensitivity_edit.setMaximumSize(113, 27)
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
        layout.setSpacing(0)
        
        self.Plot_Options = QTextBrowser()
        self.Plot_Options.setMaximumSize(136, 27)
        self.Plot_Options.setHtml("FFT Options")
        layout.addWidget(self.Plot_Options, 0, 0)
        
        self.textBrowser_15 = QTextBrowser()
        self.textBrowser_15.setMaximumSize(136, 27)
        self.textBrowser_15.setHtml("Δf:")
        layout.addWidget(self.textBrowser_15, 1, 0)
        
        self.Hz = QTextEdit()
        self.Hz.setPlaceholderText("")
        self.Hz.setStyleSheet("background-color: lightgray;color: black;")
        self.Hz.setMaximumSize(136, 27)
        layout.addWidget(self.Hz, 1, 1)
        
        self.textBrowser_16 = QTextBrowser()
        self.textBrowser_16.setMaximumSize(136, 27)
        self.textBrowser_16.setHtml("Windown Function:")
        layout.addWidget(self.textBrowser_16, 2, 0)
        
        self.Function = QComboBox()
        self.Function.setStyleSheet("background-color: lightgray;color: black;")
        self.Function.addItem("Rectangular")
        self.Function.addItem("Hanning")
        self.Function.addItem("Flattop")
        self.Function.setMaximumSize(136, 27)
        layout.addWidget(self.Function, 2, 1)
        
        self.textBrowser_17 = QTextBrowser()
        self.textBrowser_17.setMaximumSize(136, 27)
        self.textBrowser_17.setHtml("Overlap Factor:")
        layout.addWidget(self.textBrowser_17, 3, 0)
        
        self.Overlap_Factor = QComboBox()
        self.Overlap_Factor.setStyleSheet("background-color: lightgray;color: black;")
        self.Overlap_Factor.addItem("0%")
        self.Overlap_Factor.addItem("25%")
        self.Overlap_Factor.addItem("50%")
        self.Overlap_Factor.addItem("75%")
        self.Overlap_Factor.setMaximumSize(136, 27)
        layout.addWidget(self.Overlap_Factor, 3, 1)
        
        self.select_type_convert = QTextBrowser()
        self.select_type_convert.setMaximumSize(136, 27)
        self.select_type_convert.setHtml("Convert")
        layout.addWidget(self.select_type_convert, 4, 0)
        
        self.select_pytpe = QComboBox()
        self.select_pytpe.setStyleSheet("background-color: lightgray;color: black;")
        self.select_pytpe.addItem("ACC", 1)
        self.select_pytpe.addItem("VEL", 2)
        self.select_pytpe.addItem("DIS", 3)
        self.select_pytpe.setMaximumSize(136, 27)
        layout.addWidget(self.select_pytpe, 4, 1)
        
        self.plot_button = QPushButton("Plot")
        self.plot_button.setMaximumSize(136, 27)
        self.plot_button.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.plot_button, 5, 0)
        
        self.next_button = QPushButton("Next")
        self.next_button.setMaximumSize(136, 27)
        self.next_button.setStyleSheet("background-color: lightgray;color: black;")
        layout.addWidget(self.next_button, 5, 1)
        
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
        self.waveax.set_title("Waveform", fontsize=7)
        self.wavecanvas.setFocusPolicy(Qt.StrongFocus)
        
        self.figure = Figure(figsize=(10, 4), dpi=dpi)
        self.figure.set_tight_layout({'rect': [0, 0, 0.88, 1]})
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Vibration Spectrum", fontsize=7)
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        
        self.hover_dot = self.ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
        
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
        x_autoscale.setMaximumSize(100, 31)
        x_layout.addWidget(x_autoscale)
        
        auto_y = QCheckBox("Auto Y")
        auto_y.setChecked(True)
        y_layout.addWidget(auto_y)
        
        y_autoscale = QPushButton("Auto Scale")
        y_autoscale.setMaximumSize(100, 31)
        y_layout.addWidget(y_autoscale)
        
        x_min_input = QLineEdit()
        x_min_input.setPlaceholderText("X min")
        x_min_input.setMaximumSize(70, 31)
        x_min_input.setStyleSheet("background-color: lightgray;color: black;")
        x_layout2.addWidget(x_min_input)
        
        x_max_input = QLineEdit()
        x_max_input.setPlaceholderText("X max")
        x_max_input.setMaximumSize(70, 31)
        x_max_input.setStyleSheet("background-color: lightgray;color: black;")
        x_layout2.addWidget(x_max_input)
        
        x_set = QPushButton("Set")
        x_set.setMaximumSize(70, 31)
        x_layout2.addWidget(x_set)
        
        y_min_input = QLineEdit()
        y_min_input.setPlaceholderText("Y min")
        y_min_input.setMaximumSize(70, 31)
        y_min_input.setStyleSheet("background-color: lightgray;color: black;")
        y_layout2.addWidget(y_min_input)
        
        y_max_input = QLineEdit()
        y_max_input.setPlaceholderText("Y max")
        y_max_input.setMaximumSize(70, 31)
        y_max_input.setStyleSheet("background-color: lightgray;color: black;")
        y_layout2.addWidget(y_max_input)
        
        y_set = QPushButton("Set")
        y_set.setMaximumSize(70, 31)
        y_layout2.addWidget(y_set)
        
        layout.addLayout(x_layout)
        layout.addLayout(x_layout2)
        layout.addLayout(y_layout)
        layout.addLayout(y_layout2)
        
        if plot_type == 'spec':
            save_button = QPushButton("Data Extraction")
            layout.addWidget(save_button)
        
        layout.addStretch(2)
        
        widget = QWidget()
        widget.setLayout(layout)
        return widget
    
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
    
    def _connect_picking_events(self):
        self.cid_move = self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self.cid_click = self.canvas.mpl_connect("button_press_event", self._on_mouse_click)
        self.cid_key = self.canvas.mpl_connect("key_press_event", self._on_key_press)
    
    def get_parameters(self) -> dict:
        return {
            'window_type': self.Function.currentText(),
            'overlap': float(self.Overlap_Factor.currentText().replace('%', '')),
            'view_type': self.select_pytpe.currentData()
        }
    
    def plot_spectrum(self, frequencies: List[float], spectrum: List[float],
                      label: str = '', color_index: int = 0, clear: bool = True):
        if clear:
            self.ax.clear()
            self.ax.set_title("Vibration Spectrum", fontsize=7)
            self.hover_dot = self.ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
            self.data_dict.clear()
        
        color = PLOT_COLORS[color_index % len(PLOT_COLORS)]
        self.ax.plot(frequencies, spectrum, color=color, linewidth=0.5, label=label, alpha=0.8)
        
        if label:
            self.data_dict[label] = (frequencies, spectrum)
        
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel(VIEW_TYPE_LABELS.get(self._current_view_type, ''))
        self.ax.grid(True)
        if label:
            self.ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), 
                          fontsize=7, frameon=True, fancybox=True, shadow=True)
        self.canvas.draw_idle()
    
    def plot_waveform(self, time: List[float], amplitude: List[float],
                      label: str = '', color_index: int = 0, clear: bool = True):
        if clear:
            self.waveax.clear()
            self.waveax.set_title("Waveform", fontsize=7)
        
        color = PLOT_COLORS[color_index % len(PLOT_COLORS)]
        self.waveax.plot(time, amplitude, color=color, linewidth=0.5, label=label, alpha=0.8)
        self.waveax.set_xlabel('Time (s)')
        self.waveax.set_ylabel(VIEW_TYPE_LABELS.get(self._current_view_type, ''))
        self.waveax.grid(True)
        if label:
            self.waveax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), 
                             fontsize=7, frameon=True, fancybox=True, shadow=True)
        self.wavecanvas.draw_idle()
    
    def set_view_type(self, view_type: str):
        self._current_view_type = view_type
    
    def clear_plots(self):
        self.ax.clear()
        self.ax.set_title("Vibration Spectrum", fontsize=7)
        self.hover_dot = self.ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
        self.markers.clear()
        self.data_dict.clear()
        self.canvas.draw()
        self.waveax.clear()
        self.waveax.set_title("Waveform", fontsize=7)
        self.wavecanvas.draw()
    
    def set_files(self, files: List[str]):
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
                            fontsize=7, color='red', 
                            verticalalignment='bottom')
        self.markers.append((marker, label))
        self.canvas.draw_idle()
    
    def clear_markers(self):
        for marker, label in self.markers:
            marker.remove()
            label.remove()
        self.markers.clear()
        self.canvas.draw_idle()
