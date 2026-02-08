"""
그래프 시각화 개선 모듈
- Waterfall 차트 현대화
- 모든 그래프 디자인 통일
- 고해상도 렌더링
- 인터랙티브 기능 추가
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Rectangle
from scipy import signal
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class ModernPlotStyle:
    """
    현대적인 플롯 스타일 정의
    """
    
    # 컬러 팔레트 (Material Design 기반)
    COLORS = {
        'primary': '#2196F3',      # Blue
        'secondary': '#FF9800',    # Orange
        'success': '#4CAF50',      # Green
        'danger': '#F44336',       # Red
        'warning': '#FFC107',      # Amber
        'info': '#00BCD4',         # Cyan
        'dark': '#212121',         # Dark Gray
        'light': '#F5F5F5'         # Light Gray
    }
    
    # 컬러맵
    COLORMAPS = {
        'default': 'viridis',
        'thermal': 'hot',
        'ocean': 'ocean',
        'rainbow': 'rainbow',
        'grayscale': 'gray'
    }
    
    # 폰트 크기
    FONT_SIZES = {
        'title': 14,
        'label': 12,
        'tick': 10,
        'legend': 10
    }
    
    # DPI 설정
    DPI = {
        'screen': 100,
        'print': 300,
        'presentation': 150
    }


class WaterfallPlotEnhanced:
    """
    개선된 Waterfall (Spectrogram) 차트
    - 고품질 렌더링
    - 로그 스케일 지원
    - 피크 감지 및 하이라이트
    """
    
    def __init__(self, style: str = 'modern'):
        """
        Args:
            style: 'modern', 'classic', 'minimal'
        """
        self.style = style
        self.fig = None
        self.ax = None
        self._setup_style()
    
    def _setup_style(self):
        """스타일 적용"""
        if self.style == 'modern':
            plt.style.use('seaborn-v0_8-darkgrid')
        elif self.style == 'minimal':
            plt.style.use('seaborn-v0_8-white')
        else:
            plt.style.use('classic')
    
    def create_waterfall(
        self,
        data: np.ndarray,
        frequencies: np.ndarray,
        times: np.ndarray,
        cmap: str = 'viridis',
        title: str = "Waterfall Plot",
        freq_scale: str = 'log',  # 'linear' or 'log'
        db_range: Tuple[float, float] = None,
        dpi: int = 150,
        figsize: Tuple[float, float] = (12, 6)
    ) -> Tuple[plt.Figure, plt.Axes]:
        """
        Waterfall 차트 생성
        
        Args:
            data: STFT 결과 (freq x time)
            frequencies: 주파수 배열 [Hz]
            times: 시간 배열 [s]
            cmap: 컬러맵 이름
            title: 차트 제목
            freq_scale: 주파수 축 스케일 ('linear' or 'log')
            db_range: dB 범위 (min, max), None이면 자동
            dpi: 해상도
            figsize: 그림 크기
        
        Returns:
            (figure, axes) 튜플
        """
        # Figure 생성
        self.fig, self.ax = plt.subplots(figsize=figsize, dpi=dpi)
        
        # 데이터 전처리: 크기를 dB로 변환
        magnitude = np.abs(data)
        magnitude_db = 20 * np.log10(magnitude + 1e-10)  # 0 방지
        
        # dB 범위 설정
        if db_range is None:
            vmin = np.percentile(magnitude_db, 5)   # 하위 5%
            vmax = np.percentile(magnitude_db, 95)  # 상위 95%
        else:
            vmin, vmax = db_range
        
        # Pcolormesh로 렌더링 (imshow보다 빠르고 유연함)
        mesh = self.ax.pcolormesh(
            times,
            frequencies,
            magnitude_db,
            cmap=cmap,
            shading='gouraud',  # 부드러운 그라데이션
            rasterized=True,    # PDF 저장 시 최적화
            vmin=vmin,
            vmax=vmax
        )
        
        # 주파수 축 스케일
        if freq_scale == 'log':
            self.ax.set_yscale('log')
            # 로그 스케일에서 y축 범위 제한 (너무 낮은 주파수 제외)
            freq_min = max(frequencies[frequencies > 0].min(), 10)
            freq_max = frequencies.max()
            self.ax.set_ylim(freq_min, freq_max)
        
        # 레이블 및 제목
        self.ax.set_xlabel('Time (s)', fontsize=ModernPlotStyle.FONT_SIZES['label'], weight='bold')
        self.ax.set_ylabel('Frequency (Hz)', fontsize=ModernPlotStyle.FONT_SIZES['label'], weight='bold')
        self.ax.set_title(title, fontsize=ModernPlotStyle.FONT_SIZES['title'], weight='bold', pad=15)
        
        # 컬러바 추가 (개선된 스타일)
        cbar = self.fig.colorbar(mesh, ax=self.ax, label='Magnitude (dB)', pad=0.01)
        cbar.ax.tick_params(labelsize=ModernPlotStyle.FONT_SIZES['tick'])
        
        # 그리드 (선택적)
        self.ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        
        # 틱 스타일
        self.ax.tick_params(labelsize=ModernPlotStyle.FONT_SIZES['tick'])
        
        # 레이아웃 최적화
        plt.tight_layout()
        
        return self.fig, self.ax
    
    def add_peak_markers(
        self,
        peak_times: List[float],
        peak_freqs: List[float],
        labels: Optional[List[str]] = None,
        color: str = 'red',
        marker: str = 'x',
        size: int = 100
    ):
        """
        피크 포인트 하이라이트
        
        Args:
            peak_times: 피크 시간 리스트
            peak_freqs: 피크 주파수 리스트
            labels: 각 피크의 레이블 (선택)
            color: 마커 색상
            marker: 마커 모양
            size: 마커 크기
        """
        if not self.ax:
            raise ValueError("먼저 create_waterfall()을 호출하세요")
        
        # 피크 포인트 표시
        scatter = self.ax.scatter(
            peak_times,
            peak_freqs,
            c=color,
            s=size,
            marker=marker,
            linewidths=2,
            zorder=10,
            edgecolors='white',
            label='Detected Peaks'
        )
        
        # 레이블 추가 (선택)
        if labels:
            for t, f, label in zip(peak_times, peak_freqs, labels):
                self.ax.annotate(
                    label,
                    xy=(t, f),
                    xytext=(5, 5),
                    textcoords='offset points',
                    fontsize=8,
                    color=color,
                    weight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
                )
        
        # 범례
        self.ax.legend(loc='upper right', fontsize=ModernPlotStyle.FONT_SIZES['legend'])
    
    def add_frequency_band(
        self,
        freq_low: float,
        freq_high: float,
        label: str = "",
        color: str = 'yellow',
        alpha: float = 0.2
    ):
        """
        특정 주파수 대역 하이라이트
        
        Args:
            freq_low: 하한 주파수 [Hz]
            freq_high: 상한 주파수 [Hz]
            label: 대역 레이블
            color: 색상
            alpha: 투명도
        """
        if not self.ax:
            raise ValueError("먼저 create_waterfall()을 호출하세요")
        
        self.ax.axhspan(freq_low, freq_high, color=color, alpha=alpha, label=label)
        if label:
            self.ax.legend(loc='upper right')
    
    def save(self, filepath: str, dpi: int = 300, transparent: bool = False):
        """
        고해상도 저장
        
        Args:
            filepath: 저장 경로
            dpi: 해상도
            transparent: 배경 투명 여부
        """
        if not self.fig:
            raise ValueError("먼저 create_waterfall()을 호출하세요")
        
        self.fig.savefig(
            filepath,
            dpi=dpi,
            bbox_inches='tight',
            transparent=transparent,
            facecolor='white' if not transparent else 'none'
        )
        logger.info(f"Waterfall 차트 저장: {filepath}")


class FFTPlotEnhanced:
    """
    개선된 FFT 스펙트럼 차트
    """
    
    def __init__(self):
        self.fig = None
        self.ax = None
    
    def create_fft_plot(
        self,
        frequencies: np.ndarray,
        magnitudes: np.ndarray,
        title: str = "FFT Spectrum",
        freq_range: Tuple[float, float] = None,
        scale: str = 'db',  # 'db' or 'linear'
        figsize: Tuple[float, float] = (10, 5),
        dpi: int = 150
    ) -> Tuple[plt.Figure, plt.Axes]:
        """
        FFT 스펙트럼 플롯 생성
        
        Args:
            frequencies: 주파수 배열
            magnitudes: 크기 배열
            title: 제목
            freq_range: 표시할 주파수 범위 (Hz)
            scale: 'db' (데시벨) 또는 'linear'
            figsize: 그림 크기
            dpi: 해상도
        """
        self.fig, self.ax = plt.subplots(figsize=figsize, dpi=dpi)
        
        # 스케일 변환
        if scale == 'db':
            plot_data = 20 * np.log10(magnitudes + 1e-10)
            ylabel = 'Magnitude (dB)'
        else:
            plot_data = magnitudes
            ylabel = 'Magnitude'
        
        # 플롯
        self.ax.plot(
            frequencies,
            plot_data,
            color=ModernPlotStyle.COLORS['primary'],
            linewidth=1.5,
            alpha=0.8
        )
        
        # 주파수 범위 설정
        if freq_range:
            self.ax.set_xlim(freq_range)
        
        # 레이블
        self.ax.set_xlabel('Frequency (Hz)', fontsize=ModernPlotStyle.FONT_SIZES['label'], weight='bold')
        self.ax.set_ylabel(ylabel, fontsize=ModernPlotStyle.FONT_SIZES['label'], weight='bold')
        self.ax.set_title(title, fontsize=ModernPlotStyle.FONT_SIZES['title'], weight='bold')
        
        # 그리드
        self.ax.grid(True, alpha=0.3, linestyle='--')
        
        # 틱
        self.ax.tick_params(labelsize=ModernPlotStyle.FONT_SIZES['tick'])
        
        plt.tight_layout()
        
        return self.fig, self.ax
    
    def add_peak_annotations(
        self,
        peak_freqs: List[float],
        peak_mags: List[float],
        n_top: int = 5
    ):
        """
        주요 피크에 주석 달기
        
        Args:
            peak_freqs: 피크 주파수들
            peak_mags: 피크 크기들
            n_top: 표시할 상위 피크 개수
        """
        if not self.ax:
            raise ValueError("먼저 create_fft_plot()을 호출하세요")
        
        # 상위 N개 피크 선택
        indices = np.argsort(peak_mags)[-n_top:]
        
        for idx in indices:
            freq = peak_freqs[idx]
            mag = peak_mags[idx]
            
            # 마커
            self.ax.plot(freq, mag, 'ro', markersize=8, zorder=10)
            
            # 주석
            self.ax.annotate(
                f'{freq:.1f} Hz',
                xy=(freq, mag),
                xytext=(10, 10),
                textcoords='offset points',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='red')
            )


class TrendPlotEnhanced:
    """
    개선된 트렌드 차트 (시계열)
    """
    
    def __init__(self):
        self.fig = None
        self.ax = None
    
    def create_trend_plot(
        self,
        times: np.ndarray,
        values: np.ndarray,
        title: str = "Trend Analysis",
        ylabel: str = "Value",
        figsize: Tuple[float, float] = (12, 4),
        dpi: int = 150
    ) -> Tuple[plt.Figure, plt.Axes]:
        """
        트렌드 플롯 생성
        """
        self.fig, self.ax = plt.subplots(figsize=figsize, dpi=dpi)
        
        # 메인 라인
        self.ax.plot(
            times,
            values,
            color=ModernPlotStyle.COLORS['primary'],
            linewidth=2,
            alpha=0.8,
            label='Data'
        )
        
        # 영역 채우기 (선택)
        self.ax.fill_between(
            times,
            values,
            alpha=0.2,
            color=ModernPlotStyle.COLORS['primary']
        )
        
        # 레이블
        self.ax.set_xlabel('Time (s)', fontsize=ModernPlotStyle.FONT_SIZES['label'], weight='bold')
        self.ax.set_ylabel(ylabel, fontsize=ModernPlotStyle.FONT_SIZES['label'], weight='bold')
        self.ax.set_title(title, fontsize=ModernPlotStyle.FONT_SIZES['title'], weight='bold')
        
        # 그리드
        self.ax.grid(True, alpha=0.3, linestyle='--')
        
        # 틱
        self.ax.tick_params(labelsize=ModernPlotStyle.FONT_SIZES['tick'])
        
        plt.tight_layout()
        
        return self.fig, self.ax
    
    def add_threshold_line(self, threshold: float, label: str = "Threshold", color: str = 'red'):
        """임계값 라인 추가"""
        if not self.ax:
            raise ValueError("먼저 create_trend_plot()을 호출하세요")
        
        self.ax.axhline(
            threshold,
            color=color,
            linestyle='--',
            linewidth=2,
            label=label
        )
        self.ax.legend()


# ===== 기존 코드 통합용 래퍼 함수 =====

def create_modern_waterfall(data, freqs, times, **kwargs):
    """
    기존 waterfall 함수를 대체하는 래퍼
    
    기존 코드:
        fig, ax = create_waterfall(data, freqs, times)
    
    개선 코드:
        from visualization_enhanced import create_modern_waterfall as create_waterfall
        fig, ax = create_waterfall(data, freqs, times)
    """
    plotter = WaterfallPlotEnhanced()
    return plotter.create_waterfall(data, freqs, times, **kwargs)


if __name__ == "__main__":
    # 테스트 코드
    
    # 1. Waterfall 테스트
    print("Waterfall 차트 생성 테스트...")
    
    # 샘플 데이터 생성
    duration = 5.0  # 초
    sr = 44100
    n_fft = 2048
    
    # 테스트 신호 (chirp)
    t = np.linspace(0, duration, int(sr * duration))
    f0, f1 = 100, 8000
    signal_test = signal.chirp(t, f0, duration, f1, method='linear')
    
    # STFT 계산
    f, t_stft, Zxx = signal.stft(signal_test, sr, nperseg=n_fft)
    
    # Waterfall 생성
    plotter = WaterfallPlotEnhanced(style='modern')
    fig, ax = plotter.create_waterfall(
        Zxx,
        f,
        t_stft,
        title="테스트 Waterfall - Chirp 신호",
        cmap='viridis',
        freq_scale='log'
    )
    
    # 피크 추가 (예시)
    plotter.add_peak_markers([1.0, 2.5, 4.0], [1000, 3000, 6000])
    
    # 저장
    fig.savefig('/tmp/waterfall_test.png', dpi=300)
    print("✓ Waterfall 저장: /tmp/waterfall_test.png")
    plt.close()
    
    # 2. FFT 테스트
    print("FFT 차트 생성 테스트...")
    
    fft_plotter = FFTPlotEnhanced()
    freqs_fft = np.fft.rfftfreq(len(signal_test), 1/sr)
    mags_fft = np.abs(np.fft.rfft(signal_test))
    
    fig, ax = fft_plotter.create_fft_plot(
        freqs_fft,
        mags_fft,
        title="테스트 FFT 스펙트럼",
        freq_range=(0, 10000),
        scale='db'
    )
    
    fig.savefig('/tmp/fft_test.png', dpi=300)
    print("✓ FFT 저장: /tmp/fft_test.png")
    plt.close()
    
    print("\n모든 테스트 완료!")
