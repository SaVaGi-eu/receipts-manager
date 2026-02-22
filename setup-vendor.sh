#!/bin/bash
set -e

echo "🔧 Setting up vendor dependencies for macOS build..."
echo ""

# Check for Homebrew
if ! command -v brew &> /dev/null; then
  echo "❌ Homebrew not found. Please install it first:"
  echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  exit 1
fi

# Install required tools
echo "📦 Installing poppler and dylibbundler..."
brew install poppler dylibbundler

# Detect Homebrew prefix (works for both Intel and Apple Silicon)
BREW_PREFIX=$(brew --prefix)
POPPLER_LIB="${BREW_PREFIX}/lib"
POPPLER_BIN="${BREW_PREFIX}/bin"

# Create directories
mkdir -p vendor/poppler/bin
mkdir -p vendor/poppler/lib

# Copy the three binaries pdf2image needs
echo "📋 Copying poppler binaries..."
cp "${POPPLER_BIN}/pdftoppm"   vendor/poppler/bin/
cp "${POPPLER_BIN}/pdftocairo" vendor/poppler/bin/
cp "${POPPLER_BIN}/pdfinfo"    vendor/poppler/bin/

# Bundle all dylib dependencies with explicit search paths
echo "📚 Bundling dylib dependencies (this takes ~30 seconds)..."
dylibbundler -od -b \
  -x vendor/poppler/bin/pdftoppm \
  -d vendor/poppler/lib/ \
  -p @executable_path/../lib/ \
  -s "${POPPLER_LIB}" \
  -s /usr/lib \
  -s /usr/local/lib

dylibbundler -od -b \
  -x vendor/poppler/bin/pdftocairo \
  -d vendor/poppler/lib/ \
  -p @executable_path/../lib/ \
  -s "${POPPLER_LIB}" \
  -s /usr/lib \
  -s /usr/local/lib

dylibbundler -od -b \
  -x vendor/poppler/bin/pdfinfo \
  -d vendor/poppler/lib/ \
  -p @executable_path/../lib/ \
  -s "${POPPLER_LIB}" \
  -s /usr/lib \
  -s /usr/local/lib

echo ""
echo "✅ Vendor setup complete! You can now run: npm run build"
