"""
Base matplotlib widget for vibration analysis plots.

Provides common plotting infrastructure with FigureCanvasQTAgg,
DPI scaling, and consistent styling across the application.
"""
from typing import Optional, Tuple

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore import pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class PlotWidget(QWidget):
    """
    Base widget for matplotlib plots with DPI-aware scaling.
    
    Provides common infrastructure for all plot types including
    figure management, canvas handling, and responsive sizing.
    
    Signals:
        plot_clicked: Emitted when plot area is clicked (x, y)
        plot_updated: Emitted after draw() completes
    """
    
    plot_clicked = pyqtSignal(float, float)
    plot_updated = pyqtSignal()
    
    DEFAULT_STYLE = {'title_size': 12, 'label_size': 10, 'tick_size': 9, 'grid_alpha': 0.3, 'grid_style': '--'}
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        figsize: Tuple[float, float] = (10, 6),
        dpi: Optional[int] = None
    ):
        """
        Initialize plot widget.
        
        Args:
            parent: Parent widget
            figsize: Figure size (width, height) in inches
            dpi: Dots per inch for rendering (auto-detected if None)
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
        """Get screen DPI for scaling."""
        try:
            screen = QApplication.primaryScreen()
            if screen:
                return int(screen.logicalDotsPerInch())
        except Exception:
            pass
        return 100
    
    def _apply_default_style(self):
        """Apply default plot styling."""
        self.axes.grid(
            True,
            alpha=self.DEFAULT_STYLE['grid_alpha'],
            linestyle=self.DEFAULT_STYLE['grid_style'],
            linewidth=0.5
        )
        self.axes.tick_params(labelsize=self.DEFAULT_STYLE['tick_size'])
    
    def _on_click(self, event):
        """Handle mouse click events on canvas."""
        if event.inaxes == self.axes and event.xdata is not None:
            self.plot_clicked.emit(event.xdata, event.ydata)
    
    def draw(self):
        """Redraw the canvas."""
        self.canvas.draw()
        self.plot_updated.emit()
    
    def draw_idle(self):
        """Request redraw when idle (non-blocking)."""
        self.canvas.draw_idle()
    
    def clear(self):
        """Clear the axes and reset style."""
        self.axes.clear()
        self._apply_default_style()
    
    def get_axes(self):
        """Get the matplotlib axes."""
        return self.axes
    
    def get_figure(self):
        """Get the matplotlib figure."""
        return self.figure
    
    def set_title(self, title: str, **kwargs):
        """Set plot title with default styling."""
        kwargs.setdefault('fontsize', self.DEFAULT_STYLE['title_size'])
        kwargs.setdefault('fontweight', 'bold')
        kwargs.setdefault('pad', 10)
        self.axes.set_title(title, **kwargs)
    
    def set_labels(self, xlabel: str = '', ylabel: str = '', **kwargs):
        """Set axis labels with default styling."""
        kwargs.setdefault('fontsize', self.DEFAULT_STYLE['label_size'])
        if xlabel:
            self.axes.set_xlabel(xlabel, **kwargs)
        if ylabel:
            self.axes.set_ylabel(ylabel, **kwargs)
    
    def tight_layout(self, **kwargs):
        """Apply tight layout to figure."""
        kwargs.setdefault('pad', 1.0)
        self.figure.tight_layout(**kwargs)
    
    def save(self, filepath: str, dpi: int = 300, **kwargs):
        """
        Save plot to file.
        
        Args:
            filepath: Output file path
            dpi: Resolution for saved image
            **kwargs: Additional savefig arguments
        """
        kwargs.setdefault('bbox_inches', 'tight')
        kwargs.setdefault('facecolor', 'white')
        self.figure.savefig(filepath, dpi=dpi, **kwargs)

