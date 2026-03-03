#!/bin/bash

cd "$(dirname "$0")"

echo "=========================================="
echo "Receipt & Warranty Manager (standalone)"
echo "=========================================="
echo ""

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

# 1) Check for python3
if ! need_cmd python3; then
  echo "Error: python3 is not installed or not in PATH."
  read -p "Press Enter to exit..."
  exit 1
fi

echo -n "Python 3 found: "
python3 --version || true
echo ""

# Activate venv if it exists
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
fi

# 2) Auto-install missing dependencies
echo "Checking dependencies..."
python3 << 'EOF'
import sys
import subprocess

# Required packages (import_name: package_name)
required = {
    'pdf2image': 'pdf2image',
    'easyocr': 'easyocr',
    'PIL': 'Pillow',
    'cv2': 'opencv-python',
    'torch': 'torch',
    'torchvision': 'torchvision'
}

missing = []
for module, package in required.items():
    try:
        __import__(module)
    except ImportError:
        missing.append(package)

if missing:
    print(f"\n📦 Installing missing dependencies: {', '.join(missing)}")
    print("This may take a few minutes...\n")
    try:
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '--user', '--quiet'] + missing,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        print("\n✅ Dependencies installed successfully!\n")
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️  Warning: Some dependencies failed to install: {e}")
        print("You may need to install them manually.\n")
else:
    print("✅ All required dependencies are installed.\n")
EOF

# 3) Check for available updates (informational only)
if [ -f "check_deps.py" ]; then
  python3 check_deps.py || true
fi

echo "Starting built-in HTTP server on http://127.0.0.1:5000 ..."
echo "Press Ctrl+C in this terminal to stop."
echo ""

# Run the application
python3 app.py
status=$?

if [ $status -ne 0 ]; then
  echo ""
  echo "Application exited with error (status $status)."
  read -p "Press Enter to exit..."
fi
