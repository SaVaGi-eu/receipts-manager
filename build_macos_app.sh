#!/bin/bash
# build_macos_app.sh - Build macOS .app bundle with embedded Tesseract OCR

set -e  # Exit on error

echo "🍎 Building Receipt Manager for macOS"
echo "======================================"

# Configuration
APP_NAME="ReceiptManager"
BUILD_DIR="dist"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
TESSERACT_HOMEBREW="/opt/homebrew/bin/tesseract"
TESSDATA_HOMEBREW="/opt/homebrew/share/tessdata"
BUILD_VENV="build_env"

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 not found. Install with: brew install python@3.12"
    exit 1
fi

if ! command -v tesseract &> /dev/null; then
    echo "❌ Tesseract not found. Install with: brew install tesseract"
    exit 1
fi

if [ ! -d "$TESSDATA_HOMEBREW" ]; then
    echo "⚠️  Tesseract language data not found at $TESSDATA_HOMEBREW"
    echo "Installing language files..."
    brew install tesseract-lang
fi

echo "✅ Prerequisites met"

# Clean previous build
if [ -d "$BUILD_DIR" ]; then
    echo "🧹 Cleaning previous build..."
    rm -rf "$BUILD_DIR"
fi

if [ -d "$BUILD_VENV" ]; then
    echo "🧹 Cleaning previous build environment..."
    rm -rf "$BUILD_VENV"
fi

# Create temporary virtual environment for building
echo "📦 Creating build environment..."
python3.12 -m venv --without-pip "$BUILD_VENV"
source "$BUILD_VENV/bin/activate"

# Install pip in the venv
echo "📦 Installing pip in build environment..."
curl -sS https://bootstrap.pypa.io/get-pip.py | python

# Install build dependencies
echo "📦 Installing build dependencies..."
pip install --upgrade pip setuptools wheel
pip install py2app
pip install -r requirements.txt

# Build the app using py2app
echo "🔨 Building app bundle..."
python setup.py py2app

# Deactivate venv
deactivate

# Create directories for Tesseract
echo "📁 Preparing Tesseract directories..."
mkdir -p "$APP_BUNDLE/Contents/Resources/tesseract/bin"
mkdir -p "$APP_BUNDLE/Contents/Resources/tesseract/tessdata"

# Copy Tesseract binary
echo "📋 Copying Tesseract binary..."
cp "$TESSERACT_HOMEBREW" "$APP_BUNDLE/Contents/Resources/tesseract/bin/"

# Copy language data files (multilingual support)
echo "📋 Copying Tesseract language data..."
LANGUAGES=("eng" "nld" "ell" "lav")  # English, Dutch, Greek, Latvian
for lang in "${LANGUAGES[@]}"; do
    if [ -f "$TESSDATA_HOMEBREW/$lang.traineddata" ]; then
        cp "$TESSDATA_HOMEBREW/$lang.traineddata" "$APP_BUNDLE/Contents/Resources/tesseract/tessdata/"
        echo "  ✓ $lang.traineddata"
    else
        echo "  ⚠️  $lang.traineddata not found (optional)"
    fi
done

# Copy required shared libraries
echo "📦 Bundling shared libraries..."
TESSERACT_LIBS=$(otool -L "$TESSERACT_HOMEBREW" | grep -E "homebrew|opt" | awk '{print $1}')
mkdir -p "$APP_BUNDLE/Contents/Frameworks"

for lib in $TESSERACT_LIBS; do
    if [ -f "$lib" ]; then
        lib_name=$(basename "$lib")
        cp "$lib" "$APP_BUNDLE/Contents/Frameworks/" 2>/dev/null || true
        echo "  ✓ $lib_name"
    fi
done

# Update library paths in Tesseract binary
echo "🔗 Updating library paths..."
install_name_tool -add_rpath "@executable_path/../Frameworks" \
    "$APP_BUNDLE/Contents/Resources/tesseract/bin/tesseract" 2>/dev/null || true

# Set permissions
echo "🔒 Setting permissions..."
chmod +x "$APP_BUNDLE/Contents/Resources/tesseract/bin/tesseract"

# Create DMG (optional)
echo "📀 Creating DMG installer..."
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$BUILD_DIR" \
    -ov -format UDZO \
    "$BUILD_DIR/$APP_NAME.dmg"

# Clean up build environment
echo "🧹 Cleaning up build environment..."
rm -rf "$BUILD_VENV"

echo ""
echo "✅ Build complete!"
echo "   App bundle: $APP_BUNDLE"
echo "   DMG installer: $BUILD_DIR/$APP_NAME.dmg"
echo ""
echo "📦 Tesseract included:"
echo "   Binary: $(file $APP_BUNDLE/Contents/Resources/tesseract/bin/tesseract | cut -d: -f2-)"
echo "   Languages: ${LANGUAGES[*]}"
echo ""
echo "🧪 To test: open $APP_BUNDLE"
