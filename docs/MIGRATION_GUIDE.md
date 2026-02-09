# 마이그레이션 가이드: 레거시 → 모듈화 아키텍처

## 개요

이 문서는 레거시 코드(`cn_3F_trend_optimized.py`)를 참조하는 코드를 새로운 모듈화 아키텍처로
마이그레이션하는 방법을 안내합니다.

---

## 1. 임포트 변경

### 1.1 기본 임포트 매핑

```python
# ========== 레거시 ==========
from cn_3F_trend_optimized import Ui_MainWindow

# ========== 리팩토링 ==========
from vibration.presentation.views import MainWindow
```

### 1.2 서비스 임포트

```python
# ========== 레거시 ==========
# 서비스 레이어 없음 - 모든 로직이 Ui_MainWindow 내부

# ========== 리팩토링 ==========
from vibration.core.services import FFTService, TrendService, PeakService, FileService
from vibration.core.services.fft_engine import FFTEngine
from vibration.core.services.file_parser import FileParser
```

### 1.3 도메인 모델 임포트

```python
# ========== 레거시 ==========
# 모델 없음 - raw dict/numpy array 사용

# ========== 리팩토링 ==========
from vibration.core.domain.models import FFTResult, SignalData, TrendResult, FileMetadata
```

### 1.4 프레젠터 임포트

```python
# ========== 레거시 ==========
# 프레젠터 패턴 없음

# ========== 리팩토링 ==========
from vibration.presentation.presenters import (
    DataQueryPresenter,
    SpectrumPresenter,
    TrendPresenter,
    WaterfallPresenter,
    PeakPresenter,
)
```

### 1.5 뷰 임포트

```python
# ========== 레거시 ==========
# 모든 UI가 Ui_MainWindow 안에 포함

# ========== 리팩토링 ==========
from vibration.presentation.views import MainWindow
from vibration.presentation.views.tabs import (
    DataQueryTabView,
    SpectrumTabView,
    TrendTabView,
    WaterfallTabView,
    PeakTabView,
)
from vibration.presentation.views.dialogs import (
    ProgressDialog,
    AxisRangeDialog,
    ListSaveDialog,
)
from vibration.presentation.views.widgets import PlotWidget, MarkerManager
```

### 1.6 인프라스트럭처 임포트

```python
# ========== 레거시 ==========
# 이벤트 시스템 없음

# ========== 리팩토링 ==========
from vibration.infrastructure import get_event_bus, EventBus
```

---

## 2. 호환성 레이어

현재 `vibration/legacy/cn_3F_trend_optimized.py`는 **호환성 심(shim)**으로 동작합니다.
기존 임포트가 자동으로 새 모듈로 리다이렉트됩니다.

```python
# 이 코드는 여전히 동작하지만 DeprecationWarning 발생
from vibration.legacy.cn_3F_trend_optimized import ProgressDialog

# 권장: 직접 임포트
from vibration.presentation.views.dialogs import ProgressDialog
```

> **경고**: 호환성 레이어는 v3.0에서 제거될 예정입니다. 직접 임포트로 마이그레이션하세요.

---

## 3. 코드 패턴 변경

### 3.1 파일 로딩

```python
# ========== 레거시 ==========
data = []
with open(file_path, 'r') as f:
    for line in f:
        data.append(float(line))
data = np.array(data)

# ========== 리팩토링 ==========
file_service = FileService()
result = file_service.load_file(filepath)
data = result['data']
sampling_rate = result['sampling_rate']
```

### 3.2 FFT 연산

```python
# ========== 레거시 ==========
# 인라인 FFT (scipy 직접 호출)
f, Pxx = signal.welch(data, fs=sampling_rate, ...)
P = np.sqrt(Pxx)
# ACC→VEL 변환 (인라인)
if view_type == 2:
    P = P / (2 * np.pi * f + 1e-10)

# ========== 리팩토링 ==========
fft_service = FFTService(
    sampling_rate=sampling_rate,
    delta_f=1.0,
    overlap=50.0,
    window_type='hanning'
)
result: FFTResult = fft_service.compute_spectrum(
    data=data,
    view_type='VEL',
    input_signal_type='ACC'
)
# result.frequency, result.spectrum, result.rms 등 접근
```

### 3.3 트렌드 분석

```python
# ========== 레거시 ==========
# 순차 for 루프
rms_list = []
for file_path in file_paths:
    data = load_txt_file_only(file_path)
    # ... FFT + RMS 계산 ...
    rms_list.append(rms)
# UI 직접 업데이트
self.trend_ax.plot(timestamps, rms_list)

# ========== 리팩토링 ==========
trend_service = TrendService(max_workers=None)  # CPU-1 자동
result: TrendResult = trend_service.compute_trend(
    file_paths=file_paths,
    delta_f=1.0,
    overlap=50.0,
    window_type='hanning',
    view_type=1,  # ACC
    frequency_band=(0, 10000),
    progress_callback=lambda current, total: print(f"{current}/{total}")
)
# result.rms_values, result.timestamps, result.filenames 등 접근
```

### 3.4 진행률 표시

```python
# ========== 레거시 ==========
# 정적 메시지만 표시
progress = QProgressDialog("파일 처리 중...", None, 0, 0, self)
progress.show()
# ... 작업 ... (진행률 업데이트 없음)
progress.close()

# ========== 리팩토링 ==========
progress_dialog = ProgressDialog(total_tasks=len(file_paths), parent=self)
progress_dialog.show()

def update_progress(current, total):
    progress_dialog.update_progress(current)
    QApplication.processEvents()

result = trend_service.compute_trend(
    file_paths=file_paths,
    ...,
    progress_callback=update_progress  # 실시간 진행률
)
progress_dialog.close()
```

### 3.5 이벤트 통신

```python
# ========== 레거시 ==========
# 직접 메서드 호출 (강결합)
self.tab_widget.setCurrentIndex(2)  # 탭 전환
self.plot_data_file_spectrem()      # 직접 호출

# ========== 리팩토링 ==========
# 이벤트 버스를 통한 느슨한 결합
bus = get_event_bus()
bus.tab_changed.emit("spectrum")
bus.file_loaded.emit(filepath)

# 구독
bus.file_loaded.connect(self._on_file_loaded)
bus.view_type_changed.connect(self._on_view_type_changed)
```

---

## 4. 애플리케이션 초기화

### 레거시
```python
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
```

### 리팩토링
```python
# 방법 1: ApplicationFactory 사용 (권장)
from vibration.app import ApplicationFactory

factory = ApplicationFactory(config={
    'sampling_rate': 10240.0,
    'delta_f': 1.0,
    'max_workers': None
})
main_window = factory.create_application()
main_window.show()

# 방법 2: main() 진입점
from vibration.app import main
main()

# 방법 3: 모듈 실행
# python -m vibration
```

---

## 5. 탭별 접근 방법

### 레거시
```python
# 모든 위젯이 self에 직접 존재
self.Querry_list.addItems(files)       # Tab 1
self.Querry_list2.addItems(files)      # Tab 2
self.Querry_list3.addItems(files)      # Tab 4
self.Hz.toPlainText()                  # Δf 입력
self.Function.currentText()            # 윈도우 함수
```

### 리팩토링
```python
# 탭별 독립 뷰를 통해 접근
data_tab = main_window.get_tab(MainWindow.TAB_DATA_QUERY)
spectrum_tab = main_window.get_tab(MainWindow.TAB_SPECTRUM)
trend_tab = main_window.get_tab(MainWindow.TAB_TREND)

# 뷰 메서드로 데이터 설정/조회
spectrum_tab.set_files(files)
params = trend_tab.get_parameters()  # {delta_f, window_type, overlap, ...}
selected = trend_tab.get_selected_files()
```

---

## 6. 테스트 작성 가이드

### 레거시 (테스트 불가)
```python
# UI 의존성으로 인해 단위 테스트 불가
# QApplication 인스턴스 필요
# 실제 파일 I/O 필요
```

### 리팩토링 (서비스 레이어 테스트)
```python
# core/ 레이어는 Qt 의존성 없이 테스트 가능
import numpy as np
from vibration.core.services import FFTService

def test_fft_service():
    service = FFTService(
        sampling_rate=10240.0,
        delta_f=1.0,
        overlap=50.0,
        window_type='hanning'
    )

    # 테스트 신호: 100Hz 사인파
    t = np.linspace(0, 1, 10240)
    data = np.sin(2 * np.pi * 100 * t)

    result = service.compute_spectrum(data, view_type='ACC')

    assert result.peak_frequency == pytest.approx(100.0, abs=1.0)
    assert result.rms > 0
    assert len(result.frequency) == len(result.spectrum)
```

---

## 7. 주의사항

### 7.1 레거시 코드 직접 수정 금지
- `vibration/legacy/` 내 파일은 **참조 전용**
- 신규 기능 추가 시 `vibration/` 패키지에 구현

### 7.2 호환성 심 제거 예정
- `cn_3F_trend_optimized.py` 호환성 레이어는 v3.0에서 제거
- 마이그레이션 완료 후 레거시 임포트를 새 경로로 교체

### 7.3 의존성 방향 준수
```
app.py → presentation/ → core/
                       → infrastructure/

금지: core/ → presentation/ (역방향 의존)
금지: core/ → PyQt5 (프레임워크 의존)
```

### 7.4 프레젠터 규칙
- 프레젠터는 뷰와 서비스를 **조율만** 수행
- 프레젠터에 비즈니스 로직 직접 구현 금지
- 프레젠터에 UI 위젯 직접 생성 금지 (ProgressDialog 제외)
