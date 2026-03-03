#!/bin/bash

cd "$(dirname "$0")"

echo "=========================================="
echo "Receipt & Warranty Manager (standalone)"
echo "=========================================="
echo ""

# Detect OS
OS="unknown"
case "$(uname -s)" in
    Darwin*)
        OS="macos"
        ;;
    Linux*)
        OS="linux"
        ;;
    CYGWIN*|MINGW*|MSYS*)
        OS="windows"
        ;;
esac

echo "Detected OS: $OS"
echo ""

# Check for python3
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH."
    read -p "Press Enter to exit..."
    exit 1
fi

echo -n "Python 3 found: "
python3 --version || true
echo ""

# Platform-specific setup
if [ "$OS" = "macos" ]; then
    # macOS: Use platform-specific setup
    if [ -f "platforms/macos/setup.sh" ]; then
        bash platforms/macos/setup.sh
        
        if [ $? -ne 0 ]; then
            echo ""
            echo "❌ Setup failed. Cannot continue."
            read -p "Press Enter to exit..."
            exit 1
        fi
    else
        echo "⚠️  Warning: macOS setup script not found."
        echo "Attempting to run with system Python..."
        echo ""
    fi
else
    # Linux/Other: Generic dependency check with auto-install
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

    # Check for available updates (informational only)
    if [ -f "check_deps.py" ]; then
        python3 check_deps.py || true
    fi
fi

echo "Starting built-in HTTP server on http://127.0.0.1:5000 ..."
echo "Press Ctrl+C in this terminal to stop."
echo ""

# Run the application
# Determine Python to use based on OS
if [ "$OS" = "macos" ]; then
    # macOS: Use venv from home directory
    MACOS_VENV="$HOME/.receipts-manager-venv/bin/python"
    if [ -f "$MACOS_VENV" ]; then
        "$MACOS_VENV" app.py
    else
        echo "⚠️  Warning: Virtual environment not found. Using system Python."
        python3 app.py
    fi
else
    # Linux/Other: Use local venv if available, otherwise system Python
    if [ -f "venv/bin/python" ]; then
        venv/bin/python app.py
    else
        python3 app.py
    fi
fi

status=$?

if [ $status -ne 0 ]; then
    echo ""
    echo "Application exited with error (status $status)."
    read -p "Press Enter to exit..."
fi
