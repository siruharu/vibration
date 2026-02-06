#!/bin/bash
# Modern build script for modular vibration package
# Updated for vibration/ package structure

set -e  # Exit on error

echo "🔧 Building CNAVE Analyzer (Modular Version)..."
echo ""

# 1. Check Python version
echo "📌 Checking Python version..."
python --version
echo ""

# 2. Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller
echo ""

# 3. Run tests
echo "🧪 Running tests..."
pytest tests/ -v --tb=short || {
    echo "⚠️  Tests failed! Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
}
echo ""

# 4. Clean previous build
echo "🧹 Cleaning previous build..."
rm -rf build dist *.spec 2>/dev/null || true
echo ""

# 5. Build with PyInstaller
echo "🏗️  Building executable..."
pyinstaller \
  --name="CNAVE_Analyzer" \
  --windowed \
  --onefile \
  --add-data="vibration:vibration" \
  --hidden-import="vibration.core.services.fft_service" \
  --hidden-import="vibration.core.services.trend_service" \
  --hidden-import="vibration.core.services.peak_service" \
  --hidden-import="vibration.core.services.file_service" \
  --hidden-import="vibration.core.domain.models" \
  --hidden-import="vibration.presentation.views" \
  --hidden-import="vibration.presentation.presenters" \
  --hidden-import="vibration.presentation.models" \
  --hidden-import="vibration.infrastructure.event_bus" \
  --hidden-import="numpy" \
  --hidden-import="scipy" \
  --hidden-import="matplotlib" \
  --hidden-import="PyQt5" \
  --hidden-import="pandas" \
  --hidden-import="soundfile" \
  --hidden-import="librosa" \
  --hidden-import="nptdms" \
  cn_3F_trend_optimized.py

echo ""
echo "✅ Build complete!"
echo ""
echo "📦 Output files:"
ls -lh dist/
echo ""

# 6. Test the built app (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 macOS detected. Testing app launch..."
    echo "   Running: timeout 3 open dist/CNAVE_Analyzer.app"
    timeout 3 open dist/CNAVE_Analyzer.app 2>/dev/null || true
    echo "   (App should launch briefly - this is normal)"
    echo ""
fi

echo "🎉 Done! Your app is ready at:"
echo "   dist/CNAVE_Analyzer.app (macOS)"
echo "   dist/CNAVE_Analyzer (Linux/Windows executable)"
echo ""
echo "To distribute:"
echo "   1. Zip the .app bundle: zip -r CNAVE_Analyzer.zip dist/CNAVE_Analyzer.app"
echo "   2. Share the .zip file"
