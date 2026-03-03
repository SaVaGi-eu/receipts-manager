# Receipt & Warranty Manager

A multilingual receipt and warranty management system with OCR support for scanning and organizing receipts, warranties, and related documents.

## 🚀 Quick Start

### 📦 macOS Users (Recommended)

Download the latest `ReceiptManager.dmg` from [Releases](https://github.com/SaVaGi-eu/receipts-manager/releases):

1. Open the DMG file
2. Drag `ReceiptManager.app` to Applications
3. Double-click to run

**No additional setup required!** The app includes:
- Python runtime
- All Python dependencies
- Tesseract OCR with multilingual support (English, Dutch, Greek, Latvian)
- Complete database and storage system

### 🐧 Linux Users

Use the automated setup script:

```bash
git clone https://github.com/SaVaGi-eu/receipts-manager.git
cd receipts-manager
chmod +x run.sh
./run.sh
```

The script will automatically:
- Detect your Linux distribution
- Install required system dependencies (Tesseract, Python packages)
- Set up the virtual environment
- Launch the application

## 📋 Features

- 📸 **Receipt Scanning**: OCR-powered text extraction from receipt images
- 🗂️ **Warranty Tracking**: Organize and track product warranties with expiration alerts
- 🌍 **Multilingual**: Full support for English, Dutch, Greek, and Latvian
- 🔍 **Full-Text Search**: Search across all receipts and documents
- 📊 **Expense Tracking**: Categorize and analyze spending
- 🏷️ **Smart Tagging**: Automatic categorization and custom tags
- 💾 **Local Storage**: All data stored locally for privacy
- 🖼️ **Image Management**: Attach multiple images per receipt

## 🔨 Building from Source

### macOS

Build the standalone .app bundle:

```bash
# Install build dependencies
brew install python@3.12 tesseract tesseract-lang

# Clone repository
git clone https://github.com/SaVaGi-eu/receipts-manager.git
cd receipts-manager

# Build the app
chmod +x build_macos_app.sh
./build_macos_app.sh

# The built app will be in dist/ReceiptManager.app
# DMG installer will be in dist/ReceiptManager.dmg
```

### Linux

For development or running from source:

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv tesseract-ocr

# Clone and run
git clone https://github.com/SaVaGi-eu/receipts-manager.git
cd receipts-manager
chmod +x run.sh
./run.sh
```

## 🛠️ Development Setup

### macOS Development (without building .app)

```bash
# Install Tesseract
brew install tesseract tesseract-lang

# Install Python dependencies
pip install -r requirements.txt

# Run development server
python app.py
```

### Linux Development

```bash
# The run.sh script handles everything
./run.sh
```

## 📚 Documentation

- [Docker Setup](DOCKER.md) - Run in Docker container
- [Integration Guide](INTEGRATION_GUIDE.md) - API and integration options
- [OCR Setup](OCR_SETUP.md) - Detailed OCR configuration
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [Quick Start](QUICKSTART.md) - Getting started guide
- [Workflows](WORKFLOWS.md) - Usage workflows and examples
- [Structure](STRUCTURE.md) - Project layout and architecture

## 📁 Project Structure

See [STRUCTURE.md](STRUCTURE.md) for detailed project layout.

## 🌐 Multilingual Support

The application supports OCR and interface in:
- 🇬🇧 English (eng)
- 🇳🇱 Dutch (nld)
- 🇬🇷 Greek (ell)
- 🇱🇻 Latvian (lav)

Additional languages can be added by installing the corresponding Tesseract language pack.

## 💻 System Requirements

### macOS
- macOS 10.15 (Catalina) or later
- 200 MB disk space
- Apple Silicon (M1/M2) or Intel processor

### Linux
- Ubuntu 20.04+, Debian 10+, or equivalent
- Python 3.8 or later
- Tesseract OCR 4.0+
- 200 MB disk space

## 🐳 Docker

For containerized deployment:

```bash
docker-compose up -d
```

See [DOCKER.md](DOCKER.md) for details.

## 🔒 Security

See [SECURITY.md](SECURITY.md) for security policy and vulnerability reporting.

## 📄 License

[Add your license here]

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📮 Support

- Create an issue: [GitHub Issues](https://github.com/SaVaGi-eu/receipts-manager/issues)
- Jira Board: [RM Project](https://savagi.atlassian.net/jira/software/c/projects/RM/boards/42)

## 🙏 Acknowledgments

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - OCR engine
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Pillow](https://python-pillow.org/) - Image processing

---

Built with ❤️ for better receipt and warranty management
