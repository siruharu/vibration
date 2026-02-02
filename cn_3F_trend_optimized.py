import faulthandler

import gc

gc.enable()
gc.set_threshold(700, 10, 10)

from PyQt5.QtGui import QFont
from performance_logger import PerformanceLogger
from OPTIMIZATION_PATCH_LEVEL1 import FileCache, BatchProcessor, MemoryEfficientProcessor


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

faulthandler.enable(all_threads=True)


import sys
import os

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

from PyQt5 import QtGui
from PyQt5.QtWidgets import QMessageBox
import re
from matplotlib.figure import Figure
from PyQt5 import QtWidgets, QtCore
from datetime import datetime
from PyQt5.QtWidgets import QApplication
import matplotlib.dates as mdates
from PyQt5.QtWidgets import QSizePolicy
from scipy.fft import fft
from scipy.signal.windows import hann, flattop
import itertools
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt
import csv
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from PyQt5.QtGui import QIcon
from matplotlib import rcParams
rcParams.update({'font.size': 7, 'font.family': 'Nanum Gothic'})

# 로거 초기화 (한 번만)
perf_logger = PerformanceLogger(
    log_file="performance_log.txt",
    console_output=True  # 콘솔에도 출력
)

def set_plot_font(plot_item, font_size=7):
    font = QFont("Nanum Gothic", font_size)
    for axis in ['bottom', 'left', 'top', 'right']:
        plot_item.getAxis(axis).setTickFont(font)
    plot_item.setTitle("제목입니다", size=f"{font_size+2}pt")
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

class ListSaveDialog(QtWidgets.QDialog):
        def __init__(self, channel_files: dict, parent=None, headers=None, directory_path=None):
                super().__init__(parent)
                self.marker_points = []  # 마커를 저장할 리스트
                self.cursor_circles = []
                self.markers = []
                self.setWindowTitle("Select Files to Save")
                self.resize(1920, 1027)
                self.color_cycle = itertools.cycle(plt.cm.tab10.colors)

                self.progress_dialog = None  # 진행률 창 초기화
                self.directory_path = directory_path  # ✅ 메인 윈도우에서 전달받은 경로 저장
                file_path2 = self.directory_path

                self.tab_layout = QtWidgets.QGridLayout()
                self.layout = QtWidgets.QHBoxLayout()

                self.left_layout = QtWidgets.QVBoxLayout()
                
                self.list_widget = QtWidgets.QListWidget()
                # 채널별로 항목 정렬
                for ch_name in sorted(channel_files.keys()):
                        # 채널 헤더 (비선택 항목)
                        item = QtWidgets.QListWidgetItem(ch_name)
                        item.setFlags(QtCore.Qt.NoItemFlags)  # 선택 불가
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                        self.list_widget.addItem(item)

                        # 해당 채널의 파일 목록
                        for filename in channel_files[ch_name]:
                                self.list_widget.addItem(filename)

                #self.list_widget.itemClicked.connect(self.on_file_itmes_clicked)

                self.plot_button = QtWidgets.QPushButton()
                
                self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

                self.file_name = QtWidgets.QPushButton("Plot")
                self.file_name.clicked.connect(self.on_file_itmes_clicked)
                self.left_layout.addWidget(self.file_name)
                self.left_layout.addWidget(self.list_widget)

                self.tab_layout.addLayout(self.left_layout, 0, 0, 2, 1)
                self.tab_layout.setColumnStretch(1,4)


                self.tab_wave_layout = QtWidgets.QHBoxLayout()
                self.tab_spec_layout = QtWidgets.QHBoxLayout()

                # 그래프를 표시할 수직 Splitter 생성
                self.tab_graph_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
                self.tab_graph_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

                # ▶ Waveform 그래프
                self.tab_waveform_figure = Figure()
                self.tab_wavecanvas = FigureCanvas(self.tab_waveform_figure)
                self.tab_wavecanvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.tab_waveax = self.tab_waveform_figure.add_subplot(111)
                self.tab_waveax.set_title("Waveform", fontsize=7, fontname='Nanum Gothic')
                self.tab_wavecanvas.setFocusPolicy(QtCore.Qt.StrongFocus)
                self.tab_wavecanvas.setFocus()
                #self.wavecanvas.setMinimumHeight(600)
                #self.wavecanvas.setMaximumHeight(600)

                # ▶ Spectrum 그래프
                self.tab_figure = Figure()
                self.tab_canvas = FigureCanvas(self.tab_figure)
                self.tab_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.tab_ax = self.tab_figure.add_subplot(111)
                self.tab_ax.set_title("Vibration Spectrum", fontsize=7, fontname='Nanum Gothic')
                self.tab_waveax.tick_params(axis='x', labelsize = 7)
                self.tab_waveax.tick_params(axis='y', labelsize = 7)
                self.tab_ax.tick_params(axis='x', labelsize = 7)
                self.tab_ax.tick_params(axis='y', labelsize = 7)
                self.tab_canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
                self.tab_canvas.setFocus()
                #self.canvas.setMinimumHeight(200)
                #self.canvas.setMaximumHeight(600)

                # # ▶ Splitter에 그래프 추가
                # self.tab_graph_splitter.addWidget(self.tab_wavecanvas)
                # self.tab_graph_splitter.addWidget(self.tab_canvas)

                # self.tab_layout.addWidget(self.tab_graph_splitter, 0, 1, 1, 7)

                
                self.tab_wave_scale_layout = QtWidgets.QVBoxLayout()
                self.tab_wave_scale_layout.addStretch(2)

                self.tab_wave_x_layout = QtWidgets.QHBoxLayout()
                self.tab_wave_x_layout2 = QtWidgets.QHBoxLayout()
                self.tab_wave_y_layout = QtWidgets.QHBoxLayout()
                self.tab_wave_y_layout2 = QtWidgets.QHBoxLayout()
                # ✅ X축, Y축 Limit 설정 UI 추가
                self.tab_auto_wave_x = QtWidgets.QCheckBox("Auto X")
                self.tab_auto_wave_x.setChecked(True)  # 기본값 Auto
                self.tab_wave_x_layout.addWidget(self.tab_auto_wave_x)

                self.tab_wave_x_autoscale = QtWidgets.QPushButton("Auto Scale")
                self.tab_wave_x_autoscale.setMaximumSize(100, 31)
                self.tab_wave_x_layout.addWidget(self.tab_wave_x_autoscale)

                self.tab_auto_wave_y = QtWidgets.QCheckBox("Auto Y")
                self.tab_auto_wave_y.setChecked(True)
                self.tab_wave_y_layout.addWidget(self.tab_auto_wave_y)

                self.tab_wave_y_autoscale = QtWidgets.QPushButton("Auto Scale")
                self.tab_wave_y_autoscale.setMaximumSize(100, 31)
                self.tab_wave_y_layout.addWidget(self.tab_wave_y_autoscale)


                self.tab_x_min_input = QtWidgets.QLineEdit()
                self.tab_x_min_input.setPlaceholderText("X min")
                self.tab_x_min_input.setMaximumSize(70, 31)
                self.tab_x_min_input.setStyleSheet("""background-color: lightgray;color: black;""")
                self.tab_wave_x_layout2.addWidget(self.tab_x_min_input)

                self.tab_x_max_input = QtWidgets.QLineEdit()
                self.tab_x_max_input.setPlaceholderText("X max")
                self.tab_x_max_input.setMaximumSize(70, 31)
                self.tab_x_max_input.setStyleSheet("""background-color: lightgray;color: black;""")
                self.tab_wave_x_layout2.addWidget(self.tab_x_max_input)

                self.tab_wave_x_set = QtWidgets.QPushButton("Set")
                self.tab_wave_x_set.setMaximumSize(70, 31)
                self.tab_wave_x_layout2.addWidget(self.tab_wave_x_set)


                self.tab_y_min_wave_input = QtWidgets.QLineEdit()
                self.tab_y_min_wave_input.setPlaceholderText("Y min")
                self.tab_y_min_wave_input.setStyleSheet("""background-color: lightgray;color: black;""")
                self.tab_y_min_wave_input.setMaximumSize(70, 31)
                self.tab_wave_y_layout2.addWidget(self.tab_y_min_wave_input)

                self.tab_y_max_wave_input = QtWidgets.QLineEdit()
                self.tab_y_max_wave_input.setPlaceholderText("Y max")
                self.tab_y_max_wave_input.setStyleSheet("""background-color: lightgray;color: black;""")
                self.tab_y_max_wave_input.setMaximumSize(70, 31)
                self.tab_wave_y_layout2.addWidget(self.tab_y_max_wave_input)

                self.tab_wave_y_set = QtWidgets.QPushButton("Set")
                self.tab_wave_y_set.setMaximumSize(70, 31)
                self.tab_wave_y_layout2.addWidget(self.tab_wave_y_set)

                self.tab_wave_x_set.clicked.connect(self.set_wave_x_axis)
                self.tab_wave_y_set.clicked.connect(self.set_wave_y_axis)
                self.tab_wave_x_autoscale.clicked.connect(self.auto_wave_scale_x)
                self.tab_wave_y_autoscale.clicked.connect(self.auto_wave_scale_y)

                self.tab_wave_x_layout.addStretch()
                self.tab_wave_y_layout.addStretch()
                self.tab_wave_x_layout2.addStretch()
                self.tab_wave_y_layout2.addStretch()


                self.tab_wave_scale_layout.addLayout(self.tab_wave_x_layout)
                self.tab_wave_scale_layout.addLayout(self.tab_wave_x_layout2)
                self.tab_wave_scale_layout.addLayout(self.tab_wave_y_layout)
                self.tab_wave_scale_layout.addLayout(self.tab_wave_y_layout2)
                self.tab_wave_scale_layout.setAlignment(self.tab_wave_x_layout, QtCore.Qt.AlignVCenter)
                self.tab_wave_scale_layout.setAlignment(self.tab_wave_x_layout2, QtCore.Qt.AlignVCenter)
                self.tab_wave_scale_layout.setAlignment(self.tab_wave_y_layout, QtCore.Qt.AlignVCenter)
                self.tab_wave_scale_layout.setAlignment(self.tab_wave_y_layout2, QtCore.Qt.AlignTop)
                self.tab_wave_scale_layout.addStretch(2)

                #self.tab_layout.addLayout(self.tab_wave_scale_layout, 0, 2, 1, 1)
                
        #spectrum
                self.tab_spectrum_scale_layout = QtWidgets.QVBoxLayout()
                self.tab_spectrum_scale_layout.addStretch(2)

                self.tab_spectrum_x_layout = QtWidgets.QHBoxLayout()
                self.tab_spectrum_x_layout2 = QtWidgets.QHBoxLayout()
                self.tab_spectrum_y_layout = QtWidgets.QHBoxLayout()
                self.tab_spectrum_y_layout2 = QtWidgets.QHBoxLayout()
                # ✅ X축, Y축 Limit 설정 UI 추가
                self.tab_auto_spectrum_x = QtWidgets.QCheckBox("Auto X")
                self.tab_auto_spectrum_x.setChecked(True)  # 기본값 Auto
                self.tab_spectrum_x_layout.addWidget(self.tab_auto_spectrum_x)

                self.tab_spectrum_x_autoscale = QtWidgets.QPushButton("Auto Scale")
                self.tab_spectrum_x_autoscale.setMaximumSize(100, 31)
                self.tab_spectrum_x_layout.addWidget(self.tab_spectrum_x_autoscale)

                self.tab_auto_spectrum_y = QtWidgets.QCheckBox("Auto Y")
                self.tab_auto_spectrum_y.setChecked(True)
                self.tab_spectrum_y_layout.addWidget(self.tab_auto_spectrum_y)

                self.tab_spectrum_y_autoscale = QtWidgets.QPushButton("Auto Scale")
                self.tab_spectrum_y_autoscale.setMaximumSize(100, 31)
                self.tab_spectrum_y_layout.addWidget(self.tab_spectrum_y_autoscale)


                self.tab_spectrum_x_min_input = QtWidgets.QLineEdit()
                self.tab_spectrum_x_min_input.setPlaceholderText("X min")
                self.tab_spectrum_x_min_input.setMaximumSize(70, 31)
                self.tab_spectrum_x_min_input.setStyleSheet("""background-color: lightgray;color: black;""")
                self.tab_spectrum_x_layout2.addWidget(self.tab_spectrum_x_min_input)

                self.tab_spectrum_x_max_input = QtWidgets.QLineEdit()
                self.tab_spectrum_x_max_input.setPlaceholderText("X max")
                self.tab_spectrum_x_max_input.setMaximumSize(70, 31)
                self.tab_spectrum_x_max_input.setStyleSheet("""background-color: lightgray;color: black;""")
                self.tab_spectrum_x_layout2.addWidget(self.tab_spectrum_x_max_input)

                self.tab_spectrum_x_set = QtWidgets.QPushButton("Set")
                self.tab_spectrum_x_set.setMaximumSize(70, 31)
                self.tab_spectrum_x_layout2.addWidget(self.tab_spectrum_x_set)


                self.tab_spectrum_y_min_input = QtWidgets.QLineEdit()
                self.tab_spectrum_y_min_input.setPlaceholderText("Y min")
                self.tab_spectrum_y_min_input.setMaximumSize(70,31)
                self.tab_spectrum_y_min_input.setStyleSheet("""background-color: lightgray;color: black;""")
                self.tab_spectrum_y_layout2.addWidget(self.tab_spectrum_y_min_input)

                self.tab_spectrum_y_max_input = QtWidgets.QLineEdit()
                self.tab_spectrum_y_max_input.setPlaceholderText("Y max")
                self.tab_spectrum_y_max_input.setMaximumSize(70,31)
                self.tab_spectrum_y_max_input.setStyleSheet("""background-color: lightgray;color: black;""")
                self.tab_spectrum_y_layout2.addWidget(self.tab_spectrum_y_max_input)

                self.tab_spectrum_y_set = QtWidgets.QPushButton("Set")
                self.tab_spectrum_y_set.setMaximumSize(70,31)
                self.tab_spectrum_y_layout2.addWidget(self.tab_spectrum_y_set)

                self.tab_spectrum_x_set.clicked.connect(self.set_x_axis)
                self.tab_spectrum_y_set.clicked.connect(self.set_y_axis)
                self.tab_spectrum_x_autoscale.clicked.connect(self.auto_scale_x)
                self.tab_spectrum_y_autoscale.clicked.connect(self.auto_scale_y)


                self.tab_save_button = QtWidgets.QPushButton("Data Extraction")
                # self.save_button.setGeometry(QtCore.QRect(1750, 205, 80, 30))
                self.tab_save_button.clicked.connect(self.on_save_button_clicked)
                


                self.tab_spectrum_x_layout.addStretch()
                self.tab_spectrum_x_layout2.addStretch()
                self.tab_spectrum_y_layout.addStretch()
                self.tab_spectrum_y_layout2.addStretch()

                self.tab_spectrum_scale_layout.addLayout(self.tab_spectrum_x_layout)
                self.tab_spectrum_scale_layout.addLayout(self.tab_spectrum_x_layout2)
                self.tab_spectrum_scale_layout.addLayout(self.tab_spectrum_y_layout)
                self.tab_spectrum_scale_layout.addLayout(self.tab_spectrum_y_layout2)
                self.tab_spectrum_scale_layout.setAlignment(self.tab_spectrum_x_layout, QtCore.Qt.AlignVCenter)
                self.tab_spectrum_scale_layout.setAlignment(self.tab_spectrum_x_layout2, QtCore.Qt.AlignVCenter)
                self.tab_spectrum_scale_layout.setAlignment(self.tab_spectrum_y_layout, QtCore.Qt.AlignVCenter)
                self.tab_spectrum_scale_layout.setAlignment(self.tab_spectrum_y_layout2, QtCore.Qt.AlignTop)

                self.tab_spectrum_scale_layout.addWidget(self.tab_save_button)
                self.tab_spectrum_scale_layout.addStretch(2)

                

                spec_scale_widget = QtWidgets.QWidget()
                spec_scale_widget.setLayout(self.tab_spectrum_scale_layout)
                
                
                wave_scale_widget = QtWidgets.QWidget()
                wave_scale_widget.setLayout(self.tab_wave_scale_layout)
                
                
                # 수평 Splitter - Wave
                wave_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
                wave_splitter.addWidget(self.tab_wavecanvas)
                wave_splitter.addWidget(wave_scale_widget)

                # 수평 Splitter - Spec
                spec_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
                spec_splitter.addWidget(self.tab_canvas)
                spec_splitter.addWidget(spec_scale_widget)

                # 수직 Splitter - 상단: Wave / 하단: Spec
                main_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
                main_splitter.addWidget(wave_splitter)
                main_splitter.addWidget(spec_splitter)

                # 전체 레이아웃에 추가
                self.tab_layout.addWidget(main_splitter, 0, 1, 1, 7)

                # Stretch 비율 조정 (선택사항)
                main_splitter.setStretchFactor(0, 1)  # wave 영역
                main_splitter.setStretchFactor(1, 1)  # spec 영역

                wave_splitter.setStretchFactor(0, 5)  # wave canvas
                wave_splitter.setStretchFactor(1, 1)  # wave scale

                spec_splitter.setStretchFactor(0, 5)  # spec canvas
                spec_splitter.setStretchFactor(1, 1)  # spec scale

                self.setLayout(self.layout)
                self.layout.addLayout(self.tab_layout)
                self.hover_pos_spect = [None, None]  # 현재 hover_dot 위치 저장 (float x, y) spectrum
                self.markers_spect = []  # 마커와 텍스트를 저장할 리스트
                self.mouse_tracking_enabled = True  # 기본값은 True로 설정

        def get_selected_files(self):
                return [
                item.text()
                for i in range(self.list_widget.count())
                if (item := self.list_widget.item(i)).isSelected() and item.flags() != QtCore.Qt.NoItemFlags
                ]
        
        def parse_array_string(self,s):
                import re
                # 숫자 또는 지수 표기된 수 추출 (예: 1.23e+02)
                return np.array([float(val) for val in re.findall(r"[-+]?\d*\.\d+|\d+e[-+]?\d+", s)])
        
        def on_file_itmes_clicked(self):
                self.data_dict = {}  # 파일별 (x_data, y_data)
                self.clear_all_graphs()

                selected_items = self.list_widget.selectedItems()
                total_files = len(selected_items)

                if total_files == 0:
                        return
                # ✅ ProgressDialog 생성 및 띄우기
                progress_dialog = ProgressDialog(total_files, self)
                progress_dialog.setModal(True)  # 사용자 입력 막기 (선택사항)
                progress_dialog.show()


                for i, item in enumerate(selected_items):
                        selected_file = item.text()
                        self.load_and_plot_file(selected_file)
                        progress_dialog.update_progress(i + 1)

                        
                       
                # ✅ 완료 후 창 닫기
                progress_dialog.label.setText("완료되었습니다.")
                QtWidgets.QApplication.processEvents()
                QtCore.QThread.msleep(300)  # 조금 보여주고 닫기
                progress_dialog.close()
                self.finalize_plot()

        def clear_all_graphs(self):
                self.tab_waveax.clear()
                self.tab_ax.clear()
                self.tab_wavecanvas.draw()
                self.tab_canvas.draw()
                self.color_cycle = itertools.cycle(plt.cm.tab10.colors)

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

        def load_txt_file_only(self, file_path):
                """
                ✨ 최적화된 파일 로딩 (NumPy + 캐싱)
                - NumPy 직접 로딩: 3-5배 빠름
                - 캐싱: 반복 실행 시 10배 이상 빠름
                """
                try:
                        # 캐시를 사용한 빠른 로딩
                        if hasattr(self, 'file_cache'):
                                data = self.file_cache.load_with_cache(file_path)
                                return data
                except Exception as e:
                        perf_logger.log_warning(f"⚠️ 캐시 로딩 실패, 기존 방식 사용: {e}")

                # 폴백: 기존 방식
                data = []
                with open(file_path, 'r') as f:
                        for line in f:
                                line = line.strip()
                                try:
                                        data.append(float(line))
                                except ValueError:
                                        continue
                return np.array(data)


        def get_json_value(self, metadata, key, default=None, value_type=None):
                val = metadata.get(key, default)  # metadata는 dict 여야 함
                if val is None:
                        return default
                if value_type:
                        try:
                                val = value_type(val)
                        except Exception as e:
                                print(f"⚠ {key} 타입 변환 오류: {e}, 기본값 사용")
                                val = default
                return val

        def load_and_plot_file(self, file_path):
                # 전체 경로
                if hasattr(self, 'directory_path') and self.directory_path:
                        file_path = os.path.join(self.directory_path, file_path)

                base_name = os.path.splitext(os.path.basename(file_path))[0]

                # JSON 경로
                # JSON 경로를 항상 trend_data 폴더 안으로 지정
                json_folder = os.path.join(self.directory_path, "trend_data",  "full" ) if hasattr(self, 'directory_path') else "trend_data"
                json_path = os.path.join(json_folder, f"{base_name}_full.json")

                # 확인용 출력
                print("JSON 경로:", json_path)
                # JSON 읽기
                metadata = {}
                if os.path.exists(json_path):
                        try:
                                with open(json_path, 'r') as f:
                                        metadata = load_json(f)
                        except Exception as e:
                                QtWidgets.QMessageBox.warning(None, "JSON 오류", f"{json_path}\n\n{str(e)}")

                # TXT 파일에서 waveform 데이터 읽기
                try:
                        data = self.load_txt_file_only(file_path)
                except Exception as e:
                        QtWidgets.QMessageBox.critical(None, "파일 오류", f"{file_path}\n\n{str(e)}")
                        return

                if data is None or len(data) == 0:
                        QtWidgets.QMessageBox.warning(None, "데이터 없음", f"{base_name} 파일에 데이터가 없습니다.")
                        return

                # ----------------------------
                # JSON 우선으로 값 가져오기
                # ----------------------------
                sampling_rate = self.get_json_value(metadata, "sampling_rate", value_type=float)
                print(f"!!!!!!!!!!{sampling_rate}")
                delta_f = self.get_json_value(metadata, "delta_f",  value_type=float)
                print(f"!!!!!!!!!!{delta_f}")
                overlap = self.get_json_value(metadata, "overlap", value_type=float)
                print(f"!!!!!!!!!!{overlap}")
                window_str = self.get_json_value(metadata, "window", default="hanning", value_type=str).lower()
                print(f"!!!!!!!!!!{window_str}")
                view_type_str = self.get_json_value(metadata, "view_type", default="ACC", value_type=str).upper()
                print(f"!!!!!!!!!!{view_type_str}")
                b_sensitivity = self.get_json_value(metadata, "b_sensitivity",  value_type=None)
                print(f"!!!!!!!!!!{b_sensitivity}")
                sensitivity = self.get_json_value(metadata, "sensitivity",  value_type=None)
                print(f"!!!!!!!!!!{sensitivity}")
                start_time = self.get_json_value(metadata, "start_time",  value_type=str)
                print(f"!!!!!!!!!!{start_time}")
                duration_str = self.get_json_value(metadata, "duration",  value_type=str)
                print(f"!!!!!!!!!!{duration_str}")
                rest_time = self.get_json_value(metadata, "rest_time",  value_type=str)
                print(f"!!!!!!!!!!{rest_time}")
                repetition = self.get_json_value(metadata, "repetition",  value_type=str)
                print(f"!!!!!!!!!!{repetition}")
                iepe = self.get_json_value(metadata, "iepe",  value_type=str)
                print(f"!!!!!!!!!!{iepe}")
                channel_num = self.get_json_value(metadata, "channel_num",  value_type=str)
                print(f"!!!!!!!!!!{channel_num}")
                filename_json = self.get_json_value(metadata, "filename", value_type=str)
                print(f"!!!!!!!!!!{filename_json}")
                # ----------------------------
                # 윈도우 플래그
                # ----------------------------
                win_flag = {"rectangular":0, "hanning":1, "flattop":2}.get(window_str, 1)

                # View Type
                conv2sgnl = {"ACC":1,"VEL":2,"DIS":3}.get(view_type_str,1)

                # 민감도 보정
                if b_sensitivity is not None and sensitivity is not None:
                        try:
                                b_sens_match = re.findall(r"[-+]?[0-9]*\.?[0-9]+", str(b_sensitivity))
                                sens_match = re.findall(r"[-+]?[0-9]*\.?[0-9]+", str(sensitivity))
                                if b_sens_match and sens_match:
                                        b_sens = float(b_sens_match[0])
                                        sens = float(sens_match[0])
                                        if sens != 0:
                                                data = (b_sens / sens) * data
                        except Exception as e:
                                print(f"⚠ 민감도 스케일 오류: {e}")

                # ----------------------------
                # FFT 최소 길이 1024 보장
                # ----------------------------
                MIN_FFT_LENGTH = 1024
                N = len(data)
                if sampling_rate is None:
                        QMessageBox.critical(None, "오류", "sampling_rate가 없습니다.")
                        return

                if delta_f is None:
                        delta_f = 1.0

                delta_f_min = sampling_rate / max(N, MIN_FFT_LENGTH)

                # duration 기반 재계산
                if duration_str:
                        match = re.findall(r"[-+]?\d*\.\d+|\d+", duration_str)
                        if match:
                                duration_val = float(match[0])
                                if duration_val > 0:
                                        hz_value = round(1 / duration_val + 0.01, 2)
                                        delta_f = max(delta_f_min, hz_value)
                else:
                        delta_f = max(delta_f, delta_f_min)

                # FFT 길이 계산 및 제로 패딩
                N_fft = max(int(sampling_rate / delta_f), MIN_FFT_LENGTH)
                if N_fft > N:
                        data = np.pad(data, (0, N_fft - N), 'constant')
                        N = N_fft

                # ----------------------------
                # FFT 계산
                # ----------------------------
                try:
                        type_flag = 2
                        win_flag = {"rectangular":0, "hanning":1, "flattop":2}.get(window_str, 1)
                        conv2sgnl = {"ACC":1,"VEL":2,"DIS":3}.get(view_type_str,1)

                        w, f, P, ACF, ECF, rms_w, Sxx = self.mdl_FFT_N(
                        type_flag,
                        sampling_rate,
                        data,
                        delta_f,
                        overlap,
                        win_flag,
                        1,           # 입력 신호: 가속도
                        conv2sgnl,
                        0            # Zero padding 없음 (이미 패딩)
                        )
                except Exception as e:
                        QtWidgets.QMessageBox.critical(None, "FFT 오류", f"{base_name} 처리 중 오류:\n\n{str(e)}")
                        return

                # ----------------------------
                # 파형 플로팅
                # ----------------------------
                time = np.arange(len(data)) / sampling_rate
                color = next(self.color_cycle)
                self.tab_waveax.plot(time, data, label=base_name, color=color, linewidth=0.5)
                                                              
                # 스펙트럼 플로팅
                spectrum = ACF * np.abs(P)
                self.tab_ax.plot(f, spectrum, label=base_name, color=color, linewidth=0.5)

                # ----------------------------
                # 내부 데이터 저장
                # ----------------------------
                if not hasattr(self, 'spectrum_data_dict1'):
                        self.spectrum_data_dict1 = {}
                if not hasattr(self, 'frequency_array1'):
                        self.frequency_array1 = None
                if not hasattr(self, 'file_names_used1'):
                        self.file_names_used1 = []
                if not hasattr(self, 'sample_rate1'):
                        self.sample_rate1 = {}

                self.spectrum_data_dict1[base_name] = spectrum
                self.frequency_array1 = f
                self.file_names_used1.append(base_name)
                self.sample_rate1[base_name] = sampling_rate

                # 메타데이터 저장
                self.delta_f1 = delta_f
                self.window_type1 = window_str
                self.overlap1 = overlap
                self.start_time1 = start_time
                self.Duration1 = duration_str
                self.Rest_time1 = rest_time
                self.repetition1 = repetition
                self.IEPE1 = iepe
                self.Sensitivity1 = sensitivity
                self.b_Sensitivity1 = b_sensitivity
                self.dt1 = self.get_json_value(metadata, "dt", default=None, value_type=str)
                self.channel_info1 = channel_num
                self.file_name1 = base_name

                self.data_dict[file_path] = (f, spectrum)

                # ----------------------------
                # Y축 라벨
                # ----------------------------
                view_labels = {1: "Vibration Acceleration \n (m/s², RMS)",
                                2: "Vibration Velocity \n (mm/s, RMS)",
                                3: "Vibration Displacement \n (μm, RMS)"}
                ylabel = view_labels.get(conv2sgnl, "Vibration (mm/s, RMS)")
                self.tab_ax.set_ylabel(ylabel, fontsize=7, fontname='Nanum Gothic')
                self.tab_waveax.set_ylabel(ylabel, fontsize=7, fontname='Nanum Gothic')

                self.tab_ax.legend(fontsize=7)
                self.tab_waveax.legend(fontsize=7)

        def finalize_plot(self):
                self.tab_waveax.set_title("Waveform", fontsize=7, fontname='Nanum Gothic')
                self.tab_waveax.set_xlabel("Time (s)", fontsize=7, fontname='Nanum Gothic')
                self.tab_waveax.legend()
                self.tab_waveax.grid(True)
                self.tab_wavecanvas.draw()
                

                self.tab_ax.set_title("Vibration Spectrum", fontsize=7, fontname='Nanum Gothic')
                self.tab_ax.set_xlabel("Frequency (Hz)", fontsize=7, fontname='Nanum Gothic')
                self.tab_ax.legend()
                self.tab_ax.grid(True)
                self.tab_canvas.draw()
                self.hover_dot_spect = self.tab_ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
                self.tab_canvas.mpl_connect("motion_notify_event", self.on_mouse_move_spect)
                self.tab_canvas.mpl_connect("button_press_event", self.on_mouse_click)
                self.tab_canvas.mpl_connect("key_press_event", self.on_key_press)
                
        def start_loading_files(self, selected_files):
                self.progress_bar.setMaximum(len(selected_files))
                for i, file_path in enumerate(selected_files):
                        self.load_and_plot_file(file_path)
                        self.progress_bar.setValue(i + 1)
                        QtWidgets.QApplication.processEvents()
 
        def on_mouse_move_spect(self, event):
                if not self.mouse_tracking_enabled:  # X축 범위 설정 중에는 마우스 이벤트 무시
                        return
                """마우스가 그래프 위를 움직일 때 가장 가까운 점을 찾아서 점 표시"""
                if not event.inaxes:
                        if self.hover_pos_spect is not None:  # hover_pos가 None이 아니면 점을 지우기
                                self.hover_dot_spect.set_data([], [])
                                self.hover_pos_spect = None
                                self.tab_canvas.draw()
                        return

                closest_x, closest_y, min_dist = None, None, np.inf  # np.inf로 수정

                # 모든 라인에서 가장 가까운 점 찾기
                for line in self.tab_ax.get_lines():
                        x_data_move, y_data_move = line.get_xdata(), line.get_ydata()

                        # 데이터가 없으면 건너뛴다
                        if len(x_data_move) == 0 or len(y_data_move) == 0:
                                continue

                        # datetime 타입이면 float(ordinal)로 변환
                        if isinstance(x_data_move[0], datetime):
                                x_data_move = mdates.date2num(x_data_move)
                                self.initialize_hover_step_spect(x_data_move, y_data_move)  # datetime 처리 후 호출

                        for x, y in zip(x_data_move, y_data_move):
                                dist = np.hypot(event.xdata - x, event.ydata - y)
                                if dist < min_dist:
                                        min_dist = dist
                                        closest_x, closest_y = x, y

                # 가장 가까운 점이 존재하면 해당 점을 표시
                if closest_x is not None:
                        self.hover_dot_spect.set_data([closest_x], [closest_y])
                        self.hover_pos_spect = [closest_x, closest_y]  # 현재 좌표 저장
                        self.tab_canvas.draw()

        def on_mouse_click(self, event):
                """마우스를 클릭했을 때 가장 가까운 점을 고정된 마커로 표시"""
                if not event.inaxes:
                        return

                # hover_dot 위치를 가져와서 마커로 고정
                x, y = self.hover_dot_spect.get_data()

                

                if x and y:
                        self.add_marker_spect(x,y)

                if event.button == 3:  # 오른쪽 클릭
                        for marker, label in self.markers_spect:
                                marker.remove()
                                label.remove()
                        self.markers_spect.clear()

                        # for annotation in self.annotations:
                        #         annotation.remove()
                        # self.annotations.clear()
                        # for filename in self.marker_filenames:
                        #         self.remove_marker_filename_from_list(filename)
                        # self.marker_filenames.clear()

                        self.tab_canvas.draw()
                        return

        def initialize_hover_step_spect(self, x_data, y_data):
                x_spacing = np.mean(np.diff(x_data))
                y_spacing = np.mean(np.diff(y_data))
                self.hover_step = [x_spacing, y_spacing]

        def on_key_press(self, event):
                """키보드 입력 처리 (방향키로 점 이동, 엔터로 마커 고정)"""
                x, y = self.hover_dot_spect.get_data()

                

                # 모든 라인에서 x, y 데이터를 가져옵니다.
                all_x_data = []
                all_y_data = []
                for line in self.tab_ax.get_lines():
                        x_data, y_data = line.get_xdata(), line.get_ydata()
                        if len(x_data) == 0 or len(y_data) == 0:
                                continue
                        if isinstance(x_data[0], datetime):
                                x_data = mdates.date2num(x_data)
                        all_x_data.extend(x_data)
                        all_y_data.extend(y_data)
                        self.initialize_hover_step_spect(x_data, y_data)

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
                        self.add_marker_spect(all_x_data[current_index], all_y_data[current_index])
                        return
                if candidates:
                        # 가장 가까운 x 또는 y를 가진 index 선택
                        candidates.sort(key=lambda t: t[1])  # 거리 기준 정렬
                        current_index = candidates[0][0]

                # 이동된 위치로 hover_dot 위치 업데이트
                new_x = all_x_data[current_index]
                new_y = all_y_data[current_index]
                self.hover_pos_spect = [new_x, new_y]
                self.hover_dot_spect.set_data([new_x], [new_y])
                self.tab_canvas.draw()

        def add_marker_spect(self,  x, y):
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

                                marker = self.tab_ax.plot(np.round(closest_x, 4), np.round(closest_y, 4), marker='o', color='red', markersize=7)[0]
                        

                        label = self.tab_ax.text(
                                float(closest_x), float(closest_y) + 0.001,
                                f"file: {closest_file}\nX: {float(closest_x):.4f}, Y: {float(closest_y):.4f}",
                                fontsize=7, fontweight='bold', color='black',
                                ha='center', va='bottom'
                        )
                        self.markers_spect.append((marker, label))
                        # self.annotations.append(annotation)
                        self.tab_canvas.draw()

        def set_x_axis(self):
                try:
                        # 현재 그래프의 첫 번째 축 객체와 그 안의 라인 객체들
                        ax = self.tab_canvas.figure.axes[0]  # matplotlib 축 객체
                        lines = ax.get_lines()  # 그래프 라인들

                        x_min = float(self.tab_spectrum_x_min_input.text())
                        x_max = float(self.tab_spectrum_x_max_input.text())
                        if x_min >= x_max:
                                raise ValueError
                        
                        self.tab_auto_spectrum_x.setChecked(False)
                        self.tab_ax.set_xlim(x_min, x_max)

                        y_data_in_x_range = []
                        for line in lines:
                                x_data = line.get_xdata()  # 현재 라인의 X 데이터
                                y_data = line.get_ydata()  # 현재 라인의 Y 데이터

                                # x_data가 list라면 NumPy 배열로 변환
                                x_data = np.array(x_data)
                                y_data = np.array(y_data)  # y_data도 NumPy 배열로 변환

                                mask = (x_data >= x_min) & (x_data <= x_max)  # X 범위에 해당하는 값들만 필터링
                                y_filtered = y_data[mask]  # 해당 범위의 Y값만 추출
                                y_data_in_x_range.extend(y_filtered)  # Y 데이터 모은 리스트에 추가

                        if y_data_in_x_range:  # 데이터가 있을 경우만
                                y_min = min(y_data_in_x_range)
                                y_max = max(y_data_in_x_range)
                                ax.set_ylim(y_min, y_max)  # Y축 범위 설정

                        self.tab_auto_spectrum_y.setChecked(False)  # Y축 자동 스케일 해제

                        self.tab_canvas.draw()
                except ValueError:
                        print("")

        def set_y_axis(self):
                try:
                        y_min = float(self.tab_spectrum_y_min_input.text())
                        y_max = float(self.tab_spectrum_y_max_input.text())
                        if y_min >= y_max:
                                raise ValueError
                        self.tab_auto_spectrum_y.setChecked(False)
                        self.tab_ax.set_ylim(y_min, y_max)
                        self.tab_canvas.draw()
                except ValueError:
                        print("")

        def auto_scale_x(self):
                ax = self.tab_canvas.figure.axes[0]  # matplotlib 축 객체
                self.tab_auto_spectrum_x.setChecked(True)
                self.tab_auto_spectrum_y.setChecked(True)
                ax.autoscale(enable=True, axis='x')
                self.tab_canvas.draw()

        def auto_scale_y(self):
                ax = self.tab_canvas.figure.axes[0]  # matplotlib 축 객체
                self.tab_auto_spectrum_y.setChecked(True)
                ax.autoscale(enable=True, axis='y')
                self.tab_canvas.draw()

        def set_wave_x_axis(self):
                try:
                                # 현재 그래프의 첫 번째 축 객체와 그 안의 라인 객체들
                        ax = self.tab_wavecanvas.figure.axes[0]  # matplotlib 축 객체
                        lines = ax.get_lines()  # 그래프 라인들

                        x_min = float(self.tab_x_min_input.text())
                        x_max = float(self.tab_x_max_input.text())
                        if x_min >= x_max:
                                raise ValueError
                        
                        self.tab_auto_wave_x.setChecked(False)
                        self.tab_waveax.set_xlim(x_min, x_max)

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

                        self.tab_auto_wave_y.setChecked(False)  # Y축 자동 스케일 해제

                        self.tab_wavecanvas.draw()
                except ValueError:
                        print("")

        def set_wave_y_axis(self):
                try:
                        y_min = float(self.tab_y_min_wave_input.text())
                        y_max = float(self.tab_y_max_wave_input.text())
                        if y_min >= y_max:
                                raise ValueError
                        self.tab_auto_wave_y.setChecked(False)
                        self.tab_waveax.set_ylim(y_min, y_max)
                        self.tab_wavecanvas.draw()
                except ValueError:
                        print("")

        def auto_wave_scale_x(self):
                ax = self.tab_wavecanvas.figure.axes[0]  # matplotlib 축 객체
                self.tab_auto_wave_x.setChecked(True)
                self.tab_auto_wave_y.setChecked(True)
                ax.autoscale(enable=True, axis='x')
                self.tab_wavecanvas.draw()

        def auto_wave_scale_y(self):
                ax = self.tab_wavecanvas.figure.axes[0]  # matplotlib 축 객체
                self.tab_auto_wave_y.setChecked(True)
                ax.autoscale(enable=True, axis='y')
                self.tab_wavecanvas.draw()

        def on_save_button_clicked(self):
                        # Spectrum이 아닌 경우 저장하지 않음
                        if not hasattr(self, 'spectrum_data_dict1') or not self.spectrum_data_dict1:
                                return

                        self.tab_save_spectrum_to_csv(
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
                                self.file_name1
                                )
                        # print(f"{self.file_names_used}")

        def tab_save_spectrum_to_csv(self, spectrum_data1, frequencies1, file_names1, delta_f1, window_type1, overlap1, channel_info1, sampling_rates1, dt1, start_time1, Duration1, Rest_time1, repetition1, IEPE1, Sensitivity1, b_Sensitivity1, channel_infos1, view_type, file_name1):
                # 🔽 파일 저장 위치 선택
                save_path, _ = QFileDialog.getSaveFileName(None, "Save CSV File", "", "CSV Files (*.csv)")
                if not save_path:
                        return
                if not save_path.endswith(".csv"):
                        save_path += ".csv"

                with open(save_path, mode='w', newline='', encoding='utf-8-sig') as csv_file:
                        writer = csv.writer(csv_file)

                        # ✅ 헤더 정보 먼저 기록
                        writer.writerow(["Δf", delta_f1])
                        writer.writerow(["Window", window_type1])
                        writer.writerow(["Overlap", f"{overlap1}%"])
                        writer.writerow(["Sampling", sampling_rates1.get(file_names1[0], "N/A")])
                        writer.writerow(["Record Length", Duration1])
                        writer.writerow(["Rest Time", Rest_time1])
                        writer.writerow(["IEPE", IEPE1])
                        writer.writerow(["Time Resolution(dt)", dt1])
                        writer.writerow(["Starting Time", start_time1])
                        writer.writerow(["Repetition", repetition1])
                        writer.writerow(["Sensitivity", Sensitivity1])
                        writer.writerow(["b.Sensitivity", b_Sensitivity1])
                        writer.writerow(["View Type", str(view_type)])

                        writer.writerow([])  # 빈 줄 추가

                        # ✅ 채널 정보 행
                        channel_row = [""]  # 첫 번째 빈 셀 (Frequency 칸)
                        for file_name in file_names1:
                                match = re.search(r'_(\d+)$', file_name)
                                channel = f"CH {match.group(1)}" if match else "CH ?"
                                channel_row.append(channel)
                        writer.writerow(channel_row)

                        # ✅ 열 제목
                        header = ["Frequency (Hz)"] + file_names1
                        writer.writerow(header)

                        # ✅ 데이터 행
                        for i, freq in enumerate(frequencies1):
                                row = [freq]
                                for file_name in file_names1:
                                        spectrum = spectrum_data1.get(file_name)
                                        if spectrum is not None and i < len(spectrum):
                                                row.append(float(spectrum[i]))
                                        else:
                                                row.append("")
                        writer.writerow(row)
                        
class Ui_MainWindow(object):
        
        def setupUi(self, MainWindow): 
                self.main_window = MainWindow

                self._optimization_initialized = False

                font = QtGui.QFont("Nanum Gothic", 9)
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
                self.lift_layout.addWidget(self.Querry_list, 2,0)
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
                self.data_center_allin.addLayout(self.data_center_layout, 0,0, alignment=QtCore.Qt.AlignTop)
                self.data_center_allin.addLayout(self.data_center_layout2, 0,1,  alignment=QtCore.Qt.AlignTop)
                # self.data_center_allin.setRowStretch(0, 0)
                self.data_center_allin.setContentsMargins(0, 0, 0, 0)
                self.data_center_allin.setSpacing(0)
                


                

                # ▶ Waveform 그래프
                self.waveform_figure = Figure()
                self.wavecanvas = FigureCanvas(self.waveform_figure)
                self.wavecanvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.waveax = self.waveform_figure.add_subplot(111)
                self.waveax.set_title("Waveform", fontsize=7, fontname='Nanum Gothic')
                self.wavecanvas.setFocusPolicy(QtCore.Qt.StrongFocus)
                self.wavecanvas.setFocus()

                # ▶ Spectrum 그래프
                self.figure = Figure()
                self.canvas = FigureCanvas(self.figure)
                self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.ax = self.figure.add_subplot(111)
                self.ax.set_title("Vibration Spectrum", fontsize=7, fontname='Nanum Gothic')
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
                self.spectrum_y_min_input.setMaximumSize(70,31)
                self.spectrum_y_min_input.setStyleSheet("""background-color: lightgray;color: black;""")
                self.spectrum_y_layout2.addWidget(self.spectrum_y_min_input)

                self.spectrum_y_max_input = QtWidgets.QLineEdit()
                self.spectrum_y_max_input.setPlaceholderText("Y max")
                self.spectrum_y_max_input.setMaximumSize(70,31)
                self.spectrum_y_max_input.setStyleSheet("""background-color: lightgray;color: black;""")
                self.spectrum_y_layout2.addWidget(self.spectrum_y_max_input)

                self.spectrum_y_set = QtWidgets.QPushButton("Set")
                self.spectrum_y_set.setMaximumSize(70,31)
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
                self.plot_button.setMaximumSize(129,27)
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

                
                self.alloption_layout.addLayout(self.option1_layout, 1, 0,)
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
                self.checksBox2.addWidget(self.checkBox_18, 1 ,2)

                self.data_layout.addLayout(self.checksBox2, 0, 0)
                self.data_layout.addLayout(self.buttonall_layout, 1, 0)
                self.data_layout.addWidget(self.Querry_list3, 2,0)
                self.tab4_layout.addLayout(self.data_layout, 0, 0 ,2, 1, alignment=QtCore.Qt.AlignTop)  # 왼쪽 콘텐츠 레이아웃 추가
                self.tab4_layout.setColumnStretch(1, 4)  # 왼쪽 콘텐츠용
                 
                self.trend_section_layout = QtWidgets.QHBoxLayout()

                # ✅ trend 그래프를 표시할 위젯 추가
                self.trend_graph_layout = QtWidgets.QVBoxLayout()

                # trend 생성
                self.trend_figure = Figure()
                
                # FigureCanvas를 생성하여 trend 그래프 위젯에 추가
                self.trend_canvas = FigureCanvas(self.trend_figure)
                
                # ✅ 크기 정책 설정: 가로/세로 모두 확장 가능
                self.trend_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.trend_canvas.setFocusPolicy(Qt.ClickFocus)
                self.trend_canvas.setFocus()
                
                self.trend_graph_layout.addWidget(self.trend_canvas)

                # trend 그래프를 그릴 Axes 생성
                self.trend_ax = self.trend_figure.add_subplot(111)
                self.trend_ax.set_title("Overall RMS Trend", fontsize=7, fontname='Nanum Gothic')


                self.data_list_layout = QtWidgets.QVBoxLayout()

                self.data_list_label = QtWidgets.QTextBrowser()
                self.data_list_label.setObjectName("Pick Data List")
                self.data_list_label.setMaximumSize(175,31)
                self.data_list_label.setObjectName("data_list_label")

                self.data_list_text = QtWidgets.QTextEdit()
                self.data_list_text.setMaximumSize(175,900)
                self.data_list_text.setReadOnly(True)

                # 채널 헤더만 미리 입력해 둡니다
                initial_text = "\n".join(["Ch1", "-", "Ch2", "-", "Ch3", "-", "Ch4", "-", "Ch5", "-", "Ch6", "-"])
                self.data_list_text.setText(initial_text)
                self.data_list_save_btn = QtWidgets.QPushButton("List Save")
                self.data_list_save_btn.setMaximumSize(175,31)
                self.data_list_save_btn.clicked.connect(self.on_list_save_btn_clicked)
                self.data_list_layout.addWidget(self.data_list_label,1)
                self.data_list_layout.addWidget(self.data_list_text,2)
                self.data_list_layout.addWidget(self.data_list_save_btn,1)
                self.trend_section_layout.addLayout(self.trend_graph_layout, 3)    # 왼쪽: 리스트
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
                self.peak_figure = Figure()

                # FigureCanvas를 생성하여 peak 그래프 위젯에 추가
                self.peak_canvas = FigureCanvas(self.peak_figure)
                self.peak_graph_layout.addWidget(self.peak_canvas)
                
                self.peak_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.peak_canvas.setFocusPolicy(Qt.ClickFocus)
                self.peak_canvas.setFocus()

                # peak 그래프를 그릴 Axes 생성
                self.peak_ax = self.peak_figure.add_subplot(111)
                self.peak_ax.set_title("Band Peak Trend", fontsize=7, fontname='Nanum Gothic')

                self.tab5_layout.addLayout(self.peak_graph_layout, 1, 1, 1, 3, alignment=QtCore.Qt.AlignLeft)  # 그래프 위젯 추가


        #Waterfalltab
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

                self.plot_waterfall_button = QtWidgets.QPushButton("Plot Waterfall")
                self.plot_waterfall_button.setMaximumSize(129, 27)
                # self.plot_waterfall_button.setGeometry(QtCore.QRect(450, 95, 150, 30))
                self.plot_waterfall_button.clicked.connect(self.plot_waterfall_spectrum)
                self.options2_layout.addWidget(self.plot_waterfall_button)
                self.options2_layout.setContentsMargins(0,0,0,0)
                self.options2_layout.setSpacing(0)
                self.options2_layout.setRowStretch(0,1)
                self.options2_layout.setRowStretch(1,1)
                self.options2_layout.setColumnStretch(1,1)

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
                self.waterfall_figure = plt.Figure()

                # FigureCanvas를 생성하여 Waterfall 그래프 위젯에 추가
                self.waterfall_canvas = FigureCanvas(self.waterfall_figure)
                self.waterfall_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.waterfall_graph_layout.addWidget(self.waterfall_canvas)
                # self.waterfall_toolbar = NavigationToolbar(self.waterfall_canvas, MainWindow)
                # self.waterfall_graph_layout.addWidget(self.waterfall_toolbar)
                

                # Waterfall 그래프를 그릴 Axes 생성
                self.waterfall_ax = self.waterfall_figure.add_subplot(111)
                # self.waterfall_ax.set_title("Waterfall")
                self.waterfall_ax.set_title("Waterfall Spectrum", fontsize=7, fontname='Nanum Gothic')
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
                self.select_type_convert3.setHtml(_translate("MainWindow","Convert"))
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
                dir_path = QtWidgets.QFileDialog.getExistingDirectory(None, "Select Directory", "", QtWidgets.QFileDialog.ShowDirsOnly)
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
                                date_part = parts[0]             # '2025-04-10'
                                time_part = parts[1]             # '13-36-13'
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
                        self.sample_rate=self.Sample_rate_view.setText(parsed_data.get("D.Sampling Freq.", ""))
                        self.Duration=self.Duration_view.setText(parsed_data.get("Record Length", ""))
                        self.Rest_time=self.Rest_time_view.setText(parsed_data.get("rest_time", ""))
                        self.Channel_view.setText(parsed_data.get("channel", ""))
                        self.IEPE=self.IEPE_view.setText(parsed_data.get("iepe", ""))
                        self.Sensitivity=self.Sensitivity_view.setText(parsed_data.get("sensitivity", ""))


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
                ⭐ Level 2 최적화 적용: 병렬 처리 + 배치 렌더링
                예상 성능: 896초 → 160-220초
                """
                from PyQt5.QtWidgets import QMessageBox, QApplication
                from PyQt5.QtCore import Qt
                import numpy as np
                import time

                # ========== 전체 작업 측정 시작 ==========
                start_total = perf_logger.start_timer("전체 플롯 작업 (병렬)")

                try:
                        if not self.Querry_list.count():
                                perf_logger.end_timer("전체 플롯 작업 (병렬)", start_total)
                                return

                        # ===== 1. 파라미터 준비 =====
                        selected_files = [item.text() for item in self.Querry_list.selectedItems()]

                        # 파일 개수 제한
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

                        # 파라미터 읽기
                        try:
                                delta_f = float(self.Hz.toPlainText())
                                overlap = float(self.Overlap_Factor.currentText().replace('%', ''))
                                window_type = self.Function.currentText().lower()
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

                        # ===== 4. 병렬 처리 실행 =====
                        perf_logger.log_info(f"🚀 병렬 처리 시작 ({len(selected_files)}개 파일)")
                        start_parallel = perf_logger.start_timer("병렬 파일 처리")

                        results = self.parallel_processor.process_files(
                                file_names=selected_files,
                                directory_path=self.directory_path,
                                delta_f=delta_f,
                                overlap=overlap,
                                window_type=window_type,
                                view_type=view_type,
                                mdl_FFT_N_func=self.mdl_FFT_N,
                                load_file_func=self.load_file_data,
                                progress_callback=progress_update
                        )

                        perf_logger.end_timer("병렬 파일 처리", start_parallel)

                        # ===== 5. 배치 렌더링 =====
                        perf_logger.log_info("🎨 배치 렌더링 시작")
                        start_render = perf_logger.start_timer("배치 렌더링")

                        colors = ["b", "g", "r", "c", "m", "y"]

                        # Spectrum 렌더링
                        BatchRenderer.render_lines_batch(
                                self.ax, results, colors, data_type='spectrum'
                        )

                        # Waveform 렌더링
                        BatchRenderer.render_lines_batch(
                                self.waveax, results, colors, data_type='waveform'
                        )

                        # ===== 6. 그래프 설정 =====
                        self.ax.set_title("Vibration Spectrum", fontsize=7, fontname='Nanum Gothic')
                        self.waveax.set_title("Waveform", fontsize=7, fontname='Nanum Gothic')

                        view_type_map = {1: "ACC", 2: "VEL", 3: "DIS"}
                        view_type_str = view_type_map.get(view_type, "ACC")

                        labels = {
                                "ACC": "Vibration Acceleration \n (m/s^2, RMS)",
                                "VEL": "Vibration Velocity \n (mm/s, RMS)",
                                "DIS": "Vibration Displacement \n (μm, RMS)"
                        }
                        ylabel = labels.get(view_type_str, "Vibration (mm/s, RMS)")

                        self.ax.set_xlabel("Frequency (Hz)", fontsize=7, fontname='Nanum Gothic')
                        self.ax.set_ylabel(ylabel, fontsize=7, fontname='Nanum Gothic')
                        self.waveax.set_xlabel("Time (s)", fontsize=7, fontname='Nanum Gothic')
                        self.waveax.set_ylabel(ylabel, fontsize=7, fontname='Nanum Gothic')

                        self.ax.grid(True)
                        self.waveax.grid(True)
                        self.ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=7)
                        self.waveax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=7)

                        # ===== 7. 한 번에 렌더링 (핵심!) =====
                        self.canvas.draw_idle()
                        self.wavecanvas.draw_idle()

                        perf_logger.end_timer("배치 렌더링", start_render)

                        # ===== 8. 데이터 저장 (기존 로직 유지) =====
                        self.spectrum_data_dict1 = {}
                        self.file_names_used1 = []
                        self.sample_rate1 = {}

                        for result in results:
                                if result.success:
                                        self.spectrum_data_dict1[result.file_name] = result.spectrum
                                        self.file_names_used1.append(result.file_name)
                                        self.sample_rate1[result.file_name] = result.sampling_rate

                        if results and results[0].success:
                                self.frequency_array1 = results[0].frequency
                                self.delta_f1 = delta_f
                                self.window_type1 = window_type
                                self.overlap1 = overlap
                                self.view_type = view_type_str

                        # ===== 9. 마우스 이벤트 연결 =====
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

                        # ===== 10. 정리 =====
                        self.progress_dialog.close()

                        import gc
                        gc.collect()

                        perf_logger.end_timer("전체 플롯 작업 (병렬)", start_total)
                        perf_logger.log_info("✅ 병렬 처리 완료")

                except Exception as e:
                        perf_logger.end_timer("전체 플롯 작업 (병렬)", start_total)
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

        def save_spectrum_to_csv(self, spectrum_data1, frequencies1, file_names1, delta_f1, window_type1, overlap1, channel_info1, sampling_rates1, dt1, start_time1, Duration1, Rest_time1, repetition1, IEPE1, Sensitivity1, b_Sensitivity1, channel_infos1, view_type):
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
                for marker, label in self.markers:
                        marker.remove()
                        label.remove()
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
                for marker, label in self.markers:
                        marker.remove()
                        label.remove()
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
                for marker, label in self.markers:
                        marker.remove()
                        label.remove()
                self.markers.clear()
                ax = self.canvas.figure.axes[0]  # matplotlib 축 객체
                self.auto_spectrum_x.setChecked(True)
                self.auto_spectrum_y.setChecked(True)
                ax.autoscale(enable=True, axis='x')
                self.canvas.draw()

        def auto_scale_y(self):
                for marker, label in self.markers:
                        marker.remove()
                        label.remove()
                self.markers.clear()
                ax = self.canvas.figure.axes[0]  # matplotlib 축 객체
                self.auto_spectrum_y.setChecked(True)
                ax.autoscale(enable=True, axis='y')
                self.canvas.draw()

        def set_wave_x_axis(self):
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
                for marker, label in self.markers:
                        marker.remove()
                        label.remove()
                self.markers.clear()

        def on_mouse_click(self, event):
                """마우스를 클릭했을 때 가장 가까운 점을 고정된 마커로 표시"""
                if not event.inaxes:
                        return

                # hover_dot 위치를 가져와서 마커로 고정
                x, y = self.hover_dot2.get_data()

                

                if x and y:
                        self.add_marker(x,y)

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

        def add_marker(self,  x, y):
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

                                marker = self.ax.plot(np.round(closest_x, 4), np.round(closest_y, 4), marker='o', color='red', markersize=7)[0]
                        

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
     
        def plot_waterfall_spectrum(self, x_min=None, x_max=None, z_min=None, z_max=None):
                """3D Waterfall 스펙트럼 그래프"""

                selected_items = self.Querry_list2.selectedItems()

                if not selected_items:
                        QMessageBox.critical(None, "오류", "파일을 선택하세요")
                        return

                # ✅ Δf 값 읽기
                try:
                        delta_f_text = self.Hz_2.toPlainText()
                        if not delta_f_text:
                                raise ValueError("Δf 값이 입력되지 않았습니다.")
                        delta_f = float(delta_f_text)
                except ValueError as e:
                        QMessageBox.critical(None, "입력 오류", str(e))
                        return

                # ✅ 오버랩 비율 읽기
                overlap_str = self.Overlap_Factor_2.currentText()
                try:
                        if not overlap_str:
                                raise ValueError("오버랩 비율이 선택되지 않았습니다.")
                        overlap = float(overlap_str.replace('%', ''))
                except ValueError as e:
                        QMessageBox.critical(None, "입력 오류", str(e))
                        return

                # ✅ 윈도우 함수 읽기
                window_type = self.Function_2.currentText().lower()
                if not window_type:
                        QMessageBox.critical(None, "입력 오류", "윈도우 함수가 선택되지 않았습니다.")
                        return
                window_type = window_type.lower()

                # ✅ View Type 읽기
                view_type = self.select_pytpe2.currentData()
                if view_type is None:
                        QMessageBox.critical(None, "입력 오류", "View Type이 선택되지 않았습니다.")
                        return
                
                self.progress_dialog = ProgressDialog(len(selected_items), self.main_window)
                self.progress_dialog.setWindowModality(Qt.WindowModal)
                self.progress_dialog.show()

                # 그래프 초기화: 기존 3D Axes 완전히 닫고, 새로 띄웁니다
                self.waterfall_figure.clf()
                self.waterfall_ax = self.waterfall_figure.add_subplot(111)
                self.waterfall_ax.set_title("Waterfall Spectrum", fontsize=7, fontname='Nanum Gothic')

                # 시간 오프셋 설정 (파일명에서 시간 추출)
                angle = float(self.angle_input.text()) if self.angle_input.text().strip() else 270.0  # 기본 각도
                time_offset = 0
                offset_step = 20  # 파일별 y축 간격
                time_stamps = []  # 파일별 시간 저장 리스트
                x_labels = []
                sampling_rates = []  # 각 파일의 샘플링 레이트 저장 리스트
                self.original_line_data = []

                start_time = None  # start_time 초기화
                # 리스트로 변환
                selected_list = list(selected_items)

                # (item, timestamp) 튜플 생성
                items_with_time = []
                for item in selected_list:
                        file_name = item.text()
                        try:
                                timestamp = self.extract_timestamp_from_filename(file_name)
                        except Exception:
                                timestamp = datetime.datetime.max  # 추출 실패 시 가장 나중으로 설정
                        items_with_time.append((item, timestamp))

                # 타임스탬프 기준 정렬 (오래된 순서대로: 첫 계측이 sorted_items[0])
                sorted_items = sorted(items_with_time, key=lambda x: x[1], reverse=False)

                file_labels = []
                for item, ts in sorted_items:
                        name = os.path.splitext(item.text())[0]
                        parts = name.split("_")
                        date, time_part = parts[0], parts[1]
                        rest = "_".join(parts[2:])
                        file_labels.append(f"{date}\n{time_part}_{rest}")
                        
                angle_deg = angle  # 사용자가 원하는 각도
                angle_rad = np.deg2rad(angle_deg)
                
                # Y 축 고정 범위
                fixed_ymin, fixed_ymax = 0, 130
                self.waterfall_ax.set_ylim(fixed_ymin, fixed_ymax )
                # 🔧 그래프 수만큼 높이 나눔
                num_files = len(sorted_items)    
                #🎯 오프셋 거리: 고정된 공간 안에 모두 들어오게 자동 조절
                offset_range = fixed_ymax - fixed_ymin
                offset_distance = offset_range / num_files  # 파일 수 많을수록 간격 작아짐
                dx = offset_distance * np.cos(angle_rad)
                dy = offset_distance * np.sin(angle_rad)
                
                first_start = None
                last_start = None

                y_ticks = []
                y_labels = []
                y_info_list = []
                all_offset_y_min = []  # 각 그래프의 시작 위치 저장
                all_file_names = []    # 각 그래프의 파일명 저장
                all_offset_y_pos = []  # 각 그래프의 대표 y 위치 저장 리스트
                all_offset_y_start = []  # 시작 위치 저장 (기존)
                all_offset_y_end = []    # 마지막 위치 저장 (추가)\
                first_graph_y = None
                last_graph_y = None
                max_labels = 5
                total_files = len(sorted_items)
                label_indices = list(range(total_files)) if total_files <= max_labels else \
                                np.linspace(0, total_files - 1, max_labels, dtype=int)
                                
                yticks_for_labels = []
                labels_for_ticks = []

                for draw_idx, (item, timestamp) in enumerate((sorted_items)) :
                        file_name = item.text()
                        file_path = os.path.join(self.directory_path, file_name)
                        data, record_length = self.load_file_data(file_path)
                        dt, first_start_time, duration, rest_time, repetition, channel_info, iepe, b_sensitivity, sensitivity = [None] * 9

                        # ✅ 개별 파일의 샘플링 레이트 읽기
                        try:
                                with open(file_path, 'r') as file:
                                        for line in file:
                                                if "D.Sampling Freq. " in line:
                                                        sampling_rate_str = line.split(":")[1].strip()
                                                        sampling_rate = float(sampling_rate_str.replace("Hz","").strip())
                                                elif "Starting Time" in line:
                                                        if first_start_time is None:  # ✅ 처음 등장하는 start_time만 저장
                                                                first_start_time = line.split(":")[1].strip()
                                                elif "Record Length" in line:
                                                        duration = line.split(":")[1].strip().split()[0]  # 숫자만 추출
                                                elif "b.Sensitivity" in line and b_sensitivity is None:
                                                        b_sensitivity = line.split(":")[1].strip().split()[0]
                                                elif "Sensitivity" in line:
                                                        sensitivity = line.split(":")[1].strip()
                        except Exception as e:
                                print(f"⚠ {file_name} - 메타데이터 파싱 오류: {e}")


                        if data is None or len(data) == 0:
                                self.progress_dialog.label.setText(f"{file_name} - 데이터 없음. 건너뜀.")
                                self.progress_dialog.update_progress(draw_idx + 1)
                                #print(f"❌ {file_name} - No valid data.")
                                continue
                        self.progress_dialog.label.setText(f"{file_name} 처리 중...")  # ✅ 현재 파일 표시

                        try:
                                file_timestamp = self.extract_timestamp_from_filename(file_name)
                                name_only = os.path.splitext(file_name)[0]  # 확장자 제거
                                parts = name_only.split("_")
                                if len(parts) >= 3:
                                        date = parts[0]
                                        time = parts[1]
                                        rest = '_'.join(parts[2:])
                                        new_name = f"{date}\n{time}_{rest}"
                                x_labels.append(new_name)  # "날짜_시간" 포맷으로 저장
                        except Exception as e:
                                file_timestamp = None


                        # 첫 번째 파일에서 start_time 설정
                        if start_time is None:
                                start_time = file_timestamp if file_timestamp else datetime.datetime.now()

                        if file_timestamp:
                                time_offset = (file_timestamp - start_time).total_seconds()
                        else:
                                time_offset += offset_step

                        # 샘플링 레이트 추출
                        
                        if sampling_rate is None or sampling_rate <= 0:
                                return

                        if delta_f is None or delta_f <= 0:
                                return

                        if not isinstance(data, np.ndarray) or len(data) == 0:
                                return
                        # ✅ 숫자만 추출하여 float 변환
                        def extract_numeric_value(s):
                                if s is None:  # ← 추가!
                                        return None
                                match = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
                                return float(match.group()) if match else None
                        # b.Sensitivity와 Sensitivity 존재 시 계산
                        try:
                                if b_sensitivity is not None and sensitivity is not None:
                                        b_sens = extract_numeric_value(b_sensitivity)
                                        sens = extract_numeric_value(sensitivity)

                                        if b_sens is not None and sens is not None and sens != 0:
                                                scaled_data = (b_sens / sens) * data
                                                perf_logger.log_info(f"✓ {file_name}: 민감도 보정 적용")
                                        else:
                                                scaled_data = data
                                                perf_logger.log_warning(f"⚠️ {file_name}: 민감도 값 이상")
                                else:
                                        scaled_data = data
                                        perf_logger.log_info(f"ℹ️ {file_name}: b.Sensitivity 없음, 원본 사용")
                        except Exception as e:
                                scaled_data = data
                                perf_logger.log_warning(f"⚠️ {file_name}: 민감도 보정 오류, 원본 사용")



                        if sampling_rate / delta_f > np.atleast_2d(data).shape[0]:
                                        text = record_length
                                        duration2 = text
                                        
                                        
                                        duration = float(duration2)
                                        hz_value = round(1 / duration + 0.01, 2)  # 소수점 6자리까지 반올림

                                        delta_f = hz_value
                                        QMessageBox.critical(None, "안내", "delt_f의 입력값이 너무 작아 "f"{hz_value}""로 치환 되었습니다!")


                        # FFT 계산
                        type_flag = 2
                        try:
                                w, f, P, ACF, ECF, rms_w, Sxx = self.mdl_FFT_N(
                                        type_flag, sampling_rate, scaled_data, delta_f, overlap,
                                        1 if window_type == "hanning" else 2 if window_type == "flattop" else 0, 1, view_type, 0
                                )
                        except Exception as e:
                                #print(f"❌ FFT 계산 실패: {e}")
                                continue


                        P_magnitude = np.round(np.mean(ACF * np.abs(P), axis=1),4) # shape: (주파수 점 개수,)
                        fixed_ymin, fixed_ymax = 0, np.max(P_magnitude)
                        fixed_xmin, fixed_xmax = 0, np.max(f)

                        # Step 1: x축 필터 먼저 적용
                        mask_freq = np.ones_like(f, dtype=bool)
                        if x_min is not None and x_max is not None:
                                mask_freq = (f >= x_min) & (f <= x_max)
                                
                                
                                

                        f_filtered = f[mask_freq]
                        p_filtered = P_magnitude[mask_freq]
                        
                        # ✅ 2. x 정규화 (그래프 시각 균등하게)
                        if x_min is not None and x_max is not None:
                                global_xmin, global_xmax = x_min, x_max
                                
                        else:
                                global_xmin, global_xmax = np.min(f), np.max(f)

                        x_range = global_xmax - global_xmin
                        f_normalized = (f_filtered - global_xmin) / x_range  # 0~1 정규화
                        
                        x_scale = 530  # 고정된 그래프 폭 (가로길이)
                        
                        
                        

                        # ✅ 전체 스케일 기준 정규화
                        global_max = np.max(p_filtered)  # 전체 y값의 최대값 기준으로 정규화

                        if z_min is not None and z_max is not None and z_max > z_min:
                                y_clipped = p_filtered / global_max  # 그래프엔 필터된 y 사용, 기준은 전체 max
                                y_normalized = [(val - z_min) / (z_max - z_min) for val in y_clipped]
                                
                                
                                
                        else:
                                y_normalized = p_filtered / global_max  # fallback 정규화
                        

                        scale_factor = (fixed_ymax  - fixed_ymin) * 1  # 전체 높이의 90%를 진폭 최대치로
                        y_scaled = [val * scale_factor for val in y_normalized]

                        # 위치 오프셋 (사용자 각도 유지)
                        base_x = draw_idx * dx
                        base_y = draw_idx * dy
                        offset_x = [val * x_scale + base_x for val in f_normalized]
                        offset_y = [yi + base_y for yi in y_scaled]
                        start_y = min(offset_y)
                        all_offset_y_min.append(start_y)
                        all_file_names.append(file_name)
                        

                        # 첫 번째 그래프에 한해서만 tick 표시
                        if draw_idx == 0:

                                # ✅ X축 tick: 첫 그래프 시작/끝 위치에 x_min, x_max 표시
                                if x_min is not None and x_max is not None and len(offset_x) >= 2:
                                        # x_min과 x_max 사이에 7개의 tick 위치 생성 (시작, 끝 포함)
                                        xticks = np.linspace(offset_x[0], offset_x[-1], 7)  
                                        # 눈금에 대응하는 값: x_min ~ x_max 사이를 균등 분할
                                        xtick_labels = np.linspace(x_min, x_max, 7)
                                        
                                        self.waterfall_ax.set_xticks(xticks)
                                        self.waterfall_ax.set_xticklabels([f"{val:.1f}" for val in xtick_labels])
                                if draw_idx == 0 and z_min is not None and z_max is not None and len(offset_y) >= 2:
                                        self.waterfall_ax.yaxis.set_ticks_position('left')

                                        ymin = min(offset_y)
                                        ymax = max(offset_y)
                                        yticks = np.linspace(ymin, ymax, 7)
                                        ytick_labels = np.linspace(z_min, z_max, 7)

                                        self.waterfall_ax.set_yticks(yticks)
                                        self.waterfall_ax.set_yticklabels([f"{val:.4f}" for val in ytick_labels], fontsize=7)
                                        self.waterfall_ax.tick_params(axis='y', labelleft=True)
                                        # ✅ 중요: y축 범위 고정 (그래프 기준으로)
                                        self.waterfall_ax.set_ylim(0, 150)  # <- 핵심!
                                        
                                        
                        all_offset_y_start.append(min(offset_y))
                        all_offset_y_end.append(offset_y[-1])  # 마지막 y 위치 저장
                        
                        start_y = min(offset_y)

                        # # ✅ draw_idx가 표시 대상일 때만 텍스트 추가
                        # if draw_idx in label_indices:
                        #         label_text = file_name.replace(".txt", "")  # .txt 제거
                        #         self.waterfall_ax.text(offset_x[-1] + 20, np.mean(offset_y), label_text,
                        #                         fontsize=8, va='center', ha='left')
                        
                        if draw_idx in label_indices:
                                center_y = np.min(offset_y)
                                # ✅ .txt 제거 및 두 줄로 분할
                                base_name = file_name.replace(".txt", "")
                                parts = base_name.split("_")
                                if len(parts) >= 2:
                                        label_text = parts[0] + "_" + parts[1] + "\n" + "_".join(parts[2:])
                                else:
                                        label_text = base_name  # fallback

                                yticks_for_labels.append(center_y)
                                labels_for_ticks.append(label_text)

                        # # 그리기
                        self.waterfall_ax.plot(offset_x, offset_y, alpha=0.6, label=file_name)
                        self.waterfall_ax.set_aspect('auto')
                        

                        # 전체 개수
                        total_files = len(sorted_items)

                        # 최대 5개 눈금만 표시
                        max_labels = 5
                        if total_files <= max_labels:
                                label_indices = list(range(total_files))
                        else:
                                label_indices = np.linspace(0, total_files - 1, max_labels, dtype=int)

                        
                        # 그래프 시작 위치
                        start_point = (offset_x[0], offset_y[0])
                        # 첫 번째 그래프 시작 위치 저장
                        if first_start is None:
                                first_start = start_point

                        # 매 반복마다 마지막 그래프의 시작 위치로 갱신
                        last_start = start_point

                        time_stamps.append(file_timestamp if file_timestamp else start_time)

                        

                        # 다음 파일은 한 줄 위로
                        time_offset += offset_step 
                        self.progress_dialog.update_progress(draw_idx + 1)
                        
                # ✅ 오른쪽 y축 설정 (tick 숨기고 텍스트만 표시)
                ax_right = self.waterfall_ax.twinx()
                ax_right.set_ylim(self.waterfall_ax.get_ylim())

                # ytick은 숨김 처리 (혹은 최소화)
                ax_right.set_yticks([])
                ax_right.tick_params(right=False)

                # ✅ 텍스트를 오른쪽 y축 바깥에 수직으로 정렬해서 그리기
                for y, label in zip(yticks_for_labels, labels_for_ticks):
                        ax_right.text(1.02, y, label, transform=ax_right.get_yaxis_transform(),
                                        fontsize=7, va='center', ha='left')


                if time_offset == 0:
                        #print("❌ No valid data to plot.")
                        return
                
                self.progress_dialog.close()

                # 축 설정
                view_type_map = {
                        1: "ACC",
                        2: "VEL",
                        3: "DIS"
                        }

                view_type_code = self.select_pytpe2.currentData()
                view_type = view_type_map.get(view_type_code, "ACC")  # 기본값은 "ACC"로 설정

                labels = {
                                "ACC": "Vibration Acceleration \n (m/s^2, RMS)",
                        "VEL": "Vibration Velocity \n (mm/s, RMS)",
                        "DIS": "Vibration Displacement \n (μm , RMS)"
                        }
                zlabel = labels.get(view_type, "RMS Vibration (mm/s, RMS)")
                self.waterfall_ax.set_ylabel(zlabel, fontsize=7, fontname='Nanum Gothic')


                self.waterfall_ax.set_xlabel("Frequency (Hz)", fontsize = 7)  # 또는 "Frequency (Hz)"

                self.waterfall_figure.patch.set_facecolor('white')  # Figure 배경 흰색으로 설정
                self.waterfall_ax.set_facecolor('white')  # Axes 배경 흰색으로 설정

                self.waterfall_canvas.flush_events()  # 기존 그래픽 삭제
                self.waterfall_ax.tick_params(axis='y', labelrotation=0)
                self.waterfall_ax.tick_params(axis='x', labelsize = 7)
                self.waterfall_ax.tick_params(axis='y', labelsize = 7)

                self.original_xlim = self.waterfall_ax.get_xlim()
                self.original_ylim = self.waterfall_ax.get_ylim()

                # if first_start and last_start:
                #         x0, y0 = first_start
                #         x1, y1 = last_start
                        

                #         # 기준 벡터
                #         dx = x1 - x0
                #         dy = y1 - y0

                #         # x축 전체 범위
                #         x_min, x_max = self.waterfall_ax.get_xlim()
                #         total_x_range = x_max - x_min

                #         # 원하는 전체 선 수 (기준선 + 추가 화살표)
                #         total_lines = 10

                #         # 🔹 간격 자동 계산 (기준선 뒤로 균등 분포)
                #         spacing = total_x_range / (total_lines + 2)

                #         # 기준선 먼저 그림
                #         self.waterfall_ax.annotate(
                #                 '',
                #                 xy=(x1, y1),
                #                 xytext=(x0, y0),
                #                 arrowprops=dict(arrowstyle='-', lw=1.5, alpha=0.3),
                #                 clip_on=True
                #         )

                #         # 추가 화살표 반복
                #         for i in range(1, total_lines):
                #                 x_offset = i * spacing
                #                 new_x0 = x0 + x_offset
                #                 new_x1 = x1 + x_offset
                #                 new_y0 = y0
                #                 new_y1 = y1 

                #                 # 범위를 초과하지 않도록 체크
                #                 if new_x1 > (x_max-1):
                #                         break

                #                 self.waterfall_ax.annotate(
                #                 '',
                #                 xy=(new_x1, new_y1),
                #                 xytext=(new_x0, new_y0),
                #                 arrowprops=dict(arrowstyle='-', lw=1.5, alpha=0.3),
                #                 clip_on=True
                #                 )
                if first_start and last_start:
                        x0, y0 = first_start
                        x1, y1 = last_start

                        # x축 전체 범위
                        x_min, x_max = self.waterfall_ax.get_xlim()
                        total_x_range = x_max - x_min
                        total_lines = 10
                        spacing = total_x_range / (total_lines + 2)

                        # ✅ y=0에서 시작하지만 기울기 유지한 x0 계산
                        if y1 != y0:
                                adjusted_x0 = x1 - ((x1 - x0) * y1 / (y1 - y0))
                        else:
                                adjusted_x0 = x0  # 수평선일 경우

                        adjusted_y0 = 0  # 시작 y는 항상 0

                        # 기준선 그리기
                        self.waterfall_ax.annotate(
                                '',
                                xy=(x1, y1),
                                xytext=(adjusted_x0, adjusted_y0),
                                arrowprops=dict(arrowstyle='-', lw=1.5, alpha=0.3),
                                clip_on=True
                        )

                        for i in range(1, total_lines):
                                x_offset = i * spacing

                                new_x0 = adjusted_x0 + x_offset
                                new_x1 = x1 + x_offset
                                new_y0 = adjusted_y0
                                new_y1 = y1

                                if new_x1 > (x_max - 1):
                                        break

                                self.waterfall_ax.annotate(
                                '',
                                xy=(new_x1, new_y1),
                                xytext=(new_x0, new_y0),
                                arrowprops=dict(arrowstyle='-', lw=1.5, alpha=0.3),
                                clip_on=True
                                )

                
                self.waterfall_canvas.draw()

        def show_full_view_x(self):
                try:
                        x_min = None
                        x_max = None
                        self.current_x_min = x_min
                        self.current_x_max = x_max
                        

                        
                        
                        self.auto_scale_x_2.setChecked(True)

                        # x 범위로 슬라이싱해서 다시 플로팅
                        self.plot_waterfall_spectrum(x_min=x_min, x_max=x_max, z_min=self.current_z_min, z_max=self.current_z_max)

                except ValueError:
                        print("")

        def show_full_view_z(self):
                try:
                        z_min = None
                        z_max = None
                        self.current_z_min = z_min
                        self.current_z_max = z_max
                        
                        
                        self.auto_scale_z.setChecked(True)

                        # x 범위로 슬라이싱해서 다시 플로팅
                        self.plot_waterfall_spectrum(x_min=self.current_x_min, x_max=self.current_x_max, z_min=z_min, z_max=z_max)

                except ValueError:
                        print("")

        def set_x_axis2(self):
                try:
                        x_min = float(self.x_min_input2.text())
                        x_max = float(self.x_max_input2.text())
                        if x_min >= x_max:
                                raise ValueError

                        self.current_x_min = x_min
                        self.current_x_max = x_max
                        self.auto_scale_x_2.setChecked(False)

                        self.plot_waterfall_spectrum(
                        x_min=self.current_x_min,
                        x_max=self.current_x_max,
                        z_min=self.current_z_min,
                        z_max=self.current_z_max
                        )

                except ValueError:
                        print("")

        def set_z_axis(self):
                try:
                        z_min = float(self.z_min_input.text())
                        z_max = float(self.z_max_input.text())
                        if z_min >= z_max:
                                raise ValueError

                        self.current_z_min = z_min
                        self.current_z_max = z_max
                        self.auto_scale_z.setChecked(False)
                        

                        # self.waterfall_ax.set_ylim(z_min, z_max)
                        # self.waterfall_ax.set_aspect('auto')  # 자동 비율
                        # self.waterfall_canvas.draw()

                        self.plot_waterfall_spectrum(
                        x_min=self.current_x_min,
                        x_max=self.current_x_max,
                        z_min=self.current_z_min,
                        z_max=self.current_z_max
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

                for marker in self.trend_markers:
                                marker.remove()
                self.trend_markers.clear()

                for annotation in self.trend_annotations:
                        annotation.remove()
                self.trend_annotations.clear()

                for filename in self.trend_marker_filenames:
                         self.remove_marker_filename_from_list(filename)
                self.trend_marker_filenames.clear()

                """단일 데이터에 대해 RMS 값을 계산하고 3D 트렌드 스펙트럼 그래프 그리기"""

                # 선택된 파일 확인

                selected_items = self.Querry_list3.selectedItems()
                time_stamps = []  # 파일별 시간 저장 리스트
                view_type = {}
                selected_channels = []
                channel = []
                if self.checkBox_13.isChecked(): selected_channels.append("1")
                if self.checkBox_14.isChecked(): selected_channels.append("2")
                if self.checkBox_15.isChecked(): selected_channels.append("3")
                if self.checkBox_16.isChecked(): selected_channels.append("4")
                if self.checkBox_17.isChecked(): selected_channels.append("5")
                if self.checkBox_18.isChecked(): selected_channels.append("6")

                

                

                if not selected_items:
                        QMessageBox.critical(None, "오류", "파일을 선택하세요")
                        return

                # 입력값 가져오기 (band limit 처리)
                try:
                        band_min = float(self.freq_range_inputmin.text().strip())
                        band_max = float(self.freq_range_inputmax.text().strip())
                        if not band_min :
                                raise ValueError("Band_min 값이 입력되지 않았습니다.")
                        if not band_max:
                                raise ValueError("Band_max 값이 입력되지 않았습니다.")

                except ValueError as e:
                        QMessageBox.critical(None, "입력 오류", str(e))
                        return

                # 입력값 가져오기 (Hz 및 overlap)
                # ✅ Δf 값 읽기
                try:
                        delta_f_text = self.Hz_3.toPlainText()
                        if not delta_f_text:
                                raise ValueError("Δf 값이 입력되지 않았습니다.")
                        delta_f = float(delta_f_text)
                except ValueError as e:
                        QMessageBox.critical(None, "입력 오류", str(e))
                        return

                # ✅ 오버랩 비율 읽기
                overlap_str = self.Overlap_Factor_3.currentText()
                try:
                        if not overlap_str:
                                raise ValueError("오버랩 비율이 선택되지 않았습니다.")
                        overlap = float(overlap_str.replace('%', ''))
                except ValueError as e:
                        QMessageBox.critical(None, "입력 오류", str(e))
                        return

                # ✅ 윈도우 함수 읽기
                window_type = self.Function_3.currentText()
                if not window_type:
                        QMessageBox.critical(None, "입력 오류", "윈도우 함수가 선택되지 않았습니다.")
                        return
                window_type = window_type.lower()

                # ✅ View Type 읽기
                view_type = self.select_pytpe3.currentData()
                if view_type is None:
                        QMessageBox.critical(None, "입력 오류", "View Type이 선택되지 않았습니다.")
                        return
                
                self.progress_dialog = ProgressDialog(len(selected_items), self.main_window)
                self.progress_dialog.setWindowModality(Qt.WindowModal)
                self.progress_dialog.show()

                # 그래프 초기화
                self.trend_ax.clear()
                self.trend_ax.set_title("Overall RMS Trend", fontsize=7, fontname='Nanum Gothic')

                # 초기 시간 설정
                start_time = None
                offset_step = 20  # y축 간격

                # 시간 오프셋 초기화
                time_offset = 0
                x_labels = []
                x_data = []
                y_data = []
                x_data_2 = []
                y_data_2 = []
                self.metadata_dict = {}
                channel_data = {}  # 채널별 x, y 데이터 저장
                file_name_used = []
                sampling_rates = {}
                channel_infos = []
                trend_x_data = []
                first_start_time = None
                self.data_dict = {}  # 파일별 (x_data, y_data)
                

                # 단일 데이터 처리 (여러 파일에 대해 반복)
                for idx, item in enumerate (selected_items):
                        file_name = item.text()
                        file_path = os.path.join(self.directory_path, file_name)
                        data, record_length = self.load_file_data(file_path)
                        data2, record_length = self.load_file_data(file_path)

                        if data is None or len(data) == 0:
                                self.progress_dialog.label.setText(f"{file_name} - 데이터 없음. 건너뜀.")
                                self.progress_dialog.update_progress(idx + 1)
                                #print(f"❌ {file_name} - No valid data.")
                                continue
                        self.progress_dialog.label.setText(f"{file_name} 처리 중...")  # ✅ 현재 파일 표시
                         # 초기값 설정
                        # sampling_rate = 10240.0
                        dt, first_start_time, duration, rest_time, repetition, channel_info, iepe, b_sensitivity, sensitivity = [None] * 9

                        # 파일명에서 시간 추출
                        try:
                                file_timestamp = self.extract_timestamp_from_filename(file_name)
                                x_labels.append(file_timestamp.strftime("%Y-%m-%d""\n""%H:%M:%S"))  # "날짜_시간" 포맷으로 저장
                        except Exception as e:
                                #print(f"⚠ {file_name} - 시간 추출 실패: {e}")
                                x_labels.append(file_name)

                        channel_num = file_name.split("_")[-1].replace(".txt", "")
                        if channel_num not in channel_data:
                                channel_data[channel_num] = {"x": [], "y": [], "label": []}
                        x_index = idx

                        # 첫 번째 파일에서 start_time 설정
                        if start_time is None:
                                start_time = file_timestamp if file_timestamp else datetime.datetime.now()

                        if file_timestamp:
                                time_offset = (file_timestamp - start_time).total_seconds()
                        else:
                                #print(f"❌ {file_name} - 시간 정보가 없어 기본값 사용.")
                                time_offset += offset_step

                        # 파일별 샘플링 레이트 개별 적용 (self.sampling_rate 사용 X)
                        # ✅ 개별 파일의 샘플링 레이트 읽기
                        try:
                                with open(file_path, 'r') as file:
                                        for line in file:
                                                if "D.Sampling Freq. " in line:
                                                        sampling_rate_str = line.split(":")[1].strip()
                                                        sampling_rate = float(sampling_rate_str.replace("Hz","").strip())
                                                elif "Time Resolution(dt)" in line:
                                                        dt = line.split(":")[1].strip()
                                                elif "Starting Time" in line:
                                                        if first_start_time is None:  # ✅ 처음 등장하는 start_time만 저장
                                                                first_start_time = line.split(":")[1].strip()
                                                elif "Record Length" in line:
                                                        duration = line.split(":")[1].strip().split()[0]  # 숫자만 추출
                                                elif "Rest time" in line:
                                                        rest_time = line.split(":")[1].strip().split()[0]
                                                elif "Repetition" in line:
                                                        repetition = line.split(":")[1].strip()
                                                elif "Channel" in line:
                                                        channel_info = line.split(":")[1].strip()
                                                elif "IEPE enable" in line:
                                                        iepe = line.split(":")[1].strip()
                                                elif "B.Sensitivity" in line:   
                                                        b_sensitivity = line.split(":")[1].strip()                                                
                                                elif "Sensitivity" in line:
                                                        sensitivity = line.split(":")[1].strip()
                        except Exception as e:
                                print(f"⚠ {file_name} - 메타데이터 파싱 오류: {e}")
                        #print(f"{file_name} - sampling rate: {sampling_rate}")
                        sampling_rates[file_name] = sampling_rate  # 딕셔너리에 저장
                        self.metadata_dict[file_name] = {
                                "sampling_rate": sampling_rate,
                                "file_path": file_path,
                                "window_type": window_type,
                                "overlap": overlap,
                                "delta_f": delta_f,
                                "dt": dt,
                                "start_time": first_start_time,
                                "duration": duration,
                                "rest_time": rest_time,
                                "repetition": repetition,
                                "iepe": iepe,
                                "sensitivity": sensitivity,
                                "b.Sensitivity": b_sensitivity,
                                "view_type" : view_type,
                        }

                        if sampling_rate / delta_f > np.atleast_2d(data).shape[0]:
                                        text = record_length
                                        duration2 = text
                                        
                                        
                                        duration = float(duration2)
                                        hz_value = round(1 / duration + 0.01, 2)  # 소수점 6자리까지 반올림

                                        delta_f = hz_value
                                        QMessageBox.critical(None, "안내", "delt_f의 입력값이 너무 작아 "f"{hz_value}""로 치환 되었습니다!")
                        # ✅ 숫자만 추출하여 float 변환
                        def extract_numeric_value(s):
                                match = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
                                return float(match.group()) if match else None
                        # b.Sensitivity와 Sensitivity 존재 시 계산
                        if b_sensitivity and sensitivity:
                                b_sens = extract_numeric_value(b_sensitivity) #이전
                                sens = extract_numeric_value(sensitivity) # 새로입력
                                if b_sens is not None and sens is not None and sens != 0:
                                        scaled_data = (b_sens / sens) * data
                                else:
                                        scaled_data = data
                        else:
                                scaled_data = data

                        # FFT 및 RMS 계산
                        type_flag = 2
                        try:
                                w, f, P, ACF, ECF, rms_w, Sxx = self.mdl_FFT_N(type_flag, sampling_rate, scaled_data, delta_f, overlap, 1 if window_type == "hanning" else 2 if window_type == "flattop" else 0, 1, view_type, 0)

                                if np.all(np.abs(P) == 0) or np.isnan(np.abs(P)).any():
                                                print(f"❌ {file_name} - FFT 결과가 비정상적입니다.")
                                                continue
                                

                        except Exception as e:
                                print(f"❌ FFT 계산 실패: {e}")
                                continue
                        
                        P_q= np.abs(P)
                        

                        time_stamps.append(file_timestamp if file_timestamp else start_time)
                        channel_infos.append(file_name.split("_")[0])  # 파일 이름에서 채널 정보 추출
                        time = np.arange(len(data)) / sampling_rate
                        P = P
                        ACF = ACF
                        freq = f
                        # band limit을 기준으로 RMS 값 계산
                        band_min_idx = np.argmin(np.abs(f - band_min))
                        band_max_idx = np.argmin(np.abs(f - band_max))
                        P_band = P[band_min_idx:band_max_idx+1]
                        

                        # RMS 계산
                        rms_value = np.sqrt(np.sum(P_band**2)) * ECF

                        if file_timestamp:
                                x_value = self.extract_timestamp_from_filename(file_name)
                                x_value_2 = file_name.rsplit('.', 1)[0]
                        else:
                                x_value = start_time.timestamp() + offset_step * idx

                        channel_data[channel_num]["x"].append(x_value)
                        channel_data[channel_num]["y"].append(rms_value)
                        channel_data[channel_num]["label"].append(file_name)


                        x_data.append(x_value)
                        trend_x_data.append(x_value)
                        y_data.append(rms_value)
                        x_data_2.append(x_value_2)
                        y_data_2.append(rms_value)


                        colors = ["r", "g", "b", "c", "m", "y"]
                        for i, (ch, data) in enumerate(channel_data.items()):
                                self.trend_ax.plot(data["x"], data["y"], label=f"Channel {ch}", color=colors[i % len(colors)], marker='o', markersize=2, linewidth=0.5)

                        

                        

                        self.trend_ax.set_facecolor('white')
                        handles, labels = self.trend_ax.get_legend_handles_labels()
                        unique = dict()
                        for h, l in zip(handles, labels):
                                if l not in unique:
                                        unique[l] = h
                        self.trend_ax.legend(unique.values(), unique.keys(), fontsize = 7)



                        


                        self.y_data = rms_value
                        file_name_used.append(file_name)
                        self.data_dict[file_name] = (idx, rms_value)
                        file_names = [item.text() for item in selected_items]
                        rms_values = y_data  # 위에서 append된 RMS 값들
                        self.progress_dialog.update_progress(idx + 1)
                        self.save_trend_data_per_file(file_name, rms_value, delta_f, window_type, overlap, band_min, band_max, channel, sampling_rate, dt, first_start_time, duration, rest_time, repetition, iepe, sensitivity, b_sensitivity, channel_num, view_type, time, data2, freq, P, ACF)
                        
                if not selected_items:
                        #print("❌ No valid data to plot.")
                        return
                self.progress_dialog.close()
                
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
                self.trend_ax.set_xticklabels(tick_labels, rotation=0, ha="right", fontsize=7, fontname='Nanum Gothic')
                

                # X축 눈금 (시간 축 설정)
                # self.trend_ax.set_xlabel("Time Offset (sec)")
                view_type_map = {
                        1: "ACC",
                        2: "VEL",
                        3: "DIS"
                        }

                view_type_code = self.select_pytpe3.currentData()
                view_type_label = view_type_map.get(view_type_code, "ACC")  # 기본값은 "ACC"로 설정

                labels = {
                                "ACC": "Vibration Acceleration \n (m/s^2, RMS)",
                                "VEL": "Vibration Velocity \n (mm/s, RMS)",
                                "DIS": "Vibration Displacement \n (μm , RMS)"
                        }
                ylabel = labels.get(view_type_label, "Vibration (mm/s, RMS)")
                self.trend_ax.set_xlabel("data&time", fontsize=7, fontname='Nanum Gothic')
                self.trend_ax.set_ylabel(ylabel, fontsize=7, fontname='Nanum Gothic')
                self.trend_ax.set_facecolor('white')


                # 그래프 갱신
                self.trend_canvas.flush_events()
                # self.trend_ax.set_position([0.1, 0.1, 0.7, 0.8])  # [left, bottom, width, height] 형식으로 설정
                self.trend_ax.grid(True, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
                self.trend_ax.tick_params(axis='x', labelsize = 7)
                self.trend_ax.tick_params(axis='y', labelsize = 7)
                
                
                self.trend_canvas.draw()

                view_type_map = {
                1: "ACC",
                2: "VEL",
                3: "DIS"
                }
                if isinstance(view_type, list) and view_type:
                        view_type_key = view_type[0]
                else:
                        view_type_key = view_type
                view_type_str = view_type_map.get(view_type_key, "UNKNOWN")  # 기본값은 "UNKNOWN"
                
                # 마우스, 키보드 이벤트 연결
                self.cid_move = self.trend_canvas.mpl_connect("motion_notify_event", self.on_move2)
                self.cid_click = self.trend_canvas.mpl_connect("button_press_event", self.on_click2)
                self.cid_key = self.trend_canvas.mpl_connect("key_press_event", self.on_key_press2)

                self.hover_dot = self.trend_ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
                # self.trend_canvas.mpl_connect("button_press_event", self.on_mouse_click2)
                self.trend_file_names = [item.text() for item in selected_items]
                self.file_name_used = file_name_used
                self.trend_rms_values = y_data
                self.trend_delta_f = delta_f
                self.trend_window = window_type
                self.trend_overlap = overlap
                self.trend_band_min = band_min
                self.trend_band_max = band_max
                self.channel = channel
                self.sample_rate = sampling_rate
                self.dt = dt
                self.start_time = first_start_time
                self.Duration = duration
                self.Rest_time = rest_time
                self.repetition = repetition
                self.IEPE = iepe
                self.Sensitivity = sensitivity
                self.b_Sensitivity = b_sensitivity
                self.channel_infos = channel_infos
                self.trend_x_value = trend_x_data
                self.view_type = view_type_str

        def load_trend_data_and_plot(self): #잠시대기
                selected_items = self.Querry_list3.selectedItems()
                if not selected_items:
                        print("❌ 선택된 항목이 없습니다.")
                        return

                trend_x_data = []
                self.trend_data = []           # y 값 (RMS 값)
                self.trend_file_names = []     # x 라벨 (파일 이름)
                self.channel_num = []           # 채널 번호
                self.trend_markers_load = []        # 마커 저장용
                self.trend_annotations_load = []
                self.trend_marker_filenames_load  = []  # 주석 저장용
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
                        "overlap": float(self.Overlap_Factor_3.currentText().replace('%', '').strip()) if self.Overlap_Factor_3.currentText().strip() else 50.0
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
                self.trend_ax.set_title("Overall RMS Trend \n (Loaded Data)", fontsize=7, fontname='Nanum Gothic')
                colors = ["r", "g", "b", "c", "m", "y"]

                for i, (ch, data) in enumerate(channel_data.items()):
                        self.trend_ax.plot(data["x_data"], data["y_data"], label=f"Channel {ch}", color=colors[i % len(colors)], marker='o',  markersize=3, linewidth=1.5)

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
                self.trend_ax.set_xticklabels(tick_labels, rotation=0, ha="right", fontsize=7, fontname='Nanum Gothic')
                self.trend_ax.set_xlabel("data&time", fontsize=7, fontname='Nanum Gothic')
                

                

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
                self.trend_ax.set_ylabel(ylabel, fontsize=7, fontname='Nanum Gothic')
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
                self.trend_ax.tick_params(axis='x', labelsize = 7) 
                self.trend_ax.tick_params(axis='y', labelsize = 7)
                self.trend_canvas.draw()
                self.cid_move = self.trend_canvas.mpl_connect("motion_notify_event", self.on_move_load)
                self.cid_click = self.trend_canvas.mpl_connect("button_press_event", self.on_click_load)
                self.cid_key = self.trend_canvas.mpl_connect("key_press_event", self.on_key_press_load)

                self.hover_dot_load = self.trend_ax.plot([], [], 'ko', markersize=3, alpha=0.5)[0]

                self.trend_x_value = trend_x_data
                self.trend_rms_values = y_data

        def save_trend_data_per_file(self,file_name, rms_value, delta_f, window_type, overlap, band_min, band_max, channel, sampling_rate, dt, start_time, duration, rest_time, repetition, iepe, sensitivity, b_sensitivity, channel_num, view_type, time, data2, freq, P, ACF):
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
                        dt = self.dt,
                        start_time = self.start_time,
                        duration = self.Duration,
                        rest_time = self.Rest_time,
                        repetition = self.repetition,
                        iepe = self.IEPE,
                        sensitivity = self.Sensitivity,
                        b_sensitivity = self.b_Sensitivity,
                        channel_infos = self.channel_infos,
                        view_type= self.view_type,
                        
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

                # hover_dot 위치를 가져와서 마커로 고정
                x, y = self.hover_dot.get_data()

                

                if x and y:
                        self.add_marker2(x,y)

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
                """마커 점과 텍스트를 동시에 추가"""
                # 가장 가까운 데이터 포인트 찾기
                min_distance  = float('inf')
                closest_index = -1
                for i, (data_x, data_y) in enumerate(zip(self.trend_x_value, self.trend_rms_values)):
                        # x가 datetime일 경우 float로 변환
                        if isinstance(data_x, datetime):
                                data_x_float = mdates.date2num(data_x)
                        else:
                                data_x_float = data_x

                        dx = abs(x - data_x_float)
                        dy = abs(y - data_y)

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
                        self.trend_markers.append(marker)
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
                        self.trend_annotations.append(annotation)
                        
                        
                        
                        # marked_points 리스트에 추가 (파일명, x, y, 라벨 정보 저장)
                        #self.marked_points.append((file_name, x_val, y_val, label))
                       
                        self.trend_canvas.draw()

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
                        self.add_marker_load(x,y)

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
                min_distance  = float('inf')
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
                
                if dialog.exec_() == QtWidgets.QDialog.Accepted:
                        selected_files = dialog.get_selected_files()
                        # if selected_files:
                        #         self.save_selected_files(selected_files)

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
                view_type = {}
                """단일 데이터에 대해 RMS 값을 계산하고 3D 트렌드 스펙트럼 그래프 그리기"""

                # 선택된 파일 확인
                
                selected_items = self.Querry_list4.selectedItems()
                time_stamps = []  # 파일별 시간 저장 리스트

                selected_channels = []
                channel = []
                if self.checkBox_19.isChecked(): selected_channels.append("1")
                if self.checkBox_20.isChecked(): selected_channels.append("2")
                if self.checkBox_21.isChecked(): selected_channels.append("3")
                if self.checkBox_22.isChecked(): selected_channels.append("4")
                if self.checkBox_23.isChecked(): selected_channels.append("5")
                if self.checkBox_24.isChecked(): selected_channels.append("6")

                
                
                if not selected_items:
                        QMessageBox.critical(None, "오류", "파일을 선택하세요")
                        return
                

                # 입력값 가져오기 (band limit 처리)
                try:
                        band_min = float(self.freq_range_inputmin2.text().strip())
                        band_max = float(self.freq_range_inputmax2.text().strip())
                except ValueError as e:
                        QMessageBox.critical(None, "입력 오류", str(e))
                        return

                # ✅ Δf 값 읽기
                try:
                        delta_f_text = self.Hz_4.toPlainText()
                        if not delta_f_text:
                                raise ValueError("Δf 값이 입력되지 않았습니다.")
                        delta_f = float(delta_f_text)
                except ValueError as e:
                        QMessageBox.critical(None, "입력 오류", str(e))
                        return

                # ✅ 오버랩 비율 읽기
                overlap_str = self.Overlap_Factor_4.currentText()
                try:
                        if not overlap_str:
                                raise ValueError("오버랩 비율이 선택되지 않았습니다.")
                        overlap = float(overlap_str.replace('%', ''))
                except ValueError as e:
                        QMessageBox.critical(None, "입력 오류", str(e))
                        return

                # ✅ 윈도우 함수 읽기
                window_type = self.Function_4.currentText()
                if not window_type:
                        QMessageBox.critical(None, "입력 오류", "윈도우 함수가 선택되지 않았습니다.")
                        return
                window_type = window_type.lower()

                # ✅ View Type 읽기
                view_type = self.select_pytpe4.currentData()
                if view_type is None:
                        QMessageBox.critical(None, "입력 오류", "View Type이 선택되지 않았습니다.")
                        return
                self.progress_dialog = ProgressDialog(len(selected_items), self.main_window)
                self.progress_dialog.setWindowModality(Qt.WindowModal)
                self.progress_dialog.show()

                # 그래프 초기화
                self.peak_ax.clear()
                self.peak_ax.set_title("Band Peak Trend", fontsize=7, fontname='Nanum Gothic')

                # 초기 시간 설정
                start_time = None
                offset_step = 20  # y축 간격

                # 시간 오프셋 초기화
                time_offset = 0
                x_labels = []
                peak_values = []  # ✅ 여러 파일의 peak value 저장
                rms_values = []   # ✅ 여러 파일의 RMS 값 저장
                self.metadata_dict = {} 
                channel_data = {}  # 채널별 x, y 데이터 저장
                first_start_time = None
                peak_x_data = []
                x_data = []
                y_data = []

                # 단일 데이터 처리 (여러 파일에 대해 반복)
                for idx, item in enumerate (selected_items):
                        file_name = item.text()
                        file_path = os.path.join(self.directory_path, file_name)
                        data, record_length = self.load_file_data(file_path)

                        if data is None or len(data) == 0:
                                self.progress_dialog.label.setText(f"{file_name} - 데이터 없음. 건너뜀.")
                                self.progress_dialog.update_progress(idx + 1)
                                print(f"❌ {file_name} - No valid data.")
                                continue
                        self.progress_dialog.label.setText(f"{file_name} 처리 중...")  # ✅ 현재 파일 표시
                         # 초기값 설정
                        # sampling_rate = 10240.0
                        dt, first_start_time, duration, rest_time, repetition, channel_info, iepe, b_sensitivity, sensitivity = [None] * 9

                        # 파일명에서 시간 추출
                        try:
                                file_timestamp = self.extract_timestamp_from_filename(file_name)
                                x_labels.append(file_timestamp.strftime("%Y-%m-%d""\n""%H:%M:%S"))  # "날짜_시간" 포맷으로 저장
                        except Exception as e:
                                print(f"⚠ {file_name} - 시간 추출 실패: {e}")
                                x_labels.append(file_name)
                        x_index = idx

                        channel_num = file_name.split("_")[-1].replace(".txt", "")
                        if channel_num not in channel_data:
                                channel_data[channel_num] = {"x": [], "y": [], "label": []}

                        # 첫 번째 파일에서 start_time 설정
                        if start_time is None:
                                start_time = file_timestamp if file_timestamp else datetime.datetime.now()

                        if file_timestamp:
                                time_offset = (file_timestamp - start_time).total_seconds()
                        else:
                                #print(f"❌ {file_name} - 시간 정보가 없어 기본값 사용.")
                                time_offset += offset_step

                        # 파일별 샘플링 레이트 개별 적용 (self.sampling_rate 사용 X)
                        # ✅ 개별 파일의 샘플링 레이트 읽기
                        try:
                                with open(file_path, 'r') as file:
                                        for line in file:
                                                if "D.Sampling Freq. " in line:
                                                        sampling_rate_str = line.split(":")[1].strip()
                                                        sampling_rate = float(sampling_rate_str.replace("Hz","").strip())
                                                elif "Time Resolution" in line:
                                                        dt = line.split(":")[1].strip()
                                                elif "Starting time" in line:
                                                        if first_start_time is None:  # ✅ 처음 등장하는 start_time만 저장
                                                                first_start_time = line.split(":")[1].strip()
                                                elif "Record Length" in line:
                                                        duration = line.split(":")[1].strip().split()[0]  # 숫자만 추출
                                                elif "Rest time" in line:
                                                        rest_time = line.split(":")[1].strip().split()[0]
                                                elif "Repetition" in line:
                                                        repetition = line.split(":")[1].strip()
                                                elif "Channel" in line:
                                                        channel_info = line.split(":")[1].strip()
                                                elif "IEPE enable" in line:
                                                        iepe = line.split(":")[1].strip()
                                                elif "B.Sensitivity" in line:   
                                                        b_sensitivity = line.split(":")[1].strip()   
                                                elif "Sensitivity" in line:
                                                        sensitivity = line.split(":")[1].strip()
                        except Exception as e:
                                print(f"⚠ {file_name} - 메타데이터 파싱 오류: {e}")
                        self.metadata_dict[file_name] = {
                                "dt": dt,
                                "start_time": first_start_time,
                                "duration": duration,
                                "rest_time": rest_time,
                                "repetition": repetition,
                                "channel": channel_info,
                                "iepe": iepe,
                                "sensitivity": sensitivity,
                                "b.Sensitivity": b_sensitivity,
                                "view_type" : view_type,
                        }

                        if sampling_rate / delta_f > np.atleast_2d(data).shape[0]:
                                        text = record_length
                                        duration2 = text
                                        
                                        
                                        duration = float(duration2)
                                        hz_value = round(1 / duration + 0.01, 2)  # 소수점 6자리까지 반올림

                                        delta_f = hz_value
                                        QMessageBox.critical(None, "안내", "delt_f의 입력값이 너무 작아 "f"{hz_value}""로 치환 되었습니다!")

                         # ✅ 숫자만 추출하여 float 변환
                        def extract_numeric_value(s):
                                match = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
                                return float(match.group()) if match else None
                        # b.Sensitivity와 Sensitivity 존재 시 계산
                        if b_sensitivity and sensitivity:
                                b_sens = extract_numeric_value(b_sensitivity) #이전
                                sens = extract_numeric_value(sensitivity) # 새로입력
                                if b_sens is not None and sens is not None and sens != 0:
                                        scaled_data = (b_sens / sens) * data
                                else:
                                        scaled_data = data
                        else:
                                scaled_data = data

                        # FFT 및 RMS 계산
                        type_flag = 2
                        try:
                                w, f, P, ACF, ECF, rms_w, Sxx = self.mdl_FFT_N(
                                        type_flag, sampling_rate, scaled_data, delta_f, overlap,
                                        1 if window_type == "hanning" else 2 if window_type == "flattop" else 0, 1, view_type, 0
                                )
                        except Exception as e:
                                print(f"❌ FFT 계산 실패: {e}")
                                continue



                        time_stamps.append(file_timestamp if file_timestamp else start_time)
                        P = np.abs(P)       
                        # band limit을 기준으로 RMS 값 계산
                        band_min_idx = np.argmin(np.abs(f - band_min))
                        band_max_idx = np.argmin(np.abs(f - band_max))
                        P_band = P[band_min_idx:band_max_idx+1]

                        # 최대값 찾기
                        peak_value = np.max(ACF * P_band)
                        peak_freq = f[np.argmax(ACF * P_band)]

                        

                        # RMS 계산
                        rms_value = np.sqrt(np.sum(P_band**2)) * ECF
                        peak_values.append(peak_value)
                        rms_values.append(rms_value)

                        if file_timestamp:
                                x_value = self.extract_timestamp_from_filename(file_name)
                        else:
                                x_value = start_time.timestamp() + offset_step * idx

                        channel_data[channel_num]["x"].append(x_value)
                        channel_data[channel_num]["y"].append(peak_value)
                        channel_data[channel_num]["label"].append(file_name)

                        x_data.append(x_value)
                        peak_x_data.append(x_value)
                        y_data.append(peak_value)
                        
                        colors = ["r", "g", "b", "c", "m", "y"]
                        for i, (ch, data) in enumerate(channel_data.items()):
                                self.peak_ax.plot(data["x"], data["y"], label=f"Channel {ch}", color=colors[i % len(colors)], marker='o', markersize=2, linewidth=0.5)
                        # print(f"{file_name} - Peak value: {peak_value}")
                        self.x_data, self.y_data = x_index, peak_value
                        self.progress_dialog.update_progress(idx + 1)

                if not selected_items:
                        # print("❌ No valid data to plot.")
                        return
                total_count = len(x_labels)
                self.progress_dialog.close()


                sorted_pairs = sorted(zip(x_data, x_labels))
                sorted_x, sorted_labels = zip(*sorted_pairs)

                num_ticks = 10
                total = len(sorted_x)
                if total <= num_ticks:
                        tick_indices = list(range(total))
                else:
                        tick_indices = [int(i) for i in np.linspace(0, total -1, num_ticks)]

                tick_positions = [sorted_x[i] for i in tick_indices]
                tick_labels = [sorted_labels[i] for i in tick_indices]

                # tick 위치 설정
                self.peak_ax.set_xticks(tick_positions)
                self.peak_ax.set_xticklabels(tick_labels, rotation=0, ha="right", fontsize=7, fontname='Nanum Gothic')

                view_type_map = {
                        1: "ACC",
                        2: "VEL",
                        3: "DIS"
                        }

                view_type_code = self.select_pytpe4.currentData()
                view_type = view_type_map.get(view_type_code, "ACC")  # 기본값은 "ACC"로 설정

                labels = {
                                "ACC": "Vibration Acceleration \n (m/s^2, RMS)",
                                "VEL": "Vibration Velocity \n (mm/s, RMS)",
                                "DIS": "Vibration Displacement \n (μm , RMS)"
                        }
                ylabel = labels.get(view_type, "Vibration (mm/s, RMS)")
                self.peak_ax.set_ylabel(ylabel, fontsize=7, fontname='Nanum Gothic')
                self.peak_ax.set_facecolor('white')
                handles, labels = self.peak_ax.get_legend_handles_labels()
                unique = dict()
                for h, l in zip(handles, labels):
                        if l not in unique:
                                unique[l] = h
                # legend 업데이트
                self.peak_ax.legend(unique.values(), unique.keys(), fontsize = 7)

                # 그래프 갱신
                self.peak_canvas.flush_events()
                self.peak_ax.grid(True, color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
                self.peak_ax.tick_params(axis='x', labelsize = 7)
                self.peak_ax.tick_params(axis='y', labelsize = 7)
                self.peak_canvas.draw()
                self.cid_move = self.peak_canvas.mpl_connect("motion_notify_event", self.on_move_peak)
                self.cid_click = self.peak_canvas.mpl_connect("button_press_event", self.on_click_peak)
                self.cid_key = self.peak_canvas.mpl_connect("key_press_event", self.on_key_press_peak)
                self.hover_dot_peak = self.peak_ax.plot([], [], 'ko', markersize=6, alpha=0.5)[0]
                self.peak_file_names = [item.text() for item in selected_items]

                self.peak_rms = rms_values
                self.peak_value = peak_values  # 필요시 피크값도 따로 저장
                self.peak_delta_f = delta_f
                self.peak_overlap = overlap
                self.peak_window = window_type
                self.peak_band_min = band_min
                self.peak_band_max = band_max
                self.channel = channel
                self.sample_rate = sampling_rate
                self.dt = dt
                self.start_time = first_start_time
                self.Duration = duration
                self.Rest_time = rest_time
                self.repetition = repetition
                self.IEPE = iepe
                self.Sensitivity = sensitivity
                self.b_Sensitivity = b_sensitivity
                self.peak_x_value = peak_x_data
                self.view_type = view_type

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
                                dt = self.dt,
                                start_time = self.start_time,
                                duration = self.Duration,
                                rest_time = self.Rest_time,
                                repetition = self.repetition,
                                iepe = self.IEPE,
                                sensitivity = self.Sensitivity,
                                b_sensitivity = self.b_Sensitivity,
                                view_type = self.view_type
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

                # hover_dot 위치를 가져와서 마커로 고정
                x, y = self.hover_dot_peak.get_data()

                

                if x and y:
                        self.add_marker_peak(x,y)

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
                """마커 점과 텍스트를 동시에 추가"""
                # 가장 가까운 데이터 포인트 찾기
                min_distance  = float('inf')
                closest_index = -1
                for i, (data_x, data_y) in enumerate(zip(self.peak_x_value, self.peak_value)):
                        # x가 datetime일 경우 float로 변환
                        if isinstance(data_x, datetime):
                                data_x_float = mdates.date2num(data_x)
                        else:
                                data_x_float = data_x
                        
                        dx = abs(x - data_x_float)
                        dy = abs(y - data_y)

                        # 우선순위 조건 적용
                        if dx == 0:
                                dist = dy  # x가 같으면 y 차이만 고려
                        else:
                                dist = np.hypot(dx, dy)  # 그 외는 전체 거리 기준

                        if dist < min_distance:
                                min_distance = dist
                                closest_index = i

                if closest_index != -1:
                        file_name = self.peak_file_names[closest_index]
                        x_val = self.peak_x_value[closest_index]  # 실제 x 값
                        y_val = self.peak_value[closest_index]  # 실제 y 값

                        # 마커 추가
                        marker = self.peak_ax.plot(x_val, y_val, marker='o', color='red', markersize=7)[0]
                        self.peak_markers.append(marker)
                        
                        

                        # 텍스트 추가 (파일 이름, x, y 값 표시)
                        label = f"{file_name}\nX: {x_val}\nY: {y_val:.4f}"
                        annotation = self.peak_ax.annotate(
                                label,
                                (x_val, y_val),
                                textcoords="offset points",
                                xytext=(10, 10),
                                ha='left',
                                fontsize=7,
                                bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="lightyellow", alpha=0.8)
                        )
                        self.peak_annotations.append(annotation)
                        
                        
                        
                       
                        self.peak_canvas.draw()

if __name__=="__main__":
        faulthandler.enable()
        
        app = QtWidgets.QApplication(sys.argv)
        MainWindow = QtWidgets.QMainWindow()
        font = QFont("Nanum Gothic", 10)  # 폰트 설정
        app.setFont(font)  # 전체 애플리케이션 폰트 설정
        app.setWindowIcon(QIcon("icn.ico"))  # 전체 앱 아이콘 설정
        
        ui = Ui_MainWindow()
        ui.setupUi(MainWindow)
        ui.retranslateUi(MainWindow)  # 보통 번역 함수도 호출

        MainWindow.setWindowTitle("CNAVE CNXMW Post Processor")
        MainWindow.setWindowIcon(QIcon("icn.ico"))
        MainWindow.show()

        # ⭐ 프로그램 종료 시 성능 리포트 생성
        try:
                exit_code = app.exec_()

                import gc
                gc.collect()

                # 최종 리포트 생성
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

                # 에러가 있어도 리포트는 저장
                try:
                        perf_logger.generate_summary()
                        perf_logger.save_json_report()
                except:
                        pass

                sys.exit(1)

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
