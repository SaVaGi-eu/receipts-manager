#!/bin/bash

# Receipt Manager - Release Script
# Fetches existing GitHub releases, lets you pick or create a new version,
# bumps the version in ALL source files (single source of truth),
# commits & pushes, builds the macOS DMG, and uploads to GitHub Releases.

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

REPO="SaVaGi-eu/receipts-manager"
ARCH="$(uname -m)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║        🚀 Receipt & Warranty Manager Release         ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ── Preflight checks ────────────────────────────────────────────────────────

if ! command -v gh &> /dev/null; then
    echo -e "${RED}✗ GitHub CLI (gh) is not installed.${NC}"
    echo "Install with: brew install gh"
    echo "Then authenticate with: gh auth login"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo -e "${RED}✗ GitHub CLI is not authenticated.${NC}"
    echo "Run: gh auth login"
    exit 1
fi

if ! command -v node &> /dev/null || ! command -v npm &> /dev/null; then
    echo -e "${RED}✗ Node.js / npm is required.${NC}"
    echo "Install with: brew install node"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met.${NC}\n"

# ── Check branding assets ────────────────────────────────────────────────────

BRANDING_DIR="$SCRIPT_DIR/media/branding"
ICON_ICNS="$BRANDING_DIR/icon.icns"
ICON_PNG="$BRANDING_DIR/icon.png"
BACKGROUND="$BRANDING_DIR/background.png"

echo "Checking branding assets..."

MISSING_ASSETS=()
[ ! -f "$ICON_ICNS" ]   && MISSING_ASSETS+=("media/branding/icon.icns")
[ ! -f "$ICON_PNG" ]    && MISSING_ASSETS+=("media/branding/icon.png")
[ ! -f "$BACKGROUND" ]  && MISSING_ASSETS+=("media/branding/background.png")

if [ ${#MISSING_ASSETS[@]} -gt 0 ]; then
    echo -e "${RED}✗ Missing branding assets:${NC}"
    for asset in "${MISSING_ASSETS[@]}"; do
        echo "    - $asset"
    done
    echo ""
    echo "Copy the files from platforms/macos/build/ if you have a previous build:"
    echo "  cp platforms/macos/build/icon.icns   media/branding/"
    echo "  cp platforms/macos/build/icon.png    media/branding/"
    echo "  cp platforms/macos/build/background.png media/branding/"
    echo ""
    echo "Or see media/branding/README.md for instructions on generating them."
    exit 1
fi

echo -e "${GREEN}✓ All branding assets present.${NC}\n"

# ── Fetch existing releases from GitHub ─────────────────────────────────────

echo "Fetching existing releases from GitHub..."
TAGS_JSON=$(gh release list --repo "$REPO" --limit 20 --json tagName,isLatest 2>/dev/null || echo "[]")
TAGS=()
while IFS= read -r line; do
    TAGS+=("$line")
done < <(echo "$TAGS_JSON" | python3 -c "
import json, sys
releases = json.load(sys.stdin)
for r in releases:
    marker = ' (latest)' if r.get('isLatest') else ''
    print(r['tagName'] + marker)
")

echo ""
echo -e "${BLUE}═══ Select Version ═══${NC}"
echo ""

i=1
declare -a TAG_ARRAY
for tag in "${TAGS[@]}"; do
    clean_tag="${tag% (latest)}"
    echo "  $i) $tag"
    TAG_ARRAY[$i]="$clean_tag"
    ((i++))
done

NEW_OPTION=$i
echo "  $i) Create a new version"
echo ""

read -p "Your choice [1-$i]: " choice

if [[ "$choice" -eq "$NEW_OPTION" || ${#TAGS[@]} -eq 0 ]]; then
    if [[ ${#TAG_ARRAY[@]} -gt 0 ]]; then
        LATEST="${TAG_ARRAY[1]}"
        CLEAN="${LATEST#v}"
        MAJOR=$(echo "$CLEAN" | cut -d. -f1)
        MINOR=$(echo "$CLEAN" | cut -d. -f2)
        PATCH=$(echo "$CLEAN" | cut -d. -f3)
        NEXT_PATCH=$((PATCH + 1))
        if [[ "$LATEST" == v* ]]; then
            SUGGESTED="v${MAJOR}.${MINOR}.${NEXT_PATCH}"
        else
            SUGGESTED="${MAJOR}.${MINOR}.${NEXT_PATCH}"
        fi
    else
        SUGGESTED="v1.0.0"
    fi

    echo ""
    read -p "Enter new version tag [suggested: $SUGGESTED]: " USER_VERSION
    APP_VERSION="${USER_VERSION:-$SUGGESTED}"
    IS_NEW_RELEASE=true
else
    if [[ -z "${TAG_ARRAY[$choice]}" ]]; then
        echo -e "${RED}Invalid choice.${NC}"
        exit 1
    fi
    APP_VERSION="${TAG_ARRAY[$choice]}"
    IS_NEW_RELEASE=false
fi

echo ""
echo -e "${GREEN}Selected version: ${APP_VERSION}${NC}"
echo ""

# ── Confirm ─────────────────────────────────────────────────────────────────

read -p "Proceed to build and release $APP_VERSION? (Y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Strip leading 'v' — used for files that need a plain semver string
NPM_VERSION="${APP_VERSION#v}"

# ── Bump version in package.json ─────────────────────────────────────────────

echo -e "\n${BLUE}═══ Updating package.json ═══${NC}\n"
cd platforms/macos
npm version "$NPM_VERSION" --no-git-tag-version --allow-same-version
cd ../..
echo -e "${GREEN}✓ package.json updated to $NPM_VERSION${NC}"

# ── Bump version in templates/index.html (the in-app Settings screen) ────────

echo -e "\n${BLUE}═══ Updating in-app version display ═══${NC}\n"
sed -i '' "s|<span id=\"appVersion\">[^<]*</span>|<span id=\"appVersion\">${NPM_VERSION}</span>|" templates/index.html
echo -e "${GREEN}✓ templates/index.html updated to $NPM_VERSION${NC}"

# ── Commit & push version bumps ───────────────────────────────────────────────

echo -e "\n${BLUE}═══ Committing version bumps ═══${NC}\n"
git add platforms/macos/package.json platforms/macos/package-lock.json templates/index.html
git commit -m "chore: bump version to ${APP_VERSION}"
git push origin main
echo -e "${GREEN}✓ Version bump committed and pushed${NC}"

# ── Prepare build/ directory with branding assets ────────────────────────────

echo -e "\n${BLUE}═══ Preparing branding assets ═══${NC}\n"

BUILD_DIR="$SCRIPT_DIR/platforms/macos/build"
mkdir -p "$BUILD_DIR"

cp "$ICON_ICNS"  "$BUILD_DIR/icon.icns"
cp "$ICON_PNG"   "$BUILD_DIR/icon.png"
cp "$BACKGROUND" "$BUILD_DIR/background.png"

echo -e "${GREEN}✓ Branding assets copied to platforms/macos/build/${NC}"

# ── Build ────────────────────────────────────────────────────────────────────

echo -e "\n${BLUE}═══ Building macOS DMG ═══${NC}\n"

# Ensure venv exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment so subsequent Python commands use it
# Note: this assumes `deactivate` will be called later when Python work is done.
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

cd platforms/macos

if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

if [[ "$ARCH" == "arm64" ]]; then
    echo -e "${GREEN}Building for Apple Silicon (M1/M2/M3/M4)...${NC}"
    npm run build
else
    echo -e "${GREEN}Building for Intel Mac...${NC}"
    npm run build:x64
fi

cd ../..

DMG_FILE=$(ls platforms/macos/dist/*.dmg 2>/dev/null | head -n 1)

if [ -z "$DMG_FILE" ]; then
    echo -e "${RED}✗ Build failed — no DMG found in platforms/macos/dist/${NC}"
    exit 1
fi

# Rename DMG to ensure the filename matches the selected release version
VERSIONED_DMG="platforms/macos/dist/ReceiptsManager-${NPM_VERSION}.dmg"
if [ "$DMG_FILE" != "$VERSIONED_DMG" ]; then
    mv "$DMG_FILE" "$VERSIONED_DMG"
fi
DMG_FILE="$VERSIONED_DMG"

echo -e "${GREEN}✓ Build successful: $DMG_FILE${NC}"

# ── Upload to GitHub Releases ─────────────────────────────────────────────────

echo -e "\n${BLUE}═══ Publishing to GitHub Releases ═══${NC}\n"

if [ "$IS_NEW_RELEASE" = true ]; then
    echo "Creating new GitHub release $APP_VERSION and uploading DMG..."
    gh release create "$APP_VERSION" "$DMG_FILE" \
        --repo "$REPO" \
        --title "Release $APP_VERSION" \
        --notes "Release $APP_VERSION" \
        --latest
else
    echo "Uploading DMG to existing release $APP_VERSION..."
    gh release upload "$APP_VERSION" "$DMG_FILE" \
        --repo "$REPO" \
        --clobber
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
INNER_WIDTH=55
success_msg="  ✓ Release $APP_VERSION published successfully!"
msg_len=${#success_msg}
if [ "$msg_len" -lt "$INNER_WIDTH" ]; then
    padding_len=$(( INNER_WIDTH - msg_len ))
else
    padding_len=0
fi
padding=""
while [ ${#padding} -lt "$padding_len" ]; do
    padding="${padding} "
done
echo -e "${GREEN}║${success_msg}${padding}║${NC}"
echo -e "${GREEN}║  https://github.com/$REPO/releases/tag/$APP_VERSION   ${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
