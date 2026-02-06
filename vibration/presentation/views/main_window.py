"""
Main application window (thin shell).

Coordinates tab views and delegates all business logic to presenters.
Keeps UI state minimal - presenters handle data flow.
"""
from typing import Optional, Dict, Any
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar, QMenuBar, QMenu, QAction, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QFont

from vibration.presentation.views.tabs import (
    DataQueryTabView,
    WaterfallTabView,
    SpectrumTabView,
    TrendTabView,
    PeakTabView
)


class MainWindow(QMainWindow):
    """
    Main application window - thin shell pattern.
    
    Responsibilities:
    - Window chrome (title, size, icon)
    - Tab widget management
    - Menu/status bar structure
    
    NOT responsible for:
    - Business logic (delegated to presenters)
    - Data management (handled by services)
    - Complex UI state (managed by tab views)
    """
    
    app_closing = pyqtSignal()
    tab_changed = pyqtSignal(int, str)
    
    TAB_DATA_QUERY = 'data_query'
    TAB_WATERFALL = 'waterfall'
    TAB_SPECTRUM = 'spectrum'
    TAB_TREND = 'trend'
    TAB_PEAK = 'peak'
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize main window."""
        super().__init__(parent)
        self._tabs: Dict[str, QWidget] = {}
        
        self._setup_window()
        self._create_central_widget()
        self._create_tabs()
        self._create_menu_bar()
        self._create_status_bar()
        self._connect_signals()
    
    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle("CNAVE Vibration Analyzer")
        self.setMinimumSize(1920, 1027)
        self.resize(1920, 1080)
        
        font = QFont("Malgun Gothic", 9)
        self.setFont(font)
        
        icon_path = Path("icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
    
    def _create_central_widget(self):
        """Create central widget with layout."""
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        
        self._main_layout = QVBoxLayout(self._central_widget)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
    
    def _create_tabs(self):
        """Create tab widget with all tabs."""
        self.tab_widget = QTabWidget()
        self._main_layout.addWidget(self.tab_widget)
        
        self.data_query_tab = DataQueryTabView()
        self._tabs[self.TAB_DATA_QUERY] = self.data_query_tab
        self.tab_widget.addTab(self.data_query_tab, "Data Query")
        
        self.waterfall_tab = WaterfallTabView()
        self._tabs[self.TAB_WATERFALL] = self.waterfall_tab
        self.tab_widget.addTab(self.waterfall_tab, "Waterfall")
        
        self.spectrum_tab = SpectrumTabView()
        self._tabs[self.TAB_SPECTRUM] = self.spectrum_tab
        self.tab_widget.addTab(self.spectrum_tab, "Spectrum")
        
        self.trend_tab = TrendTabView()
        self._tabs[self.TAB_TREND] = self.trend_tab
        self.tab_widget.addTab(self.trend_tab, "Trend")
        
        self.peak_tab = PeakTabView()
        self._tabs[self.TAB_PEAK] = self.peak_tab
        self.tab_widget.addTab(self.peak_tab, "Peak")
    
    def _create_menu_bar(self):
        """Create menu bar structure."""
        self._menu_bar = QMenuBar(self)
        self.setMenuBar(self._menu_bar)
        
        self._file_menu = QMenu("File", self)
        self._menu_bar.addMenu(self._file_menu)
        self._exit_action = QAction("Exit", self)
        self._exit_action.setShortcut("Ctrl+Q")
        self._exit_action.triggered.connect(self.close)
        self._file_menu.addAction(self._exit_action)
        
        self._view_menu = QMenu("View", self)
        self._menu_bar.addMenu(self._view_menu)
        
        self._help_menu = QMenu("Help", self)
        self._menu_bar.addMenu(self._help_menu)
        self._about_action = QAction("About", self)
        self._help_menu.addAction(self._about_action)
    
    def _create_status_bar(self):
        """Create status bar."""
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")
    
    def _connect_signals(self):
        """Connect internal signals."""
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _on_tab_changed(self, index: int):
        """Handle tab change event."""
        tab_names = [
            self.TAB_DATA_QUERY,
            self.TAB_WATERFALL,
            self.TAB_SPECTRUM,
            self.TAB_TREND,
            self.TAB_PEAK
        ]
        if 0 <= index < len(tab_names):
            self.tab_changed.emit(index, tab_names[index])
    
    def get_tab(self, name: str) -> Optional[QWidget]:
        """
        Get tab view by name.
        
        Args:
            name: Tab name constant (TAB_DATA_QUERY, etc.)
            
        Returns:
            Tab view widget or None if not found
        """
        return self._tabs.get(name)
    
    def set_current_tab(self, name: str) -> bool:
        """
        Switch to specified tab.
        
        Args:
            name: Tab name constant
            
        Returns:
            True if tab found and switched, False otherwise
        """
        tab = self._tabs.get(name)
        if tab:
            self.tab_widget.setCurrentWidget(tab)
            return True
        return False
    
    def get_current_tab_name(self) -> str:
        """Get name of current tab."""
        current_widget = self.tab_widget.currentWidget()
        for name, tab in self._tabs.items():
            if tab is current_widget:
                return name
        return ""
    
    def set_status_message(self, message: str, timeout: int = 0):
        """
        Set status bar message.
        
        Args:
            message: Message to display
            timeout: Timeout in ms (0 = permanent)
        """
        self._status_bar.showMessage(message, timeout)
    
    def add_menu_action(self, menu_name: str, action: QAction):
        """
        Add action to specified menu.
        
        Args:
            menu_name: 'file', 'view', or 'help'
            action: Action to add
        """
        menus = {
            'file': self._file_menu,
            'view': self._view_menu,
            'help': self._help_menu
        }
        menu = menus.get(menu_name.lower())
        if menu:
            menu.addAction(action)
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.app_closing.emit()
        super().closeEvent(event)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    print(f"MainWindow created successfully")
    print(f"Tabs: {list(window._tabs.keys())}")
    sys.exit(app.exec_())
