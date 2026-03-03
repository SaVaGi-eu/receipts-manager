#!/bin/bash
# macOS-specific setup for Receipt Manager

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/venv"
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
PYTHON_VERSION=$($WORKING_PYTHON --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
echo "Using: $WORKING_PYTHON (Python $PYTHON_VERSION)"

# Check if this is Python 3.14+ (known venv issues)
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

USE_MANUAL_PIP=false
if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 14 ]; then
    echo "⚠️  Python 3.14+ detected - will use manual pip installation"
    USE_MANUAL_PIP=true
fi

# Check if venv exists and is valid
echo ""
VENV_NEEDS_CREATION=false

if [ -d "$VENV_DIR" ]; then
    # Check if venv is valid (has activate script and python binary)
    if [ ! -f "$VENV_DIR/bin/activate" ] || [ ! -f "$VENV_DIR/bin/python" ]; then
        echo "⚠️  Existing virtual environment is broken/incomplete"
        echo "🧹 Removing broken venv..."
        rm -rf "$VENV_DIR"
        VENV_NEEDS_CREATION=true
    fi
else
    VENV_NEEDS_CREATION=true
fi

if [ "$VENV_NEEDS_CREATION" = true ]; then
    echo "📦 Creating Python virtual environment..."
    
    if [ "$USE_MANUAL_PIP" = true ]; then
        # For Python 3.14+, always use manual pip method
        echo "⚙️  Using manual pip installation method for Python 3.14+..."
        
        if "$WORKING_PYTHON" -m venv --without-pip "$VENV_DIR" 2>/dev/null; then
            echo "✅ Virtual environment created (without pip)"
            
            # Bootstrap pip manually
            echo "📦 Installing pip..."
            source "$VENV_DIR/bin/activate"
            
            if curl -sS https://bootstrap.pypa.io/get-pip.py | python; then
                echo "✅ pip installed successfully"
            else
                echo "❌ Failed to install pip"
                exit 1
            fi
        else
            echo "❌ Failed to create virtual environment"
            echo ""
            echo "Troubleshooting:"
            echo "1. Try: brew reinstall python@3.14"
            echo "2. Or install Python 3.13: brew install python@3.13"
            echo ""
            exit 1
        fi
    else
        # Try normal venv creation first
        if "$WORKING_PYTHON" -m venv "$VENV_DIR" 2>/dev/null; then
            echo "✅ Virtual environment created"
        else
            # Fallback to manual pip method
            echo "⚙️  Standard method failed, using manual pip installation..."
            
            if "$WORKING_PYTHON" -m venv --without-pip "$VENV_DIR" 2>/dev/null; then
                echo "✅ Virtual environment created (without pip)"
                
                # Bootstrap pip manually
                echo "📦 Installing pip..."
                source "$VENV_DIR/bin/activate"
                
                if curl -sS https://bootstrap.pypa.io/get-pip.py | python; then
                    echo "✅ pip installed successfully"
                else
                    echo "❌ Failed to install pip"
                    exit 1
                fi
            else
                echo "❌ Failed to create virtual environment"
                exit 1
            fi
        fi
    fi
else
    echo "✅ Virtual environment exists and is valid"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Verify activation worked
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Upgrade pip in venv
echo ""
echo "Upgrading pip in virtual environment..."
python -m pip install --upgrade pip --quiet 2>/dev/null

# Check if dependencies need to be installed
echo ""
echo "Checking Python dependencies..."

NEED_INSTALL=false

# Read requirements and check if installed
while IFS= read -r line; do
    # Skip comments and empty lines
    [[ "$line" =~ ^#.*$ ]] && continue
    [[ -z "$line" ]] && continue
    
    # Extract package name (before >= or ==)
    package=$(echo "$line" | sed 's/[><=].*//')
    
    # Map package name to import name if different
    import_name="$package"
    case "$package" in
        "opencv-python") import_name="cv2" ;;
        "Pillow") import_name="PIL" ;;
    esac
    
    if ! python -c "import $import_name" 2>/dev/null; then
        NEED_INSTALL=true
        break
    fi
done < "$REQUIREMENTS"

if [ "$NEED_INSTALL" = true ]; then
    echo ""
    echo "📦 Installing Python dependencies..."
    echo "This may take several minutes (especially torch/torchvision)..."
    echo ""
    
    pip install -r "$REQUIREMENTS"
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "⚠️  Warning: Some Python packages failed to install."
        echo "You may need to install them manually inside the venv."
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
