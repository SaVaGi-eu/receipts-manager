#!/bin/bash

# Build Receipt Manager for macOS using PyInstaller
# This handles complex dependencies better than py2app

set -e  # Exit on error

echo "🍎 Building Receipt Manager for macOS with PyInstaller"
echo "======================================================"

# Check prerequisites
echo "📋 Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

if ! command -v tesseract &> /dev/null; then
    echo "❌ Tesseract is not installed. Install with: brew install tesseract tesseract-lang"
    exit 1
fi

echo "✅ Prerequisites met"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build_env/ dist/ build/ *.spec

# Create fresh virtual environment
echo "📦 Creating build environment..."
python3 -m venv build_env
source build_env/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

echo "🔨 Building app bundle with PyInstaller..."

# Create PyInstaller spec file
cat > receipts-manager.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
    ],
    hiddenimports=[
        'flask',
        'werkzeug',
        'jinja2',
        'click',
        'itsdangerous',
        'markupsafe',
        'pytesseract',
        'PIL',
        'PIL._imaging',
        'pdf2image',
        'easyocr',
        'torch',
        'torchvision',
        'cv2',
        'numpy',
        'scipy',
        'skimage',
        'yaml',
        'ocr_service',
        'config',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'tkinter',
        'test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ReceiptManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ReceiptManager',
)

app = BUNDLE(
    coll,
    name='ReceiptManager.app',
    icon=None,
    bundle_identifier='eu.savagi.receipts-manager',
    info_plist={
        'CFBundleName': 'Receipt Manager',
        'CFBundleDisplayName': 'Receipt Manager',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
    },
)
EOF

# Build with PyInstaller
echo "🔨 Running PyInstaller..."
pyinstaller receipts-manager.spec --clean --noconfirm

if [ -d "dist/ReceiptManager.app" ]; then
    echo "✅ Build successful!"
    echo "📦 Application: dist/ReceiptManager.app"
    echo ""
    echo "To test the app:"
    echo "  open dist/ReceiptManager.app"
    echo ""
    echo "To create a DMG installer:"
    echo "  ./create_dmg.sh"
else
    echo "❌ Build failed - app bundle not created"
    exit 1
fi

# Deactivate virtual environment
deactivate
