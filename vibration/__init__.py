"""진동 분석 패키지 - 모듈화 아키텍처."""

__version__ = "2.0.0"
__author__ = "Vibration Analysis Team"

def __getattr__(name):
    """패키지 로드 시 Qt 의존성을 피하기 위한 지연 임포트."""
    if name in ('main', 'ApplicationFactory'):
        from .app import main, ApplicationFactory
        return main if name == 'main' else ApplicationFactory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
