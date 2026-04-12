#!/bin/bash

# Receipt Manager - Universal Installer
# Supports macOS app building, Docker deployment, and direct execution

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║        📦 Receipt & Warranty Manager Installer        ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

echo -e "${GREEN}Detected System:${NC} $OS ($ARCH)"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to check Node.js
check_nodejs() {
    if command_exists node && command_exists npm; then
        NODE_VERSION=$(node --version)
        echo -e "${GREEN}✓${NC} Node.js installed: $NODE_VERSION"
        return 0
    else
        echo -e "${RED}✗${NC} Node.js not found"
        return 1
    fi
}

# Function to check Python
check_python() {
    if command_exists python3; then
        PY_VERSION=$(python3 --version)
        echo -e "${GREEN}✓${NC} Python installed: $PY_VERSION"
        return 0
    else
        echo -e "${RED}✗${NC} Python 3 not found"
        return 1
    fi
}

# Function to check Docker
check_docker() {
    if command_exists docker; then
        DOCKER_VERSION=$(docker --version)
        echo -e "${GREEN}✓${NC} Docker installed: $DOCKER_VERSION"
        return 0
    else
        echo -e "${RED}✗${NC} Docker not found"
        return 1
    fi
}

# Function to check Tesseract
check_tesseract() {
    if command_exists tesseract; then
        TESS_VERSION=$(tesseract --version 2>&1 | head -n1)
        echo -e "${GREEN}✓${NC} Tesseract installed: $TESS_VERSION"
        return 0
    else
        echo -e "${YELLOW}!${NC} Tesseract not found (OCR will not work)"
        return 1
    fi
}

# Function to install Tesseract
install_tesseract() {
    echo -e "\n${BLUE}═══ Installing Tesseract OCR ═══${NC}\n"

    case "$OS" in
        Darwin)
            if command_exists brew; then
                echo "Installing Tesseract via Homebrew..."
                brew install tesseract tesseract-lang
                echo -e "${GREEN}✓ Tesseract installed successfully!${NC}"
                return 0
            else
                echo -e "${RED}Homebrew is required to auto-install Tesseract.${NC}"
                echo "Install Homebrew from: https://brew.sh"
                echo "Then run: brew install tesseract tesseract-lang"
                return 1
            fi
            ;;
        Linux)
            if command_exists apt-get; then
                echo "Installing Tesseract via apt-get..."
                echo "This requires sudo privileges."
                sudo apt-get update
                sudo apt-get install -y tesseract-ocr
                echo "You can install additional language packs as needed, e.g.: sudo apt-get install tesseract-ocr-eng"
                echo -e "${GREEN}✓ Tesseract installed successfully!${NC}"
                return 0
            elif command_exists yum; then
                echo "Installing Tesseract via yum..."
                echo "This requires sudo privileges."
                sudo yum install -y tesseract tesseract-langpack-eng tesseract-langpack-nld
                echo -e "${GREEN}✓ Tesseract installed successfully!${NC}"
                echo "Note: On yum-based systems, only English (eng) and Dutch (nld) language packs are installed by default."
                echo "If you need additional languages such as Greek (ell) or Latvian (lav), please install the corresponding Tesseract language packages manually."
                return 0
            else
                echo -e "${RED}Unable to auto-install Tesseract.${NC}"
                echo "Please install manually: sudo apt-get install tesseract-ocr"
                return 1
            fi
            ;;
        *)
            echo -e "${RED}Unsupported OS for auto-installation.${NC}"
            return 1
            ;;
    esac
}

# Function to prepare branding assets for electron-builder
# Copies icon and DMG background from media/branding/ into platforms/macos/build/
# Warns if assets are missing but does not abort — electron-builder will use its defaults.
prepare_branding() {
    local BRANDING_DIR="$SCRIPT_DIR/media/branding"
    local BUILD_DIR="$SCRIPT_DIR/platforms/macos/build"
    local MISSING=()

    [ ! -f "$BRANDING_DIR/icon.icns" ]     && MISSING+=("media/branding/icon.icns")
    [ ! -f "$BRANDING_DIR/icon.png" ]      && MISSING+=("media/branding/icon.png")
    [ ! -f "$BRANDING_DIR/background.png" ] && MISSING+=("media/branding/background.png")

    if [ ${#MISSING[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠ Branding assets not found — build will use default Electron icon:${NC}"
        for f in "${MISSING[@]}"; do
            echo "    - $f"
        done
        echo "  See media/branding/README.md for instructions."
        echo ""
        return
    fi

    mkdir -p "$BUILD_DIR"
    cp "$BRANDING_DIR/icon.icns"      "$BUILD_DIR/icon.icns"
    cp "$BRANDING_DIR/icon.png"       "$BUILD_DIR/icon.png"
    cp "$BRANDING_DIR/background.png" "$BUILD_DIR/background.png"
    echo -e "${GREEN}✓ Branding assets ready.${NC}"
}

# Set up Python virtual environment (create or refresh) and activate it.
# Creates the venv if missing. If requirements.txt is newer than the last
# install marker, the venv is fully recreated. Leaves the venv activated.
setup_venv() {
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        echo "Installing dependencies..."
        pip install -r requirements.txt
        touch venv/.requirements_installed
    elif [ "requirements.txt" -nt "venv/.requirements_installed" ]; then
        echo "requirements.txt has changed; recreating Python virtual environment..."
        rm -rf venv
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        touch venv/.requirements_installed
    else
        source venv/bin/activate
    fi
}

# Build macOS App
build_macos_app() {
    echo -e "\n${BLUE}═══ Building macOS Application ═══${NC}\n"

    # Check prerequisites
    echo "Checking prerequisites..."
    check_nodejs || {
        echo -e "\n${RED}Node.js is required to build the macOS app.${NC}"
        echo "Install with: brew install node"
        exit 1
    }

    check_python || {
        echo -e "\n${RED}Python 3 is required.${NC}"
        echo "Install with: brew install python@3.12"
        exit 1
    }

    if ! check_tesseract; then
        echo -e "\n${YELLOW}Tesseract is recommended for OCR functionality.${NC}"
        read -p "Would you like to install Tesseract now? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            install_tesseract || {
                echo -e "${YELLOW}Continuing without Tesseract. OCR features will be disabled.${NC}"
            }
        fi
    fi

    # Detect architecture
    if [[ "$ARCH" == "arm64" ]]; then
        BUILD_TARGET="--mac --arm64"
        echo -e "${GREEN}Building for Apple Silicon (M1/M2/M3)${NC}"
    else
        BUILD_TARGET="--mac --x64"
        echo -e "${GREEN}Building for Intel Mac${NC}"
    fi

    # Prepare branding assets
    echo ""
    echo "Preparing branding assets..."
    prepare_branding

    # Navigate to macOS build directory
    cd platforms/macos

    # Install Node dependencies in a reproducible way
    if [ -f "package-lock.json" ]; then
        echo "Installing Node.js dependencies with npm ci..."
        npm ci
    elif [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies..."
        npm install
    fi

    # Create or refresh venv in root based on requirements.txt
    cd ../..
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        deactivate
        touch venv/.requirements_installed
    else
        # Refresh venv if requirements.txt is newer than the last install marker
        if [ "requirements.txt" -nt "venv/.requirements_installed" ]; then
            echo "requirements.txt has changed; recreating Python virtual environment..."
            rm -rf venv
            python3 -m venv venv
            source venv/bin/activate
            pip install --upgrade pip
            pip install -r requirements.txt
            deactivate
            touch venv/.requirements_installed
        fi
    fi

    # Build the app
    cd platforms/macos
    echo "Building Electron app..."
    npm run build

    cd ../..

    if [ -d "platforms/macos/dist" ]; then
        echo -e "\n${GREEN}✓ Build successful!${NC}"
        echo -e "\n${BLUE}Application location:${NC}"
        ls -lh platforms/macos/dist/*.pkg 2>/dev/null || ls -d platforms/macos/dist/*.app 2>/dev/null
        echo -e "\n${YELLOW}To install:${NC}"
        echo "  1. Double-click the PKG file in platforms/macos/dist/"
        echo "  2. Follow the installer — enter your password when prompted"
        echo "  3. Receipt Manager will be installed to /Applications and opened without Gatekeeper warnings"
    else
        echo -e "\n${RED}✗ Build failed${NC}"
        exit 1
    fi
}

# Run Docker Container (pull from Docker Hub, fall back to local build)
build_docker() {
    echo -e "\n${BLUE}═══ Docker Deployment ═══${NC}\n"

    check_docker || {
        echo -e "\n${RED}Docker is required.${NC}"
        echo "Install from: https://www.docker.com/products/docker-desktop"
        exit 1
    }

    DOCKER_HUB_IMAGE="savagi/receipts-manager:latest"

    # Try to pull from Docker Hub first; fall back to local build if unavailable
    echo "Pulling image from Docker Hub..."
    if docker pull "$DOCKER_HUB_IMAGE" 2>/dev/null; then
        echo -e "${GREEN}✓ Image pulled: $DOCKER_HUB_IMAGE${NC}"
        export DOCKER_IMAGE="$DOCKER_HUB_IMAGE"
    else
        echo -e "${YELLOW}! Docker Hub pull failed — building image locally instead.${NC}"
        export DOCKER_IMAGE="receipts-manager:latest"
        cd platforms/docker
        docker build -f Dockerfile -t "$DOCKER_IMAGE" ../..
        cd ../..
        echo -e "${GREEN}✓ Image built locally.${NC}"
    fi

    echo -e "\n${YELLOW}To stop the container later:${NC}"
    echo "  cd platforms/docker && docker-compose down"

    read -p "Start the container now? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        cd platforms/docker
        docker-compose up -d
        cd ../..
        echo -e "\n${GREEN}✓ Container started!${NC}"
        echo -e "Open your browser to: ${BLUE}http://localhost:8765${NC}"
    else
        echo ""
        echo "To start later:"
        echo "  cd platforms/docker && DOCKER_IMAGE=\"$DOCKER_IMAGE\" docker-compose up -d"
    fi
}

# Run Application Directly
run_direct() {
    echo -e "\n${BLUE}═══ Running Application ═══${NC}\n"

    check_python || {
        echo -e "\n${RED}Python 3 is required.${NC}"
        case "$OS" in
            Darwin)
                echo "Install with: brew install python@3.12"
                ;;
            Linux)
                echo "Install with: sudo apt-get install python3 python3-venv"
                ;;
        esac
        exit 1
    }

    # Check and offer to install Tesseract
    if ! check_tesseract; then
        echo ""
        read -p "Would you like to install Tesseract now for OCR functionality? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            if install_tesseract; then
                echo -e "${GREEN}Tesseract installed successfully!${NC}"
            else
                echo -e "${YELLOW}Continuing without Tesseract. OCR features will be disabled.${NC}"
            fi
        else
            echo -e "${YELLOW}Continuing without Tesseract. OCR features will be disabled.${NC}"
        fi
    fi

    # Set up Python virtual environment
    setup_venv

    echo -e "\n${GREEN}Starting Receipt Manager...${NC}"
    echo "Access the app at: http://127.0.0.1:8765"
    echo "Press Ctrl+C to stop"
    echo ""

    python3 app.py
}

# Show menu
show_menu() {
    echo "What would you like to do?"
    echo ""

    if [[ "$OS" == "Darwin" ]]; then
        echo "  1) Build macOS Application (.pkg)"
        echo "  2) Build Docker Container"
        echo "  3) Run Application Directly (development mode)"
        echo "  4) Exit"
        echo ""
        read -p "Enter your choice [1-4]: " choice

        case $choice in
            1)
                build_macos_app
                ;;
            2)
                build_docker
                ;;
            3)
                run_direct
                ;;
            4)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice${NC}"
                exit 1
                ;;
        esac
    else
        echo "  1) Build Docker Container"
        echo "  2) Run Application Directly (development mode)"
        echo "  3) Exit"
        echo ""
        read -p "Enter your choice [1-3]: " choice

        case $choice in
            1)
                build_docker
                ;;
            2)
                run_direct
                ;;
            3)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice${NC}"
                exit 1
                ;;
        esac
    fi
}

show_menu
