# AGENTS.md - Vibration Analysis Project

> **For AI coding agents working on this codebase.**  
> This is a PyQt5-based audio/vibration analysis application with performance optimization focus.

---

## Quick Reference

| Action | Command |
|--------|---------|
| Install dependencies | `pip install -r requirements.txt` |
| Run application | `python cn_3F_trend_optimized.py` |
| Run module test | `python <module>.py` (most modules have `if __name__ == "__main__"` blocks) |
| Build Mac app | `./build.sh` |
| Build with PyInstaller | `pyinstaller CNAVE_Analyzer.spec` |

---

## Project Overview

**Purpose**: Audio/vibration analysis desktop application for signal processing, FFT analysis, and trend visualization.

**Tech Stack**:
- Python 3.8+ (3.11 recommended)
- PyQt5 - GUI framework
- NumPy/SciPy - Scientific computing, FFT
- Matplotlib - Visualization
- librosa/soundfile - Audio processing
- nptdms - LabVIEW TDMS file support

**Architecture**: Monolithic legacy app (`cn_3F_trend_optimized.py` ~6000+ lines) with modular optimization components.

---

## Build & Run Commands

### Development
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run application
python cn_3F_trend_optimized.py
```

### Testing Individual Modules
Most modules have test blocks. Run directly:
```bash
python fft_engine.py           # FFT engine test with synthetic signal
python file_parser.py <file>   # File parser test
python json_handler.py         # JSON serialization test
python platform_config.py      # Platform detection test
python performance_logger.py   # Performance logging test
```

### Building Executable
```bash
# Mac
./build.sh

# Or manual PyInstaller
pyinstaller --onefile --windowed --name="CNAVE_Analyzer" cn_3F_trend_optimized.py
```

---

## Code Style Guidelines

### General Style
- **PEP 8** compliant
- **4 spaces** for indentation (no tabs)
- **Line length**: 100 chars recommended, 120 max
- **Korean comments** are acceptable (this is a Korean project)

### Imports Order
```python
# 1. Standard library
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from datetime import datetime
from functools import wraps

# 2. Third-party
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QTableView, QApplication
from PyQt5.QtCore import Qt, QAbstractTableModel

# 3. Local modules
from json_handler import save_json, load_json
from platform_config import initialize_platform_support
from performance_logger import measure_time
```

### Type Hints
Always use type hints for function signatures:
```python
def compute_fft(data: np.ndarray, sampling_rate: float) -> Dict[str, Any]:
    """Compute FFT spectrum."""
    ...

def load_files(file_paths: List[str]) -> List[Dict]:
    ...
```

### Docstrings (Google Style)
```python
def save_analysis_result(data: Dict, filepath: Union[str, Path], 
                        indent: int = 2) -> bool:
    """
    Save analysis results to JSON with NumPy array support.
    
    Args:
        data: Dictionary containing analysis data (NumPy arrays allowed)
        filepath: Output file path
        indent: JSON indentation level
    
    Returns:
        True if save successful, False otherwise
    
    Raises:
        IOError: If file cannot be written
    """
```

### Naming Conventions
| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `FFTEngine`, `FileParser`, `PerformanceLogger` |
| Functions/Methods | snake_case | `compute_fft()`, `load_files()`, `get_sampling_rate()` |
| Variables | snake_case | `sampling_rate`, `fft_result`, `file_data` |
| Constants | UPPER_SNAKE_CASE | `VERSION = "2.0"`, `MAX_WORKERS = 6` |
| Private | leading underscore | `_data`, `_metadata`, `_parse_metadata_line()` |
| Protected (internal) | single underscore | `_create_window()`, `_window` |

### Error Handling Pattern
```python
def load_file(self):
    """Standard error handling pattern."""
    try:
        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Process...
    except FileNotFoundError:
        logger.error(f"File not found: {self.file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error loading file: {e}")
        return {}
```

### Logging
Use the `logging` module, not `print()`:
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Processing file: {filename}")
logger.warning(f"Font not found: {font_name}")
logger.error(f"FFT calculation failed: {e}")
```

---

## Key Design Patterns

### Singleton Pattern
Used for global managers:
```python
_platform_manager = None

def get_platform_manager() -> PlatformManager:
    global _platform_manager
    if _platform_manager is None:
        _platform_manager = PlatformManager()
    return _platform_manager
```

### Performance Decorator
For timing operations:
```python
from performance_logger import measure_time

@measure_time("File Loading")
def load_files(files: List[str]) -> List[Dict]:
    ...
```

### NumPy Vectorization
Prefer vectorized operations over loops:
```python
# Good: Vectorized
P = np.sqrt(Pxx)
P = P / (2 * np.pi * f + 1e-10)

# Avoid: Loop-based
for i in range(len(Pxx)):
    P[i] = math.sqrt(Pxx[i])
```

---

## Module Reference

| Module | Purpose |
|--------|---------|
| `cn_3F_trend_optimized.py` | Main application (legacy monolith) |
| `fft_engine.py` | FFT computation with scipy.welch |
| `file_parser.py` | Fast file loading with NumPy |
| `json_handler.py` | JSON with NumPy array serialization |
| `table_optimizer.py` | QTableView virtualization |
| `platform_config.py` | Cross-platform font/path handling |
| `performance_logger.py` | Timing and profiling utilities |
| `visualization_enhanced.py` | Waterfall plots and graphs |

---

## Critical Rules

### DO
- Use `Path` from `pathlib` for all file paths
- Use type hints on all public functions
- Handle NumPy arrays with `json_handler.save_json()` (not raw `json.dump()`)
- Initialize platform support at app start: `initialize_platform_support()`
- Use `try/except` with specific exception types
- Preserve existing UI layout when optimizing

### DON'T
- Don't use `print()` for logging (use `logging` module)
- Don't use `json.dump()` directly with NumPy arrays (TypeError)
- Don't modify UI code when making performance improvements
- Don't hardcode Windows paths (use `platform_config.py`)
- Don't use bare `except:` - always specify exception type
- Don't suppress errors silently (at minimum, log them)

---

## File Formats

### Input Data Files
- `.txt` files with metadata header and numerical data
- TDMS files (LabVIEW format via `nptdms`)
- Audio files via `librosa`/`soundfile`

### JSON Data Format
```json
{
  "version": "2.0",
  "timestamp": "2026-02-06T08:00:00",
  "data": {
    "filename": "sample.wav",
    "fft_result": {"__ndarray__": [...], "dtype": "float64", "shape": [1024, 512]}
  }
}
```

---

## Performance Considerations

1. **File Loading**: Use parallel processing via `concurrent.futures`
2. **Tables**: Use `QTableView` with `QAbstractTableModel` (not `QTableWidget`)
3. **FFT**: Use `scipy.signal.welch()` for efficient spectral estimation
4. **Memory**: Pre-allocate NumPy arrays where possible
5. **GUI**: Avoid blocking main thread during computation

---

## Cross-Platform Notes

| Concern | Solution |
|---------|----------|
| Korean fonts | `platform_config.py` auto-detects system fonts |
| Path separators | Use `pathlib.Path`, not string concatenation |
| DPI scaling | `DPIScaler` class handles high-DPI displays |
| Line endings | Files use UTF-8 encoding |

---

## Common Tasks

### Adding a New Optimization Module
1. Create module with docstring explaining purpose
2. Add `if __name__ == "__main__"` test block
3. Use type hints and Google-style docstrings
4. Import in main app and test integration
5. Update README.md if needed

### Debugging Performance
```python
from performance_logger import PerformanceLogger

logger = PerformanceLogger()

@logger.measure_time("My Operation")
def my_function():
    ...

# After execution:
logger.generate_summary()
```
