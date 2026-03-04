#!/bin/bash
# macOS-specific setup for Receipt Manager

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Use a hidden directory in user's home (avoids macOS permission issues and spaces in path)
VENV_DIR="$HOME/.receipts-manager-venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

cd "$PROJECT_ROOT"

echo "🍎 macOS Setup for Receipt Manager"
echo "====================================="
echo ""

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew is not installed."
    echo ""
    echo "Homebrew is needed to install system dependencies (like poppler for PDF support)."
    echo ""
    read -p "Would you like to install Homebrew now? (y/n): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Check if installation succeeded
        if ! command -v brew &> /dev/null; then
            echo ""
            echo "❌ Homebrew installation failed. Please install it manually:"
            echo "   https://brew.sh"
            echo ""
            exit 1
        fi

        echo "✅ Homebrew installed successfully!"
        echo ""
    else
        echo ""
        echo "⚠️  Cannot proceed without Homebrew. Please install it manually:"
        echo "   https://brew.sh"
        echo ""
        exit 1
    fi
else
    echo "✅ Homebrew is installed"
fi

# Check for required system dependencies
echo ""
echo "Checking system dependencies..."

MISSING_BREW_DEPS=()

# poppler is needed for pdf2image
if ! brew list poppler &> /dev/null; then
    MISSING_BREW_DEPS+=("poppler")
fi

if [ ${#MISSING_BREW_DEPS[@]} -gt 0 ]; then
    echo ""
    echo "📦 Missing system dependencies: ${MISSING_BREW_DEPS[*]}"
    echo ""
    read -p "Would you like to install them via Homebrew? (y/n): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 Installing system dependencies..."
        brew install "${MISSING_BREW_DEPS[@]}"
        echo "✅ System dependencies installed!"
    else
        echo "⚠️  Warning: Some features (like PDF support) may not work without these dependencies."
    fi
else
    echo "✅ All system dependencies are installed"
fi

# Find Python version
echo ""
WORKING_PYTHON="python3"

# Check if Python 3.13 is available and prefer it over 3.14
if command -v python3.13 &> /dev/null; then
    WORKING_PYTHON="python3.13"
    echo "Using: python3.13 (stable version)"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
    echo "Using: python3 (Python $PYTHON_VERSION)"

    # Warn about Python 3.14
    MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 14 ]; then
        echo "⚠️  Python 3.14 has known issues with virtual environments"
    fi
else
    echo "❌ Python 3 not found"
    exit 1
fi

# Check if virtualenv is installed
echo ""
echo "Checking for virtualenv..."

if ! $WORKING_PYTHON -m pip show virtualenv &> /dev/null; then
    echo "📦 virtualenv not found, installing..."
    echo ""

    if $WORKING_PYTHON -m pip install --break-system-packages virtualenv 2>/dev/null; then
        echo "✅ virtualenv installed"
    else
        if $WORKING_PYTHON -m pip install virtualenv 2>/dev/null; then
            echo "✅ virtualenv installed"
        else
            echo "❌ Failed to install virtualenv"
            exit 1
        fi
    fi
else
    echo "✅ virtualenv is installed"
fi

# Clear virtualenv cache
echo ""
echo "Clearing virtualenv cache..."
VIRTUALENV_CACHE="$HOME/Library/Caches/virtualenv"
if [ -d "$VIRTUALENV_CACHE" ]; then
    rm -rf "$VIRTUALENV_CACHE" 2>/dev/null
    echo "✅ Cache cleared"
else
    echo "✅ No cache to clear"
fi

# Check if venv exists and is valid
echo ""
VENV_NEEDS_CREATION=false

if [ -d "$VENV_DIR" ]; then
    if [ ! -f "$VENV_DIR/bin/activate" ] || [ ! -f "$VENV_PYTHON" ] || [ ! -f "$VENV_PIP" ]; then
        echo "⚠️  Existing virtual environment is broken/incomplete"
        echo "🧹 Removing broken venv..."
        rm -rf "$VENV_DIR" 2>/dev/null
        VENV_NEEDS_CREATION=true
    fi
else
    VENV_NEEDS_CREATION=true
fi

if [ "$VENV_NEEDS_CREATION" = true ]; then
    echo "📦 Creating Python virtual environment..."

    # Try to create venv
    VENV_ERROR=$(mktemp)
    if $WORKING_PYTHON -m virtualenv --no-seed "$VENV_DIR" 2>"$VENV_ERROR" >/dev/null; then
        rm -f "$VENV_ERROR"

        if [ -f "$VENV_PYTHON" ]; then
            echo "✅ Virtual environment created"

            # Manually install pip
            echo "📦 Installing pip..."

            if curl -sS https://bootstrap.pypa.io/get-pip.py | "$VENV_PYTHON" > /dev/null 2>&1; then
                if [ -f "$VENV_PIP" ] && "$VENV_PIP" --version > /dev/null 2>&1; then
                    echo "✅ pip installed successfully"
                else
                    echo "❌ pip installation verification failed"
                    exit 1
                fi
            else
                echo "❌ Failed to install pip"
                exit 1
            fi
        else
            echo "❌ Virtual environment creation failed - missing python binary"
            exit 1
        fi
    else
        # Failed - show error and offer Python 3.13
        echo "❌ Failed to create virtual environment"
        echo ""
        echo "Error details:"
        cat "$VENV_ERROR"
        rm -f "$VENV_ERROR"
        echo ""

        # If using Python 3.14, offer to install 3.13
        if [[ "$WORKING_PYTHON" == "python3" ]]; then
            PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
            MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
            MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

            if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 14 ]; then
                echo "Python 3.14 is too new and has broken venv support."
                echo ""

                if ! command -v python3.13 &> /dev/null; then
                    read -p "Would you like to install Python 3.13 (stable)? (y/n): " -n 1 -r
                    echo ""

                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        echo "📦 Installing Python 3.13..."
                        brew install python@3.13

                        if command -v python3.13 &> /dev/null; then
                            echo "✅ Python 3.13 installed"
                            echo ""
                            echo "Please run ./run.sh again to use Python 3.13"
                            exit 0
                        else
                            echo "❌ Python 3.13 installation failed"
                            exit 1
                        fi
                    fi
                fi
            fi
        fi

        exit 1
    fi
else
    echo "✅ Virtual environment exists and is valid"
fi

# Upgrade pip
echo ""
echo "Upgrading pip..."
"$VENV_PYTHON" -m pip install --upgrade pip --quiet 2>/dev/null

# Check dependencies
echo ""
echo "Checking Python dependencies..."

NEED_INSTALL=false

while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ ]] && continue
    [[ -z "$line" ]] && continue

    package=$(echo "$line" | sed 's/[><=].*//')
    import_name="$package"

    case "$package" in
        "opencv-python") import_name="cv2" ;;
        "Pillow") import_name="PIL" ;;
    esac

    if ! "$VENV_PYTHON" -c "import $import_name" 2>/dev/null; then
        NEED_INSTALL=true
        break
    fi
done < "$REQUIREMENTS"

if [ "$NEED_INSTALL" = true ]; then
    echo ""
    echo "📦 Installing Python dependencies..."
    echo "This may take several minutes (especially torch/torchvision)..."
    echo ""

    "$VENV_PIP" install -r "$REQUIREMENTS"

    if [ $? -ne 0 ]; then
        echo ""
        echo "⚠️  Warning: Some Python packages failed to install."
        echo ""
    else
        echo ""
        echo "✅ All Python dependencies installed successfully!"
    fi
else
    echo "✅ All Python dependencies are installed"
fi

echo ""
echo "====================================="
echo "✅ macOS setup complete!"
echo "====================================="
echo ""
