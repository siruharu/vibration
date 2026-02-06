"""
Marker management for interactive plots.

Handles mouse events and marker placement on matplotlib plots
with safe removal and signal-based notifications.
"""
from typing import Optional, List, Tuple, Any

from PyQt5.QtCore import QObject, pyqtSignal
from matplotlib.axes import Axes


class MarkerManager(QObject):
    """
    Manages interactive markers on matplotlib plots.
    
    Provides marker creation, removal, and mouse event handling
    with Qt signal notifications for marker state changes.
    
    Signals:
        marker_added: Emitted when marker is added (x, y, label)
        marker_cleared: Emitted when markers are cleared
    """
    
    marker_added = pyqtSignal(float, float, str)
    marker_cleared = pyqtSignal()
    
    DEFAULT_MARKER_STYLE = {'marker': 'o', 'color': 'red', 'markersize': 8, 'linestyle': ''}
    DEFAULT_LABEL_STYLE = {'fontsize': 9, 'fontweight': 'bold', 'color': 'black', 'ha': 'center', 'va': 'bottom'}
    
    def __init__(self, axes: Axes, parent: Optional[QObject] = None):
        """
        Initialize marker manager.
        
        Args:
            axes: Matplotlib axes to manage markers on
            parent: Parent QObject for signal connections
        """
        super().__init__(parent)
        self.axes = axes
        self._markers: List[Tuple[Any, Optional[Any]]] = []
    
    def add_marker(
        self,
        x: float,
        y: float,
        label: Optional[str] = None,
        label_format: str = "X: {x:.4f}\nY: {y:.4f}",
        **marker_kwargs
    ) -> Tuple[Any, Optional[Any]]:
        """
        Add a marker to the plot at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            label: Optional custom label text
            label_format: Format string for auto-generated labels
            **marker_kwargs: Override default marker styling
            
        Returns:
            Tuple of (marker_artist, label_artist or None)
        """
        style = {**self.DEFAULT_MARKER_STYLE, **marker_kwargs}
        
        marker_line, = self.axes.plot([x], [y], **style)
        
        label_text = None
        if label is not None or label_format:
            display_label = label or label_format.format(x=x, y=y)
            label_style = self.DEFAULT_LABEL_STYLE.copy()
            label_text = self.axes.text(
                x, y + (y * 0.02 if y != 0 else 0.001),
                display_label,
                **label_style
            )
        
        self._markers.append((marker_line, label_text))
        self.marker_added.emit(x, y, label or "")
        
        return marker_line, label_text
    
    def clear_markers(self):
        """Remove all markers from the plot safely."""
        for marker, label in self._markers:
            self._safe_remove(marker)
            if label:
                self._safe_remove(label)
        
        self._markers.clear()
        self.marker_cleared.emit()
    
    def _safe_remove(self, artist):
        """Safely remove a matplotlib artist with fallback handling."""
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
    
    def get_marker_count(self) -> int:
        """Return current number of markers."""
        return len(self._markers)
    
    def get_marker_positions(self) -> List[Tuple[float, float]]:
        """Return list of (x, y) positions for all markers."""
        positions = []
        for marker, _ in self._markers:
            try:
                xdata, ydata = marker.get_data()
                if len(xdata) > 0 and len(ydata) > 0:
                    positions.append((float(xdata[0]), float(ydata[0])))
            except Exception:
                pass
        return positions
    
    def on_mouse_click(self, event):
        """
        Handle mouse click events for marker placement.
        
        Left click: Add marker at clicked position
        Right click: Clear all markers
        
        Args:
            event: Matplotlib mouse event
        """
        if event.inaxes != self.axes:
            return
        
        if event.button == 1:
            self.add_marker(event.xdata, event.ydata)
        elif event.button == 3:
            self.clear_markers()

