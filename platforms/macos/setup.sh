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

# Find a working Python version for venv
echo ""
echo "Finding suitable Python version..."

WORKING_PYTHON=""
PYTHON_CANDIDATES=("python3" "python3.13" "python3.12" "python3.11" "python3.10")

for py_cmd in "${PYTHON_CANDIDATES[@]}"; do
    if command -v "$py_cmd" &> /dev/null; then
        echo -n "Testing $py_cmd... "
        
        # Test if this Python can create a venv
        TEST_VENV="/tmp/test_venv_$$"
        if "$py_cmd" -m venv "$TEST_VENV" &> /dev/null; then
            rm -rf "$TEST_VENV"
            echo "✅ Works!"
            WORKING_PYTHON="$py_cmd"
            break
        else
            # Try with --without-pip
            if "$py_cmd" -m venv --without-pip "$TEST_VENV" &> /dev/null; then
                rm -rf "$TEST_VENV"
                echo "✅ Works (needs manual pip)!"
                WORKING_PYTHON="$py_cmd"
                NEEDS_MANUAL_PIP=true
                break
            else
                rm -rf "$TEST_VENV" 2>/dev/null
                echo "❌ Broken"
            fi
        fi
    fi
done

if [ -z "$WORKING_PYTHON" ]; then
    echo ""
    echo "❌ No working Python version found for venv creation."
    echo ""
    echo "Homebrew Python 3.14 has known issues with venv."
    echo ""
    read -p "Would you like to install Python 3.13 via Homebrew? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 Installing Python 3.13..."
        brew install python@3.13
        
        if command -v python3.13 &> /dev/null; then
            WORKING_PYTHON="python3.13"
            echo "✅ Python 3.13 installed successfully!"
        else
            echo "❌ Installation failed."
            exit 1
        fi
    else
        echo ""
        echo "Cannot proceed without a working Python version."
        exit 1
    fi
fi

echo ""
echo "Using: $WORKING_PYTHON ($($WORKING_PYTHON --version))"

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
    
    if [ "$NEEDS_MANUAL_PIP" = true ]; then
        # Create without pip, then install it manually
        "$WORKING_PYTHON" -m venv --without-pip "$VENV_DIR"
        
        if [ $? -eq 0 ]; then
            echo "✅ Virtual environment created (without pip)"
            
            # Bootstrap pip manually
            echo "📦 Installing pip..."
            source "$VENV_DIR/bin/activate"
            
            curl -sS https://bootstrap.pypa.io/get-pip.py | python
            
            if [ $? -eq 0 ]; then
                echo "✅ pip installed successfully"
            else
                echo "❌ Failed to install pip"
                exit 1
            fi
        else
            echo "❌ Failed to create virtual environment"
            exit 1
        fi
    else
        # Normal venv creation
        "$WORKING_PYTHON" -m venv "$VENV_DIR"
        
        if [ $? -eq 0 ]; then
            echo "✅ Virtual environment created"
        else
            echo "❌ Failed to create virtual environment"
            exit 1
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
