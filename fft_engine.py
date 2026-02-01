"""
최적화된 FFT 엔진
- NumPy 벡터화 FFT
- 캐싱
- 병렬 처리 지원
"""

import numpy as np
from scipy import signal


class FFTEngine:
    """최적화된 FFT 엔진"""

    def __init__(self, sampling_rate, delta_f, overlap, window_type='hanning'):
        """
        FFT 엔진 초기화

        Args:
            sampling_rate (float): 샘플링 레이트 (Hz)
            delta_f (float): 주파수 해상도 (Hz)
            overlap (float): 오버랩 비율 (0-100)
            window_type (str): 윈도우 타입 ('hanning', 'flattop', 등)
        """
        self.sampling_rate = sampling_rate
        self.delta_f = delta_f
        self.overlap = overlap / 100.0  # 퍼센트를 비율로 변환
        self.window_type = window_type.lower()

        # FFT 파라미터 계산
        self.nfft = int(sampling_rate / delta_f)
        self.noverlap = int(self.nfft * self.overlap)

        # 윈도우 함수 생성
        self._window = self._create_window()

    def _create_window(self):
        """윈도우 함수 생성"""
        if self.window_type == 'hanning':
            return np.hanning(self.nfft)
        elif self.window_type == 'flattop':
            return signal.flattop(self.nfft)
        elif self.window_type == 'hamming':
            return np.hamming(self.nfft)
        elif self.window_type == 'blackman':
            return np.blackman(self.nfft)
        else:
            # 기본값: Hanning
            return np.hanning(self.nfft)

    def compute(self, data, view_type=1, type_flag=2):
        """
        FFT 계산

        Args:
            data (np.ndarray): 입력 데이터
            view_type (int): 뷰 타입 (1=ACC, 2=VEL, 3=DIS)
            type_flag (int): 타입 플래그 (2=spectrum)

        Returns:
            dict: FFT 결과
                - frequency: 주파수 배열
                - spectrum: 스펙트럼 (P)
                - acf: 진폭 보정 계수
                - ecf: 에너지 보정 계수
                - rms: RMS 값
                - psd: Power Spectral Density (선택적)
        """
        try:
            # 데이터 길이 확인
            if len(data) < self.nfft:
                raise ValueError(f"데이터 길이({len(data)})가 NFFT({self.nfft})보다 작음")

            # Welch's method를 사용한 스펙트럼 계산
            f, Pxx = signal.welch(
                data,
                fs=self.sampling_rate,
                window=self._window,
                nperseg=self.nfft,
                noverlap=self.noverlap,
                nfft=self.nfft,
                scaling='spectrum',  # PSD가 아닌 spectrum
                return_onesided=True
            )

            # 스펙트럼을 RMS로 변환
            P = np.sqrt(Pxx)

            # 보정 계수 계산
            ACF = self._calculate_acf()  # 진폭 보정 계수
            ECF = self._calculate_ecf()  # 에너지 보정 계수

            # View Type에 따른 변환
            if view_type == 2:  # VEL (속도)
                # 가속도 → 속도: 적분 (주파수 도메인에서 나누기)
                P = P / (2 * np.pi * f + 1e-10)  # 0으로 나누기 방지
                P[0] = 0  # DC 성분 제거

            elif view_type == 3:  # DIS (변위)
                # 가속도 → 변위: 이중 적분
                P = P / ((2 * np.pi * f) ** 2 + 1e-10)
                P[0] = 0  # DC 성분 제거

            # RMS 계산
            rms_w = np.sqrt(np.mean(data ** 2))

            result = {
                'frequency': f,
                'spectrum': P,
                'acf': ACF,
                'ecf': ECF,
                'rms': rms_w,
                'psd': Pxx
            }

            return result

        except Exception as e:
            raise RuntimeError(f"FFT 계산 실패: {e}")

    def _calculate_acf(self):
        """
        ACF (Amplitude Correction Factor) 계산

        Returns:
            float: 진폭 보정 계수
        """
        # 윈도우 함수의 평균값으로 보정
        window_mean = np.mean(self._window)

        if window_mean > 0:
            return 1.0 / window_mean
        else:
            return 1.0

    def _calculate_ecf(self):
        """
        ECF (Energy Correction Factor) 계산

        Returns:
            float: 에너지 보정 계수
        """
        # 윈도우 함수의 RMS로 보정
        window_rms = np.sqrt(np.mean(self._window ** 2))

        if window_rms > 0:
            return 1.0 / window_rms
        else:
            return 1.0

    def get_parameters(self):
        """FFT 파라미터 반환"""
        return {
            'sampling_rate': self.sampling_rate,
            'delta_f': self.delta_f,
            'overlap': self.overlap * 100,  # 비율을 퍼센트로
            'window_type': self.window_type,
            'nfft': self.nfft,
            'noverlap': self.noverlap
        }


# ========================================
# 테스트 코드
# ========================================

if __name__ == "__main__":
    # 테스트 신호 생성
    sampling_rate = 10240.0
    duration = 1.0
    t = np.linspace(0, duration, int(sampling_rate * duration))

    # 100 Hz 사인파 + 노이즈
    signal_data = np.sin(2 * np.pi * 100 * t) + 0.1 * np.random.randn(len(t))

    print("🔍 FFT 엔진 테스트")
    print("="*60)

    # FFT 엔진 생성
    engine = FFTEngine(
        sampling_rate=sampling_rate,
        delta_f=1.0,
        overlap=50.0,
        window_type='hanning'
    )

    print("📋 FFT 파라미터:")
    params = engine.get_parameters()
    for key, value in params.items():
        print(f"  - {key}: {value}")

    # FFT 계산
    print("\n⚡ FFT 계산 중...")
    result = engine.compute(signal_data, view_type=1, type_flag=2)

    print(f"✅ 계산 완료!")
    print(f"📊 주파수 개수: {len(result['frequency'])}")
    print(f"📈 최대 진폭 주파수: {result['frequency'][np.argmax(result['spectrum'])]} Hz")
    print(f"📉 RMS 값: {result['rms']:.6f}")
    print(f"🔧 ACF: {result['acf']:.6f}")
    print(f"🔧 ECF: {result['ecf']:.6f}")