#!/bin/bash
# build_mac.sh

# 1. 의존성 확인
pip install -r requirements.txt
pip install pyinstaller

# 2. 기본 빌드
pyinstaller \
  --name="AudioAnalysis" \
  --windowed \
  --onefile \
  --icon="" \
  --add-data="file_parser.py:." \
  --add-data="fft_engine.py:." \
  --add-data="json_handler.py:." \
  --add-data="table_optimizer.py:." \
  --add-data="visualization_enhanced.py:." \
  --add-data="platform_config.py:." \
  --hidden-import="numpy" \
  --hidden-import="scipy" \
  --hidden-import="librosa" \
  --hidden-import="soundfile" \
  --hidden-import="nptdms" \
  "cn 3F trend_optimized.py"