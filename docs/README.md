# CNAVE 기술 문서

진동 분석 애플리케이션(CNAVE)의 기술 문서입니다.

## 문서 목록

| 문서 | 내용 | 대상 |
|------|------|------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 아키텍처 개요, 레이어 구조, 설계 패턴, 데이터 흐름 | 전체 구조 파악 시 |
| [CHANGELOG.md](./CHANGELOG.md) | 레거시→리팩토링 변경 이력, 모듈별 변경 상세, 성능 비교 | 변경 사항 추적 시 |
| [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) | 임포트 변경, 코드 패턴 변경, 테스트 작성 가이드 | 레거시 코드 마이그레이션 시 |

## 빠른 참조

### 프로젝트 구조
```
vibration/
├── core/               # 비즈니스 로직 (Qt 의존성 없음)
│   ├── domain/         # 도메인 모델 (FFTResult, TrendResult, ProjectData 등)
│   └── services/       # 서비스 (FFT, 파일, 트렌드, 피크, 프로젝트)
├── presentation/       # UI 레이어 (PyQt5)
│   ├── presenters/     # 프레젠터 (뷰-서비스 조율)
│   ├── views/          # 뷰 (탭, 다이얼로그, 위젯)
│   └── models/         # UI 모델 (FileListModel)
├── infrastructure/     # 크로스커팅 (EventBus)
├── legacy/             # 레거시 코드 아카이브 (참조용)
└── app.py              # 애플리케이션 팩토리 (진입점)
```

### 주요 기능

| 탭 | 기능 |
|----|------|
| **Data Query** | 프로젝트 기반 데이터 관리 — 엄마폴더 스캔, 날짜 필터, 이상파일 감지/격리, 프로젝트 저장/로드, 측정타입 자동 판별 |
| **Spectrum** | FFT 스펙트럼 분석 |
| **Trend** | 시간 영역 트렌드 분석 |
| **Peak Pick** | 피크 추출 및 분석 |
| **Waterfall** | 3D 워터폴 플롯 |

### 실행 방법
```bash
python -m vibration
```
