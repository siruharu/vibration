"""Vibration analysis package - modular architecture."""

__version__ = "2.0.0"
__author__ = "Vibration Analysis Team"

def __getattr__(name):
    """Lazy import to avoid Qt dependency on package load."""
    if name in ('main', 'ApplicationFactory'):
        from .app import main, ApplicationFactory
        return main if name == 'main' else ApplicationFactory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
