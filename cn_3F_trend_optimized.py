"""
DEPRECATED: This file is now a compatibility layer.

This file has been refactored into a modular package structure.
Please use:
- `python -m vibration` to run the application
- `from vibration.presentation.views.dialogs import ProgressDialog` for imports

This file will be removed in version 3.0.
"""
import warnings
import sys

# Deprecation warning
warnings.warn(
    "Importing from cn_3F_trend_optimized.py is deprecated. "
    "Use 'from vibration.presentation.views.dialogs import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)

# ===== Re-exports for backward compatibility =====

# Dialog classes
from vibration.presentation.views.dialogs import (
    ProgressDialog,
    AxisRangeDialog,
    ListSaveDialog
)

# Main window UI
from vibration.presentation.views import MainWindow as Ui_MainWindow

# Services (core layer)
from vibration.core.services import (
    FFTService,
    TrendService,
    PeakService,
    FileService
)

# Domain models
from vibration.core.domain.models import (
    FFTResult,
    SignalData,
    TrendResult,
    FileMetadata
)

# Presenters
from vibration.presentation.presenters import (
    DataQueryPresenter,
    WaterfallPresenter,
    SpectrumPresenter,
    TrendPresenter,
    PeakPresenter
)

# Views/Tabs
from vibration.presentation.views.tabs import (
    DataQueryTabView,
    WaterfallTabView,
    SpectrumTabView,
    TrendTabView,
    PeakTabView
)

# Widgets
from vibration.presentation.views.widgets import (
    PlotWidget,
    MarkerManager
)

# Models
from vibration.presentation.models import FileListModel

# Infrastructure
from vibration.infrastructure import EventBus, get_event_bus

# Application factory
from vibration.app import ApplicationFactory, main

# ===== Entry point for backward compatibility =====

if __name__ == "__main__":
    main()
