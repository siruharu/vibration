"""
애플리케이션 전역 시그널을 위한 이벤트 버스.

모듈 간 직접 의존성 없이 크로스커팅 이벤트 통신을 제공하는 싱글톤 패턴.

사용법:
    from vibration.infrastructure.event_bus import get_event_bus
    
    # 이벤트 구독
    bus = get_event_bus()
    bus.file_loaded.connect(on_file_loaded)
    
    # 이벤트 발행
    bus.file_loaded.emit("/path/to/file.txt")
    
참고:
    크로스커팅 관심사에만 제한적으로 사용하세요.
    대부분의 경우 프레젠터 간 직접 통신을 권장합니다.
"""
from PyQt5.QtCore import QObject, pyqtSignal


class EventBus(QObject):
    """
    애플리케이션 전역 시그널을 위한 싱글톤 이벤트 버스.
    
    느슨하게 결합된 모듈 간 크로스커팅 이벤트 통신을 위한
    중앙 집중식 메커니즘을 제공합니다.
    
    속성:
        file_loaded: 단일 파일 로드 시 발행 (filepath)
        files_loaded: 다중 파일 로드 시 발행 (filepaths 목록)
        analysis_complete: 분석 완료 시 발행 (analysis_type, results)
        error_occurred: 오류 발생 시 발행 (error_type, message)
        progress_updated: 진행률 업데이트 시 발행 (percentage, message)
        data_changed: 데이터 변경 시 발행 (data_type)
        selection_changed: 선택 변경 시 발행 (selected_items)
        tab_changed: 탭 변경 시 발행 (tab_name)
        view_type_changed: 뷰 타입 변경 시 발행 (view_type: ACC/VEL/DIS)
    """
    
    # 애플리케이션 이벤트
    file_loaded = pyqtSignal(str)  # 파일 경로
    files_loaded = pyqtSignal(list)  # 파일 경로 목록
    directory_selected = pyqtSignal(str)  # 디렉토리 경로
    analysis_complete = pyqtSignal(str, dict)  # 분석 유형, 결과
    error_occurred = pyqtSignal(str, str)  # 오류 유형, 메시지
    progress_updated = pyqtSignal(int, str)  # 백분율, 메시지
    
    # 데이터 이벤트
    data_changed = pyqtSignal(str)  # 데이터 유형
    selection_changed = pyqtSignal(list)  # 선택된 항목
    
    # UI 이벤트
    tab_changed = pyqtSignal(str)  # 탭 이름
    view_type_changed = pyqtSignal(str)  # 뷰 타입 (ACC/VEL/DIS)
    
    _instance = None
    
    def __new__(cls):
        """싱글톤 인스턴스를 보장합니다."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            super(EventBus, cls._instance).__init__()
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'EventBus':
        """
        싱글톤 인스턴스를 가져옵니다.
        
        반환:
            전역 EventBus 인스턴스.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        싱글톤 인스턴스를 초기화합니다 (테스트 용도).
        
        경고:
            테스트에서만 사용하세요. 기존의 모든 연결이 끊어집니다.
        """
        cls._instance = None


def get_event_bus() -> EventBus:
    """
    전역 이벤트 버스 인스턴스를 가져옵니다.
    
    싱글톤 EventBus에 접근하기 위한 편의 함수.
    
    반환:
        전역 EventBus 인스턴스.
    
    예시:
        >>> bus = get_event_bus()
        >>> bus.file_loaded.connect(my_handler)
        >>> bus.file_loaded.emit("/path/to/file.txt")
    """
    return EventBus.get_instance()
