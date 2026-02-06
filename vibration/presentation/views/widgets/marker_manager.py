"""Marker management for interactive plots with mouse/keyboard handling."""
from typing import Optional, List, Tuple, Any, Callable, Union
from enum import Enum
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from matplotlib.axes import Axes


class MarkerType(Enum):
    POINT = "point"
    VLINE = "vline"
    HLINE = "hline"


class MarkerManager(QObject):
    """Manages interactive markers: hover tracking, click placement, multiple marker types."""
    
    marker_added = pyqtSignal(float, float, str)
    marker_cleared = pyqtSignal()
    
    DEFAULT_MARKER_STYLE = {'marker': 'o', 'color': 'red', 'markersize': 8, 'linestyle': ''}
    DEFAULT_LABEL_STYLE = {'fontsize': 9, 'fontweight': 'bold', 'color': 'black', 'ha': 'center', 'va': 'bottom'}
    
    def __init__(self, axes: Axes, canvas: Any = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.axes = axes
        self.canvas = canvas
        self._markers: List[Tuple[Any, Optional[Any]]] = []
        self._hover_dot = None
        self._hover_pos: Optional[List[float]] = None
        self._label_formatter: Optional[Callable[[float, float, Optional[str]], str]] = None

    def set_label_formatter(self, formatter: Callable[[float, float, Optional[str]], str]):
        self._label_formatter = formatter

    def init_hover_dot(self, color: str = 'blue', size: int = 10) -> Any:
        self._hover_dot, = self.axes.plot([], [], 'o', color=color, markersize=size)
        return self._hover_dot

    def find_closest_point(self, x: float, y: float) -> Tuple[Optional[float], Optional[float], float]:
        closest_x, closest_y, min_dist = None, None, np.inf
        for line in self.axes.get_lines():
            if line == self._hover_dot:
                continue
            xdata, ydata = line.get_xdata(), line.get_ydata()
            if len(xdata) == 0:
                continue
            xdata, ydata = np.asarray(xdata), np.asarray(ydata)
            dists = np.hypot(xdata - x, ydata - y)
            idx = np.argmin(dists)
            if dists[idx] < min_dist:
                min_dist, closest_x, closest_y = dists[idx], float(xdata[idx]), float(ydata[idx])
        return closest_x, closest_y, min_dist

    def on_mouse_move(self, event) -> Optional[Tuple[float, float]]:
        if not event.inaxes or event.inaxes != self.axes:
            if self._hover_pos and self._hover_dot:
                self._hover_dot.set_data([], [])
                self._hover_pos = None
                self._draw()
            return None
        cx, cy, _ = self.find_closest_point(event.xdata, event.ydata)
        if cx is not None and self._hover_dot:
            self._hover_dot.set_data([cx], [cy])
            self._hover_pos = [cx, cy]
            self._draw()
        return (cx, cy) if cx else None

    def on_mouse_click(self, event, data_lookup: Optional[Callable] = None):
        if not event.inaxes or event.inaxes != self.axes:
            return
        if event.button == 3:
            self.clear_markers()
            self._draw()
            return
        if event.button == 1:
            x, y = (self._hover_pos or [event.xdata, event.ydata])[:2]
            label = None
            if data_lookup:
                result = data_lookup(x, y)
                if result:
                    x, y, label = result
            self.add_marker(x, y, label=label)
            self._draw()

    def add_marker(self, x: float, y: float, label: Optional[str] = None,
                   label_format: str = "X: {x:.4f}\nY: {y:.4f}",
                   marker_type: MarkerType = MarkerType.POINT, **kwargs) -> Tuple[Any, Optional[Any]]:
        x, y = self._to_scalar(x), self._to_scalar(y)
        style = {**self.DEFAULT_MARKER_STYLE, **kwargs}
        if marker_type == MarkerType.VLINE:
            artist = self.axes.axvline(x, color=style.get('color', 'red'), linestyle='--')
        elif marker_type == MarkerType.HLINE:
            artist = self.axes.axhline(y, color=style.get('color', 'red'), linestyle='--')
        else:
            artist, = self.axes.plot([x], [y], **style)
        label_artist = None
        display_label = self._format_label(x, y, label, label_format)
        if display_label:
            label_artist = self.axes.text(x, y + (abs(y) * 0.02 or 0.001), display_label, **self.DEFAULT_LABEL_STYLE)
        self._markers.append((artist, label_artist))
        self.marker_added.emit(x, y, label or "")
        return artist, label_artist

    def _format_label(self, x: float, y: float, label: Optional[str], fmt: str) -> str:
        if self._label_formatter:
            return self._label_formatter(x, y, label)
        return label or fmt.format(x=x, y=y)

    def _to_scalar(self, val: Union[float, list, np.ndarray]) -> float:
        if isinstance(val, (list, np.ndarray)) and len(val) > 0:
            return float(val[0])
        return float(val)

    def clear_markers(self):
        for marker, label in self._markers:
            self._safe_remove(marker)
            if label:
                self._safe_remove(label)
        self._markers.clear()
        self.marker_cleared.emit()

    def _safe_remove(self, artist):
        try:
            artist.remove()
        except (NotImplementedError, ValueError, AttributeError):
            try:
                if hasattr(artist, 'set_data'):
                    artist.set_data([], [])
                elif hasattr(artist, 'set_visible'):
                    artist.set_visible(False)
            except Exception:
                pass

    def _draw(self):
        if self.canvas: self.canvas.draw_idle()

    def get_marker_count(self) -> int: return len(self._markers)

    def get_marker_positions(self) -> List[Tuple[float, float]]:
        positions = []
        for marker, _ in self._markers:
            try:
                xdata, ydata = marker.get_data()
                if len(xdata) > 0: positions.append((float(xdata[0]), float(ydata[0])))
            except Exception: pass
        return positions

    def get_hover_position(self) -> Optional[Tuple[float, float]]:
        return tuple(self._hover_pos) if self._hover_pos else None
