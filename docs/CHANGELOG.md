# 변경 이력: 레거시 → 리팩토링

## 개요

이 문서는 레거시 모놀리식 코드(`cn_3F_trend_optimized.py`)에서 모듈화 MVP 아키텍처(`vibration/`)로의
전체 변경 사항을 기록합니다.

---

## 1. 구조적 변경

### 1.1 파일 구조

| 항목 | 레거시 | 리팩토링 |
|------|--------|---------|
| **파일 수** | 1개 (모놀리스) | 30+ 파일 |
| **총 코드 라인** | ~6,384줄 | ~8,232줄 |
| **최대 파일 크기** | 6,384줄 | 615줄 (spectrum_tab.py) |
| **평균 파일 크기** | 6,384줄 | ~270줄 |
| **디렉토리 깊이** | 1 | 4 (vibration/presentation/views/tabs/) |

### 1.2 아키텍처 패턴

| 항목 | 레거시 | 리팩토링 |
|------|--------|---------|
| **패턴** | 없음 (갓 클래스) | MVP + DI |
| **관심사 분리** | 없음 | core / presentation / infrastructure |
| **의존성 관리** | 암묵적 | 생성자 주입 (ApplicationFactory) |
| **이벤트 통신** | 직접 메서드 호출 | EventBus (PyQt 시그널) |
| **데이터 모델** | 없음 (raw dict/array) | 데이터클래스 (FFTResult, TrendResult 등) |

---

## 2. 모듈별 변경 상세

### 2.1 파일 로딩

#### 레거시: `load_txt_file_only()` in Ui_MainWindow
```python
# 문제점:
# - UI 클래스 내부에 파일 I/O 직접 구현
# - 순차적 처리 (1000개 파일 → 860초)
# - 에러 핸들링 미비
# - 캐싱 없음
def load_txt_file_only(self, file_path):
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            data.append(float(line))
    return np.array(data)
```

#### 리팩토링: FileParser + FileService
```python
# 개선점:
# ✅ 파서와 서비스 분리
# ✅ NumPy 직접 로딩 (np.loadtxt)
# ✅ 메타데이터 캐싱 (_file_cache)
# ✅ 감도 관리 (sensitivity_cache)
# ✅ 디렉토리 스캔 + 날짜/시간 그룹화

# file_parser.py - 단일 파일 파싱
class FileParser:
    def _load_file(self):
        # 메타데이터와 데이터를 한번에 파싱
        # NumPy 벡터화 로딩

# file_service.py - 파일 관리 서비스
class FileService:
    def scan_directory(self, directory, pattern) -> List[FileMetadata]
    def scan_directory_grouped(self, directory, pattern) -> Dict
    def load_file(self, filepath) -> dict
    # 감도 캐싱: set_sensitivity(), get_sensitivity()
```

### 2.2 FFT 연산

#### 레거시: 인라인 FFT in UI 메서드
```python
# 문제점:
# - plot_data_file_spectrem() 내부에 FFT 로직 혼재
# - 신호 변환 로직이 렌더링 코드와 섞임
# - 재사용 불가
```

#### 리팩토링: FFTEngine + FFTService
```python
# fft_engine.py - 저수준 FFT 엔진
class FFTEngine:
    def compute(self, data, view_type, type_flag) -> dict
    # scipy.signal.welch() 기반
    # 윈도우 함수: hanning, flattop, hamming, blackman
    # ACF/ECF 보정 계수 계산

# fft_service.py - 고수준 FFT 서비스
class FFTService:
    def compute_spectrum(self, data, view_type, input_signal_type, zero_padding_freq) -> FFTResult
    # 신호 변환: ACC ↔ VEL ↔ DIS (주파수 영역 적분/미분)
    # 제로 패딩 적용
    # FFTResult 데이터클래스로 결과 반환
```

**변경된 신호 변환 로직:**
| 변환 | 레거시 | 리팩토링 |
|------|--------|---------|
| ACC→VEL | `P / (2πf) * 1000` (인라인) | `_apply_signal_conversion()` jω 나눗셈 |
| ACC→DIS | `P / (2πf)² * 1000` (인라인) | `_apply_signal_conversion()` (jω)² 나눗셈 |
| VEL→ACC | 미지원 | jω 곱셈 |
| DIS→ACC | 미지원 | (jω)² 곱셈 |

### 2.3 트렌드 분석

#### 레거시: `plot_overall()` in Ui_MainWindow
```python
# 문제점:
# - 순차 파일 처리 (for 루프)
# - FFT + RMS 계산 + 렌더링이 하나의 메서드에
# - 진행률 표시 없음 ("파일 처리 중..." 고정 메시지)
# - UI 블로킹
```

#### 리팩토링: TrendService + TrendParallelProcessor + TrendPresenter
```python
# OPTIMIZATION_PATCH_LEVEL5_TREND.py - 병렬 프로세서
class TrendParallelProcessor:
    # ProcessPoolExecutor (CPU 코어 - 1개 워커)
    # 파일별 독립 처리: 로딩 → 메타데이터 → 감도보정 → FFT → RMS/Peak
    # as_completed()로 진행률 콜백

# trend_service.py - 서비스 레이어
class TrendService:
    def compute_trend(self, file_paths, ..., progress_callback) -> TrendResult
    # 병렬 프로세서 호출 → 결과 집계 → 타임스탬프 추출 → 채널 그룹화

# trend_presenter.py - 프레젠터
class TrendPresenter:
    def _on_compute_requested(self):
        # ProgressDialog 생성
        # progress_callback 정의 (update_progress + processEvents)
        # TrendService 호출
        # 결과로 뷰 업데이트
```

### 2.4 워터폴 분석

#### 레거시: `plot_waterfall_spectrum()` in Ui_MainWindow
```python
# 문제점:
# - imshow() 기반 렌더링 (성능 문제)
# - FFT 재연산 (축/각도 변경 시마다)
# - 캐싱 없음
```

#### 리팩토링: WaterfallPresenter
```python
# waterfall_presenter.py
class WaterfallPresenter:
    # FFT 결과 캐싱 (_cached_spectra)
    # 축/각도 변경 시 캐시 활용 (재연산 방지)
    # 3D surface plot 렌더링 분리
```

### 2.5 UI 컴포넌트

#### 레거시: 단일 setupUi() 메서드
```python
# 문제점:
# - 5개 탭의 모든 위젯을 하나의 메서드에서 생성
# - 위젯 이름 충돌 위험
# - 시그널 연결이 산재
```

#### 리팩토링: 탭별 독립 뷰 클래스
```python
# 각 탭이 독립 클래스로 분리:
# - DataQueryTabView: 파일 선택 + 테이블
# - SpectrumTabView: 파형 + 스펙트럼 플롯 + 피킹
# - TrendTabView: RMS 트렌드 그래프 + Pick Data List
# - WaterfallTabView: 3D 워터폴 + 축 컨트롤
# - PeakTabView: 피크 트렌드 그래프 + Pick Data List

# MainWindow는 씬 셸 패턴:
# - 탭 위젯 관리만 수행
# - 비즈니스 로직 없음
# - 226줄 (vs 레거시 6,384줄)
```

### 2.6 데이터 모델

#### 레거시: raw dict/array 직접 사용
```python
# 문제점:
# - 타입 정보 없음
# - 키 오타 시 런타임 에러
# - 문서화 불가
result = {'frequency': f, 'spectrum': P, 'rms': rms}
```

#### 리팩토링: 타입 안전 데이터클래스
```python
@dataclass
class FFTResult:
    frequency: np.ndarray
    spectrum: np.ndarray
    view_type: str
    window_type: str
    sampling_rate: float
    delta_f: float
    overlap: float
    acf: float
    ecf: float
    rms: float
    psd: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 계산 프로퍼티
    @property
    def max_frequency(self) -> float: ...
    @property
    def peak_frequency(self) -> float: ...
    @property
    def peak_amplitude(self) -> float: ...
```

---

## 3. 성능 개선

### 3.1 최적화 이력 (레거시 패치 → 리팩토링)

레거시 코드에 5단계의 최적화 패치가 시도되었으며, 최종적으로 리팩토링에 통합되었습니다.

| 레벨 | 내용 | 기법 | 성능 (1000파일) | 리팩토링 반영 |
|------|------|------|----------------|-------------|
| **원본** | 순차 처리 | for 루프 | ~860초 | - |
| **Level 1** | 파일 캐싱 | .npy 디스크 캐시, NumPy 직접 로딩 | ~150초 | 부분 (인메모리 캐시) |
| **Level 2** | 병렬 처리 | ThreadPoolExecutor 6워커 | ~25초 | 핵심 반영 |
| **Level 3** | 극한 최적화 | 정규식 사전컴파일, 헤더만 파싱 | ~100초 | 부분 반영 |
| **Level 4** | 렌더링 최적화 | draw_idle(), 범례 샘플링 | 즉시 응답 | 프레젠테이션 레이어 |
| **Level 5** | 프로세스 병렬 | ProcessPoolExecutor (CPU-1) | ~3-5초 | **핵심 아키텍처** |
| **리팩토링** | MVP + Level 5 | 모듈화 + ProcessPool | ~3-5초 | 최종 구현 |

### 3.2 최종 성능 비교

| 시나리오 | 레거시 | 리팩토링 | 개선율 |
|----------|--------|---------|--------|
| 1,000 파일 RMS 트렌드 | ~860초 | ~3-5초 | **170-280x** |
| 100 파일 스펙트럼 분석 | ~30초 | ~0.5초 | **60x** |
| 파일 로딩 (캐시 히트) | N/A | 즉시 | ∞ |
| UI 응답성 | 10-30초 멈춤 | 즉시 | **논블로킹** |

---

## 4. 기능별 매핑

### 레거시 메서드 → 리팩토링 모듈 매핑

| 레거시 메서드 | 리팩토링 위치 | 비고 |
|-------------|-------------|------|
| `setupUi()` | `MainWindow.__init__()` + 각 탭 뷰 | 5개 탭으로 분리 |
| `load_txt_file_only()` | `FileParser._load_file()` | NumPy 벡터화 |
| `plot_data_file_spectrem()` | `SpectrumPresenter` + `FFTService` | 연산/렌더링 분리 |
| `plot_overall()` | `TrendPresenter` + `TrendService` | 병렬 처리 |
| `plot_waterfall_spectrum()` | `WaterfallPresenter` | FFT 캐싱 추가 |
| `json.dump()` (26건) | `json_handler.py` (레거시) | EnhancedJSONEncoder |
| `QTableWidget` 조작 | `FileListModel` (QAbstractTableModel) | MVC 분리 |
| 직접 진행률 표시 | `ProgressDialog` + `progress_callback` | 실시간 진행률 |

### 신규 기능 (레거시에 없던 것)

| 기능 | 모듈 | 설명 |
|------|------|------|
| **도메인 모델** | `core/domain/models.py` | 타입 안전 데이터클래스 |
| **이벤트 버스** | `infrastructure/event_bus.py` | 느슨한 결합 통신 |
| **감도 캐싱** | `FileService` | sensitivity/b_sensitivity 관리 |
| **신호 역변환** | `FFTService` | VEL→ACC, DIS→ACC 등 |
| **스플래시 스크린** | `splash_screen.py` | 로딩 진행률 표시 |
| **마커 관리자** | `MarkerManager` | 재사용 가능 마커 시스템 |
| **DPI 스케일링** | `PlotWidget` | 화면 해상도 자동 감지 |
| **반응형 레이아웃** | `ResponsiveLayoutMixin` | DPI 기반 위젯 스케일링 |
| **Pick Data List** | `TrendTabView`, `PeakTabView` | 채널별 파일 피킹 |
| **List Save 다이얼로그** | `ListSaveDialog` | 상세 분석 + CSV 내보내기 |

---

## 5. 레거시 파일 목록 및 상태

### 보존된 레거시 파일 (vibration/legacy/)

| 파일 | 줄 수 | 용도 | 상태 |
|------|------|------|------|
| `cn_3F_trend_optimized.py` | 86 | 호환성 심 (re-export) | 호환 레이어 |
| `OPTIMIZATION_PATCH_LEVEL1.py` | 521 | 파일 캐싱 + NumPy | 참고용 |
| `OPTIMIZATION_PATCH_LEVEL2_PARALLEL.py` | 322 | 병렬 처리 (Thread) | 참고용 |
| `OPTIMIZATION_PATCH_LEVEL3_ULTRA.py` | 412 | 극한 최적화 | 참고용 |
| `OPTIMIZATION_PATCH_LEVEL4_RENDERING.py` | 179 | 렌더링 최적화 | 참고용 |
| `OPTIMIZATION_PATCH_LEVEL5_SPECTRUM.py` | 310 | 스펙트럼 병렬 (Process) | 참고용 |
| `INTEGRATION_GUIDE.py` | 416 | 패치 적용 가이드 | 참고용 |
| `APPLY_GUIDE.py` | 487 | Level 1 적용 가이드 | 참고용 |
| `auto_patcher.py` | 294 | 자동 패칭 프레임워크 | 참고용 |
| `auto_patch.py` | 356 | Level 1 자동 적용 | 참고용 |
| `perf_patcher.py` | 182 | 성능 로깅 패처 | 참고용 |
| `quick_patch.py` | 99 | 빠른 수정 유틸 | 참고용 |
| `bug_fix.py` | 178 | JSON/폰트 버그 수정 | 참고용 |
| `json_handler.py` | 353 | NumPy JSON 직렬화 | 참고용 |
| `performance_wrapper.py` | 40 | @measure_performance | 참고용 |
| `performance_logger.py` | 393 | 성능 로깅 | 참고용 |
| `platform_config.py` | 393 | 크로스플랫폼 설정 | 참고용 |
| `table_optimizer.py` | 385 | QTableView 최적화 | 참고용 |
| `visualization_enhanced.py` | 526 | 시각화 개선 | 참고용 |
| `demo.py` | 296 | 데모 스크립트 | 참고용 |
| `pyqt_plotly_example.py` | 51 | Plotly 예제 | 참고용 |

> **참고**: 모든 레거시 파일은 참조 목적으로만 보존됩니다. 신규 개발 시 `vibration/` 패키지를 사용하세요.
