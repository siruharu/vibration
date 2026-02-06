"""
Event bus for application-wide signals.

Singleton pattern for cross-cutting event communication.
Provides decoupled communication between modules without direct dependencies.

Usage:
    from vibration.infrastructure.event_bus import get_event_bus
    
    # Subscribe to events
    bus = get_event_bus()
    bus.file_loaded.connect(on_file_loaded)
    
    # Emit events
    bus.file_loaded.emit("/path/to/file.txt")
    
Note:
    Use sparingly - only for cross-cutting concerns.
    Prefer direct presenter communication for most cases.
"""
from PyQt5.QtCore import QObject, pyqtSignal


class EventBus(QObject):
    """
    Singleton event bus for application-wide signals.
    
    Provides a centralized mechanism for cross-cutting event communication
    between loosely coupled modules.
    
    Attributes:
        file_loaded: Emitted when a single file is loaded (filepath)
        files_loaded: Emitted when multiple files are loaded (list of filepaths)
        analysis_complete: Emitted when analysis finishes (analysis_type, results)
        error_occurred: Emitted on errors (error_type, message)
        progress_updated: Emitted for progress updates (percentage, message)
        data_changed: Emitted when data changes (data_type)
        selection_changed: Emitted when selection changes (selected_items)
        tab_changed: Emitted when tab changes (tab_name)
        view_type_changed: Emitted when view type changes (view_type: ACC/VEL/DIS)
    """
    
    # Application events
    file_loaded = pyqtSignal(str)  # filepath
    files_loaded = pyqtSignal(list)  # list of filepaths
    analysis_complete = pyqtSignal(str, dict)  # analysis_type, results
    error_occurred = pyqtSignal(str, str)  # error_type, message
    progress_updated = pyqtSignal(int, str)  # percentage, message
    
    # Data events
    data_changed = pyqtSignal(str)  # data_type
    selection_changed = pyqtSignal(list)  # selected_items
    
    # UI events
    tab_changed = pyqtSignal(str)  # tab_name
    view_type_changed = pyqtSignal(str)  # view_type (ACC/VEL/DIS)
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            super(EventBus, cls._instance).__init__()
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'EventBus':
        """
        Get singleton instance.
        
        Returns:
            The global EventBus instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset singleton instance (for testing purposes).
        
        Warning:
            Only use in tests. Will disconnect all existing connections.
        """
        cls._instance = None


def get_event_bus() -> EventBus:
    """
    Get global event bus instance.
    
    Convenience function for accessing the singleton EventBus.
    
    Returns:
        The global EventBus instance.
    
    Example:
        >>> bus = get_event_bus()
        >>> bus.file_loaded.connect(my_handler)
        >>> bus.file_loaded.emit("/path/to/file.txt")
    """
    return EventBus.get_instance()
