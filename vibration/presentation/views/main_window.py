"""
메인 애플리케이션 윈도우 (씬 셸).

탭 뷰를 조율하고 모든 비즈니스 로직을 프레젠터에 위임합니다.
UI 상태를 최소화 - 프레젠터가 데이터 흐름을 처리합니다.
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
from vibration.presentation.views.dialogs.responsive_layout_utils import APP_FONT_FAMILY, get_screen_size
from vibration import get_resource_path


class MainWindow(QMainWindow):
    """
    메인 애플리케이션 윈도우 - 씬 셸 패턴.
    
    역할:
    - 윈도우 크롬 (타이틀, 크기, 아이콘)
    - 탭 위젯 관리
    - 메뉴/상태바 구조
    
    역할 아님:
    - 비즈니스 로직 (프레젠터에 위임)
    - 데이터 관리 (서비스가 처리)
    - 복잡한 UI 상태 (탭 뷰가 관리)
    """
    
    app_closing = pyqtSignal()
    tab_changed = pyqtSignal(int, str)
    
    TAB_DATA_QUERY = 'data_query'
    TAB_WATERFALL = 'waterfall'
    TAB_SPECTRUM = 'spectrum'
    TAB_TREND = 'trend'
    TAB_PEAK = 'peak'
    
    def __init__(self, parent: Optional[QWidget] = None):
        """메인 윈도우를 초기화합니다."""
        super().__init__(parent)
        self._tabs: Dict[str, QWidget] = {}
        
        self._setup_window()
        self._create_central_widget()
        self._create_tabs()
        self._create_menu_bar()
        self._create_status_bar()
        self._connect_signals()
    
    def _setup_window(self):
        """윈도우 속성을 설정합니다."""
        self.setWindowTitle("CNAVE Vibration Analyzer")
        screen_w, screen_h = get_screen_size()
        self.setMinimumSize(int(screen_w * 0.6), int(screen_h * 0.6))
        self.resize(int(screen_w * 0.85), int(screen_h * 0.85))
        
        font = QFont(APP_FONT_FAMILY, 9)
        self.setFont(font)
        
        icon_path = get_resource_path("icn.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
    
    def _create_central_widget(self):
        """레이아웃이 포함된 중앙 위젯을 생성합니다."""
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        
        self._main_layout = QVBoxLayout(self._central_widget)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
    
    def _create_tabs(self):
        """모든 탭이 포함된 탭 위젯을 생성합니다."""
        self.tab_widget = QTabWidget()
        self._main_layout.addWidget(self.tab_widget)
        
        self.data_query_tab = DataQueryTabView()
        self._tabs[self.TAB_DATA_QUERY] = self.data_query_tab
        self.tab_widget.addTab(self.data_query_tab, "Data Query")
        
        self.spectrum_tab = SpectrumTabView()
        self._tabs[self.TAB_SPECTRUM] = self.spectrum_tab
        self.tab_widget.addTab(self.spectrum_tab, "Time/Spectrum")
        
        self.trend_tab = TrendTabView()
        self._tabs[self.TAB_TREND] = self.trend_tab
        self.tab_widget.addTab(self.trend_tab, "RMS Trend")
        
        self.peak_tab = PeakTabView()
        self._tabs[self.TAB_PEAK] = self.peak_tab
        self.tab_widget.addTab(self.peak_tab, "Band Peak Trend")
        
        self.waterfall_tab = WaterfallTabView()
        self._tabs[self.TAB_WATERFALL] = self.waterfall_tab
        self.tab_widget.addTab(self.waterfall_tab, "Waterfall")
    
    def _create_menu_bar(self):
        """메뉴바 구조를 생성합니다."""
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
        """상태바를 생성합니다."""
        self._status_bar = QStatusBar(self)
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")
    
    def _connect_signals(self):
        """내부 시그널을 연결합니다."""
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _on_tab_changed(self, index: int):
        """탭 변경 이벤트를 처리합니다."""
        tab_names = [
            self.TAB_DATA_QUERY,
            self.TAB_SPECTRUM,
            self.TAB_TREND,
            self.TAB_PEAK,
            self.TAB_WATERFALL
        ]
        if 0 <= index < len(tab_names):
            self.tab_changed.emit(index, tab_names[index])
    
    def get_tab(self, name: str) -> Optional[QWidget]:
        """
        이름으로 탭 뷰를 가져옵니다.
        
        인자:
            name: 탭 이름 상수 (TAB_DATA_QUERY 등)
            
        반환:
            탭 뷰 위젯 또는 찾지 못한 경우 None
        """
        return self._tabs.get(name)
    
    def set_current_tab(self, name: str) -> bool:
        """
        지정된 탭으로 전환합니다.
        
        인자:
            name: 탭 이름 상수
            
        반환:
            탭을 찾아 전환한 경우 True, 아닌 경우 False
        """
        tab = self._tabs.get(name)
        if tab:
            self.tab_widget.setCurrentWidget(tab)
            return True
        return False
    
    def get_current_tab_name(self) -> str:
        """현재 탭의 이름을 반환합니다."""
        current_widget = self.tab_widget.currentWidget()
        for name, tab in self._tabs.items():
            if tab is current_widget:
                return name
        return ""
    
    def set_status_message(self, message: str, timeout: int = 0):
        """
        상태바 메시지를 설정합니다.
        
        인자:
            message: 표시할 메시지
            timeout: 타임아웃 (ms, 0 = 영구)
        """
        self._status_bar.showMessage(message, timeout)
    
    def add_menu_action(self, menu_name: str, action: QAction):
        """
        지정된 메뉴에 액션을 추가합니다.
        
        인자:
            menu_name: 'file', 'view' 또는 'help'
            action: 추가할 액션
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
        """윈도우 닫기 이벤트를 처리합니다."""
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
