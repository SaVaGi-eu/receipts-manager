# Changelog

All notable changes to Receipt Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Unified `install.sh` installer for all platforms
- Comprehensive documentation (CONTRIBUTING.md, LICENSE, etc.)
- Development tooling (.editorconfig, .pre-commit-config.yaml, pyproject.toml)
- Environment variable configuration (.env.example)
- GitHub Actions workflow for automated releases
- Docker deployment support with organized structure
- Changelog to track version history

### Changed
- Reorganized repository structure with platforms/ directory
- Updated README with simplified installation instructions
- Simplified run.sh and run.command to be wrappers for install.sh
- Moved Docker files to platforms/docker/
- Improved macOS Electron app build process

### Removed
- Obsolete build scripts (build_macos_app.sh, build_macos_pyinstaller.sh, etc.)
- Root-level Docker files (moved to platforms/docker/)
- py2app setup.py (switched to Electron-based approach)

## [1.0.0] - 2026-03-03

### Added
- Initial release
- Receipt scanning with OCR (Tesseract and EasyOCR)
- Warranty tracking with expiration alerts
- Multilingual support (English, Dutch, Greek, Latvian)
- Full-text search across receipts
- Expense tracking and categorization
- Smart tagging system
- Local data storage for privacy
- Image management (multiple images per receipt)
- macOS native app with Electron
- Docker support
- Web-based interface
- PDF support
- Backup and restore functionality

### Technical
- Flask backend (Python 3.8+)
- Electron frontend for macOS
- SQLite-like JSON database
- Responsive web UI
- REST API for integrations

[Unreleased]: https://github.com/SaVaGi-eu/receipts-manager/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/SaVaGi-eu/receipts-manager/releases/tag/v1.0.0
