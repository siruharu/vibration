# Modular Package Structure Refactoring Plan

## TL;DR

> **Quick Summary**: Refactor the 6,235-line monolithic `cn_3F_trend_optimized.py` into a clean, testable package structure using the MVP pattern. Extract in 5 phases: Dialogs → Spectrum Tab → Trend Tab → Remaining Tabs → Main Window Shell.
> 
> **Deliverables**:
> - New `vibration/` package with layered architecture (core, presentation, infrastructure)
> - 13 existing optimization modules reorganized (not rewritten)
> - Backward-compatible transition layer during migration
> - Unit tests for core business logic
> - ~150 lines per module maximum
> 
> **Estimated Effort**: Large (40-60 hours across 5 phases)
> **Parallel Execution**: YES - 3 waves per phase
> **Critical Path**: Phase 1 (Dialogs) → Phase 2 (Spectrum) → Phase 3 (Trend) → Phase 4 (Tabs) → Phase 5 (Shell)

---

## Context

### Original Request
Design and implement a modular package structure for a PyQt5 vibration analysis application with a 6,235-line monolithic file that needs to be refactored for maintainability, testability, and scalability.

### Interview Summary
**Key Decisions**:
- **Migration Strategy**: Incremental - one module at a time, test each step
- **Backward Compatibility**: Temporary transition layer during migration, then deprecate
- **Priority Order**: Dialogs → Tab 3 (Spectrum) → Tab 4 (Trend) → Remaining Tabs → Main Window Shell
- **Testing Strategy**: Business logic only (core analysis modules), skip UI testing
- **State Management**: Minimal centralization using simple dataclasses

**Additional Preferences**:
- Follow MVP (Model-View-Presenter) pattern
- Keep OPTIMIZATION_PATCH_* modules as-is, just reorganize
- Use dependency injection for testability
- Target ~150 lines per module maximum

### Research Findings
**Codebase Analysis**:
- `cn_3F_trend_optimized.py`: 6,235 lines, 4 classes, 106 methods
- `Ui_MainWindow`: 5,300+ lines (85% of file) - the main target
- `setupUi()`: 1,333 lines - needs splitting into tab builders
- 8 natural seams identified for extraction
- 13 existing optimization/utility modules already modular

**Architecture Recommendation**:
- MVP pattern with Qt's Model/View for tables
- Layered architecture: Core → Application → Presentation → Infrastructure
- Custom signals for loose coupling between modules
- Constructor injection + Factory pattern for DI

### Gap Analysis (Self-Performed)
**Identified Gaps** (addressed in plan):
1. **Entry Point Handling**: Need to ensure `python cn_3F_trend_optimized.py` still works → Solution: Transition layer with re-exports
2. **PyInstaller Spec**: May need updating after refactor → Added as final task
3. **Circular Import Prevention**: Strategy needed → Solution: Layered architecture with strict import rules
4. **ListSaveDialog Coupling**: Check for tight coupling to main window → Research task added
5. **Shared State Discovery**: May have more shared state than expected → Audit task added

---

## Work Objectives

### Core Objective
Transform the monolithic 6,235-line PyQt5 application into a modular, testable package structure following MVP architecture, while maintaining 100% backward compatibility during the transition period.

### Concrete Deliverables
1. **Package Structure**: `vibration/` package with `core/`, `presentation/`, `infrastructure/` layers
2. **Dialog Modules**: `progress_dialog.py`, `axis_range_dialog.py`, `list_save_dialog.py` (~150 lines each)
3. **Tab Modules**: 5 tab view files + 5 presenter files (~150 lines each)
4. **Core Services**: `fft_service.py`, `trend_service.py`, `peak_service.py`, `file_service.py`
5. **Transition Layer**: `cn_3F_trend_optimized.py` becomes thin wrapper with re-exports
6. **Unit Tests**: Tests for core services (FFT, trend, peak analysis)
7. **Updated Build**: PyInstaller spec updated for new structure

### Definition of Done
- [ ] `python cn_3F_trend_optimized.py` launches app (backward compat)
- [ ] `python -m vibration` launches app (new entry point)
- [ ] All 5 tabs function identically to current behavior
- [ ] All optimization modules work without performance regression
- [ ] Unit tests pass for core services: `python -m pytest tests/unit/`
- [ ] No circular import errors on startup
- [ ] Each module ≤150 lines (exceptions documented)

### Must Have
- Backward compatibility via transition layer
- MVP pattern for UI/logic separation
- Unit tests for core analysis logic (FFT, trend, peak)
- ~150 lines per module maximum
- Korean comment preservation
- Zero performance regression in critical paths

### Must NOT Have (Guardrails)
- **NO rewriting optimization modules** - reorganize only, keep code identical
- **NO new features** - pure refactoring, no behavior changes
- **NO over-engineering** - simple dataclasses, no complex state management frameworks
- **NO breaking existing imports** until final deprecation phase
- **NO UI testing** - focus on business logic tests only
- **NO circular dependencies** - strict layer enforcement

---

## Verification Strategy

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.
> The executing agent verifies each deliverable using tools (Bash, Python, pytest).

### Test Decision
- **Infrastructure exists**: NO (need to set up pytest)
- **Automated tests**: YES (Tests-after for core services)
- **Framework**: pytest

### Test Setup Task (Phase 1)
- Install: `pip install pytest pytest-cov`
- Config: Create `pytest.ini` and `tests/` directory
- Verify: `pytest --version` → shows version
- Example: Create `tests/unit/test_example.py`
- Verify: `pytest tests/` → 1 test passes

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

**Verification Tool by Deliverable Type:**

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| **Module extraction** | Bash (python -c "from X import Y") | Import succeeds, no errors |
| **Application launch** | Bash (timeout 5s python app.py) | App starts without crash |
| **Unit tests** | Bash (pytest tests/unit/) | All tests pass |
| **Import compatibility** | Bash (python -c "from cn_3F... import ...") | Old imports still work |
| **No circular imports** | Bash (python -c "import vibration") | No ImportError |

---

## Execution Strategy

### Phase Overview

```
Phase 1: Foundation + Dialogs (Week 1)
├── Task 1.1: Create package structure
├── Task 1.2: Set up test infrastructure
├── Task 1.3: Extract ProgressDialog
├── Task 1.4: Extract AxisRangeDialog
└── Task 1.5: Extract ListSaveDialog + dependencies

Phase 2: Spectrum Tab Extraction (Week 2)
├── Task 2.1: Extract FFT service (core)
├── Task 2.2: Create plot widget base class
├── Task 2.3: Extract spectrum tab view
├── Task 2.4: Create spectrum presenter
└── Task 2.5: Write FFT service tests

Phase 3: Trend Tab Extraction (Week 3)
├── Task 3.1: Extract trend service (core)
├── Task 3.2: Extract trend tab view
├── Task 3.3: Create trend presenter
├── Task 3.4: Write trend service tests
└── Task 3.5: Extract marker manager (shared widget)

Phase 4: Remaining Tabs (Week 4)
├── Task 4.1: Extract data query tab
├── Task 4.2: Extract waterfall tab
├── Task 4.3: Extract peak tab
├── Task 4.4: Extract file service (core)
└── Task 4.5: Write file service tests

Phase 5: Main Window Shell + Cleanup (Week 5)
├── Task 5.1: Create main window shell
├── Task 5.2: Create application factory
├── Task 5.3: Create event bus for signals
├── Task 5.4: Update transition layer
├── Task 5.5: Update PyInstaller spec
└── Task 5.6: Final integration tests
```

### Parallel Execution Waves

```
Phase 1 Wave 1 (Start Immediately):
├── Task 1.1: Create package structure
└── Task 1.2: Set up test infrastructure

Phase 1 Wave 2 (After Wave 1):
├── Task 1.3: Extract ProgressDialog
└── Task 1.4: Extract AxisRangeDialog

Phase 1 Wave 3 (After Wave 2):
└── Task 1.5: Extract ListSaveDialog
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1.1 | None | 1.3, 1.4, 1.5 | 1.2 |
| 1.2 | None | 2.5, 3.4, 4.5 | 1.1 |
| 1.3 | 1.1 | 1.5 | 1.4 |
| 1.4 | 1.1 | 1.5 | 1.3 |
| 1.5 | 1.3, 1.4 | 2.1 | None |
| 2.1 | 1.5 | 2.3, 2.4 | 2.2 |
| 2.2 | 1.5 | 2.3, 3.2, 4.2 | 2.1 |
| 2.3 | 2.1, 2.2 | 2.4 | None |
| 2.4 | 2.3 | 3.1 | 2.5 |
| 2.5 | 2.1, 1.2 | None | 2.4 |

---

## Package Structure

### Target Directory Layout

```
vibration/
├── __init__.py                    # Package exports
├── __main__.py                    # Entry: python -m vibration
├── app.py                         # ApplicationFactory, main()
│
├── core/                          # Business logic (NO Qt imports!)
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models.py              # FFTResult, TrendResult, FileMetadata dataclasses
│   │   └── constants.py           # Window types, view types, defaults
│   ├── services/
│   │   ├── __init__.py
│   │   ├── fft_service.py         # Wraps fft_engine, adds business logic
│   │   ├── trend_service.py       # Wraps Level 5 trend processor
│   │   ├── peak_service.py        # Wraps Level 5 peak processor
│   │   ├── file_service.py        # Wraps file_parser, directory scanning
│   │   └── export_service.py      # CSV/JSON export logic
│   └── interfaces/
│       ├── __init__.py
│       └── repositories.py        # Abstract interfaces for DI
│
├── presentation/                  # Qt-specific code
│   ├── __init__.py
│   ├── views/
│   │   ├── __init__.py
│   │   ├── main_window.py         # Shell only (~200 lines)
│   │   ├── tabs/
│   │   │   ├── __init__.py
│   │   │   ├── data_query_tab.py  # Tab 1 view
│   │   │   ├── waterfall_tab.py   # Tab 2 view
│   │   │   ├── spectrum_tab.py    # Tab 3 view
│   │   │   ├── trend_tab.py       # Tab 4 view
│   │   │   └── peak_tab.py        # Tab 5 view
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── plot_widget.py     # Base matplotlib widget
│   │   │   ├── spectrum_plot.py   # Spectrum-specific plotting
│   │   │   ├── trend_plot.py      # Trend-specific plotting
│   │   │   └── marker_manager.py  # Shared marker logic
│   │   └── dialogs/
│   │       ├── __init__.py
│   │       ├── progress_dialog.py
│   │       ├── axis_range_dialog.py
│   │       └── list_save_dialog.py
│   ├── presenters/
│   │   ├── __init__.py
│   │   ├── main_presenter.py      # Main window coordination
│   │   ├── data_query_presenter.py
│   │   ├── waterfall_presenter.py
│   │   ├── spectrum_presenter.py
│   │   ├── trend_presenter.py
│   │   └── peak_presenter.py
│   └── models/
│       ├── __init__.py
│       └── file_list_model.py     # QAbstractTableModel for file list
│
├── infrastructure/                # Cross-cutting concerns
│   ├── __init__.py
│   ├── platform_config.py         # Existing (moved)
│   ├── performance_logger.py      # Existing (moved)
│   ├── json_handler.py            # Existing (moved)
│   ├── event_bus.py               # New: inter-module signals
│   └── threading/
│       ├── __init__.py
│       └── worker_thread.py       # QThread worker pattern
│
├── optimization/                  # Existing modules (reorganized, NOT rewritten)
│   ├── __init__.py
│   ├── level1_caching.py          # FileCache, BatchProcessor (was OPTIMIZATION_PATCH_LEVEL1)
│   ├── level3_ultra.py            # UltraParallelProcessor (was LEVEL3_ULTRA)
│   ├── level4_rendering.py        # ParallelTrendSaver (was LEVEL4_RENDERING)
│   └── level5/
│       ├── __init__.py
│       ├── spectrum_processor.py  # SpectrumParallelProcessor (was LEVEL5_SPECTRUM)
│       └── trend_processor.py     # TrendParallelProcessor (was LEVEL5_TREND)
│
└── legacy/                        # Transition layer
    ├── __init__.py
    └── compat.py                  # Re-exports for backward compatibility

tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── test_fft_service.py
│   ├── test_trend_service.py
│   ├── test_peak_service.py
│   └── test_file_service.py
└── integration/
    ├── __init__.py
    └── test_analysis_workflow.py

cn_3F_trend_optimized.py           # Transition layer: thin wrapper with re-exports
```

---

## TODOs

### Phase 1: Foundation + Dialogs

- [x] 1.1. Create Package Structure

  **What to do**:
  - Create `vibration/` directory with `__init__.py`
  - Create subdirectories: `core/`, `presentation/`, `infrastructure/`, `optimization/`, `legacy/`
  - Create nested directories per structure above
  - Add `__init__.py` files to all packages
  - Create `vibration/__main__.py` with placeholder main()

  **Must NOT do**:
  - Do NOT move any code yet - just create empty structure
  - Do NOT modify existing files
  - Do NOT create any business logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple file/directory creation, no complex logic
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - `git-master`: Not needed for file creation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1.2)
  - **Blocks**: Tasks 1.3, 1.4, 1.5
  - **Blocked By**: None

  **References**:
  - Package structure diagram above - exact directories to create
  - `AGENTS.md` - Python package conventions

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Package structure is importable
    Tool: Bash (python)
    Preconditions: Package directories created
    Steps:
      1. python -c "import vibration"
      2. python -c "from vibration import core, presentation, infrastructure"
      3. python -c "from vibration.presentation import views, presenters"
    Expected Result: All imports succeed with no errors
    Evidence: Exit code 0 for all commands

  Scenario: Directory structure matches specification
    Tool: Bash (find)
    Preconditions: Package created
    Steps:
      1. find vibration -name "__init__.py" | wc -l
      2. Assert: Count >= 15 (all packages have __init__.py)
    Expected Result: All directories are proper Python packages
    Evidence: Command output showing count
  ```

  **Commit**: YES
  - Message: `refactor(structure): create vibration package skeleton`
  - Files: `vibration/**/__init__.py`, `vibration/__main__.py`
  - Pre-commit: `python -c "import vibration"`

---

- [x] 1.2. Set Up Test Infrastructure

  **What to do**:
  - Install pytest: `pip install pytest pytest-cov`
  - Create `pytest.ini` with configuration
  - Create `tests/` directory structure
  - Create `tests/conftest.py` with shared fixtures
  - Create `tests/unit/test_example.py` with passing test
  - Update `requirements.txt` with pytest

  **Must NOT do**:
  - Do NOT write actual business logic tests yet
  - Do NOT modify production code

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple configuration setup
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1.1)
  - **Blocks**: Tasks 2.5, 3.4, 4.5
  - **Blocked By**: None

  **References**:
  - `AGENTS.md` - Test conventions ("Run module test" section)
  - pytest documentation for configuration

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Pytest runs successfully
    Tool: Bash (pytest)
    Preconditions: pytest installed, tests/ directory exists
    Steps:
      1. pytest tests/unit/test_example.py -v
      2. Assert: Exit code 0
      3. Assert: Output contains "1 passed"
    Expected Result: Example test passes
    Evidence: pytest output captured

  Scenario: Pytest configuration is valid
    Tool: Bash (pytest)
    Preconditions: pytest.ini exists
    Steps:
      1. pytest --co tests/
      2. Assert: No configuration errors
    Expected Result: Collection succeeds
    Evidence: Command output
  ```

  **Commit**: YES
  - Message: `test(setup): add pytest infrastructure`
  - Files: `pytest.ini`, `tests/**`, `requirements.txt`
  - Pre-commit: `pytest tests/unit/test_example.py`

---

- [ ] 1.3. Extract ProgressDialog

  **What to do**:
  - Copy `ProgressDialog` class (lines 117-139) to `vibration/presentation/views/dialogs/progress_dialog.py`
  - Add proper imports (PyQt5)
  - Add module docstring and Google-style class docstring
  - Add `if __name__ == "__main__"` test block
  - Add re-export in `vibration/presentation/views/dialogs/__init__.py`
  - Update `cn_3F_trend_optimized.py` to import from new location

  **Must NOT do**:
  - Do NOT modify the class logic
  - Do NOT change method signatures
  - Do NOT remove original code yet (keep for compatibility)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple class extraction, minimal logic
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 1.4)
  - **Blocks**: Task 1.5
  - **Blocked By**: Task 1.1

  **References**:
  - `cn_3F_trend_optimized.py:117-139` - Original ProgressDialog class
  - `AGENTS.md` - Docstring style (Google-style), naming conventions

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: ProgressDialog is importable from new location
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.views.dialogs import ProgressDialog"
      2. python -c "from vibration.presentation.views.dialogs.progress_dialog import ProgressDialog"
    Expected Result: Both imports succeed
    Evidence: Exit code 0

  Scenario: ProgressDialog module runs standalone
    Tool: Bash (python)
    Steps:
      1. timeout 3 python vibration/presentation/views/dialogs/progress_dialog.py || true
      2. Assert: No import errors (may fail on Qt display, that's OK)
    Expected Result: Module loads without import errors
    Evidence: No ImportError in output

  Scenario: Backward compatibility maintained
    Tool: Bash (python)
    Steps:
      1. python -c "from cn_3F_trend_optimized import ProgressDialog"
    Expected Result: Old import still works
    Evidence: Exit code 0
  ```

  **Commit**: YES
  - Message: `refactor(dialogs): extract ProgressDialog to separate module`
  - Files: `vibration/presentation/views/dialogs/progress_dialog.py`, `cn_3F_trend_optimized.py`
  - Pre-commit: `python -c "from vibration.presentation.views.dialogs import ProgressDialog"`

---

- [ ] 1.4. Extract AxisRangeDialog

  **What to do**:
  - Copy `AxisRangeDialog` class (lines 160-228) to `vibration/presentation/views/dialogs/axis_range_dialog.py`
  - Add proper imports (PyQt5)
  - Add module docstring and Google-style class docstring
  - Add `if __name__ == "__main__"` test block
  - Add re-export in `vibration/presentation/views/dialogs/__init__.py`
  - Update `cn_3F_trend_optimized.py` to import from new location

  **Must NOT do**:
  - Do NOT modify the class logic
  - Do NOT change method signatures

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple class extraction
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 1.3)
  - **Blocks**: Task 1.5
  - **Blocked By**: Task 1.1

  **References**:
  - `cn_3F_trend_optimized.py:160-228` - Original AxisRangeDialog class
  - `AGENTS.md` - Code style guidelines

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: AxisRangeDialog is importable
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.views.dialogs import AxisRangeDialog"
    Expected Result: Import succeeds
    Evidence: Exit code 0

  Scenario: Module is under 150 lines
    Tool: Bash (wc)
    Steps:
      1. wc -l vibration/presentation/views/dialogs/axis_range_dialog.py
      2. Assert: Line count <= 150
    Expected Result: Module respects size limit
    Evidence: Line count output
  ```

  **Commit**: YES (groups with 1.3)
  - Message: `refactor(dialogs): extract AxisRangeDialog to separate module`
  - Files: `vibration/presentation/views/dialogs/axis_range_dialog.py`
  - Pre-commit: `python -c "from vibration.presentation.views.dialogs import AxisRangeDialog"`

---

- [ ] 1.5. Extract ListSaveDialog with Dependencies

  **What to do**:
  - Analyze `ListSaveDialog` (lines 230-878) for dependencies
  - Copy class to `vibration/presentation/views/dialogs/list_save_dialog.py`
  - Split if >150 lines: create helper module for plotting logic
  - Ensure imports from `file_parser`, `fft_engine` work
  - Add proper docstrings
  - Create `vibration/presentation/views/dialogs/__init__.py` with all exports
  - Update main file imports

  **Must NOT do**:
  - Do NOT break existing ListSaveDialog functionality
  - Do NOT modify analysis logic

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex dialog with plotting, needs careful extraction
  - **Skills**: None needed
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: Not needed, preserving existing UI

  **Parallelization**:
  - **Can Run In Parallel**: NO (final dialog, depends on pattern from 1.3, 1.4)
  - **Parallel Group**: Wave 3 (sequential)
  - **Blocks**: Phase 2 tasks
  - **Blocked By**: Tasks 1.3, 1.4

  **References**:
  - `cn_3F_trend_optimized.py:230-878` - Original ListSaveDialog (649 lines)
  - `file_parser.py` - FileParser class used by dialog
  - `fft_engine.py` - FFTEngine class used by dialog
  - `responsive_layout_utils.py:ResponsiveLayoutMixin` - Mixin used by dialog

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: ListSaveDialog imports correctly
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.views.dialogs import ListSaveDialog"
      2. python -c "from vibration.presentation.views.dialogs.list_save_dialog import ListSaveDialog"
    Expected Result: Both imports succeed
    Evidence: Exit code 0

  Scenario: ListSaveDialog dependencies are available
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.views.dialogs.list_save_dialog import ListSaveDialog; print('Dependencies OK')"
    Expected Result: No ImportError for file_parser, fft_engine, etc.
    Evidence: "Dependencies OK" in output

  Scenario: Dialog module respects size limit (or is split)
    Tool: Bash (wc/find)
    Steps:
      1. wc -l vibration/presentation/views/dialogs/list_save_dialog.py
      2. If > 150 lines, check for helper module
    Expected Result: Either <=150 lines OR split into multiple modules
    Evidence: Line count output
  ```

  **Commit**: YES
  - Message: `refactor(dialogs): extract ListSaveDialog with plotting helpers`
  - Files: `vibration/presentation/views/dialogs/list_save_dialog.py`, related helpers
  - Pre-commit: `python -c "from vibration.presentation.views.dialogs import ListSaveDialog, ProgressDialog, AxisRangeDialog"`

---

### Phase 2: Spectrum Tab Extraction

- [ ] 2.1. Extract FFT Service (Core Layer)

  **What to do**:
  - Create `vibration/core/services/fft_service.py`
  - Wrap existing `fft_engine.FFTEngine` with service layer
  - Extract `mdl_FFT_N()` logic (lines 2622-2785) into service methods
  - Create dataclass `FFTResult` in `vibration/core/domain/models.py`
  - Service should have NO Qt imports
  - Add type hints and docstrings

  **Must NOT do**:
  - Do NOT modify `fft_engine.py` (existing module)
  - Do NOT add any PyQt5 imports to core layer
  - Do NOT change FFT algorithm

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Core business logic, needs careful extraction
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 2 Wave 1 (with Task 2.2)
  - **Blocks**: Tasks 2.3, 2.4
  - **Blocked By**: Task 1.5

  **References**:
  - `cn_3F_trend_optimized.py:2622-2785` - `mdl_FFT_N()` method (164 lines)
  - `fft_engine.py` - Existing FFTEngine class to wrap
  - `AGENTS.md` - Type hints, docstring style

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: FFT service is importable with no Qt dependencies
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.core.services.fft_service import FFTService"
      2. python -c "import vibration.core.services.fft_service; import sys; assert 'PyQt5' not in sys.modules"
    Expected Result: Service imports without pulling in Qt
    Evidence: Exit code 0, no Qt in modules

  Scenario: FFT service can compute spectrum
    Tool: Bash (python)
    Steps:
      1. python -c "
         import numpy as np
         from vibration.core.services.fft_service import FFTService
         svc = FFTService(sampling_rate=10240.0, delta_f=1.0, overlap=0.5)
         result = svc.compute_spectrum(np.random.randn(10240))
         assert 'frequency' in result
         assert 'spectrum' in result
         print('FFT Service OK')
         "
    Expected Result: Service computes FFT correctly
    Evidence: "FFT Service OK" in output
  ```

  **Commit**: YES
  - Message: `refactor(core): extract FFT service with domain models`
  - Files: `vibration/core/services/fft_service.py`, `vibration/core/domain/models.py`
  - Pre-commit: `python -c "from vibration.core.services.fft_service import FFTService"`

---

- [ ] 2.2. Create Plot Widget Base Class

  **What to do**:
  - Create `vibration/presentation/views/widgets/plot_widget.py`
  - Implement `MatplotlibWidget` base class with FigureCanvasQTAgg
  - Include common functionality: figure, canvas, axes, draw methods
  - Extract marker management into `vibration/presentation/views/widgets/marker_manager.py`
  - Add `on_mouse_move()`, `on_mouse_click()`, `add_marker()` as reusable methods

  **Must NOT do**:
  - Do NOT include spectrum-specific logic in base class
  - Do NOT break existing matplotlib integration patterns

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI widget with matplotlib integration
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 2 Wave 1 (with Task 2.1)
  - **Blocks**: Tasks 2.3, 3.2, 4.2
  - **Blocked By**: Task 1.5

  **References**:
  - `cn_3F_trend_optimized.py:3325-3540` - Mouse handling code patterns
  - `visualization_enhanced.py` - Modern plot styling (reference for patterns)
  - `responsive_layout_utils.py:ResponsiveLayoutMixin` - DPI scaling mixin

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Plot widget is importable
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.views.widgets import PlotWidget, MarkerManager"
    Expected Result: Both imports succeed
    Evidence: Exit code 0

  Scenario: Base widget under 150 lines
    Tool: Bash (wc)
    Steps:
      1. wc -l vibration/presentation/views/widgets/plot_widget.py
    Expected Result: <=150 lines
    Evidence: Line count output
  ```

  **Commit**: YES
  - Message: `refactor(widgets): create PlotWidget base class and MarkerManager`
  - Files: `vibration/presentation/views/widgets/plot_widget.py`, `marker_manager.py`
  - Pre-commit: Import test

---

- [ ] 2.3. Extract Spectrum Tab View

  **What to do**:
  - Create `vibration/presentation/views/tabs/spectrum_tab.py`
  - Extract Tab 3 UI elements from `setupUi()` (spectrum-related)
  - Create `SpectrumTabView` class inheriting from QWidget
  - Move spectrum plotting code from `plot_signal_data()` (lines 2786-3027)
  - Use `PlotWidget` from Task 2.2 for matplotlib integration
  - Keep under 150 lines (split plotting into separate widget if needed)

  **Must NOT do**:
  - Do NOT include business logic (FFT computation) in view
  - Do NOT duplicate code - use base classes

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Complex UI extraction with plotting
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Phase 2 Wave 2 (sequential after 2.1, 2.2)
  - **Blocks**: Task 2.4
  - **Blocked By**: Tasks 2.1, 2.2

  **References**:
  - `cn_3F_trend_optimized.py:2786-3027` - `plot_signal_data()` (242 lines)
  - `cn_3F_trend_optimized.py:901-2234` - `setupUi()` Tab 3 section
  - `vibration/presentation/views/widgets/plot_widget.py` - Base widget from 2.2

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Spectrum tab view is importable
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.views.tabs import SpectrumTabView"
    Expected Result: Import succeeds
    Evidence: Exit code 0

  Scenario: View does not contain business logic
    Tool: Bash (grep)
    Steps:
      1. grep -E "scipy|welch|fft\(" vibration/presentation/views/tabs/spectrum_tab.py || true
      2. Assert: No scipy/fft imports in view
    Expected Result: No business logic in view layer
    Evidence: Empty grep output
  ```

  **Commit**: YES
  - Message: `refactor(tabs): extract SpectrumTabView from monolith`
  - Files: `vibration/presentation/views/tabs/spectrum_tab.py`
  - Pre-commit: Import test

---

- [ ] 2.4. Create Spectrum Presenter

  **What to do**:
  - Create `vibration/presentation/presenters/spectrum_presenter.py`
  - Implement `SpectrumPresenter` class that coordinates:
    - View (SpectrumTabView)
    - Service (FFTService)
    - Event handling (compute FFT, update plot)
  - Use constructor injection for dependencies
  - Connect view signals to presenter methods
  - Handle file loading and FFT computation workflow

  **Must NOT do**:
  - Do NOT put UI code in presenter
  - Do NOT access Qt widgets directly (use view interface)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Complex coordination logic, MVP pattern implementation
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 2 Wave 3 (with Task 2.5)
  - **Blocks**: Phase 3
  - **Blocked By**: Task 2.3

  **References**:
  - `cn_3F_trend_optimized.py:2786-3027` - Current workflow in `plot_signal_data()`
  - `vibration/presentation/views/tabs/spectrum_tab.py` - View from 2.3
  - `vibration/core/services/fft_service.py` - Service from 2.1
  - PyQt5 architecture research - MVP pattern examples

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Presenter is importable
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.presenters import SpectrumPresenter"
    Expected Result: Import succeeds
    Evidence: Exit code 0

  Scenario: Presenter accepts injected dependencies
    Tool: Bash (python)
    Steps:
      1. python -c "
         from vibration.presentation.presenters.spectrum_presenter import SpectrumPresenter
         import inspect
         sig = inspect.signature(SpectrumPresenter.__init__)
         params = list(sig.parameters.keys())
         assert 'view' in params or len(params) > 1
         print('DI OK')
         "
    Expected Result: Constructor accepts dependencies
    Evidence: "DI OK" in output
  ```

  **Commit**: YES
  - Message: `refactor(presenters): create SpectrumPresenter with DI`
  - Files: `vibration/presentation/presenters/spectrum_presenter.py`
  - Pre-commit: Import test

---

- [ ] 2.5. Write FFT Service Unit Tests

  **What to do**:
  - Create `tests/unit/test_fft_service.py`
  - Write tests for:
    - `FFTService.compute_spectrum()` with known input
    - Different window types (hanning, flattop)
    - Different view types (ACC, VEL, DIS)
    - Edge cases (empty data, single point)
  - Use pytest fixtures for common setup
  - Target 80%+ code coverage for FFT service

  **Must NOT do**:
  - Do NOT test UI components
  - Do NOT require Qt for tests

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Test design for numerical algorithms
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 2 Wave 3 (with Task 2.4)
  - **Blocks**: None
  - **Blocked By**: Tasks 2.1, 1.2

  **References**:
  - `vibration/core/services/fft_service.py` - Service to test from 2.1
  - `fft_engine.py` - Existing FFT implementation for expected behavior
  - `tests/conftest.py` - Shared fixtures from 1.2

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: FFT service tests pass
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/test_fft_service.py -v
      2. Assert: All tests pass
      3. Assert: At least 5 test cases
    Expected Result: Tests pass, good coverage
    Evidence: pytest output with pass count

  Scenario: Tests don't require Qt
    Tool: Bash (python)
    Steps:
      1. pytest tests/unit/test_fft_service.py --co
      2. python -c "import tests.unit.test_fft_service; import sys; assert 'PyQt5' not in sys.modules"
    Expected Result: No Qt dependency in tests
    Evidence: Exit code 0
  ```

  **Commit**: YES
  - Message: `test(fft): add unit tests for FFT service`
  - Files: `tests/unit/test_fft_service.py`
  - Pre-commit: `pytest tests/unit/test_fft_service.py`

---

### Phase 3: Trend Tab Extraction

- [ ] 3.1. Extract Trend Service (Core Layer)

  **What to do**:
  - Create `vibration/core/services/trend_service.py`
  - Wrap existing `TrendParallelProcessor` from Level 5 optimization
  - Extract trend calculation logic from `plot_trend()` (lines 4208-4500)
  - Create `TrendResult` dataclass in domain models
  - Service should have NO Qt imports
  - Include batch processing support

  **Must NOT do**:
  - Do NOT rewrite Level 5 optimization code
  - Do NOT add Qt dependencies

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Core business logic extraction
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 3 Wave 1 (with Task 3.2)
  - **Blocks**: Tasks 3.3, 3.4
  - **Blocked By**: Phase 2 completion

  **References**:
  - `cn_3F_trend_optimized.py:4208-4500` - `plot_trend()` (293 lines)
  - `OPTIMIZATION_PATCH_LEVEL5_TREND.py` - TrendParallelProcessor to wrap
  - `vibration/core/domain/models.py` - Domain models from 2.1

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Trend service importable without Qt
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.core.services.trend_service import TrendService"
      2. python -c "import vibration.core.services.trend_service; import sys; assert 'PyQt5' not in sys.modules"
    Expected Result: No Qt dependency
    Evidence: Exit code 0
  ```

  **Commit**: YES
  - Message: `refactor(core): extract TrendService wrapping Level5 optimizer`
  - Files: `vibration/core/services/trend_service.py`
  - Pre-commit: Import test

---

- [ ] 3.2. Extract Trend Tab View

  **What to do**:
  - Create `vibration/presentation/views/tabs/trend_tab.py`
  - Extract Tab 4 UI elements from `setupUi()`
  - Create `TrendTabView` class using `PlotWidget` base
  - Move trend plotting logic, keeping under 150 lines
  - Include trend-specific plot widget if needed

  **Must NOT do**:
  - Do NOT include trend computation in view
  - Do NOT duplicate marker management (use shared widget)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 3 Wave 1 (with Task 3.1)
  - **Blocks**: Task 3.3
  - **Blocked By**: Task 2.2

  **References**:
  - `cn_3F_trend_optimized.py:4208-4694` - Trend plotting code
  - `vibration/presentation/views/widgets/plot_widget.py` - Base widget
  - `vibration/presentation/views/widgets/marker_manager.py` - Shared markers

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Trend tab view is importable
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.views.tabs import TrendTabView"
    Expected Result: Import succeeds
    Evidence: Exit code 0
  ```

  **Commit**: YES
  - Message: `refactor(tabs): extract TrendTabView from monolith`
  - Files: `vibration/presentation/views/tabs/trend_tab.py`
  - Pre-commit: Import test

---

- [ ] 3.3. Create Trend Presenter

  **What to do**:
  - Create `vibration/presentation/presenters/trend_presenter.py`
  - Implement `TrendPresenter` coordinating view and service
  - Handle batch trend computation workflow
  - Use constructor injection
  - Connect signals for progress updates

  **Must NOT do**:
  - Do NOT access Qt widgets directly

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Phase 3 Wave 2
  - **Blocks**: Task 3.4
  - **Blocked By**: Tasks 3.1, 3.2

  **References**:
  - `vibration/presentation/presenters/spectrum_presenter.py` - Pattern from 2.4
  - `vibration/core/services/trend_service.py` - Service from 3.1

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Trend presenter is importable
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.presenters import TrendPresenter"
    Expected Result: Import succeeds
    Evidence: Exit code 0
  ```

  **Commit**: YES
  - Message: `refactor(presenters): create TrendPresenter with DI`
  - Files: `vibration/presentation/presenters/trend_presenter.py`
  - Pre-commit: Import test

---

- [ ] 3.4. Write Trend Service Unit Tests

  **What to do**:
  - Create `tests/unit/test_trend_service.py`
  - Test RMS calculation, batch processing, result aggregation
  - Use synthetic data for deterministic tests
  - Verify integration with Level 5 processor

  **Must NOT do**:
  - Do NOT test UI
  - Do NOT require real files

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 3 Wave 3 (with Task 3.5)
  - **Blocks**: None
  - **Blocked By**: Tasks 3.1, 1.2

  **References**:
  - `vibration/core/services/trend_service.py` - Service to test
  - `tests/unit/test_fft_service.py` - Test pattern from 2.5

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Trend service tests pass
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/test_trend_service.py -v
    Expected Result: All tests pass
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `test(trend): add unit tests for TrendService`
  - Files: `tests/unit/test_trend_service.py`
  - Pre-commit: `pytest tests/unit/test_trend_service.py`

---

- [ ] 3.5. Extract Marker Manager (Shared Widget)

  **What to do**:
  - Enhance `vibration/presentation/views/widgets/marker_manager.py` from 2.2
  - Ensure all tabs can use same marker logic
  - Extract common patterns from:
    - `on_mouse_move()`, `on_mouse_move2()`, `on_move_peak()`
    - `on_mouse_click()`, `on_click2()`, `on_click_peak()`
    - `add_marker()`, `add_marker2()`, `add_marker_peak()`
  - Create unified `MarkerManager` class

  **Must NOT do**:
  - Do NOT break existing marker functionality

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 3 Wave 3 (with Task 3.4)
  - **Blocks**: Phase 4 tab extractions
  - **Blocked By**: Task 2.2

  **References**:
  - `cn_3F_trend_optimized.py:3325-3540` - Tab 3 marker code
  - `cn_3F_trend_optimized.py:4813-5260` - Tab 4 marker code
  - `cn_3F_trend_optimized.py:5682-5900` - Tab 5 marker code

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: MarkerManager provides unified interface
    Tool: Bash (python)
    Steps:
      1. python -c "
         from vibration.presentation.views.widgets import MarkerManager
         import inspect
         methods = [m for m in dir(MarkerManager) if not m.startswith('_')]
         assert 'add_marker' in methods
         assert 'on_mouse_click' in methods or 'handle_click' in methods
         print('MarkerManager OK')
         "
    Expected Result: MarkerManager has expected methods
    Evidence: "MarkerManager OK" in output
  ```

  **Commit**: YES
  - Message: `refactor(widgets): unify MarkerManager across all tabs`
  - Files: `vibration/presentation/views/widgets/marker_manager.py`
  - Pre-commit: Import test

---

### Phase 4: Remaining Tabs

- [ ] 4.1. Extract Data Query Tab

  **What to do**:
  - Create `vibration/presentation/views/tabs/data_query_tab.py`
  - Create `vibration/presentation/presenters/data_query_presenter.py`
  - Extract Tab 1 UI and file selection logic
  - Use `file_parser.FileParser` for data loading
  - Create `FileListModel(QAbstractTableModel)` for file table

  **Must NOT do**:
  - Do NOT modify file_parser.py

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 4 Wave 1 (with Tasks 4.2, 4.3)
  - **Blocks**: Task 4.4
  - **Blocked By**: Phase 3

  **References**:
  - `cn_3F_trend_optimized.py` - Tab 1 sections in setupUi and related methods
  - `file_parser.py` - FileParser class

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Data query tab and presenter importable
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.views.tabs import DataQueryTabView"
      2. python -c "from vibration.presentation.presenters import DataQueryPresenter"
    Expected Result: Both imports succeed
    Evidence: Exit code 0
  ```

  **Commit**: YES
  - Message: `refactor(tabs): extract DataQueryTab with FileListModel`
  - Files: `data_query_tab.py`, `data_query_presenter.py`, `file_list_model.py`
  - Pre-commit: Import tests

---

- [ ] 4.2. Extract Waterfall Tab

  **What to do**:
  - Create `vibration/presentation/views/tabs/waterfall_tab.py`
  - Create `vibration/presentation/presenters/waterfall_presenter.py`
  - Extract `plot_waterfall_spectrum()` logic (lines 3614-3990)
  - Use 3D plotting patterns from existing code
  - Consider using `visualization_enhanced.WaterfallPlotEnhanced` if applicable

  **Must NOT do**:
  - Do NOT break 3D visualization
  - Do NOT modify optimization code

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 4 Wave 1 (with Tasks 4.1, 4.3)
  - **Blocks**: None
  - **Blocked By**: Phase 3

  **References**:
  - `cn_3F_trend_optimized.py:3614-3990` - `plot_waterfall_spectrum()` (377 lines)
  - `visualization_enhanced.py:WaterfallPlotEnhanced` - Reference implementation

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Waterfall tab importable
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.views.tabs import WaterfallTabView"
    Expected Result: Import succeeds
    Evidence: Exit code 0
  ```

  **Commit**: YES
  - Message: `refactor(tabs): extract WaterfallTab with 3D visualization`
  - Files: `waterfall_tab.py`, `waterfall_presenter.py`
  - Pre-commit: Import test

---

- [ ] 4.3. Extract Peak Tab

  **What to do**:
  - Create `vibration/presentation/views/tabs/peak_tab.py`
  - Create `vibration/presentation/presenters/peak_presenter.py`
  - Create `vibration/core/services/peak_service.py`
  - Extract `plot_peak()` logic (lines 5354-5614)
  - Use shared `MarkerManager`

  **Must NOT do**:
  - Do NOT duplicate marker logic

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 4 Wave 1 (with Tasks 4.1, 4.2)
  - **Blocks**: None
  - **Blocked By**: Phase 3

  **References**:
  - `cn_3F_trend_optimized.py:5354-5614` - `plot_peak()` (261 lines)
  - `OPTIMIZATION_PATCH_LEVEL5_TREND.py:PeakParallelProcessor` - Peak processing

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Peak tab and service importable
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.presentation.views.tabs import PeakTabView"
      2. python -c "from vibration.core.services.peak_service import PeakService"
    Expected Result: Both imports succeed
    Evidence: Exit code 0
  ```

  **Commit**: YES
  - Message: `refactor(tabs): extract PeakTab with PeakService`
  - Files: `peak_tab.py`, `peak_presenter.py`, `peak_service.py`
  - Pre-commit: Import tests

---

- [ ] 4.4. Extract File Service (Core Layer)

  **What to do**:
  - Create `vibration/core/services/file_service.py`
  - Wrap `file_parser.FileParser`
  - Add directory scanning from `load_data()`
  - Create `FileMetadata` dataclass
  - Handle sensitivity management

  **Must NOT do**:
  - Do NOT modify file_parser.py
  - Do NOT add Qt dependencies

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on 4.1 for requirements clarity)
  - **Parallel Group**: Phase 4 Wave 2
  - **Blocks**: Task 4.5
  - **Blocked By**: Task 4.1

  **References**:
  - `cn_3F_trend_optimized.py` - `load_data()`, `select_directory()` methods
  - `file_parser.py` - FileParser to wrap

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: File service importable without Qt
    Tool: Bash (python)
    Steps:
      1. python -c "from vibration.core.services.file_service import FileService"
      2. python -c "import vibration.core.services.file_service; import sys; assert 'PyQt5' not in sys.modules"
    Expected Result: No Qt dependency
    Evidence: Exit code 0
  ```

  **Commit**: YES
  - Message: `refactor(core): extract FileService wrapping file_parser`
  - Files: `vibration/core/services/file_service.py`
  - Pre-commit: Import test

---

- [ ] 4.5. Write File Service Unit Tests

  **What to do**:
  - Create `tests/unit/test_file_service.py`
  - Test file loading, metadata extraction, directory scanning
  - Use temp files for testing
  - Test edge cases (invalid files, empty directory)

  **Must NOT do**:
  - Do NOT require actual data files

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 4 Wave 3
  - **Blocks**: None
  - **Blocked By**: Tasks 4.4, 1.2

  **References**:
  - `vibration/core/services/file_service.py` - Service to test
  - `tests/unit/test_fft_service.py` - Test patterns

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: File service tests pass
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/test_file_service.py -v
    Expected Result: All tests pass
    Evidence: pytest output
  ```

  **Commit**: YES
  - Message: `test(file): add unit tests for FileService`
  - Files: `tests/unit/test_file_service.py`
  - Pre-commit: `pytest tests/unit/test_file_service.py`

---

### Phase 5: Main Window Shell + Cleanup

- [ ] 5.1. Create Main Window Shell

  **What to do**:
  - Create `vibration/presentation/views/main_window.py`
  - Implement thin `MainWindow` class (~200 lines)
  - Create tab widget and add extracted tab views
  - Delegate all logic to presenters
  - Move `setupUi()` tab creation to individual tab classes

  **Must NOT do**:
  - Do NOT include business logic in main window
  - Do NOT exceed 200 lines

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Phase 5 Wave 1
  - **Blocks**: Tasks 5.2, 5.3
  - **Blocked By**: Phase 4

  **References**:
  - `cn_3F_trend_optimized.py:880-6198` - Current Ui_MainWindow
  - Extracted tab views from Phase 2-4

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Main window is importable and under size limit
    Tool: Bash (python/wc)
    Steps:
      1. python -c "from vibration.presentation.views import MainWindow"
      2. wc -l vibration/presentation/views/main_window.py
      3. Assert: Line count <= 250 (200 target + buffer)
    Expected Result: Thin main window
    Evidence: Line count output
  ```

  **Commit**: YES
  - Message: `refactor(views): create thin MainWindow shell`
  - Files: `vibration/presentation/views/main_window.py`
  - Pre-commit: Import test

---

- [ ] 5.2. Create Application Factory

  **What to do**:
  - Create `vibration/app.py` with `ApplicationFactory` class
  - Wire all dependencies: services, presenters, views
  - Create `main()` function as entry point
  - Implement factory methods for each presenter

  **Must NOT do**:
  - Do NOT use Service Locator pattern (use constructor injection)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 5 Wave 2 (with Task 5.3)
  - **Blocks**: Task 5.4
  - **Blocked By**: Task 5.1

  **References**:
  - PyQt5 architecture research - Factory pattern examples
  - All services and presenters from previous phases

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Application factory creates main window
    Tool: Bash (python)
    Steps:
      1. python -c "
         from vibration.app import ApplicationFactory
         factory = ApplicationFactory()
         # Don't actually create window (needs display)
         print('Factory OK')
         "
    Expected Result: Factory is importable
    Evidence: "Factory OK" in output
  ```

  **Commit**: YES
  - Message: `refactor(app): create ApplicationFactory with DI`
  - Files: `vibration/app.py`
  - Pre-commit: Import test

---

- [ ] 5.3. Create Event Bus for Signals

  **What to do**:
  - Create `vibration/infrastructure/event_bus.py`
  - Implement singleton `EventBus` class with pyqtSignals
  - Define application-wide events (file_loaded, analysis_complete, etc.)
  - Allow modules to subscribe/emit without direct coupling

  **Must NOT do**:
  - Do NOT overuse - only for cross-cutting concerns

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Phase 5 Wave 2 (with Task 5.2)
  - **Blocks**: Task 5.4
  - **Blocked By**: Task 5.1

  **References**:
  - PyQt5 architecture research - Event bus pattern
  - `platform_config.py` - Singleton pattern example

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Event bus is singleton
    Tool: Bash (python)
    Steps:
      1. python -c "
         from vibration.infrastructure.event_bus import EventBus
         eb1 = EventBus()
         eb2 = EventBus()
         assert eb1 is eb2
         print('Singleton OK')
         "
    Expected Result: Same instance returned
    Evidence: "Singleton OK" in output
  ```

  **Commit**: YES
  - Message: `feat(infrastructure): add EventBus for loose coupling`
  - Files: `vibration/infrastructure/event_bus.py`
  - Pre-commit: Import test

---

- [ ] 5.4. Update Transition Layer

  **What to do**:
  - Update `cn_3F_trend_optimized.py` to become thin wrapper
  - Re-export all classes from new locations for backward compatibility
  - Add deprecation warnings for direct imports
  - Ensure `python cn_3F_trend_optimized.py` still launches app
  - Create `vibration/__main__.py` for `python -m vibration`

  **Must NOT do**:
  - Do NOT break existing import paths
  - Do NOT remove original file (just make it thin)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Phase 5 Wave 3
  - **Blocks**: Task 5.5
  - **Blocked By**: Tasks 5.2, 5.3

  **References**:
  - Current `cn_3F_trend_optimized.py` - All exports to preserve
  - `vibration/app.py` - New entry point

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Old entry point still works
    Tool: Bash (python)
    Steps:
      1. timeout 5 python cn_3F_trend_optimized.py --help 2>&1 || timeout 5 python cn_3F_trend_optimized.py 2>&1 &
      2. sleep 2; pkill -f cn_3F_trend || true
      3. Assert: No ImportError in output
    Expected Result: App starts (may fail on display, that's OK)
    Evidence: No import errors

  Scenario: New entry point works
    Tool: Bash (python)
    Steps:
      1. timeout 5 python -m vibration 2>&1 &
      2. sleep 2; pkill -f vibration || true
      3. Assert: No ImportError in output
    Expected Result: App starts via module
    Evidence: No import errors

  Scenario: Old imports still work with deprecation warning
    Tool: Bash (python)
    Steps:
      1. python -c "from cn_3F_trend_optimized import Ui_MainWindow" 2>&1
      2. Assert: Import succeeds (may show DeprecationWarning)
    Expected Result: Backward compatibility maintained
    Evidence: Exit code 0
  ```

  **Commit**: YES
  - Message: `refactor(compat): convert monolith to transition layer`
  - Files: `cn_3F_trend_optimized.py`, `vibration/__main__.py`
  - Pre-commit: Both entry point tests

---

- [ ] 5.5. Update PyInstaller Spec

  **What to do**:
  - Update `CNAVE_Analyzer.spec` for new package structure
  - Add `vibration/` package to `pathex`
  - Update `hiddenimports` if needed
  - Test build with `pyinstaller CNAVE_Analyzer.spec`
  - Verify built executable launches

  **Must NOT do**:
  - Do NOT change app name or icon

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Phase 5 Wave 4
  - **Blocks**: Task 5.6
  - **Blocked By**: Task 5.4

  **References**:
  - `CNAVE_Analyzer.spec` - Current PyInstaller configuration
  - `build.sh` - Current build script

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: PyInstaller build succeeds
    Tool: Bash (pyinstaller)
    Steps:
      1. pyinstaller CNAVE_Analyzer.spec --noconfirm
      2. Assert: Exit code 0
      3. ls dist/CNAVE_Analyzer* or dist/CNAVE_Analyzer.app
    Expected Result: Build produces executable
    Evidence: Executable exists in dist/

  Scenario: Built executable contains vibration package
    Tool: Bash (strings/grep)
    Steps:
      1. Check executable or .app for vibration module references
    Expected Result: Package is bundled
    Evidence: vibration references found
  ```

  **Commit**: YES
  - Message: `build: update PyInstaller spec for new package structure`
  - Files: `CNAVE_Analyzer.spec`
  - Pre-commit: `pyinstaller CNAVE_Analyzer.spec --noconfirm`

---

- [ ] 5.6. Final Integration Tests

  **What to do**:
  - Create `tests/integration/test_analysis_workflow.py`
  - Test complete workflow: load file → compute FFT → display result
  - Verify all services work together
  - Run full test suite: `pytest tests/`
  - Verify no circular imports
  - Document any known issues

  **Must NOT do**:
  - Do NOT require GUI for integration tests (mock views)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Phase 5 Wave 5 (final)
  - **Blocks**: None (final task)
  - **Blocked By**: Task 5.5

  **References**:
  - All services from core layer
  - `tests/conftest.py` - Shared fixtures

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios:**

  ```
  Scenario: Full test suite passes
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/ -v --tb=short
      2. Assert: All tests pass
      3. Assert: No import errors
    Expected Result: Clean test run
    Evidence: pytest output showing all pass

  Scenario: No circular imports
    Tool: Bash (python)
    Steps:
      1. python -c "import vibration; print('No circular imports')"
      2. python -c "from vibration.app import main; print('App importable')"
    Expected Result: Clean imports
    Evidence: Success messages

  Scenario: Application launches without error
    Tool: Bash (python)
    Steps:
      1. timeout 10 python -m vibration 2>&1 &
      2. sleep 5
      3. pgrep -f "python -m vibration" && echo "Running" || echo "Not running"
      4. pkill -f "python -m vibration" || true
    Expected Result: App starts and runs briefly
    Evidence: "Running" in output (or graceful exit if no display)
  ```

  **Commit**: YES
  - Message: `test(integration): add final integration tests`
  - Files: `tests/integration/test_analysis_workflow.py`
  - Pre-commit: `pytest tests/ -v`

---

## Commit Strategy

| Phase | After Task | Message | Files | Verification |
|-------|------------|---------|-------|--------------|
| 1 | 1.1 | `refactor(structure): create vibration package skeleton` | vibration/**/__init__.py | `python -c "import vibration"` |
| 1 | 1.2 | `test(setup): add pytest infrastructure` | pytest.ini, tests/** | `pytest tests/unit/test_example.py` |
| 1 | 1.3-1.4 | `refactor(dialogs): extract Progress and AxisRange dialogs` | dialogs/*.py | Import tests |
| 1 | 1.5 | `refactor(dialogs): extract ListSaveDialog` | list_save_dialog.py | Import test |
| 2 | 2.1 | `refactor(core): extract FFT service` | fft_service.py, models.py | Import test |
| 2 | 2.2 | `refactor(widgets): create PlotWidget and MarkerManager` | widgets/*.py | Import test |
| 2 | 2.3-2.4 | `refactor(spectrum): extract tab view and presenter` | spectrum_*.py | Import tests |
| 2 | 2.5 | `test(fft): add unit tests` | test_fft_service.py | `pytest tests/unit/test_fft_service.py` |
| 3 | 3.1-3.3 | `refactor(trend): extract tab, presenter, and service` | trend_*.py | Import tests |
| 3 | 3.4 | `test(trend): add unit tests` | test_trend_service.py | `pytest tests/unit/test_trend_service.py` |
| 3 | 3.5 | `refactor(widgets): unify MarkerManager` | marker_manager.py | Import test |
| 4 | 4.1-4.3 | `refactor(tabs): extract Data Query, Waterfall, Peak tabs` | *_tab.py, *_presenter.py | Import tests |
| 4 | 4.4-4.5 | `refactor(core): extract FileService with tests` | file_service.py, tests | `pytest tests/unit/test_file_service.py` |
| 5 | 5.1 | `refactor(views): create thin MainWindow shell` | main_window.py | Import test |
| 5 | 5.2-5.3 | `feat(app): add ApplicationFactory and EventBus` | app.py, event_bus.py | Import tests |
| 5 | 5.4 | `refactor(compat): convert monolith to transition layer` | cn_3F_trend_optimized.py | Entry point tests |
| 5 | 5.5 | `build: update PyInstaller spec` | CNAVE_Analyzer.spec | Build test |
| 5 | 5.6 | `test(integration): final integration tests` | test_analysis_workflow.py | `pytest tests/` |

---

## Success Criteria

### Verification Commands
```bash
# All imports work
python -c "import vibration"
python -c "from vibration.core.services import FFTService, TrendService, FileService"
python -c "from vibration.presentation.views.tabs import SpectrumTabView, TrendTabView"
python -c "from vibration.app import ApplicationFactory"

# Backward compatibility
python -c "from cn_3F_trend_optimized import Ui_MainWindow, ProgressDialog"

# Tests pass
pytest tests/ -v

# No circular imports
python -c "from vibration.app import main"

# Application launches
python -m vibration  # Should start without import errors
python cn_3F_trend_optimized.py  # Should still work

# Build works
pyinstaller CNAVE_Analyzer.spec --noconfirm
```

### Final Checklist
- [ ] All "Must Have" requirements present
- [ ] All "Must NOT Have" guardrails respected
- [ ] All 5 tabs function identically to original
- [ ] All optimization modules work (no performance regression)
- [ ] All unit tests pass (>80% coverage on core services)
- [ ] No circular import errors
- [ ] Each module ≤150 lines (documented exceptions only)
- [ ] Backward compatibility via transition layer
- [ ] PyInstaller build succeeds
- [ ] Application launches via both entry points

---

## File Mapping (Monolith → New Location)

| Original Location | New Location | Notes |
|-------------------|--------------|-------|
| `cn_3F_trend_optimized.py:117-139` | `vibration/presentation/views/dialogs/progress_dialog.py` | ProgressDialog |
| `cn_3F_trend_optimized.py:160-228` | `vibration/presentation/views/dialogs/axis_range_dialog.py` | AxisRangeDialog |
| `cn_3F_trend_optimized.py:230-878` | `vibration/presentation/views/dialogs/list_save_dialog.py` | ListSaveDialog (may split) |
| `cn_3F_trend_optimized.py:2622-2785` | `vibration/core/services/fft_service.py` | mdl_FFT_N logic |
| `cn_3F_trend_optimized.py:2786-3027` | `vibration/presentation/views/tabs/spectrum_tab.py` + `presenters/spectrum_presenter.py` | plot_signal_data |
| `cn_3F_trend_optimized.py:3614-3990` | `vibration/presentation/views/tabs/waterfall_tab.py` + `presenters/waterfall_presenter.py` | plot_waterfall_spectrum |
| `cn_3F_trend_optimized.py:4208-4500` | `vibration/core/services/trend_service.py` | plot_trend logic |
| `cn_3F_trend_optimized.py:5354-5614` | `vibration/core/services/peak_service.py` | plot_peak logic |
| `cn_3F_trend_optimized.py:880-2234` | `vibration/presentation/views/main_window.py` + `tabs/*.py` | setupUi split |
| `OPTIMIZATION_PATCH_LEVEL1.py` | `vibration/optimization/level1_caching.py` | Renamed, code unchanged |
| `OPTIMIZATION_PATCH_LEVEL3_ULTRA.py` | `vibration/optimization/level3_ultra.py` | Renamed, code unchanged |
| `OPTIMIZATION_PATCH_LEVEL4_RENDERING.py` | `vibration/optimization/level4_rendering.py` | Renamed, code unchanged |
| `OPTIMIZATION_PATCH_LEVEL5_SPECTRUM.py` | `vibration/optimization/level5/spectrum_processor.py` | Renamed, code unchanged |
| `OPTIMIZATION_PATCH_LEVEL5_TREND.py` | `vibration/optimization/level5/trend_processor.py` | Renamed, code unchanged |
| `file_parser.py` | Keep in place OR `vibration/infrastructure/file_parser.py` | User choice |
| `fft_engine.py` | Keep in place OR `vibration/infrastructure/fft_engine.py` | User choice |
| `json_handler.py` | `vibration/infrastructure/json_handler.py` | Move to infrastructure |
| `performance_logger.py` | `vibration/infrastructure/performance_logger.py` | Move to infrastructure |
| `platform_config.py` | `vibration/infrastructure/platform_config.py` | Move to infrastructure |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Circular imports | Strict layer enforcement: Core → Infrastructure, Presentation → Core |
| Performance regression | Keep optimization modules unchanged, only reorganize imports |
| Breaking changes | Transition layer with re-exports, deprecation warnings |
| Large task scope | Phased approach, each phase independently deployable |
| Lost functionality | Each extraction includes verification tests |

---

*Plan generated by Prometheus on 2026-02-06*
*Estimated effort: 40-60 hours across 5 phases*
