# Platform-Specific Setup

This directory contains platform-specific setup scripts to handle OS differences in dependency installation and environment setup.

## How It Works

The main `run.sh` launcher:

1. Detects the operating system (macOS, Linux, Windows, etc.)
2. Delegates to the appropriate platform-specific setup script
3. Falls back to generic setup for unsupported platforms
4. Runs the application using the appropriate Python environment

## Supported Platforms

### macOS (`platforms/macos/`)

**Problem:** Homebrew Python is "externally managed" (PEP 668), preventing direct pip installations.

**Solution:**

- Checks for Homebrew (offers to install if missing)
- Installs system dependencies via Homebrew (e.g., `poppler` for PDF support)
- Creates a Python virtual environment (`venv/`)
- Installs Python packages inside the venv
- Runs the app using `venv/bin/python`

**Files:**

- `setup.sh` - Interactive setup script
- `requirements.txt` - Python dependencies for venv

**Usage:**

```bash
./run.sh  # Automatically detects macOS and runs setup
```

### Linux (`platforms/linux/`) - *Coming Soon*

Linux setup will handle:

- Package manager detection (apt, dnf, pacman, etc.)
- System dependency installation
- Python package installation via pip

### Windows (`platforms/windows/`) - *Coming Soon*

Windows setup will handle:

- Chocolatey or winget for system dependencies
- Python package installation via pip
- Path configuration

## Adding a New Platform

To add support for a new platform:

1. Create a directory: `platforms/<platform-name>/`
2. Add a setup script: `platforms/<platform-name>/setup.sh` (or `.bat` for Windows)
3. Add requirements if needed: `platforms/<platform-name>/requirements.txt`
4. Update `run.sh` to detect and delegate to your platform

### Setup Script Requirements

Your setup script should:

- ✅ Check for required system dependencies
- ✅ Prompt user before installing anything
- ✅ Create/manage Python environment if needed
- ✅ Install Python packages from requirements.txt
- ✅ Exit with non-zero status code on failure
- ✅ Print clear status messages

## Generic Fallback

For unsupported platforms, `run.sh` falls back to:

- Generic dependency check via pip
- Attempt `pip install --user` for missing packages
- Run with system Python

This works on most Linux distributions and other Unix-like systems.
