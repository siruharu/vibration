# CNXMW Post Processor (가칭: CNAVE)

## 개요

장기 계측용 진동/음향 데이터의 후처리 및 분석 프로그램입니다. 6,384줄의 레거시 모놀리식 코드를 MVP(Model-View-Presenter) 아키텍처로 전면 재설계한 v2.0.0 버전입니다.

**주요 특징:**
- MVP 패턴 기반 계층 분리 (core/presentation/infrastructure)
- Qt 의존성 없는 비즈니스 로직 (core 레이어)
- 병렬 RMS 계산 및 캐싱 시스템
- 이상 파일 자동 감지 및 격리
- 프로젝트 저장/로드 기능
- 실시간 Progress 피드백

---

## 프로젝트 구조

```
vibration/
├── core/                       # 비즈니스 로직 (Qt 의존성 없음)
│   ├── domain/
│   │   └── models.py           # 도메인 모델 (FFTResult, SignalData, TrendResult, ProjectData 등)
│   └── services/               # 서비스 (FFT, 파일, 트렌드, 피크, 프로젝트)
│       ├── fft_engine.py
│       ├── fft_service.py
│       ├── file_parser.py
│       ├── file_service.py
│       ├── trend_service.py
│       ├── peak_service.py
│       └── project_service.py
├── presentation/               # UI 레이어 (PyQt5)
│   ├── presenters/             # 프레젠터 (뷰-서비스 조율)
│   ├── views/
│   │   ├── tabs/               # 탭 뷰 (Data Query, Spectrum, Trend, Peak, Waterfall)
│   │   ├── dialogs/            # 다이얼로그 (Progress, AxisRange, ListSave, SpectrumWindow)
│   │   ├── main_window.py
│   │   └── splash_screen.py
│   └── models/
│       └── file_list_model.py  # 테이블 데이터 모델
├── infrastructure/             # 크로스커팅 (EventBus)
├── legacy/                     # 레거시 코드 아카이브 (참조용)
├── __init__.py                 # 패키지 초기화, get_resource_path()
├── __main__.py                 # 엔트리포인트
└── app.py                      # 애플리케이션 팩토리 (DI 와이어링)
```

---

## 주요 기능

### 1. Data Query 탭
- 엄마폴더 스캔 및 하위 파일 자동 탐색
- 날짜 범위 필터링 (시작일/종료일)
- 이상 파일 자동 감지 및 격리 (Abnormal Files 리스트)
- 프로젝트 저장/로드 (JSON 형식)
- 측정 타입 자동 판별 (진동/음향)
- 파일 리스트 테이블 (QTableView 가상화)

### 2. Time/Spectrum 탭
- FFT 스펙트럼 분석 (scipy.signal.welch)
- Waveform과 Spectrum 동시 표시
- SpanSelector를 이용한 시간 구간 선택 후 FFT 팝업
- Picking 기능 (파일 선택 시 자동 업데이트)
- 마우스 줌/팬 (matplotlib NavigationToolbar)

### 3. Overall RMS Trend 탭
- 병렬 RMS 계산 (multiprocessing)
- 실시간 Progress 다이얼로그
- Picking 후 Detail Analysis (선택 파일 상세 분석)
- 캐싱 시스템 (계산 결과 재사용)
- 날짜 범위 필터링

### 4. Band Peak Trend 탭
- Overall RMS Trend와 동일한 구조
- 주파수 대역별 피크 추출
- 병렬 계산 및 캐싱
- Picking 기능

### 5. Waterfall 탭
- 3D Waterfall 플롯 (STFT 기반)
- Picking 기능 (파일 선택 시 업데이트)
- Band Trend 분석
- 날짜 범위 필터링
- 캐싱 시스템

---

## 빠른 시작

### 설치

```bash
# 의존성 설치
pip install -r requirements.txt
```

### 실행

```bash
# 패키지 모듈로 실행
python -m vibration

# 또는 직접 실행
python vibration/app.py
```

---

## Windows 실행 파일 빌드

### PyInstaller 빌드

```bash
# Windows 환경에서 실행 (크로스 컴파일 불가)
pyinstaller CNAVE_Analyzer.spec
```

**주의사항:**
- Windows 실행 파일은 반드시 Windows 환경에서 빌드해야 합니다
- Mac/Linux에서 크로스 컴파일은 지원되지 않습니다
- 빌드 시 `icn.ico` 아이콘 파일이 필요합니다
- 결과물: `dist/CNAVE_Analyzer.exe`

---

## 기술 스택

| 항목 | 기술 | 버전 |
|------|------|------|
| 언어 | Python | 3.8+ |
| GUI | PyQt5 | 5.15+ |
| 수치 계산 | numpy | 1.21+ |
| 신호 처리 | scipy | 1.7+ |
| 시각화 | matplotlib | 3.5+ |
| 데이터 처리 | pandas | 1.3+ |
| 오디오 | soundfile, librosa | - |
| 계측 데이터 | nptdms | - |

---

## 아키텍처 특징

### MVP 패턴
- **Model**: 도메인 모델 (core/domain/models.py)
- **View**: PyQt5 뷰 (presentation/views/)
- **Presenter**: 뷰-서비스 조율 (presentation/presenters/)

### 계층 분리
- **core**: Qt 의존성 없는 순수 비즈니스 로직
- **presentation**: UI 레이어 (PyQt5)
- **infrastructure**: 크로스커팅 관심사 (EventBus)

### 의존성 주입
- ApplicationFactory에서 모든 의존성 와이어링
- 서비스 간 느슨한 결합
- 테스트 용이성 향상

---

## 관련 문서

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - 아키텍처 상세 설명
- [CHANGELOG.md](docs/CHANGELOG.md) - 버전별 변경 이력
- [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) - 레거시 코드 마이그레이션 가이드

---

## 버전

**현재 버전: v2.0.0**

---

## 라이선스

MIT License

---

## 개발자

Vibration Analysis Team
