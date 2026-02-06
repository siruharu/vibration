#!/bin/bash
set -e

echo "================================================"
echo "Cleaning Python cache and running app"
echo "================================================"

cd "$(dirname "$0")"

echo "1. Removing all __pycache__ directories..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo "2. Removing all .pyc files..."
find . -name "*.pyc" -delete 2>/dev/null || true

echo "3. Removing .pytest_cache..."
rm -rf .pytest_cache 2>/dev/null || true

echo "4. Cache cleaned!"
echo ""
echo "5. Running application..."
echo "================================================"
echo ""
echo "⚠️  IMPORTANT: Use 'python -m vibration', NOT 'python vibration/app.py'"
echo ""

# Use venv if exists, otherwise system python
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python"
fi

# IMPORTANT: Must use -m vibration, not direct file path
$PYTHON -m vibration

