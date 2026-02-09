# 변경 이력

## 개요

이 문서는 레거시 모놀리식 코드(`cn_3F_trend_optimized.py`)에서 모듈화 MVP 아키텍처(`vibration/`)로의
전체 변경 사항과, 이후 기능 추가/수정 사항을 기록합니다.

---

## 10. Time/Spectrum 플롯 성능 복원 — 배치 렌더링 + Next 캐시 (2026-02-10)

### 10.1 변경 개요

리팩토링 과정에서 깨진 레거시 플롯 동작을 복원했습니다:
1. **Plot 버튼** — 파일 하나씩 `draw_idle()` 호출하며 그리던 것을 레거시처럼 모든 데이터를 먼저 계산한 뒤 한번에 렌더링
2. **Next 버튼** — 모든 선택 파일을 매번 디스크에서 다시 읽고 FFT 재계산하던 것을 이미 계산된 결과를 유지하고 새 파일만 추가 계산
3. **Y Auto 110% 제거** — 커스텀 110% 스케일을 제거하고 matplotlib 기본 autoscale로 복원

| 항목 | 이전 (버그) | 이후 (레거시 복원) |
|------|------------|-------------------|
| **Plot 렌더링** | 파일마다 `draw_idle()` — N파일이면 2N번 호출 | 모든 계산 완료 후 `end_batch()`에서 2번만 호출 |
| **Next 동작** | `_on_compute_requested()` 호출 → 전체 파일 재로드+재계산 | 기존 결과 유지, 새 파일 1개만 로드+계산+플롯 추가 |
| **FFT 캐시** | 없음 — `_last_results = []` 매번 초기화 | `_computed_cache` 딕셔너리로 파일별 결과 보존 |
| **Y Auto 110%** | `_apply_auto_y_scale()` — 최대값 × 1.10 강제 스케일 | 제거 — matplotlib 기본 autoscale |

### 10.2 파일별 변경 상세

#### 10.2.1 `vibration/presentation/presenters/spectrum_presenter.py`

| 함수 | 변경 유형 | 상세 |
|------|----------|------|
| `__init__` | 수정 | `_computed_cache: Dict[str, Tuple[SignalData, FFTResult]]` 인스턴스 변수 추가 |
| `_on_compute_requested` | 수정 | 직접 파일 처리 루프 제거 → `_computed_cache.clear()` + `_load_and_plot_files()` 위임 |
| `_load_and_plot_files` | **신규** | 2페이즈 공통 메서드 — Phase 1: 파일 로드+FFT 계산 축적, Phase 2: `begin_batch()` → 일괄 플롯 → `end_batch()` |
| `_on_next_file_requested` | 수정 | `_on_compute_requested()` 호출 제거 → 캐시 확인 후 새 파일만 `_load_and_plot_files([새파일])` |

**이전 (`_on_next_file_requested`):**
```python
def _on_next_file_requested(self) -> None:
    # ... 다음 파일 선택 추가 ...
    next_item.setSelected(True)
    self._on_compute_requested()  # 전체 재계산
```

**이후:**
```python
def _on_next_file_requested(self) -> None:
    # ... 다음 파일 선택 추가 ...
    next_item.setSelected(True)

    if next_filename in self._computed_cache:
        return  # 이미 계산됨 — 스킵

    self._load_and_plot_files([next_filename])  # 새 파일만 계산+플롯
```

**이전 (`_load_and_plot_files` — 구 `_on_compute_requested` 내부):**
```python
for idx, filename in enumerate(selected_files):
    file_data = self.file_service.load_file(filepath)  # 디스크 I/O
    result = self._compute_single_signal(...)            # FFT
    self.view.plot_waveform(...)                          # draw_idle() 호출
    self.view.plot_spectrum(...)                          # draw_idle() 호출
    # → 파일마다 2번 draw_idle — 화면 깜빡임
```

**이후 (`_load_and_plot_files` 2페이즈):**
```python
# Phase 1: 계산 (draw 없음)
for idx, filename in enumerate(filenames):
    file_data = self.file_service.load_file(filepath)
    result = self._compute_single_signal(...)
    computed_batch.append((filename, signal_data, result))

# Phase 2: 일괄 렌더링
self.view.begin_batch()
for filename, signal_data, result in computed_batch:
    self.view.plot_waveform(...)   # draw_idle 억제됨
    self.view.plot_spectrum(...)   # draw_idle 억제됨
self.view.end_batch()              # 여기서만 draw_idle 2번
```

#### 10.2.2 `vibration/presentation/views/tabs/spectrum_tab.py`

| 함수 | 변경 유형 | 상세 |
|------|----------|------|
| `__init__` | 수정 | `_batch_mode = False` 인스턴스 변수 추가 |
| `begin_batch` | **신규** | `_batch_mode = True` 설정 — 이후 `draw_idle()` 호출 억제 |
| `end_batch` | **신규** | `_batch_mode = False` 해제 → 범례 업데이트 + `draw_idle()` 최종 호출 + SpanSelector 생성 |
| `_update_legend` | 수정 | `_batch_mode` 체크 — `True`이면 `canvas.draw_idle()` 스킵 |
| `plot_waveform` | 수정 | `_batch_mode` 체크 — `True`이면 SpanSelector 생성 스킵 (`end_batch`에서 1회만 생성) |
| `_apply_auto_y_scale` | **삭제** | Y Auto 110% 로직 전체 제거 (41줄) |
| `plot_spectrum` | 수정 | `_apply_auto_y_scale('spec')` 호출 제거 |
| `plot_waveform` | 수정 | `_apply_auto_y_scale('wave')` 호출 제거 |

### 10.3 성능 영향

| 시나리오 | 이전 | 이후 | 개선 |
|----------|------|------|------|
| Plot 10파일 — `draw_idle()` 횟수 | 20번 | 2번 | **10×** |
| Next 5회 (10파일 선택 후) — 파일 로드+FFT | 75회 | 15회 | **5×** |
| Next 1회 — 디스크 I/O | 기존 파일 전부 재로드 | 새 파일 1개만 | **N→1** |

### 10.4 영향 범위

| 레이어 | 영향 |
|--------|------|
| 프레젠터 (`spectrum_presenter.py`) | `_on_compute_requested`, `_on_next_file_requested` 수정, `_load_and_plot_files` 신규 |
| 뷰 (`spectrum_tab.py`) | `begin_batch`/`end_batch` 신규, `_update_legend`·`plot_waveform` 배치 모드 대응, `_apply_auto_y_scale` 삭제 |
| 도메인 모델 | ✅ 변경 없음 |
| 서비스 레이어 | ✅ 변경 없음 |

---

## 9. PyInstaller exe 빌드 안정화 (2026-02-09)

### 9.1 변경 개요

PyInstaller로 Windows exe를 빌드했을 때 발생하는 3가지 핵심 문제를 수정했습니다:
1. **multiprocessing 창 다중 생성** — `freeze_support()` 미호출로 exe 실행 시 프로세스가 무한 생성
2. **Spectrum picking 미작동** — exe 환경에서 Detail Analysis 다이얼로그의 그래프 피킹 기능 미동작
3. **아이콘/로고 표시 실패** — exe 번들 환경에서 리소스 경로 미해결

| 항목 | 이전 | 이후 |
|------|------|------|
| **multiprocessing** | exe 실행 시 창 여러 개 뜨며 오류 | `freeze_support()` 이중 안전장치로 정상 동작 |
| **Spectrum picking** | Detail Analysis에서 클릭해도 마커 없음 | 좌클릭=빨간 마커+라벨, 우클릭=마커 제거 |
| **아이콘 경로** | `Path("icon.ico")` — exe에서 찾지 못함 | `get_resource_path("icn.ico")` — `sys._MEIPASS` 자동 해결 |
| **spec 파일** | `datas=[]` — 아이콘 미번들 | `datas=[('icn.ico', '.')]` — 아이콘 번들 포함 |

### 9.2 파일별 변경 상세

#### 9.2.1 `vibration/__init__.py`

**이전:**
```python
# 빈 패키지 초기화 파일
```

**이후:**
```python
import sys
from pathlib import Path

def get_resource_path(relative_path: str) -> Path:
    """PyInstaller exe 번들 환경과 개발 환경 모두에서 리소스 경로를 해결합니다.
    
    - exe 환경: sys._MEIPASS (임시 추출 디렉토리) 기준
    - 개발 환경: 프로젝트 루트 (vibration/ 상위) 기준
    """
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent
    return base / relative_path
```

#### 9.2.2 `vibration/__main__.py`

**이전:**
```python
from vibration.app import main
main()
```

**이후:**
```python
import multiprocessing
multiprocessing.freeze_support()  # PyInstaller exe에서 반드시 먼저 호출

from vibration.app import main
main()
```

> `freeze_support()`는 모든 import보다 먼저 호출되어야 합니다. Windows에서 `ProcessPoolExecutor` 사용 시 자식 프로세스가 메인 모듈을 re-import하는데, 이 호출이 없으면 GUI 창이 무한 생성됩니다.

#### 9.2.3 `vibration/app.py`

**이전:**
```python
def main():
    app = QApplication(sys.argv)
    # ...
```

**이후:**
```python
def main():
    import multiprocessing
    multiprocessing.freeze_support()  # 이중 안전장치
    app = QApplication(sys.argv)
    # ...
```

#### 9.2.4 `vibration/presentation/views/tabs/spectrum_tab.py`

**변경 내용:**
- `_reconnect_picking_events()` 메서드 추가 — disconnect → reconnect + hover_dot 재생성
- `plot_spectrum(clear=True)` 시 `_reconnect_picking_events()` 호출
- `clear_plots()` 시 `_reconnect_picking_events()` 호출
- `_connect_picking_events()`에 hover_dot 생성 통합 (중복 제거)
- canvas focus 정책: `ClickFocus` → `StrongFocus`

**원인:** `fig.clf()` 호출 시 기존 이벤트 연결과 hover_dot 참조가 소실되어, 이후 picking이 작동하지 않았습니다.

#### 9.2.5 `vibration/presentation/views/dialogs/list_save_dialog_helpers.py`

**이전:**
```python
class SpectrumPicker:
    def on_mouse_click(self, event): pass  # 빈 메서드
    def add_marker(self, x, y): pass       # 빈 메서드
```

**이후:**
```python
class SpectrumPicker:
    def on_mouse_click(self, event):
        if event.button == 1:       # 좌클릭 → 마커 추가
            self.add_marker(event.xdata, event.ydata)
        elif event.button == 3:     # 우클릭 → 마커 전체 제거
            self._clear_markers()
    
    def add_marker(self, x, y):
        # 레거시 add_marker_spect 기반 구현
        # 1. data_dict에서 모든 라인 데이터 수집
        # 2. 클릭 좌표에서 가장 가까운 파일+데이터포인트 탐색
        # 3. 빨간 마커 ('ro', ms=8) + 텍스트 라벨 (파일명, 주파수, 진폭) 표시
        # 4. canvas.draw_idle()로 갱신
```

#### 9.2.6 `vibration/presentation/views/dialogs/list_save_dialog.py`

**변경 내용:**
- `_finalize_plot()`에서 이벤트 중복 등록 방지 패턴 적용
- `_cid_move`, `_cid_click`, `_cid_key` 인스턴스 변수로 이벤트 ID 저장
- 다음 Plot 시 기존 이벤트 disconnect → 새로 connect

**원인:** Plot 버튼을 여러 번 누르면 이벤트 핸들러가 중복 등록되어 마커 생성이 비정상적이었습니다.

#### 9.2.7 `vibration/presentation/views/splash_screen.py`

**이전:**
```python
icon_path = Path(__file__).parent.parent.parent.parent / "icn.ico"
```

**이후:**
```python
from vibration import get_resource_path
icon_path = get_resource_path("icn.ico")
```

#### 9.2.8 `vibration/presentation/views/main_window.py`

**이전:**
```python
icon_path = Path("icon.ico")  # 파일명 오류 + 상대경로
if icon_path.exists():
    self.setWindowIcon(QIcon(str(icon_path)))
```

**이후:**
```python
from vibration import get_resource_path

icon_path = get_resource_path("icn.ico")  # 올바른 파일명 + exe/개발 환경 모두 지원
if icon_path.exists():
    self.setWindowIcon(QIcon(str(icon_path)))
```

#### 9.2.9 `CNAVE_Analyzer.spec`

**이전:**
```python
a = Analysis(
    ['vibration/__main__.py'],
    datas=[],
    # ...
)
exe = EXE(
    # ...
    icon='icn.ico',
)
```

**이후:**
```python
a = Analysis(
    ['vibration/__main__.py'],
    datas=[('icn.ico', '.')],  # 아이콘 파일을 exe 번들에 포함
    # ...
)
exe = EXE(
    # ...
    icon='icn.ico',
)
```

### 9.3 PyInstaller 빌드 명령어

```bash
# Windows VM에서 실행
pyinstaller CNAVE_Analyzer.spec
```

결과물: `dist/CNAVE_Analyzer.exe`

### 9.4 하위 호환성

| 항목 | 호환성 |
|------|--------|
| 개발 환경 (`python -m vibration`) | ✅ `get_resource_path()`가 프로젝트 루트 기준으로 동작 |
| 기존 시그널/위젯 | ✅ 변경 없음 |
| 기존 탭 기능 | ✅ 변경 없음 (spectrum_tab picking 재연결만 추가) |
| macOS 빌드 | ✅ `BUNDLE` 섹션 유지 |

---

## 8. Waterfall 탭 강화 (2026-02-09)

### 8.1 변경 개요

Waterfall 탭에 날짜 필터, 시간 라벨 개선, 그리드 간격 개선, Picking 기능, Single Band Trend, 채널별 파일 그룹핑을 추가했습니다.

| 항목 | 이전 | 이후 |
|------|------|------|
| **날짜 필터** | 없음 | QDateEdit From/To + Filter 버튼으로 파일 기간 필터링 |
| **Y축 시간 라벨** | `2026-01-04_12-25-19\n_2_2` (파일명 그대로) | `01-04\n12:25:19` (날짜+시각만, 최대 5개) |
| **X축 그리드** | 하드코딩 구간별 interval | `range/10` nice-number 알고리즘 (1/2/5 × 10^n) |
| **Picking** | 없음 | 좌클릭=빨간 마커+주파수/진폭 annotation, 우클릭=제거, 호버=검정 도트 |
| **Single Band Trend** | 없음 | Band Trend 버튼→주파수 입력→시간별 진폭 트렌드 팝업 |
| **파일 리스트** | 단순 텍스트 나열 | 채널별 그룹 헤더 + 색상 구분 (6색) |

### 8.2 파일별 변경 상세

#### 8.2.1 `vibration/presentation/views/tabs/waterfall_tab.py`

**이전:**
```python
# 시그널 (7개)
compute_requested = pyqtSignal(bool)
set_x_axis_requested = pyqtSignal()
set_z_axis_requested = pyqtSignal()
auto_scale_x_requested = pyqtSignal()
auto_scale_z_requested = pyqtSignal()
angle_changed = pyqtSignal()
channel_filter_changed = pyqtSignal()

# 좌측 패널: 체크박스, Select All/Deselect All, 단순 파일 리스트
# 마우스 인터랙션: 없음
# 파일 리스트: QListWidget.addItems() — 색상/그룹 구분 없음
```

**이후:**
```python
# 시그널 (9개 — 2개 추가)
compute_requested = pyqtSignal(bool)
set_x_axis_requested = pyqtSignal()
set_z_axis_requested = pyqtSignal()
auto_scale_x_requested = pyqtSignal()
auto_scale_z_requested = pyqtSignal()
angle_changed = pyqtSignal()
channel_filter_changed = pyqtSignal()
date_filter_changed = pyqtSignal(str, str)    # 날짜 필터
band_trend_requested = pyqtSignal(float)       # Band Trend 주파수

# 좌측 패널: + QDateEdit From/To + Filter 버튼
# 중앙 패널: + Band Trend 버튼 (Plot Waterfall 아래)
# 마우스 인터랙션: hover dot + 좌클릭 마커 + 우클릭 제거
# 파일 리스트: 채널별 그룹 헤더 (── CH1 (12) ──) + 6색 색상 구분

# 추가 메서드:
# _on_date_filter_clicked() — From/To 날짜 emit
# _on_band_trend_clicked() — QInputDialog로 주파수 입력 → emit
# _init_mouse_events() — canvas에 motion/click 이벤트 연결
# _on_mouse_move() — picking_data에서 최근접 포인트 탐색, hover dot 표시
# _on_mouse_click() — 좌클릭=마커, 우클릭=제거
# _add_picking_marker() — 빨간 마커 + annotation (파일명, 주파수, 진폭)
# _clear_picking_markers() — 마커/annotation 제거
# set_picking_data() — 프레젠터에서 변환 좌표+실제 값 수신
# _populate_file_list_grouped() — 채널별 헤더+색상으로 파일 리스트 구성
# _extract_channel() — 파일명에서 채널 번호 추출
```

#### 8.2.2 `vibration/presentation/presenters/waterfall_presenter.py`

**이전:**
```python
class WaterfallPresenter:
    def __init__(self, view, directory_path):
        # 6개 시그널 연결
        # _waterfall_cache: FFT 결과 캐싱

    # _render_waterfall(): 3D 라인 플롯
    #   - 오른쪽 라벨: 파일명 기반 (date_time\n_count_channel)
    # _add_grid_lines(): 하드코딩 구간별 interval
```

**이후:**
```python
class WaterfallPresenter:
    def __init__(self, view, directory_path):
        self._all_files: List[str] = []              # 전체 파일 목록 (필터링 기준)
        self._band_trend_dialogs: List[Any] = []     # Band Trend 팝업 참조 (GC 방지)
        # 8개 시그널 연결 (2개 추가)

    # 변경된 _render_waterfall():
    #   - 오른쪽 라벨: datetime 기반 (MM-DD\nHH:MM:SS)
    #   - picking 데이터 수집 (라인당 200포인트 샘플링)
    #   - fig.clf() 시 hover_dot/marker 참조 초기화

    # 변경된 _add_grid_lines():
    #   - nice-number 알고리즘: range/10 → 1/2/5 × magnitude
    #   - 예: 100Hz→10Hz, 200Hz→20Hz, 500Hz→50Hz, 1000Hz→100Hz

    # 변경된 _on_files_loaded():
    #   - _all_files 저장 (날짜 필터 기준)

    # 추가 메서드:
    # _on_date_filter_changed(from_date, to_date) — 파일명 날짜 기준 필터링
    # _on_band_trend_requested(target_freq) — 캐시된 스펙트럼에서 해당 주파수 진폭 추출
    # _show_band_trend_window(freq, timestamps, amplitudes) — QDialog 팝업 생성
```

### 8.3 채널 색상 매핑

| 채널 | RGB | 용도 |
|------|-----|------|
| CH1 | (31, 119, 180) 파랑 | 헤더 텍스트 + 파일명 텍스트 |
| CH2 | (44, 160, 44) 초록 | 헤더 텍스트 + 파일명 텍스트 |
| CH3 | (214, 39, 40) 빨강 | 헤더 텍스트 + 파일명 텍스트 |
| CH4 | (148, 103, 189) 보라 | 헤더 텍스트 + 파일명 텍스트 |
| CH5 | (255, 127, 14) 주황 | 헤더 텍스트 + 파일명 텍스트 |
| CH6 | (140, 86, 75) 갈색 | 헤더 텍스트 + 파일명 텍스트 |

### 8.4 하위 호환성

| 항목 | 호환성 |
|------|--------|
| 기존 시그널 | ✅ 모두 유지 (7개 원본 시그널 변경 없음) |
| 기존 위젯 변수명 | ✅ 변경 없음 (checkBox_7-12, Querry_list2, Hz_2 등) |
| 레이아웃 구조 | ✅ 메인 그리드 위치 동일 |
| 다른 탭 파일 | ✅ 변경 없음 (spectrum, trend, peak, data_query) |
| app.py | ✅ 변경 없음 |
| 도메인 모델 | ✅ 변경 없음 (models.py) |
| 서비스 레이어 | ✅ 변경 없음 (fft_service, file_service 등) |

---

## 7. Time/Spectrum 탭 강화 (2026-02-09)

### 7.1 변경 개요

Time/Spectrum 탭에 날짜 필터, Sensitivity 다중 적용, 그래프 Refresh, 축 컨트롤 연결, 시간 구간 선택 Spectrum 팝업 기능을 추가했습니다.

| 항목 | 이전 | 이후 |
|------|------|------|
| **날짜 필터** | 없음 | QDateEdit From/To + Filter 버튼으로 파일 기간 필터링 |
| **Sensitivity 편집** | QLineEdit만 존재, 미연결 | Enter 시 다중 선택 파일에 일괄 적용 + 재계산 |
| **Refresh/Close All** | 없음 | Refresh 버튼 (현재 파라미터로 재플롯), Close All (팝업 창 전체 닫기) |
| **Waveform Y축 라벨** | "Vibration Acceleration\n(m/s², RMS)" | "Acceleration (m/s²)" (RMS 제거, 시간영역에 적합) |
| **축 컨트롤 Set** | UI만 존재, 미연결 | Set 버튼 → 축 범위 적용, 프레젠터 연동 |
| **축 라벨 클릭** | 없음 | X축/Y축 라벨 영역 클릭 → QInputDialog 팝업으로 범위 입력 |
| **Y Auto 110%** | 없음 | Auto Y 체크 시 X축 범위 내 최대값의 110%로 자동 스케일 |
| **시간 구간 선택** | 없음 | Waveform에서 SpanSelector로 구간 드래그 → 별도 Spectrum 창 |
| **Spectrum 팝업** | 없음 | 다중 non-modal 창, 호버/마커 피킹, Close All로 일괄 닫기 |

### 7.2 파일별 변경 상세

#### 7.2.1 `vibration/presentation/views/tabs/spectrum_tab.py`

**이전:**
```python
# 시그널 (5개)
compute_requested = pyqtSignal()
next_file_requested = pyqtSignal()
view_type_changed = pyqtSignal(int)
window_type_changed = pyqtSignal(str)
file_clicked = pyqtSignal(str)

# 좌측 패널: 체크박스, Select All/Deselect All, 파일 리스트만
# 축 컨트롤: UI만 존재 (Auto X/Y, min/max, Set 버튼), 프레젠터 미연결
# Waveform Y축: VIEW_TYPE_LABELS (RMS 포함)
```

**이후:**
```python
# 시그널 (11개 — 6개 추가)
compute_requested = pyqtSignal()
next_file_requested = pyqtSignal()
view_type_changed = pyqtSignal(int)
window_type_changed = pyqtSignal(str)
file_clicked = pyqtSignal(str)
date_filter_changed = pyqtSignal(str, str)          # 날짜 필터
refresh_requested = pyqtSignal()                      # Refresh
close_all_windows_requested = pyqtSignal()            # Close All
axis_range_changed = pyqtSignal(str, str, float, float)  # 축 범위
time_range_selected = pyqtSignal(float, float)        # 시간 구간

# 좌측 패널: + QDateEdit From/To + Filter 버튼
# FFT 옵션: + Refresh (row 6, col 0) + Close All (row 6, col 1)
# 축 컨트롤: 인스턴스 변수 저장 (wave_*/spec_*), Set → axis_range_changed emit
# 축 라벨 클릭: _on_canvas_click → QInputDialog 팝업
# Y Auto 110%: _apply_auto_y_scale() 메서드
# SpanSelector: waveform에서 시간 구간 드래그 → time_range_selected emit
# Waveform Y축: WAVEFORM_Y_LABELS (RMS 미포함)
```

#### 7.2.2 `vibration/presentation/presenters/spectrum_presenter.py`

**이전:**
```python
class SpectrumPresenter:
    def __init__(self, view, fft_service, file_service):
        # 5개 시그널 연결
        # _on_compute_requested: 파일 로드 → FFT → 플롯

    # 메서드: _on_compute_requested, _on_view_type_changed,
    #         _on_window_type_changed, _on_next_file_requested,
    #         _on_file_clicked, _on_directory_selected, _on_files_loaded
```

**이후:**
```python
class SpectrumPresenter:
    def __init__(self, view, fft_service, file_service):
        self._custom_sensitivity: Optional[float] = None  # 커스텀 감도
        self._all_files: List[str] = []                     # 전체 파일 목록
        self._spectrum_windows: List[SpectrumWindow] = []   # 팝업 창 목록
        # 11개 시그널 연결 (6개 추가)

    # 추가 메서드:
    # _on_date_filter_changed(from_date, to_date) — 파일명에서 날짜 파싱, 필터링
    # _on_sensitivity_changed() — Sensitivity_edit returnPressed → 커스텀 감도 저장
    # _on_close_all_windows() — 모든 팝업 Spectrum 창 닫기
    # _on_axis_range_changed(plot_type, axis, min, max) — 축 범위 적용
    # _on_time_range_selected(t_start, t_end) — 시간 구간 FFT → SpectrumWindow 생성

    # 변경된 _on_compute_requested:
    #   + custom_sensitivity 적용 (data / (sensitivity_mV / 1000))
    # 변경된 _on_files_loaded:
    #   + _all_files 저장 (필터링 기준)
```

#### 7.2.3 `vibration/presentation/views/dialogs/spectrum_window.py` (신규)

```python
class SpectrumWindow(QWidget):
    """독립 스펙트럼 팝업 윈도우 — 시간 범위 선택 시 해당 구간 FFT 표시."""
    
    # 생성: SpectrumWindow(t_start, t_end)
    # 윈도우 타이틀: "Spectrum [0.500s - 1.200s]"
    # 크기: 800×500 (기본)
    # 기능: 호버 도트, 좌클릭 마커, 우클릭 마커 제거
    # 메서드: plot_spectrum(frequencies, spectrum, label, view_type)
    # non-modal (Qt.Window 플래그), 여러 개 동시 표시 가능
    # closeEvent: 리소스 정리 (canvas disconnect, figure clear)
```

### 7.3 하위 호환성

| 항목 | 호환성 |
|------|--------|
| 기존 시그널 | ✅ 모두 유지 (5개 원본 시그널 변경 없음) |
| 기존 위젯 변수명 | ✅ 변경 없음 (checkBox, Querry_list 등) |
| 레이아웃 구조 | ✅ 메인 그리드 위치 동일 (row 0-1, col 0-1) |
| 다른 탭 파일 | ✅ 변경 없음 (trend, peak, waterfall, data_query) |
| app.py | ✅ 변경 없음 (DI 연결 동일) |
| 도메인 모델 | ✅ 변경 없음 (models.py) |
| 서비스 레이어 | ✅ 변경 없음 (fft_service, file_service 등) |

---

## 6. Data Query 탭 강화 (2026-02-09)

### 6.1 변경 개요

Data Query 탭을 단순 파일 선택 도구에서 **프로젝트 기반 데이터 관리 허브**로 강화했습니다.

| 항목 | 이전 | 이후 |
|------|------|------|
| **폴더 스캔** | 단일 폴더만 스캔 | 엄마폴더 → 날짜별 서브폴더 재귀 스캔 |
| **날짜 필터** | 없음 | QDateEdit From/To 기간 필터링 |
| **테이블 컬럼** | 5개 (Date, Time, Count, Files, Select) | 9개 (+Ch, Fs(Hz), Sensitivity, Status) |
| **메타데이터 추출** | 파일 로딩 시에만 | `parse_header_only()` — 헤더만 빠르게 파싱 |
| **이상 파일 감지** | 없음 | 다수결 기반 sampling_rate 불일치 감지 |
| **이상 파일 관리** | 없음 | 우클릭 → Quarantine 이동 / 삭제 |
| **프로젝트 저장** | 없음 | JSON (이름+시각+설명+파일목록+메타데이터) |
| **프로젝트 로드** | 없음 | JSON에서 전체 상태 복원 |
| **결과 폴더** | 없음 | `results/spectrum/`, `results/trend/`, `results/peak/` 자동 생성 |
| **측정 타입 감지** | 없음 | IEPE + mV/g → ACC, 기타 → Pa 자동 판별 |

### 6.2 파일별 변경 상세

#### 신규 파일

##### `core/services/project_service.py` (165줄)
```python
# 프로젝트 저장/로드 서비스 (Qt 의존성 없음)
class ProjectService:
    def save_project(self, project_data, save_location) -> str
        # {이름}_{YYYYMMDD_HHMMSS}/project.json 생성
        # results/spectrum, trend, peak 하위 폴더 자동 생성
    
    def load_project(self, json_path) -> Optional[ProjectData]
        # JSON 역직렬화 → ProjectData 복원
    
    @staticmethod
    def build_project_data(parent_folder, description, grouped_data, measurement_type) -> ProjectData
        # 그룹화된 파일 데이터 → ProjectData 빌드
        # 상대경로 변환, 채널/날짜 집계, 다수결 sampling_rate 산출
```

#### 수정된 파일

##### `core/services/file_parser.py`

**이전:**
```python
class FileParser:
    def __init__(self, file_path):
        self._load_file()  # 항상 전체 데이터 로딩 (numpy 포함)
```

**이후:**
```python
class FileParser:
    @staticmethod
    def parse_header_only(filepath) -> dict:
        """메타데이터만 추출 — numpy 데이터 로딩 생략.
        첫 번째 숫자 데이터 라인에서 즉시 중단.
        수백 개 파일 스캔 시 10배 이상 빠름."""
        metadata = {}
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if is_data_line(line):
                    break  # 데이터 시작 → 즉시 중단
                if ':' in line:
                    # sampling_rate, channel, sensitivity 등 추출
        return metadata
    
    def __init__(self, file_path):
        self._load_file()  # 기존 전체 로딩 유지 (하위 호환)
```

##### `core/services/file_service.py`

**이전:**
```python
class FileService:
    def scan_directory(self, directory, pattern) -> List[FileMetadata]
    def scan_directory_grouped(self, directory, pattern) -> Dict
    # 단일 폴더만 지원
```

**이후:**
```python
class FileService:
    def scan_directory(self, directory, pattern) -> List[FileMetadata]       # 기존 유지
    def scan_directory_grouped(self, directory, pattern) -> Dict             # 기존 유지
    
    def scan_subdirectories(self, parent_dir, date_from=None, date_to=None, pattern="*.txt") -> List[str]:
        """날짜 기반 서브폴더(YYYY-MM-DD) 재귀 스캔.
        - date_from/date_to로 기간 필터링
        - 상위 폴더에 직접 .txt 있으면 단일 폴더 모드 (하위 호환)
        - 반환: 절대 경로 리스트"""
```

##### `core/domain/models.py`

**추가된 모델:**
```python
@dataclass
class ProjectFileInfo:
    """프로젝트 내 개별 파일 정보"""
    relative_path: str      # 엄마폴더 기준 상대경로
    date: str
    time: str
    channel: str = ''
    sampling_rate: float = 0.0
    sensitivity: str = ''
    is_anomaly: bool = False
    
    def to_dict(self) -> Dict: ...
    @classmethod
    def from_dict(cls, data) -> 'ProjectFileInfo': ...

@dataclass
class ProjectData:
    """프로젝트 저장/로드 컨테이너"""
    name: str               # 엄마폴더명
    description: str        # 사용자 설명
    created_at: str         # ISO 8601 타임스탬프
    parent_folder: str      # 절대경로
    measurement_type: str   # ACC / Pa / Unknown
    files: List[ProjectFileInfo]
    summary: Dict[str, Any] # total_files, date_range, channels, common_sampling_rate
    project_folder: str     # 생성된 프로젝트 폴더명
    
    def to_dict(self) -> Dict: ...
    @classmethod
    def from_dict(cls, data) -> 'ProjectData': ...
```

##### `presentation/models/file_list_model.py`

**이전:**
```python
class FileListModel(QAbstractTableModel):
    _headers = ['Date', 'Time', 'Count', 'Files', 'Select']  # 5개 컬럼
    
    def data(self, index, role):
        if role == Qt.DisplayRole:
            # Date, Time, Count, Files, Select만 처리
```

**이후:**
```python
# 컬럼 인덱스 상수 (매직넘버 제거)
COL_DATE = 0; COL_TIME = 1; COL_COUNT = 2; COL_CH = 3
COL_FS = 4; COL_SENSITIVITY = 5; COL_FILES = 6; COL_STATUS = 7; COL_SELECT = 8

ANOMALY_RED = QColor(255, 180, 180)
ANOMALY_YELLOW = QColor(255, 255, 180)

class FileListModel(QAbstractTableModel):
    _headers = ['Date', 'Time', 'Count', 'Ch', 'Fs(Hz)', 'Sensitivity', 'Files', 'Status', 'Select']
    
    def data(self, index, role):
        if role == Qt.DisplayRole:
            # 9개 컬럼 모두 처리 (Ch, Fs, Sensitivity, Status 추가)
        elif role == Qt.BackgroundRole:
            if row_data.get('is_anomaly'):
                return QBrush(ANOMALY_RED) if anomaly_type == 'error' else QBrush(ANOMALY_YELLOW)
    
    def get_row_data(self, row) -> Optional[Dict]:  # 신규
    def remove_rows(self, rows) -> None:             # 신규 (Quarantine/Delete용)
```

##### `presentation/views/tabs/data_query_tab.py`

**이전:**
```python
class DataQueryTabView(QWidget):
    # 시그널: directory_selected, files_loaded, files_chosen, switch_to_spectrum_requested, sensitivity_changed
    
    def _setup_ui(self):
        # Select, Load Data, directory_display, Choose 버튼만 존재
        self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # 매직넘버
        # 컨텍스트 메뉴 없음, 날짜 필터 없음, 프로젝트 버튼 없음
```

**이후:**
```python
class DataQueryTabView(QWidget):
    # 기존 시그널 유지 + 신규 시그널 4개 추가
    save_project_requested = pyqtSignal()
    load_project_requested = pyqtSignal()
    quarantine_requested = pyqtSignal(list)   # 선택된 행 인덱스
    delete_requested = pyqtSignal(list)       # 선택된 행 인덱스
    
    def _setup_ui(self):
        # [기존] Select, Load Data, directory_display, Choose
        # [추가] 날짜 필터 행: QDateEdit(From) ~ QDateEdit(To) + Type 라벨 + Save/Load Project 버튼
        # 테이블: COL_FILES 상수 사용, 우클릭 컨텍스트 메뉴, 행 선택 모드
    
    def _on_context_menu(self, pos):           # 우클릭 → Move to Quarantine / Delete
    def get_date_range(self):                  # From/To 날짜 반환
    def set_measurement_type(self, mtype):     # Type 라벨 업데이트
    def ask_project_description(self):         # QInputDialog로 설명 입력
    def ask_save_location(self):               # QFileDialog로 저장 위치 선택
    def ask_load_project_file(self):           # QFileDialog로 .json 선택
```

##### `presentation/presenters/data_query_presenter.py`

**이전:**
```python
class DataQueryPresenter:
    def __init__(self, view: DataQueryTabView):
        # FileParser만 사용, DI 없음
    
    def _load_files_from_directory(self):
        files = os.listdir(self._directory_path)
        # 단일 폴더 .txt 파일만 스캔
        # 날짜/시간으로 그룹화 → 테이블 표시
        # 메타데이터 추출 없음, anomaly 감지 없음
```

**이후:**
```python
class DataQueryPresenter:
    def __init__(self, view, file_service=None, project_service=None):
        # FileService + ProjectService DI 주입
    
    def _load_files_from_directory(self):
        # 1. scan_subdirectories()로 서브폴더 재귀 스캔 (날짜 필터 적용)
        # 2. 하위 호환: 서브폴더 없으면 단일 폴더 모드
        # 3. parse_header_only()로 각 파일 메타데이터 빠르게 추출
        # 4. 날짜/시간 그룹화 + 채널/Fs/Sensitivity 컬럼 데이터 구성
        # 5. _detect_anomalies(): 다수결 sampling_rate vs 각 그룹 비교
        # 6. _detect_measurement_type(): IEPE + mV/g → ACC, 기타 → Pa
        # 7. 테이블 + Type 라벨 업데이트
    
    def _on_save_project(self):    # description 입력 → 위치 선택 → JSON 저장
    def _on_load_project(self):    # .json 선택 → 상태 복원 → 결과 폴더 생성
    def _on_quarantine(self, rows): # 선택 파일 → quarantine/ 폴더로 이동
    def _on_delete(self, rows):     # 확인 다이얼로그 → 파일 삭제
```

##### `infrastructure/event_bus.py`

**추가된 시그널:**
```python
class EventBus(QObject):
    # [기존 시그널 유지]
    
    # 프로젝트 이벤트 (신규)
    project_saved = pyqtSignal(str)   # 저장된 project.json 경로
    project_loaded = pyqtSignal(str)  # 로드된 project.json 경로
```

##### `app.py`

**이전:**
```python
def create_services(self):
    self._services['file'] = FileService()
    # ... fft, trend, peak

def create_presenters(self, main_window):
    self._presenters['data_query'] = DataQueryPresenter(view=data_query_tab)
    # DI 없음 — view만 전달
```

**이후:**
```python
def create_services(self):
    self._services['file'] = FileService()
    self._services['project'] = ProjectService()    # 신규
    # ... fft, trend, peak

def create_presenters(self, main_window):
    self._presenters['data_query'] = DataQueryPresenter(
        view=data_query_tab,
        file_service=self._services['file'],        # DI 주입
        project_service=self._services['project'],  # DI 주입
    )
```

### 6.3 프로젝트 JSON 구조

```json
{
  "name": "ProjectA",
  "description": "1차 진동 측정 데이터",
  "created_at": "2026-02-09T12:45:00",
  "parent_folder": "/data/ProjectA",
  "measurement_type": "ACC",
  "files": [
    {
      "relative_path": "2025-01-10/2025-01-10_09-00-00_001_ch1.txt",
      "date": "2025-01-10",
      "time": "09:00:00",
      "channel": "ch1",
      "sampling_rate": 10240.0,
      "sensitivity": "100 mV/g",
      "is_anomaly": false
    }
  ],
  "summary": {
    "total_files": 150,
    "date_range": ["2025-01-10", "2025-01-12"],
    "channels": ["ch1", "ch2", "ch3"],
    "common_sampling_rate": 10240.0
  },
  "project_folder": "ProjectA_20260209_124500"
}
```

### 6.4 하위 호환성

| 시나리오 | 동작 |
|----------|------|
| 단일 폴더에 .txt 파일이 직접 있음 | 기존과 동일하게 스캔 (서브폴더 무시) |
| 기존 DataQueryPresenter(view=...) 호출 | `file_service`/`project_service` 기본값 자동 생성 |
| 기존 EventBus 시그널 | 변경 없음 (project_saved/loaded만 추가) |
| 기존 5컬럼 데이터 dict 전달 | 새 컬럼 값은 빈 문자열로 표시 |

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
