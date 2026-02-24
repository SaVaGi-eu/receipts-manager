# macOS Desktop Application

This folder contains the macOS-specific packaging for Receipt Manager using Electron.

## Overview

The macOS app wraps the Flask web application in an Electron window, providing:
- Native macOS application experience
- System integration (file dialogs, menu bar)
- Standalone distribution via DMG installer
- Automatic Python backend management

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- macOS 11+ (for building)

## Setup

```bash
cd platforms/macos
npm install
```

## Development

```bash
npm start
```

This will:
1. Launch Electron
2. Start the Flask backend automatically
3. Display the app in a native window

## Building Distributable DMG

### For Apple Silicon (M1/M2/M3):
```bash
npm run build:dmg
```

### For Intel Macs:
```bash
npm run build:dmg:x64
```

### Universal (both architectures):
```bash
npm run build:dmg:universal
```

The DMG will be created in `platforms/macos/dist/`.

## Architecture

```
platforms/macos/
├── electron-main.js    # Electron entry point
├── package.json        # Node dependencies & build config
└── README.md          # This file
```

### Key Features

**electron-main.js** handles:
- Python backend process management
- Port management (kills stale processes)
- First-time setup wizard (data folder selection)
- Settings persistence
- Window management
- External link handling

**Settings Storage**: `~/Library/Application Support/Receipt Manager/settings.json`

## Build Configuration

The `package.json` includes:
- Electron Builder configuration
- ASAR packaging with unpacked Python files
- DMG customization
- Code signing setup (currently disabled for development)

## Future Platforms

This folder structure is designed to support additional platforms:
- `platforms/windows/` - Windows installer
- `platforms/linux/` - Linux packages (deb, rpm, AppImage)
- `platforms/docker/` - Docker deployment

Each platform can have its own packaging logic while sharing the core Flask app from the repository root.
