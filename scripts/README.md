# Scripts Directory

Utility scripts for building, testing, and development.

## Build Scripts

### `build_modern.sh`
Modern build script for creating modular package distribution.

**Usage:**
```bash
./scripts/build_modern.sh
```

**Output:** Creates distributable package in `dist/`

### `build.sh`
Legacy build script (kept for compatibility).

## Development Scripts

### `clean_and_run.sh`
Clean Python cache and run the application.

**Usage:**
```bash
./scripts/clean_and_run.sh
```

**What it does:**
1. Removes `__pycache__` directories
2. Removes `.pyc` files
3. Runs the application via `python -m vibration`

### `generate_test_data.py`
Generate synthetic test data for development and testing.

**Usage:**
```bash
python scripts/generate_test_data.py [options]
```

## Running the Application

**Recommended method:**
```bash
python -m vibration
```

Or use the convenience script:
```bash
./scripts/clean_and_run.sh
```

## Requirements

All scripts assume:
- Python 3.11+ environment active
- Dependencies installed (`pip install -r requirements.txt`)
- Working directory is project root
