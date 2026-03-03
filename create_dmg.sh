#!/bin/bash

# Create a DMG installer for Receipt Manager

set -e

echo "💾 Creating DMG installer..."
echo "============================"

APP_NAME="ReceiptManager"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="${APP_NAME}-macOS"
VOLUME_NAME="Receipt Manager"

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "❌ Error: $APP_PATH not found"
    echo "Run ./build_macos_pyinstaller.sh first"
    exit 1
fi

# Clean old DMG
rm -f "dist/${DMG_NAME}.dmg"
rm -rf "dist/dmg_temp"

# Create temporary directory for DMG contents
mkdir -p "dist/dmg_temp"

# Copy app to temp directory
echo "📦 Copying app bundle..."
cp -R "$APP_PATH" "dist/dmg_temp/"

# Create Applications symlink
echo "🔗 Creating Applications symlink..."
ln -s /Applications "dist/dmg_temp/Applications"

# Create DMG
echo "💾 Creating DMG..."
hdiutil create -volname "$VOLUME_NAME" \
    -srcfolder "dist/dmg_temp" \
    -ov -format UDZO \
    "dist/${DMG_NAME}.dmg"

# Clean up
rm -rf "dist/dmg_temp"

if [ -f "dist/${DMG_NAME}.dmg" ]; then
    echo "✅ DMG created successfully!"
    echo "📦 Installer: dist/${DMG_NAME}.dmg"
    echo ""
    echo "To distribute:"
    echo "  1. Test: open dist/${DMG_NAME}.dmg"
    echo "  2. Upload to GitHub Releases"
else
    echo "❌ DMG creation failed"
    exit 1
fi
