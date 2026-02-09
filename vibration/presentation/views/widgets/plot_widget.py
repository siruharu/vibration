"""
진동 분석 플롯을 위한 기본 matplotlib 위젯.

FigureCanvasQTAgg, DPI 스케일링, 애플리케이션 전체에 걸친
일관된 스타일링을 제공하는 공통 플로팅 인프라.
"""
from typing import Optional, Tuple

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from vibration.presentation.views.dialogs.responsive_layout_utils import PlotFontSizes


class PlotWidget(QWidget):
    """
    DPI 인식 스케일링이 적용된 matplotlib 플롯 기본 위젯.
    
    모든 플롯 유형에 대한 figure 관리, 캔버스 처리,
    반응형 사이징을 포함하는 공통 인프라를 제공합니다.
    
    시그널:
        plot_clicked: 플롯 영역 클릭 시 발행 (x, y)
        plot_updated: draw() 완료 후 발행
    """
    
    plot_clicked = pyqtSignal(float, float)
    plot_updated = pyqtSignal()
    
    DEFAULT_STYLE = {'title_size': PlotFontSizes.TITLE, 'label_size': PlotFontSizes.LABEL, 'tick_size': PlotFontSizes.TICK, 'grid_alpha': 0.3, 'grid_style': '--'}
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        figsize: Tuple[float, float] = (10, 6),
        dpi: Optional[int] = None
    ):
        """
        플롯 위젯을 초기화합니다.
        
        인자:
            parent: 부모 위젯
            figsize: Figure 크기 (너비, 높이) 인치 단위
            dpi: 렌더링 해상도 (None이면 자동 감지)
        """
        super().__init__(parent)
        
        if dpi is None:
            dpi = self._get_screen_dpi()
        
        self._dpi = dpi
        self._figsize = figsize
        
        self.figure = Figure(figsize=figsize, dpi=dpi)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.add_subplot(111)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.canvas.mpl_connect('button_press_event', self._on_click)
        self._apply_default_style()
    
    def _get_screen_dpi(self) -> int:
        """스케일링을 위한 화면 DPI를 가져옵니다."""
        try:
            screen = QApplication.primaryScreen()
            if screen:
                return int(screen.logicalDotsPerInch())
        except Exception:
            pass
        return 100
    
    def _apply_default_style(self):
        """기본 플롯 스타일을 적용합니다."""
        self.axes.grid(
            True,
            alpha=self.DEFAULT_STYLE['grid_alpha'],
            linestyle=self.DEFAULT_STYLE['grid_style'],
            linewidth=0.5
        )
        self.axes.tick_params(labelsize=self.DEFAULT_STYLE['tick_size'])
    
    def _on_click(self, event):
        """캔버스의 마우스 클릭 이벤트를 처리합니다."""
        if event.inaxes == self.axes and event.xdata is not None:
            self.plot_clicked.emit(event.xdata, event.ydata)
    
    def draw(self):
        """캔버스를 다시 그립니다."""
        self.canvas.draw()
        self.plot_updated.emit()
    
    def draw_idle(self):
        """유휴 시 다시 그리기를 요청합니다 (비차단)."""
        self.canvas.draw_idle()
    
    def clear(self):
        """축을 초기화하고 스타일을 재설정합니다."""
        self.axes.clear()
        self._apply_default_style()
    
    def get_axes(self):
        """matplotlib axes를 반환합니다."""
        return self.axes
    
    def get_figure(self):
        """matplotlib figure를 반환합니다."""
        return self.figure
    
    def get_canvas(self):
        """matplotlib canvas를 반환합니다."""
        return self.canvas
    
    def set_title(self, title: str, **kwargs):
        """기본 스타일링으로 플롯 제목을 설정합니다."""
        kwargs.setdefault('fontsize', self.DEFAULT_STYLE['title_size'])
        kwargs.setdefault('fontweight', 'bold')
        kwargs.setdefault('pad', 10)
        self.axes.set_title(title, **kwargs)
    
    def set_labels(self, xlabel: str = '', ylabel: str = '', **kwargs):
        """기본 스타일링으로 축 라벨을 설정합니다."""
        kwargs.setdefault('fontsize', self.DEFAULT_STYLE['label_size'])
        if xlabel:
            self.axes.set_xlabel(xlabel, **kwargs)
        if ylabel:
            self.axes.set_ylabel(ylabel, **kwargs)
    
    def tight_layout(self, **kwargs):
        """figure에 tight layout을 적용합니다."""
        kwargs.setdefault('pad', 1.0)
        self.figure.tight_layout(**kwargs)
    
    def save(self, filepath: str, dpi: int = 300, **kwargs):
        """
        플롯을 파일로 저장합니다.
        
        인자:
            filepath: 출력 파일 경로
            dpi: 저장 이미지의 해상도
            **kwargs: 추가 savefig 인자
        """
        kwargs.setdefault('bbox_inches', 'tight')
        kwargs.setdefault('facecolor', 'white')
        self.figure.savefig(filepath, dpi=dpi, **kwargs)

