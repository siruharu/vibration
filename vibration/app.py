"""
Application factory and entry point.

Wires all dependencies using constructor injection.
No service locator pattern - all dependencies explicitly passed.
"""
import sys
import logging
from typing import Dict, Any

from PyQt5.QtWidgets import QApplication

from vibration.presentation.views import MainWindow
from vibration.presentation.presenters import (
    DataQueryPresenter,
    WaterfallPresenter,
    SpectrumPresenter,
    TrendPresenter,
    PeakPresenter
)
from vibration.core.services import (
    FFTService,
    TrendService,
    PeakService,
    FileService
)

logger = logging.getLogger(__name__)


class ApplicationFactory:
    """Factory for creating application with wired dependencies using constructor injection."""
    
    DEFAULT_SAMPLING_RATE = 10240.0
    DEFAULT_DELTA_F = 1.0
    DEFAULT_OVERLAP = 50.0
    DEFAULT_WINDOW_TYPE = 'hanning'
    
    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._services: Dict[str, Any] = {}
        self._presenters: Dict[str, Any] = {}
        self._main_window = None
        
    def create_services(self) -> Dict[str, Any]:
        self._services['file'] = FileService()
        
        self._services['fft'] = FFTService(
            sampling_rate=self._config.get('sampling_rate', self.DEFAULT_SAMPLING_RATE),
            delta_f=self._config.get('delta_f', self.DEFAULT_DELTA_F),
            overlap=self._config.get('overlap', self.DEFAULT_OVERLAP),
            window_type=self._config.get('window_type', self.DEFAULT_WINDOW_TYPE)
        )
        
        self._services['trend'] = TrendService(
            max_workers=self._config.get('max_workers')
        )
        
        self._services['peak'] = PeakService(
            max_workers=self._config.get('max_workers')
        )
        
        logger.info("Created all services")
        return self._services
        
    def create_main_window(self) -> MainWindow:
        self._main_window = MainWindow()
        logger.info("Created main window")
        return self._main_window
        
    def create_presenters(self, main_window: MainWindow) -> Dict[str, Any]:
        if not self._services:
            raise RuntimeError("Services must be created before presenters")
        
        data_query_tab = main_window.get_tab(MainWindow.TAB_DATA_QUERY)
        self._presenters['data_query'] = DataQueryPresenter(view=data_query_tab)
        
        waterfall_tab = main_window.get_tab(MainWindow.TAB_WATERFALL)
        self._presenters['waterfall'] = WaterfallPresenter(
            view=waterfall_tab,
            fft_service=self._services['fft']
        )
        
        spectrum_tab = main_window.get_tab(MainWindow.TAB_SPECTRUM)
        self._presenters['spectrum'] = SpectrumPresenter(
            view=spectrum_tab,
            fft_service=self._services['fft']
        )
        
        trend_tab = main_window.get_tab(MainWindow.TAB_TREND)
        self._presenters['trend'] = TrendPresenter(
            view=trend_tab,
            trend_service=self._services['trend']
        )
        
        peak_tab = main_window.get_tab(MainWindow.TAB_PEAK)
        self._presenters['peak'] = PeakPresenter(
            view=peak_tab,
            peak_service=self._services['peak']
        )
        
        logger.info("Created all presenters with DI")
        return self._presenters
        
    def create_application(self) -> MainWindow:
        self.create_services()
        main_window = self.create_main_window()
        self.create_presenters(main_window)
        logger.info("Application fully wired")
        return main_window
    
    def get_service(self, name: str) -> Any:
        return self._services.get(name)
    
    def get_presenter(self, name: str) -> Any:
        return self._presenters.get(name)


def main():
    """Application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app = QApplication(sys.argv)
    
    factory = ApplicationFactory()
    main_window = factory.create_application()
    
    main_window.show()
    
    logger.info("Application started")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
