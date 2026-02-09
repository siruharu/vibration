"""
개별 파일 검사를 위한 상세 분석 다이얼로그.

FFT 분석, 시간 영역 플롯, 데이터 내보내기 기능을 제공합니다.
cn_3F_trend_optimized.py에서 모듈화 아키텍처를 위해 추출.

의존성:
- file_parser.FileParser: 파일 로딩
- fft_engine.FFTEngine: FFT 연산
- responsive_layout_utils.ResponsiveLayoutMixin: DPI 스케일링
"""

import os
import sys
import itertools
from pathlib import Path
from typing import Dict, List, Optional

_project_root = Path(__file__).parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5 import QtWidgets, QtCore, QtGui

from .responsive_layout_utils import (
    ResponsiveLayoutMixin, 
    calculate_window_size, 
    create_responsive_button
)

try:
    from .axis_range_dialog import AxisRangeDialog
    from .list_save_dialog_helpers import (
        SpectrumPicker,
        load_file_with_fft,
        export_spectrum_to_csv,
        get_view_label
    )
except ImportError:
    from axis_range_dialog import AxisRangeDialog
    from list_save_dialog_helpers import (
        SpectrumPicker,
        load_file_with_fft,
        export_spectrum_to_csv,
        get_view_label
    )


class ListSaveDialog(QtWidgets.QDialog, ResponsiveLayoutMixin):
    """
    파일 검사 및 FFT 분석을 위한 상세 분석 다이얼로그.
    
    선택된 파일에 대한 파형 및 스펙트럼 플롯을 대화형 피킹,
    축 스케일링, CSV 내보내기 기능과 함께 표시합니다.
    
    속성:
        channel_files: 채널 이름을 파일 목록에 매핑하는 딕셔너리
        directory_path: 파일이 위치한 기본 디렉토리
    """

    def __init__(self, channel_files: dict = None, parent=None, 
                 headers=None, directory_path: str = None):
        super().__init__(parent)
        
        if channel_files is None:
            channel_files = {}

        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinMaxButtonsHint
        )
        self.setWindowTitle("Detail Analysis - Select Files to Save")

        width, height = calculate_window_size(0.85, 0.85, 1200, 800)
        self.resize(width, height)
        self.setMinimumSize(1200, 800)

        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; color: #333333; }
            QLabel { color: #333333; }
            QCheckBox { color: #333333; }
        """)

        self.directory_path = directory_path
        self.channel_files = channel_files
        self.color_cycle = itertools.cycle(plt.cm.tab10.colors)
        self.markers_spect = []
        self.hover_pos_spect = [None, None]
        self.mouse_tracking_enabled = True
        self.data_dict: Dict[str, tuple] = {}
        self.spectrum_data_dict1: Dict[str, np.ndarray] = {}
        self.spectrum_picker: Optional[SpectrumPicker] = None

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        self.left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(right_panel)
        self.splitter.setStretchFactor(0, 15)
        self.splitter.setStretchFactor(1, 85)

        main_layout.addWidget(self.splitter)

        self._populate_list_widget()
        self._adjust_left_panel_width()

    def _create_left_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot_button = create_responsive_button("Plot", 100, 35, "primary")
        self.plot_button.clicked.connect(self._on_file_items_clicked)
        layout.addWidget(self.plot_button)

        self.file_list_widget = QtWidgets.QListWidget()
        self.file_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.file_list_widget.setStyleSheet("""
            QListWidget {
                background-color: white; color: #333333; font-size: 10pt;
                border: 1px solid #cccccc; font-family: 'Courier New', monospace;
            }
            QListWidget::item { padding: 2px; }
            QListWidget::item:selected { background-color: #0078d7; color: white; }
            QListWidget::item:hover { background-color: #e5f3ff; }
        """)
        layout.addWidget(self.file_list_widget)

        return panel

    def _create_right_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        waveform_widget = self._create_graph_widget("waveform")
        layout.addWidget(waveform_widget, stretch=1)

        spectrum_widget = self._create_graph_widget("spectrum")
        layout.addWidget(spectrum_widget, stretch=1)

        button_widget = self._create_button_panel()
        layout.addWidget(button_widget)

        return panel

    def _create_graph_widget(self, graph_type: str) -> QtWidgets.QWidget:
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
        canvas.mpl_connect('button_press_event',
                          lambda event: self._on_axis_click(event, graph_type))

        layout.addWidget(canvas)
        control = self._create_control_panel(graph_type)
        layout.addWidget(control)

        return widget

    def _on_axis_click(self, event, graph_type: str) -> None:
        if event.button != 1:
            return
        if event.inaxes is not None:
            return

        ax = self.tab_waveax if graph_type == "waveform" else self.tab_ax
        bbox = ax.get_window_extent()

        if (bbox.x0 <= event.x <= bbox.x1 and
                event.y < bbox.y0 and event.y > bbox.y0 - 60):
            self._show_axis_range_dialog(graph_type, 'X')
            return

        if (bbox.y0 <= event.y <= bbox.y1 and
                event.x < bbox.x0 and event.x > bbox.x0 - 120):
            self._show_axis_range_dialog(graph_type, 'Y')
            return

    def _create_control_panel(self, graph_type: str) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        auto_x = QtWidgets.QCheckBox("Auto X")
        auto_x.setChecked(True)
        auto_x.setStyleSheet("color: #333333; font-size: 10pt;")
        auto_x.stateChanged.connect(
            lambda: self._toggle_auto_scale(graph_type, 'x', auto_x.isChecked())
        )

        auto_scale_x_btn = create_responsive_button("Auto Scale X", 100, 25, "default")
        auto_scale_x_btn.clicked.connect(lambda: self._auto_scale(graph_type, 'x'))

        auto_y = QtWidgets.QCheckBox("Auto Y")
        auto_y.setChecked(True)
        auto_y.setStyleSheet("color: #333333; font-size: 10pt;")
        auto_y.stateChanged.connect(
            lambda: self._toggle_auto_scale(graph_type, 'y', auto_y.isChecked())
        )

        auto_scale_y_btn = create_responsive_button("Auto Scale Y", 100, 25, "default")
        auto_scale_y_btn.clicked.connect(lambda: self._auto_scale(graph_type, 'y'))

        layout.addWidget(auto_x)
        layout.addWidget(auto_scale_x_btn)
        layout.addWidget(auto_y)
        layout.addWidget(auto_scale_y_btn)
        layout.addStretch()

        prefix = "waveform" if graph_type == "waveform" else "spectrum"
        setattr(self, f"tab_{prefix}_auto_x", auto_x)
        setattr(self, f"tab_{prefix}_auto_scale_x", auto_scale_x_btn)
        setattr(self, f"tab_{prefix}_auto_y", auto_y)
        setattr(self, f"tab_{prefix}_auto_scale_y", auto_scale_y_btn)

        return panel

    def _show_axis_range_dialog(self, graph_type: str, axis_name: str) -> None:
        ax = self.tab_waveax if graph_type == "waveform" else self.tab_ax

        if axis_name == 'X':
            current_min, current_max = ax.get_xlim()
        else:
            current_min, current_max = ax.get_ylim()

        dialog = AxisRangeDialog(axis_name, current_min, current_max, self)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            min_val, max_val = dialog.get_range()

            prefix = "waveform" if graph_type == "waveform" else "spectrum"
            canvas = self.tab_wavecanvas if graph_type == "waveform" else self.tab_canvas

            if min_val is None or max_val is None:
                if axis_name == 'X':
                    auto_checkbox = getattr(self, f"tab_{prefix}_auto_x")
                    auto_checkbox.setChecked(True)
                    ax.autoscale(enable=True, axis='x')
                else:
                    auto_checkbox = getattr(self, f"tab_{prefix}_auto_y")
                    auto_checkbox.setChecked(True)
                    ax.autoscale(enable=True, axis='y')
            else:
                if axis_name == 'X':
                    auto_checkbox = getattr(self, f"tab_{prefix}_auto_x")
                    auto_checkbox.setChecked(False)
                    ax.set_xlim(min_val, max_val)
                else:
                    auto_checkbox = getattr(self, f"tab_{prefix}_auto_y")
                    auto_checkbox.setChecked(False)
                    ax.set_ylim(min_val, max_val)

            canvas.draw_idle()

    def _toggle_auto_scale(self, graph_type: str, axis: str, is_auto: bool) -> None:
        if is_auto:
            self._auto_scale(graph_type, axis)

    def _auto_scale(self, graph_type: str, axis: str) -> None:
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

    def _create_button_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_save_button = create_responsive_button("Data Extraction", 120, 35)
        self.tab_save_button.clicked.connect(self._on_save_button_clicked)

        self.tab_close_button = create_responsive_button("Close", 120, 35)
        self.tab_close_button.clicked.connect(self._close_dialog)

        layout.addWidget(self.tab_save_button)
        layout.addWidget(self.tab_close_button)
        layout.addStretch()

        return panel

    def _populate_list_widget(self) -> None:
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

    def _adjust_left_panel_width(self) -> None:
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

    def _get_selected_files(self) -> List[str]:
        selected_files = []
        for item in self.file_list_widget.selectedItems():
            file_name = item.data(QtCore.Qt.UserRole)
            if file_name:
                selected_files.append(file_name)
        return selected_files

    def _on_file_items_clicked(self) -> None:
        selected_files = self._get_selected_files()

        if not selected_files:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select files")
            return

        self.tab_waveax.clear()
        self.tab_ax.clear()
        self.color_cycle = itertools.cycle(plt.cm.tab10.colors)
        self.data_dict = {}
        self.spectrum_data_dict1 = {}

        for file_name in selected_files:
            self._load_and_plot_file(file_name)

        self._finalize_plot()

    def _load_and_plot_file(self, file_name: str) -> None:
        if not self.directory_path:
            return

        file_path = os.path.join(self.directory_path, file_name)
        result = load_file_with_fft(file_path, self.directory_path)

        if result is None:
            return

        color = next(self.color_cycle)
        base_name = result['base_name']

        self.tab_waveax.plot(
            result['time'], result['data'], 
            label=base_name, color=color, linewidth=0.5, alpha=0.8
        )
        self.tab_ax.plot(
            result['frequency'], result['spectrum'],
            label=base_name, color=color, linewidth=0.5, alpha=0.8
        )

        self.data_dict[base_name] = (result['frequency'], result['spectrum'])
        self.spectrum_data_dict1[base_name] = result['spectrum']

        ylabel = get_view_label(result['view_type'])
        self.tab_ax.set_ylabel(ylabel, fontsize=7)
        self.tab_waveax.set_ylabel(ylabel, fontsize=7)

    def _finalize_plot(self) -> None:
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

        self.spectrum_picker = SpectrumPicker(
            self.tab_ax, self.tab_canvas, self.data_dict
        )
        self.tab_canvas.mpl_connect("motion_notify_event", 
                                    self.spectrum_picker.on_mouse_move)
        self.tab_canvas.mpl_connect("button_press_event", 
                                    self.spectrum_picker.on_mouse_click)
        self.tab_canvas.mpl_connect("key_press_event", 
                                    self.spectrum_picker.on_key_press)

    def _on_save_button_clicked(self) -> None:
        if not self.spectrum_data_dict1:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please plot files first")
            return

        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save CSV File", "", "CSV Files (*.csv)"
        )
        if not save_path:
            return

        success = export_spectrum_to_csv(
            save_path, self.data_dict, self.spectrum_data_dict1
        )

        if success:
            QtWidgets.QMessageBox.information(
                self, "Success", f"Saved:\n{save_path}"
            )
        else:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Save failed"
            )

    def _close_dialog(self) -> None:
        try:
            plt.close(self.tab_waveform_figure)
            plt.close(self.tab_figure)
        except:
            pass

        self.data_dict.clear()
        self.spectrum_data_dict1.clear()
        self.deleteLater()
        self.accept()

    def closeEvent(self, event) -> None:
        self._close_dialog()
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == QtCore.Qt.Key_Escape:
            self._close_dialog()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    dialog = ListSaveDialog()
    print("ListSaveDialog test: OK")
    print(f"Methods: {len([m for m in dir(dialog) if not m.startswith('_')])}")
