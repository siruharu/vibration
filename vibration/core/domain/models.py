"""
진동 분석을 위한 도메인 모델.

핵심 비즈니스 엔티티를 나타내는 데이터클래스.
이 모델들은 프레임워크에 독립적이며 Qt 의존성이 없습니다.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Union
from datetime import datetime, date

import numpy as np


@dataclass
class FFTResult:
    """
    FFT 연산 결과.
    
    FFT 처리 후 시간 신호의 주파수 영역 표현과
    연산 관련 메타데이터를 포함합니다.
    
    속성:
        frequency: 주파수 벡터 (Hz).
        spectrum: FFT 스펙트럼 진폭 값.
        view_type: 출력 신호 유형 ('ACC', 'VEL', 'DIS').
        window_type: 사용된 윈도우 함수 ('hanning', 'flattop', 'hamming' 등).
        sampling_rate: 원본 샘플링 레이트 (Hz).
        delta_f: 주파수 분해능 (Hz).
        overlap: 오버랩 비율 (0-100).
        acf: 진폭 보정 계수 (Amplitude Correction Factor).
        ecf: 에너지 보정 계수 (Energy Correction Factor).
        rms: 신호의 RMS (Root Mean Square) 값.
        psd: 파워 스펙트럼 밀도 (선택사항).
        metadata: 추가 연산 메타데이터.
    """
    frequency: np.ndarray
    spectrum: np.ndarray
    view_type: str
    window_type: str
    sampling_rate: float
    delta_f: float
    overlap: float
    acf: float = 1.0
    ecf: float = 1.0
    rms: float = 0.0
    psd: Optional[np.ndarray] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 필드 검증 및 정규화."""
        if isinstance(self.view_type, str):
            self.view_type = self.view_type.upper()
        
        if isinstance(self.window_type, str):
            self.window_type = self.window_type.lower()
        
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def max_frequency(self) -> float:
        """스펙트럼의 최대 주파수를 반환합니다."""
        if len(self.frequency) > 0:
            return float(self.frequency[-1])
        return 0.0
    
    @property
    def peak_frequency(self) -> float:
        """스펙트럼 최대 진폭의 주파수를 반환합니다."""
        if len(self.spectrum) > 0:
            peak_idx = np.argmax(self.spectrum)
            return float(self.frequency[peak_idx])
        return 0.0
    
    @property
    def peak_amplitude(self) -> float:
        """스펙트럼 최대 진폭을 반환합니다."""
        if len(self.spectrum) > 0:
            return float(np.max(self.spectrum))
        return 0.0
    
    @property
    def num_points(self) -> int:
        """주파수 포인트 수를 반환합니다."""
        return len(self.frequency)


@dataclass
class SignalData:
    """
    원시 신호 데이터 컨테이너.
    
    관련 메타데이터와 함께 시간 영역 신호 데이터를 나타냅니다.
    
    속성:
        data: 신호 진폭 값.
        sampling_rate: 샘플링 레이트 (Hz).
        signal_type: 신호 유형 ('ACC', 'VEL', 'DIS').
        channel: 채널 식별자/이름.
        metadata: 추가 신호 메타데이터.
    """
    data: np.ndarray
    sampling_rate: float
    signal_type: str = 'ACC'
    channel: str = ''
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 필드 검증 및 정규화."""
        if isinstance(self.signal_type, str):
            self.signal_type = self.signal_type.upper()
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def duration(self) -> float:
        """신호 지속 시간을 초 단위로 반환합니다."""
        if self.sampling_rate > 0:
            return len(self.data) / self.sampling_rate
        return 0.0
    
    @property
    def num_samples(self) -> int:
        """샘플 수를 반환합니다."""
        return len(self.data)


@dataclass
class TrendResult:
    """
    다중 파일에 대한 트렌드 분석 결과.
    
    배치 처리에서 집계된 RMS 트렌드 데이터를 포함합니다.
    
    속성:
        timestamps: 각 데이터 포인트의 타임스탬프 (datetime 또는 인덱스).
        rms_values: 각 파일의 RMS 값.
        filenames: 처리된 파일명 목록.
        view_type: 출력 신호 유형 ('ACC', 'VEL', 'DIS').
        frequency_band: 적용된 대역 필터 (min_freq, max_freq).
        channel_data: 채널별 집계 데이터.
        peak_values: 각 파일의 피크 값 (선택사항).
        peak_frequencies: 각 파일의 피크 주파수 (선택사항).
        sampling_rate: 공통 샘플링 레이트 (Hz).
        metadata: 추가 분석 메타데이터.
    """
    timestamps: Union[np.ndarray, List[Union[datetime, int]]]
    rms_values: np.ndarray
    filenames: List[str]
    view_type: str
    frequency_band: Optional[Tuple[float, float]] = None
    channel_data: Optional[Dict[str, Dict[str, Any]]] = None
    peak_values: Optional[np.ndarray] = None
    peak_frequencies: Optional[np.ndarray] = None
    sampling_rate: float = 0.0
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 필드 검증 및 정규화."""
        if isinstance(self.view_type, str):
            self.view_type = self.view_type.upper()
        
        if self.metadata is None:
            self.metadata = {}
        
        # 필요시 리스트를 numpy 배열로 변환
        if isinstance(self.rms_values, list):
            self.rms_values = np.array(self.rms_values)
        
        if self.peak_values is not None and isinstance(self.peak_values, list):
            self.peak_values = np.array(self.peak_values)
        
        if self.peak_frequencies is not None and isinstance(self.peak_frequencies, list):
            self.peak_frequencies = np.array(self.peak_frequencies)
    
    @property
    def num_files(self) -> int:
        """처리된 파일 수를 반환합니다."""
        return len(self.filenames)
    
    @property
    def mean_rms(self) -> float:
        """전체 파일의 평균 RMS 값을 반환합니다."""
        if len(self.rms_values) > 0:
            return float(np.mean(self.rms_values))
        return 0.0
    
    @property
    def max_rms(self) -> float:
        """최대 RMS 값을 반환합니다."""
        if len(self.rms_values) > 0:
            return float(np.max(self.rms_values))
        return 0.0
    
    @property
    def min_rms(self) -> float:
        """최소 RMS 값을 반환합니다."""
        if len(self.rms_values) > 0:
            return float(np.min(self.rms_values))
        return 0.0
    
    @property
    def std_rms(self) -> float:
        """RMS 값의 표준편차를 반환합니다."""
        if len(self.rms_values) > 1:
            return float(np.std(self.rms_values))
        return 0.0
    
    @property
    def success_count(self) -> int:
        """성공적으로 처리된 파일 수를 반환합니다."""
        # RMS 값이 0이면 일반적으로 실패를 의미
        return int(np.sum(self.rms_values > 0))


@dataclass
class FileMetadata:
    """
    로드된 진동 데이터 파일의 메타데이터.
    
    파일 시스템 정보와 파일 헤더에서 파싱된 메타데이터를 포함합니다.
    
    속성:
        filename: 파일명 (경로 제외).
        filepath: 파일의 전체 절대 경로.
        size: 파일 크기 (바이트).
        date_modified: 최종 수정 타임스탬프.
        num_channels: 파일의 데이터 채널 수.
        sampling_rate: 샘플링 레이트 (Hz).
        sensitivity: 센서 감도 (선택사항, mV/g).
        b_sensitivity: B 가중 감도 (선택사항).
        duration: 녹음 시간 (초).
        channel: 채널 식별자/이름.
        metadata: 파일의 추가 원시 메타데이터.
    """
    filename: str
    filepath: str
    size: int
    date_modified: str
    num_channels: int = 1
    sampling_rate: float = 0.0
    sensitivity: Optional[float] = None
    b_sensitivity: Optional[float] = None
    duration: Optional[float] = None
    channel: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """초기화 후 필드 검증 및 정규화."""
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def size_kb(self) -> float:
        """파일 크기를 킬로바이트 단위로 반환합니다."""
        return self.size / 1024.0
    
    @property
    def size_mb(self) -> float:
        """파일 크기를 메가바이트 단위로 반환합니다."""
        return self.size / (1024.0 * 1024.0)
    
    @property
    def has_sensitivity(self) -> bool:
        """감도 정의 여부를 확인합니다."""
        return self.sensitivity is not None and self.sensitivity > 0


@dataclass
class ProjectFileInfo:
    """프로젝트 저장 시 개별 파일 정보."""
    relative_path: str
    date: str
    time: str
    channel: str = ''
    sampling_rate: float = 0.0
    sensitivity: str = ''
    is_anomaly: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'relative_path': self.relative_path,
            'date': self.date,
            'time': self.time,
            'channel': self.channel,
            'sampling_rate': self.sampling_rate,
            'sensitivity': self.sensitivity,
            'is_anomaly': self.is_anomaly,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectFileInfo':
        return cls(
            relative_path=data.get('relative_path', ''),
            date=data.get('date', ''),
            time=data.get('time', ''),
            channel=data.get('channel', ''),
            sampling_rate=data.get('sampling_rate', 0.0),
            sensitivity=data.get('sensitivity', ''),
            is_anomaly=data.get('is_anomaly', False),
        )


@dataclass
class ProjectData:
    """프로젝트 저장/로드를 위한 데이터 컨테이너."""
    name: str
    description: str
    created_at: str
    parent_folder: str
    measurement_type: str = 'Unknown'
    files: List[ProjectFileInfo] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    project_folder: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at,
            'parent_folder': self.parent_folder,
            'measurement_type': self.measurement_type,
            'files': [f.to_dict() for f in self.files],
            'summary': self.summary,
            'project_folder': self.project_folder,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectData':
        files = [ProjectFileInfo.from_dict(f) for f in data.get('files', [])]
        return cls(
            name=data.get('name', ''),
            description=data.get('description', ''),
            created_at=data.get('created_at', ''),
            parent_folder=data.get('parent_folder', ''),
            measurement_type=data.get('measurement_type', 'Unknown'),
            files=files,
            summary=data.get('summary', {}),
            project_folder=data.get('project_folder', ''),
        )
