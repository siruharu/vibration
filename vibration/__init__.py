"""진동 분석 패키지 - 모듈화 아키텍처."""

import sys
from pathlib import Path

__version__ = "2.0.0"
__author__ = "Vibration Analysis Team"


def get_resource_path(relative_path: str) -> Path:
    # PyInstaller exe: sys._MEIPASS points to temp extraction dir
    # Development: project root (parent of vibration/)
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent
    return base / relative_path


def __getattr__(name):
    """패키지 로드 시 Qt 의존성을 피하기 위한 지연 임포트."""
    if name in ('main', 'ApplicationFactory'):
        from .app import main, ApplicationFactory
        return main if name == 'main' else ApplicationFactory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
