"""
크로스 플랫폼 호환성 모듈
- Windows/Mac 자동 감지
- 폰트 자동 선택
- 경로 처리 통일
- DPI 스케일링 대응
"""

import platform
import sys
from pathlib import Path
from typing import Optional, Tuple
import matplotlib.pyplot as plt
from matplotlib import font_manager
import logging

logger = logging.getLogger(__name__)


class PlatformManager:
    """
    플랫폼별 설정 자동 관리
    """
    
    def __init__(self):
        self.system = platform.system()  # 'Windows', 'Darwin', 'Linux'
        self.is_windows = self.system == 'Windows'
        self.is_mac = self.system == 'Darwin'
        self.is_linux = self.system == 'Linux'
        
        # 시스템 정보
        self.python_version = sys.version
        self.platform_info = platform.platform()
        
        logger.info(f"플랫폼 감지: {self.system}")
        logger.info(f"Python: {self.python_version}")
    
    def get_default_font(self) -> str:
        """
        OS별 기본 한글 폰트 반환
        """
        if self.is_mac:
            fonts = [
                'AppleGothic',
                'Apple SD Gothic Neo',
                'Apple SD 산돌고딕 Neo',
                'Nanum Gothic',
                'NanumGothic'
            ]
        elif self.is_windows:
            fonts = [
                'Malgun Gothic',
                '맑은 고딕',
                'Gulim',
                '굴림',
                'Dotum',
                '돋움',
                'Nanum Gothic'
            ]
        else:  # Linux
            fonts = [
                'Nanum Gothic',
                'NanumGothic',
                'DejaVu Sans',
                'Liberation Sans'
            ]
        
        return fonts
    
    def get_home_directory(self) -> Path:
        """OS별 홈 디렉토리"""
        return Path.home()
    
    def get_documents_directory(self) -> Path:
        """OS별 Documents 폴더"""
        if self.is_windows:
            # Windows: C:\Users\username\Documents
            return Path.home() / 'Documents'
        elif self.is_mac:
            # Mac: /Users/username/Documents
            return Path.home() / 'Documents'
        else:
            # Linux: /home/username/Documents 또는 ~/문서
            docs = Path.home() / 'Documents'
            if not docs.exists():
                docs = Path.home() / '문서'
            return docs
    
    def normalize_path(self, path_str: str) -> Path:
        """
        경로 문자열을 OS에 맞게 정규화
        
        기존 문제: Windows에서 하드코딩된 경로
            path = "C:\\Users\\...\\file.wav"  # Mac에서 작동 안 함
        
        해결:
            path = platform_mgr.normalize_path(path_str)
        """
        # 백슬래시를 슬래시로 통일
        normalized = path_str.replace('\\', '/')
        return Path(normalized)
    
    def get_temp_directory(self) -> Path:
        """임시 디렉토리"""
        import tempfile
        return Path(tempfile.gettempdir())
    
    def get_separator(self) -> str:
        """경로 구분자"""
        return '\\' if self.is_windows else '/'


class FontManager:
    """
    폰트 자동 설정 및 관리
    """
    
    def __init__(self, platform_mgr: PlatformManager = None):
        self.platform = platform_mgr or PlatformManager()
        self.available_fonts = self._get_available_fonts()
        self.selected_font = None
    
    def _get_available_fonts(self) -> list:
        """시스템에 설치된 모든 폰트 목록"""
        return [f.name for f in font_manager.fontManager.ttflist]
    
    def setup_matplotlib_korean_font(self) -> bool:
        """
        Matplotlib 한글 폰트 자동 설정
        
        Returns:
            성공 여부
        """
        candidate_fonts = self.platform.get_default_font()
        
        for font_name in candidate_fonts:
            if font_name in self.available_fonts:
                try:
                    # Matplotlib 전역 설정
                    plt.rcParams['font.family'] = font_name
                    plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
                    
                    self.selected_font = font_name
                    logger.info(f"✓ Matplotlib 폰트 설정: {font_name}")
                    return True
                except Exception as e:
                    logger.warning(f"폰트 설정 실패 ({font_name}): {e}")
                    continue
        
        logger.warning("⚠ 한글 폰트를 찾을 수 없습니다. 기본 폰트 사용")
        return False
    
    def get_pyqt_font(self, size: int = 10, bold: bool = False) -> 'QFont':
        """
        PyQt용 폰트 객체 생성
        
        Args:
            size: 폰트 크기
            bold: 굵게 여부
        """
        from PyQt5.QtGui import QFont
        
        # 한글 폰트 선택
        candidate_fonts = self.platform.get_default_font()
        font_name = None
        
        for font in candidate_fonts:
            if font in self.available_fonts:
                font_name = font
                break
        
        if not font_name:
            font_name = "Arial"  # Fallback
        
        qfont = QFont(font_name, size)
        if bold:
            qfont.setBold(True)
        
        return qfont
    
    def list_korean_fonts(self) -> list:
        """설치된 한글 폰트 목록"""
        korean_keywords = ['gothic', 'goth', 'gulim', 'dotum', 'malgun', 
                          'nanum', '고딕', '굴림', '돋움', '맑은']
        
        korean_fonts = []
        for font in self.available_fonts:
            if any(keyword in font.lower() for keyword in korean_keywords):
                korean_fonts.append(font)
        
        return korean_fonts


class DPIScaler:
    """
    High DPI 디스플레이 대응
    """
    
    def __init__(self):
        self.scale_factor = self._get_scale_factor()
    
    def _get_scale_factor(self) -> float:
        """
        시스템 DPI 스케일 팩터 계산
        """
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                screen = app.primaryScreen()
                dpi = screen.logicalDotsPerInch()
                # 기준 DPI = 96
                return dpi / 96.0
            return 1.0
        except:
            return 1.0
    
    def scale_size(self, size: int) -> int:
        """크기를 DPI에 맞게 조정"""
        return int(size * self.scale_factor)
    
    def scale_geometry(self, width: int, height: int) -> Tuple[int, int]:
        """윈도우 크기를 DPI에 맞게 조정"""
        return (
            int(width * self.scale_factor),
            int(height * self.scale_factor)
        )


class PathHelper:
    """
    경로 처리 헬퍼 (크로스 플랫폼)
    """
    
    def __init__(self, platform_mgr: PlatformManager = None):
        self.platform = platform_mgr or PlatformManager()
    
    def ensure_directory(self, path: Path) -> Path:
        """디렉토리 생성 (없으면)"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_safe_filename(self, filename: str) -> str:
        """
        안전한 파일명 생성 (특수문자 제거)
        """
        # Windows에서 금지된 문자: < > : " / \ | ? *
        forbidden = '<>:"/\\|?*'
        safe = filename
        for char in forbidden:
            safe = safe.replace(char, '_')
        return safe
    
    def join_path(self, *parts) -> Path:
        """경로 조합 (OS 독립적)"""
        return Path(*parts)
    
    def convert_to_absolute(self, path: str) -> Path:
        """상대 경로 → 절대 경로"""
        return Path(path).absolute()


# ===== 전역 인스턴스 (싱글톤 패턴) =====
_platform_manager = None
_font_manager = None
_dpi_scaler = None
_path_helper = None


def get_platform_manager() -> PlatformManager:
    """PlatformManager 싱글톤 인스턴스"""
    global _platform_manager
    if _platform_manager is None:
        _platform_manager = PlatformManager()
    return _platform_manager


def get_font_manager() -> FontManager:
    """FontManager 싱글톤 인스턴스"""
    global _font_manager
    if _font_manager is None:
        _font_manager = FontManager()
    return _font_manager


def get_dpi_scaler() -> DPIScaler:
    """DPIScaler 싱글톤 인스턴스"""
    global _dpi_scaler
    if _dpi_scaler is None:
        _dpi_scaler = DPIScaler()
    return _dpi_scaler


def get_path_helper() -> PathHelper:
    """PathHelper 싱글톤 인스턴스"""
    global _path_helper
    if _path_helper is None:
        _path_helper = PathHelper()
    return _path_helper


# ===== 초기화 함수 =====

def initialize_platform_support():
    """
    애플리케이션 시작 시 호출 - 모든 플랫폼 설정 자동화
    
    사용법:
        from platform_config import initialize_platform_support
        
        if __name__ == "__main__":
            initialize_platform_support()  # 앱 시작 시 한 번만 호출
            app = QApplication(sys.argv)
            # ...
    """
    logger.info("=== 플랫폼 초기화 시작 ===")
    
    # 1. 플랫폼 감지
    platform_mgr = get_platform_manager()
    logger.info(f"운영체제: {platform_mgr.system}")
    
    # 2. 폰트 설정
    font_mgr = get_font_manager()
    font_mgr.setup_matplotlib_korean_font()
    
    # 3. DPI 스케일링
    dpi_scaler = get_dpi_scaler()
    logger.info(f"DPI 스케일: {dpi_scaler.scale_factor:.2f}x")
    
    # 4. 경로 헬퍼 초기화
    path_helper = get_path_helper()
    logger.info(f"Documents: {platform_mgr.get_documents_directory()}")
    
    logger.info("=== 플랫폼 초기화 완료 ===")
    
    return {
        'platform': platform_mgr,
        'font': font_mgr,
        'dpi': dpi_scaler,
        'path': path_helper
    }


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)
    
    # 초기화
    config = initialize_platform_support()
    
    # 플랫폼 정보
    print("\n=== 플랫폼 정보 ===")
    print(f"OS: {config['platform'].system}")
    print(f"Python: {sys.version}")
    
    # 폰트 정보
    print("\n=== 폰트 정보 ===")
    print(f"선택된 폰트: {config['font'].selected_font}")
    korean_fonts = config['font'].list_korean_fonts()
    print(f"설치된 한글 폰트 ({len(korean_fonts)}개):")
    for font in korean_fonts[:5]:  # 처음 5개만 표시
        print(f"  - {font}")
    
    # DPI 정보
    print("\n=== DPI 정보 ===")
    print(f"스케일 팩터: {config['dpi'].scale_factor:.2f}")
    print(f"800px → {config['dpi'].scale_size(800)}px")
    
    # 경로 정보
    print("\n=== 경로 정보 ===")
    print(f"Home: {config['platform'].get_home_directory()}")
    print(f"Documents: {config['platform'].get_documents_directory()}")
    print(f"Temp: {config['platform'].get_temp_directory()}")
    
    # 경로 처리 테스트
    print("\n=== 경로 처리 테스트 ===")
    test_path = "C:\\Users\\Test\\file.wav"
    normalized = config['platform'].normalize_path(test_path)
    print(f"원본: {test_path}")
    print(f"정규화: {normalized}")
    
    # Matplotlib 테스트
    print("\n=== Matplotlib 한글 테스트 ===")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([1, 2, 3], [1, 4, 2])
    ax.set_title("한글 테스트 - 그래프 제목")
    ax.set_xlabel("시간 (초)")
    ax.set_ylabel("진폭")
    plt.savefig('/tmp/korean_test.png', dpi=100)
    print("✓ 한글 그래프 생성 완료: /tmp/korean_test.png")
    plt.close()
