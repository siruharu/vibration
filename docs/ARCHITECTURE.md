# CNAVE 아키텍처 문서

## 개요

CNAVE(진동 분석 애플리케이션)는 레거시 모놀리식 코드(`cn_3F_trend_optimized.py`, ~6,384줄)에서
MVP(Model-View-Presenter) 패턴 기반 모듈화 아키텍처로 전면 리팩토링되었습니다.

---

## 1. 아키텍처 비교: 레거시 vs 리팩토링

### 레거시 (Before)

```
cn_3F_trend_optimized.py (6,384줄, 단일 파일)
├── Ui_MainWindow 클래스
│   ├── setupUi()           ← UI 생성
│   ├── load_txt_file_only() ← 파일 I/O (비즈니스 로직 혼재)
│   ├── plot_data_file_spectrem() ← FFT 연산 + 렌더링 혼재
│   ├── plot_overall()       ← RMS 트렌드 연산 + 렌더링 혼재
│   ├── plot_waterfall_spectrum() ← 워터폴 3D + FFT 혼재
│   ├── json.dump() 호출 26+건  ← 직렬화 로직 산재
│   └── QTableWidget 직접 조작  ← 데이터 모델 없음
│
├── 문제점:
│   ❌ 관심사 분리 없음 (UI + 비즈니스 로직 + 데이터 접근 혼재)
│   ❌ 테스트 불가능 (UI 의존성)
│   ❌ 순차적 파일 처리 (UI 멈춤)
│   ❌ NumPy 배열 JSON 직렬화 오류
│   ❌ 캐싱 없음 (반복 로딩 시 성능 저하)
│   ❌ 코드 재사용 불가
└── 결과: 유지보수 어려움, 기능 추가 시 사이드이펙트 빈발
```

### 리팩토링 (After)

```
vibration/ (8,232줄, 30+ 파일)
├── core/                          # 핵심 비즈니스 로직 (Qt 의존성 없음)
│   ├── domain/
│   │   └── models.py (267줄)       # 도메인 모델 (FFTResult, SignalData, TrendResult, FileMetadata)
│   ├── services/
│   │   ├── fft_engine.py (200줄)   # FFT 엔진 (scipy.signal 래핑)
│   │   ├── fft_service.py (211줄)  # FFT 서비스 (신호 변환, 제로 패딩)
│   │   ├── file_parser.py (203줄)  # 파일 파서 (메타데이터 추출, NumPy 로딩)
│   │   ├── file_service.py (286줄) # 파일 서비스 (디렉토리 스캔, 캐싱, 감도 관리)
│   │   ├── trend_service.py (209줄)# 트렌드 서비스 (배치 RMS 트렌드)
│   │   ├── peak_service.py (263줄) # 피크 서비스 (배치 피크 트렌드)
│   │   └── OPTIMIZATION_PATCH_LEVEL5_TREND.py (424줄)
│   │                               # 병렬 프로세서 (ProcessPoolExecutor)
│   └── interfaces/                 # 인터페이스 정의 (확장용)
│
├── presentation/                   # UI 레이어 (PyQt5)
│   ├── presenters/                 # 프레젠터 (뷰와 서비스 조율)
│   │   ├── data_query_presenter.py  (152줄)
│   │   ├── spectrum_presenter.py    (349줄)
│   │   ├── trend_presenter.py       (291줄)
│   │   ├── waterfall_presenter.py   (498줄)
│   │   └── peak_presenter.py        (241줄)
│   ├── views/                      # 뷰 (순수 UI 컴포넌트)
│   │   ├── main_window.py          (226줄)  # 메인 윈도우 (씬 셸)
│   │   ├── splash_screen.py        (174줄)  # 스플래시 스크린
│   │   ├── tabs/                   # 탭 뷰
│   │   │   ├── data_query_tab.py    (122줄)
│   │   │   ├── spectrum_tab.py      (615줄)
│   │   │   ├── trend_tab.py         (545줄)
│   │   │   ├── waterfall_tab.py     (474줄)
│   │   │   └── peak_tab.py          (529줄)
│   │   ├── dialogs/                # 다이얼로그
│   │   │   ├── progress_dialog.py
│   │   │   ├── axis_range_dialog.py
│   │   │   ├── list_save_dialog.py
│   │   │   ├── list_save_dialog_helpers.py
│   │   │   └── responsive_layout_utils.py
│   │   └── widgets/                # 재사용 위젯
│   │       ├── plot_widget.py       (150줄)
│   │       └── marker_manager.py    (150줄)
│   └── models/
│       └── file_list_model.py       (178줄)  # 테이블 데이터 모델
│
├── infrastructure/                 # 크로스커팅 관심사
│   └── event_bus.py (104줄)        # 싱글톤 이벤트 버스 (PyQt 시그널)
│
└── app.py (152줄)                  # 애플리케이션 팩토리 (DI 와이어링)
```

---

## 2. 핵심 설계 패턴

### 2.1 MVP (Model-View-Presenter)

```
┌─────────────┐    시그널/슬롯    ┌──────────────┐    메서드 호출    ┌─────────────┐
│    View      │ ──────────────→ │  Presenter   │ ──────────────→ │   Service   │
│  (PyQt5 UI)  │ ←────────────── │  (조율자)     │ ←────────────── │ (비즈니스)   │
│              │   뷰 업데이트     │              │   결과 반환      │             │
└─────────────┘                  └──────────────┘                  └─────────────┘
```

**역할 분리:**
- **View**: 순수 UI (위젯 배치, 시그널 발행, 데이터 표시)
- **Presenter**: 뷰와 서비스를 조율 (이벤트 처리, 데이터 변환)
- **Service**: 비즈니스 로직 (FFT 연산, 파일 처리, 트렌드 분석)

### 2.2 생성자 주입 (Constructor Injection)

```python
# app.py - ApplicationFactory
class ApplicationFactory:
    def create_presenters(self, main_window):
        # 모든 의존성을 명시적으로 전달
        self._presenters['spectrum'] = SpectrumPresenter(
            view=spectrum_tab,              # 뷰 주입
            fft_service=self._services['fft'],  # 서비스 주입
            file_service=self._services['file']
        )
```

**장점:**
- 서비스 로케이터 패턴 미사용 (숨은 의존성 없음)
- 테스트 시 목(mock) 주입 용이
- 의존성 그래프가 코드에 명시적으로 표현

### 2.3 이벤트 버스 (Event Bus)

```python
# 싱글톤 패턴 - 크로스커팅 이벤트만 사용
bus = get_event_bus()
bus.file_loaded.connect(on_file_loaded)     # 파일 로드 이벤트
bus.tab_changed.connect(on_tab_changed)     # 탭 전환 이벤트
bus.view_type_changed.connect(on_view_type) # ACC/VEL/DIS 변경
```

**사용 원칙:** 크로스커팅 관심사에만 제한적으로 사용. 대부분의 통신은 프레젠터 간 직접 호출.

---

## 3. 레이어별 상세

### 3.1 Core 레이어 (Qt 의존성 없음)

| 모듈 | 역할 | 주요 클래스/메서드 |
|------|------|-------------------|
| `models.py` | 도메인 모델 정의 | `FFTResult`, `SignalData`, `TrendResult`, `FileMetadata` |
| `fft_engine.py` | FFT 연산 엔진 | `FFTEngine.compute()` - scipy.signal.welch 래핑 |
| `fft_service.py` | FFT 비즈니스 로직 | `FFTService.compute_spectrum()` - 신호 변환, 제로 패딩 |
| `file_parser.py` | 파일 파싱 | `FileParser` - 메타데이터 추출, NumPy 데이터 로딩 |
| `file_service.py` | 파일 관리 서비스 | `FileService` - 디렉토리 스캔, 감도 캐싱, 그룹화 |
| `trend_service.py` | RMS 트렌드 분석 | `TrendService.compute_trend()` - 병렬 배치 처리 |
| `peak_service.py` | 피크 트렌드 분석 | `PeakService.compute_peak_trend()` - 병렬 배치 처리 |

### 3.2 Presentation 레이어

| 모듈 | 역할 | 레거시 대응 |
|------|------|------------|
| `data_query_presenter.py` | 파일 로딩 워크플로우 | Tab 1 로직 |
| `spectrum_presenter.py` | 스펙트럼 분석 워크플로우 | `plot_data_file_spectrem()` |
| `trend_presenter.py` | RMS 트렌드 워크플로우 | `plot_overall()` |
| `waterfall_presenter.py` | 워터폴 3D 워크플로우 | `plot_waterfall_spectrum()` |
| `peak_presenter.py` | 피크 트렌드 워크플로우 | Tab 5 로직 |

### 3.3 Infrastructure 레이어

| 모듈 | 역할 | 시그널 |
|------|------|--------|
| `event_bus.py` | 전역 이벤트 통신 | `file_loaded`, `files_loaded`, `analysis_complete`, `error_occurred`, `progress_updated`, `data_changed`, `selection_changed`, `tab_changed`, `view_type_changed` |

---

## 4. 데이터 흐름 예시

### RMS 트렌드 분석 흐름

```
사용자: "Calculation & Plot" 클릭
    │
    ▼
TrendTabView.compute_requested (시그널)
    │
    ▼
TrendPresenter._on_compute_requested()
    ├── view.get_parameters() → {delta_f, window_type, overlap, view_type, band_min, band_max}
    ├── ProgressDialog 생성 (total_tasks = len(file_paths))
    ├── progress_callback 정의 (update_progress + processEvents)
    │
    ▼
TrendService.compute_trend(file_paths, ..., progress_callback)
    │
    ▼
TrendParallelProcessor.process_batch()
    ├── ProcessPoolExecutor(max_workers=CPU-1)
    ├── 각 파일 → _process_trend_worker()
    │   ├── 파일 로딩 (NumPy 직접)
    │   ├── 메타데이터 파싱 (상위 25줄)
    │   ├── 감도 보정
    │   ├── FFT 계산 (scipy.fft.rfft)
    │   ├── 윈도우 함수 적용
    │   ├── 신호 변환 (ACC→VEL→DIS)
    │   ├── 대역 필터링
    │   └── RMS/Peak 계산
    ├── as_completed() → progress_callback(current, total)
    └── 결과 정렬 (입력 순서 보장)
    │
    ▼
TrendPresenter._aggregate_results() → TrendResult
    │
    ▼
TrendPresenter._update_view_with_result(result)
    ├── view.plot_trend(channel_data)
    ├── view.set_trend_data(x, rms, filenames)
    └── view.update_data_list(text)
```

---

## 5. 의존성 그래프

```
app.py (ApplicationFactory)
 ├── creates → FileService
 ├── creates → FFTService(sampling_rate, delta_f, overlap, window_type)
 ├── creates → TrendService(max_workers)
 ├── creates → PeakService(max_workers)
 ├── creates → MainWindow
 │              ├── DataQueryTabView
 │              ├── SpectrumTabView
 │              ├── TrendTabView
 │              ├── WaterfallTabView
 │              └── PeakTabView
 ├── creates → DataQueryPresenter(view)
 ├── creates → SpectrumPresenter(view, fft_service, file_service)
 ├── creates → TrendPresenter(view, trend_service, file_service)
 ├── creates → WaterfallPresenter(view)
 └── creates → PeakPresenter(view, peak_service, file_service)
```

**의존성 규칙:**
- `core/` → 외부 의존성 없음 (순수 Python + NumPy + SciPy)
- `presentation/` → `core/`에 의존
- `infrastructure/` → PyQt5에 의존 (시그널)
- `app.py` → 모든 레이어에 의존 (와이어링 전용)
