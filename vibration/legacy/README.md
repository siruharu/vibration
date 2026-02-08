# Legacy Code Archive

This directory contains archived code from the original monolithic implementation and intermediate optimization attempts.

## Contents

### Original Monolithic Code
- `cn_3F_trend_optimized.py` - Original 6,384-line monolithic PyQt5 application
- `demo.py` - Demo/testing scripts

### Optimization Attempts (Pre-MVP Refactor)
These files were part of incremental optimization efforts before the full MVP refactor:

#### Patch/Migration Tools
- `auto_patch.py`, `auto_patcher.py` - Automated patching tools
- `perf_patcher.py` - Performance optimization patches
- `quick_patch.py` - Quick fix utilities
- `bug_fix.py` - Bug fix utilities

#### Optimization Guides
- `APPLY_GUIDE.py` - Application guide for patches
- `INTEGRATION_GUIDE.py` - Integration instructions
- `OPTIMIZATION_PATCH_LEVEL1.py` - Level 1 optimizations
- `OPTIMIZATION_PATCH_LEVEL2_PARALLEL.py` - Parallel processing
- `OPTIMIZATION_PATCH_LEVEL3_ULTRA.py` - Ultra optimizations
- `OPTIMIZATION_PATCH_LEVEL4_RENDERING.py` - Rendering optimizations
- `OPTIMIZATION_PATCH_LEVEL5_SPECTRUM.py` - Spectrum analysis optimizations
- `OPTIMIZATION_PATCH_LEVEL5_TREND.py` - Trend analysis optimizations

#### Helper Modules
- `fft_engine.py` - Standalone FFT computation (replaced by FFTService)
- `file_parser.py` - File parsing utilities (replaced by FileService)
- `json_handler.py` - JSON handling with NumPy support
- `table_optimizer.py` - QTableView optimization utilities
- `visualization_enhanced.py` - Enhanced visualization helpers
- `performance_logger.py` - Performance logging utilities
- `performance_wrapper.py` - Performance measurement wrappers
- `pyqt_plotly_example.py` - Plotly integration examples
- `platform_config.py` - Cross-platform configuration

## Why Archived?

These files represent intermediate optimization steps that were **superseded by the full MVP refactor**:

1. **Monolithic → Incremental Patches**: Initial optimization attempts
2. **Incremental Patches → MVP Architecture**: Final refactor (current implementation)

The current modular architecture (vibration/) achieves:
- ✅ Better code organization (MVP pattern)
- ✅ Improved testability (150 automated tests)
- ✅ Better performance (service layer with caching)
- ✅ Cleaner dependencies (DI pattern)
- ✅ Easier maintenance

## Current Implementation

See the main `vibration/` package for the production-ready modular implementation:

```
vibration/
├── core/               # Business logic (Services, Domain models)
├── presentation/       # UI layer (Views, Presenters, Dialogs)
└── infrastructure/     # Cross-cutting (Event bus, Config)
```

## Reference Only

These files are **kept for reference only** and are not part of the active codebase. Do not modify or use in new code.
