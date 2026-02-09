# 요구사항 Gap 분석 문서

> **작성일**: 2026-02-10
> **기준**: 코드베이스 전수 검사 (8개 탐색 에이전트 병렬 분석)
> **대상**: vibration/ 패키지 전체

---

## 종합 현황

| 상태 | 건수 | 설명 |
|------|------|------|
| ✅ 구현 완료 | 24 | 정상 동작 확인 |
| ⚠️ 부분 구현 | 4 | 일부 탭에만 적용 또는 미연결 |
| ❌ 미구현 | 6 | 코드 없음 |

---

## 1. 탭별 기능 매트릭스

### 1.1 Data Query 탭

| # | 기능 | 상태 | 위치 | 비고 |
|---|------|------|------|------|
| 1 | 엄마폴더 선택 | ✅ | `data_query_tab.py` | `directory_selected` 시그널 |
| 2 | 서브폴더 재귀 스캔 | ✅ | `file_service.py:scan_subdirectories()` | 날짜 기반 YYYY-MM-DD 폴더 |
| 3 | 날짜 필터 (From/To) | ✅ | `data_query_tab.py:68-85` | QDateEdit + Filter 버튼 |
| 4 | 9컬럼 테이블 | ✅ | `file_list_model.py` | Date, Time, Count, Ch, Fs, Sensitivity, Files, Status, Select |
| 5 | 헤더 전용 빠른 파싱 | ✅ | `file_parser.py:parse_header_only()` | numpy 로딩 생략 |
| 6 | 이상파일 감지 (다수결) | ✅ | `data_query_presenter.py` | sampling_rate 불일치 감지 |
| 7 | 이상파일 Quarantine/Delete | ✅ | `data_query_tab.py:_on_context_menu()` | 우클릭 컨텍스트 메뉴 |
| 8 | 프로젝트 저장 (JSON) | ✅ | `project_service.py` | 이름+시각+설명+파일+메타 |
| 9 | 프로젝트 로드 | ✅ | `project_service.py` | JSON → 전체 상태 복원 |
| 10 | 결과 폴더 자동 생성 | ✅ | `project_service.py` | results/spectrum, trend, peak |
| 11 | 측정 타입 자동 판별 | ✅ | `data_query_presenter.py` | IEPE+mV/g → ACC |
| 12 | Log Scale 옵션 | ❌ | — | 미구현 |

### 1.2 Time/Spectrum 탭

| # | 기능 | 상태 | 위치 | 비고 |
|---|------|------|------|------|
| 1 | FFT 스펙트럼 분석 | ✅ | `spectrum_presenter.py` + `fft_service.py` | welch 기반 |
| 2 | 날짜 필터 (From/To) | ✅ | `spectrum_tab.py:110-127` | QDateEdit + Filter |
| 3 | Sensitivity 다중 적용 | ✅ | `spectrum_presenter.py` | Enter → 선택 파일 일괄 |
| 4 | Refresh / Close All | ✅ | `spectrum_tab.py` | 재플롯 / 팝업 전체 닫기 |
| 5 | 축 컨트롤 (Set 버튼) | ✅ | `spectrum_tab.py:389-493` | X/Y min/max + Set |
| 6 | 축 라벨 클릭 범위 입력 | ✅ | `spectrum_tab.py:_on_canvas_click()` | QInputDialog 팝업 |
| 7 | SpanSelector 시간 구간 | ✅ | `spectrum_tab.py:675-692` | 드래그 → Spectrum 팝업 |
| 8 | Spectrum 팝업 (multi) | ✅ | `spectrum_window.py` | non-modal, 호버+마커 |
| 9 | Plot 배치 렌더링 | ✅ | `spectrum_presenter.py:_load_and_plot_files()` | begin/end_batch |
| 10 | Next 캐시 | ✅ | `spectrum_presenter.py:_computed_cache` | 새 파일만 계산 |
| 11 | Channel 체크박스 필터링 | ⚠️ | `spectrum_tab.py:91-102` | **UI만 존재, 시그널 미연결** |
| 12 | 마우스 스크롤 줌/팬 | ❌ | — | scroll_event 미연결 |
| 13 | 1초 Shift 버튼 | ❌ | — | Waveform 1초 이동 기능 없음 |

### 1.3 Trend 탭

| # | 기능 | 상태 | 위치 | 비고 |
|---|------|------|------|------|
| 1 | Overall RMS 트렌드 | ✅ | `trend_presenter.py` + `trend_service.py` | ProcessPoolExecutor 병렬 |
| 2 | Pick Data List | ✅ | `trend_tab.py:520-544` | 채널별 파일 피킹 |
| 3 | List Save (Detail Analysis) | ✅ | `list_save_dialog.py` | 디스크에서 직접 재로드+FFT |
| 4 | 날짜 필터 (From/To) | ❌ | — | **Waterfall/Spectrum에는 있으나 Trend에 없음** |
| 5 | Channel 체크박스 필터링 | ⚠️ | `trend_tab.py:81-92` | **UI만 존재, 시그널 미연결** |
| 6 | 계산 캐싱 | ❌ | — | **매번 전체 재계산 (Waterfall에는 있음)** |
| 7 | 마우스 스크롤 줌/팬 | ❌ | — | scroll_event 미연결 |

### 1.4 Peak 탭

| # | 기능 | 상태 | 위치 | 비고 |
|---|------|------|------|------|
| 1 | Peak 트렌드 분석 | ✅ | `peak_presenter.py` + `peak_service.py` | ProcessPoolExecutor 병렬 |
| 2 | Pick Data List | ✅ | `peak_tab.py` | 채널별 파일 피킹 |
| 3 | List Save (Detail Analysis) | ✅ | `list_save_dialog.py` | 디스크에서 직접 재로드+FFT |
| 4 | 날짜 필터 (From/To) | ❌ | — | **Waterfall/Spectrum에는 있으나 Peak에 없음** |
| 5 | Channel 체크박스 필터링 | ⚠️ | `peak_tab.py:86-97` | **UI만 존재, 시그널 미연결** |
| 6 | 계산 캐싱 | ❌ | — | **매번 전체 재계산 (Waterfall에는 있음)** |
| 7 | 마우스 스크롤 줌/팬 | ❌ | — | scroll_event 미연결 |

### 1.5 Waterfall 탭

| # | 기능 | 상태 | 위치 | 비고 |
|---|------|------|------|------|
| 1 | 3D Waterfall 플롯 | ✅ | `waterfall_presenter.py` | FFT 캐싱 포함 |
| 2 | 날짜 필터 (From/To) | ✅ | `waterfall_tab.py:139-171` | QDateEdit + Filter |
| 3 | Y축 시간 라벨 | ✅ | `waterfall_presenter.py` | MM-DD HH:MM:SS |
| 4 | X축 Nice-Number 그리드 | ✅ | `waterfall_presenter.py` | 1/2/5 × 10^n |
| 5 | Picking (호버+마커) | ✅ | `waterfall_tab.py` | 좌클릭 마커, 우클릭 제거 |
| 6 | Single Band Trend | ✅ | `waterfall_presenter.py` | 주파수 입력 → 시간별 진폭 |
| 7 | 채널별 파일 그룹핑 | ✅ | `waterfall_tab.py` | 6색 색상 구분 |
| 8 | Channel 체크박스 필터링 | ✅ | `waterfall_tab.py:398-435` | **완전 동작** (유일) |
| 9 | FFT 결과 캐싱 | ✅ | `waterfall_presenter.py:_waterfall_cache` | 파라미터 변경 시만 재계산 |
| 10 | 마우스 스크롤 줌/팬 | ❌ | — | scroll_event 미연결 |

### 1.6 공통 / 인프라

| # | 기능 | 상태 | 위치 | 비고 |
|---|------|------|------|------|
| 1 | DPI/반응형 스케일링 | ✅ | `responsive_layout_utils.py` | Mixin + 유틸 함수 |
| 2 | EventBus | ✅ | `event_bus.py` | PyQt 시그널 기반 |
| 3 | 스플래시 스크린 | ✅ | `splash_screen.py` | 로딩 진행률 표시 |
| 4 | PyInstaller exe 빌드 | ✅ | `CNAVE_Analyzer.spec` | Windows + macOS |
| 5 | 라이선싱 / USB 동글 | ❌ | — | 전혀 미구현 |
| 6 | 버전 관리 (SemVer) | ⚠️ | — | 코드 내 버전 번호 미확인 |

---

## 2. Gap 우선순위 분류

### 🔴 Priority 1 — 이번 작업 대상 (선택됨)

| # | Gap | 영향도 | 작업량 | 구현 계획 |
|---|-----|--------|--------|-----------|
| **G1** | Channel 체크박스 기능 연결 (Spectrum/Trend/Peak) | HIGH | MEDIUM | Waterfall 패턴 복제 — `stateChanged` → `_on_channel_filter_changed` → `_update_filtered_file_list()` |
| **G2** | 마우스 스크롤 줌/팬 (전 탭) | HIGH | MEDIUM | `scroll_event` → X/Y축 줌, Ctrl+드래그 → 팬. 기존 picking과 충돌 방지 필요 |
| **G3** | Trend/Peak 계산 캐싱 | HIGH | LOW | Waterfall `_waterfall_cache` 패턴 복제 — params 비교 → hit/miss → 재계산 |

### 🟡 Priority 2 — 기능 보강

| # | Gap | 영향도 | 작업량 | 비고 |
|---|-----|--------|--------|------|
| **G4** | Trend/Peak 날짜 필터 | MEDIUM | LOW | Waterfall/Spectrum에서 복제 |
| **G5** | 1초 Shift 버튼 (Spectrum) | MEDIUM | LOW | Waveform X축 ±1초 이동 버튼 |
| **G6** | Log Scale (Data Query) | LOW | LOW | `set_yscale('log')` 토글 |
| **G7** | 버전 관리 체계 | LOW | LOW | `__version__` + 스플래시 표시 |

### 🔵 Priority 3 — 향후 과제

| # | Gap | 비고 |
|---|-----|------|
| **G8** | 라이선싱 / USB 동글 / 만료 | 배포 시점에 결정 |
| **G9** | 해상도/스케일링 실기기 테스트 | 다양한 DPI 환경에서 QA |
| **G10** | Spectrogram 탭 | 요구사항에 언급, 아직 미착수 |
| **G11** | Multi-band Trend (1/1, 1/3 Octave) | 요구사항에 언급, 아직 미착수 |
| **G12** | RPM 매칭 | 요구사항에 언급, 아직 미착수 |

---

## 3. 구현 참조 패턴

### 3.1 Channel 체크박스 (Waterfall 패턴 → Spectrum/Trend/Peak 복제)

**참조 코드**: `waterfall_tab.py` lines 398-435

```python
# 1. 시그널 정의
channel_filter_changed = pyqtSignal()

# 2. 체크박스 연결 (기존 체크박스 재활용)
self.checkBox_7.stateChanged.connect(self._on_channel_filter_changed)
# ... 6개 모두 연결

# 3. 핸들러
def _on_channel_filter_changed(self):
    self._update_filtered_file_list()
    self.channel_filter_changed.emit()

# 4. 필터링 로직
def _update_filtered_file_list(self):
    selected_channels = []
    for idx, checkbox in enumerate(checkboxes, start=1):
        if checkbox.isChecked():
            selected_channels.append(str(idx))
    if not selected_channels:
        # 전부 미선택 = 전부 표시
        self._populate_file_list(self._all_files)
        return
    filtered = [f for f in self._all_files
                if any(f.endswith(f"_{ch}.txt") for ch in selected_channels)]
    self._populate_file_list(filtered)
```

### 3.2 마우스 스크롤 줌 (신규 구현)

```python
# scroll_event 연결
self.canvas.mpl_connect('scroll_event', self._on_scroll)

def _on_scroll(self, event):
    if event.inaxes is None:
        return
    ax = event.inaxes
    scale_factor = 0.9 if event.button == 'up' else 1.1
    
    # 현재 축 범위
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    
    # 마우스 위치 기준 줌
    xdata, ydata = event.xdata, event.ydata
    new_width = (xlim[1] - xlim[0]) * scale_factor
    new_height = (ylim[1] - ylim[0]) * scale_factor
    
    relx = (xlim[1] - xdata) / (xlim[1] - xlim[0])
    rely = (ylim[1] - ydata) / (ylim[1] - ylim[0])
    
    ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
    ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
    self.canvas.draw_idle()
```

### 3.3 Trend/Peak 캐싱 (Waterfall 패턴 복제)

```python
# 캐시 구조
self._trend_cache: Dict[str, Any] = {
    'computed': False,
    'result': None,
    'params': {}
}

# 파라미터 비교
current_params = {
    'delta_f': delta_f, 'overlap': overlap,
    'window_type': window_type, 'view_type': view_type,
    'frequency_band': frequency_band,
    'file_count': len(file_paths),
    'file_names': tuple(file_paths)
}

cache_valid = (
    self._trend_cache['computed'] and
    self._trend_cache['params'] == current_params
)

if not cache_valid:
    result = self.trend_service.compute_trend(...)
    self._trend_cache = {
        'computed': True, 'result': result, 'params': current_params
    }
else:
    result = self._trend_cache['result']
```

---

## 4. Detail Analysis 검증 결과

> **결론: 정상 동작** (이전 "BROKEN" 평가는 부정확)

`list_save_dialog_helpers.py`의 `load_file_with_fft()`가 원본 .txt 파일을 디스크에서 직접 읽고 `FFTEngine`으로 FFT를 재계산합니다. JSON 메타데이터는 FFT 파라미터(delta_f, overlap, window, view_type) 참조용으로만 사용되며, 없으면 기본값으로 fallback합니다.

| 항목 | 동작 |
|------|------|
| 파일 데이터 | 디스크에서 직접 `FileParser`로 로드 |
| FFT 계산 | `FFTEngine.compute()`로 실시간 계산 |
| JSON 의존성 | FFT 파라미터만 참조 (데이터 아님) |
| directory_path 전달 | `trend_tab.py:538` → presenter → `ListSaveDialog` → helpers 정상 |

**주의**: JSON 메타데이터 없을 시 FFT 기본값(delta_f=1.0, overlap=50, hanning, ACC) 사용 → 원래 분석과 다른 결과 가능 (엣지 케이스)

---

## 5. 작업 로드맵

```
Phase 1 (이번 작업) ━━━━━━━━━━━━━━━━━━━━
 ├─ G1: Channel 체크박스 연결 (Spectrum/Trend/Peak)
 ├─ G2: 마우스 스크롤 줌/팬 (전 탭)
 └─ G3: Trend/Peak 캐싱

Phase 2 (후속) ━━━━━━━━━━━━━━━━━━━━━━━━
 ├─ G4: Trend/Peak 날짜 필터
 ├─ G5: 1초 Shift 버튼
 ├─ G6: Log Scale
 └─ G7: 버전 관리

Phase 3 (향후) ━━━━━━━━━━━━━━━━━━━━━━━━
 ├─ G8: 라이선싱
 ├─ G9: 해상도 QA
 ├─ G10: Spectrogram 탭
 ├─ G11: Multi-band Trend
 └─ G12: RPM 매칭
```
