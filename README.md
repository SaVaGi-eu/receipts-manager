# Receipt & Warranty Manager

A multilingual receipt and warranty management system with OCR support for scanning and organizing receipts, warranties, and related documents.

## 🚀 Quick Start

**One command to install:**

```bash
git clone https://github.com/SaVaGi-eu/receipts-manager.git
cd receipts-manager
chmod +x install.sh
./install.sh
```

The installer will detect your system and offer appropriate options:

### macOS Users
1. **Build macOS Application** - Creates a native `.app` with DMG installer
2. **Build Docker Container** - Run in Docker
3. **Run Directly** - Development mode (web server)

### Linux Users  
1. **Build Docker Container** - Run in Docker
2. **Run Directly** - Development mode (web server)

## 📋 Features

- 📸 **Receipt Scanning**: OCR-powered text extraction from receipt images
- 🗂️ **Warranty Tracking**: Organize and track product warranties with expiration alerts
- 🌍 **Multilingual**: Full support for English, Dutch, Greek, and Latvian
- 🔍 **Full-Text Search**: Search across all receipts and documents
- 📊 **Expense Tracking**: Categorize and analyze spending
- 🏷️ **Smart Tagging**: Automatic categorization and custom tags
- 💾 **Local Storage**: All data stored locally for privacy
- 🖼️ **Image Management**: Attach multiple images per receipt

## 🛠️ Platform-Specific Builds

### macOS Native App

The macOS app includes:
- Python runtime bundled
- All dependencies included
- Tesseract OCR with multilingual support
- Native window with Electron
- No terminal required

**Requirements:**
- macOS 10.15 (Catalina) or later
- 200 MB disk space
- Node.js (for building)

### Docker Deployment

For server deployment or consistent environments:

```bash
./install.sh
# Choose option: Build Docker Container
```

Or manually:

```bash
cd platforms/docker
docker-compose up -d
```

Access at: `http://localhost:8765`

### Direct Execution

For development or quick testing:

```bash
./install.sh
# Choose option: Run Application Directly
```

This creates a virtual environment and runs the Flask server.

## 📁 Project Structure

```
receipts-manager/
├── install.sh              # Universal installer (START HERE)
├── app.py                  # Main Flask application
├── config.py              # Configuration
├── ocr_service.py         # OCR processing
├── requirements.txt       # Python dependencies
│
├── platforms/
│   ├── macos/            # macOS Electron app
│   │   ├── electron-main.js
│   │   ├── package.json
│   │   └── dist/         # Built .app and .dmg
│   │
│   └── docker/           # Docker deployment
│       ├── Dockerfile
│       ├── docker-compose.yml
│       └── README.md
│
├── templates/            # HTML templates
├── static/              # CSS, JS, images
├── data/                # Database and backups (created on first run)
└── storage/             # Uploaded receipt files (created on first run)
```

## 🌐 Multilingual Support

Supported OCR languages:
- 🇬🇧 English (eng)
- 🇳🇱 Dutch (nld)
- 🇬🇷 Greek (ell)
- 🇱🇻 Latvian (lav)

Additional languages can be added by installing the corresponding Tesseract language pack.

## 💻 System Requirements

### macOS App
- macOS 10.15+ (Catalina or later)
- 200 MB disk space
- Apple Silicon (M1/M2/M3) or Intel

### Docker
- Docker Desktop or Docker Engine
- 500 MB disk space

### Direct Execution
- Python 3.8+
- Tesseract OCR 4.0+ (optional, for OCR features)
- 200 MB disk space

## 📚 Documentation

- [Docker Setup](platforms/docker/README.md) - Docker-specific instructions
- [Integration Guide](INTEGRATION_GUIDE.md) - API and integration options
- [OCR Setup](OCR_SETUP.md) - Detailed OCR configuration
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [Quick Start](QUICKSTART.md) - Getting started guide
- [Workflows](WORKFLOWS.md) - Usage workflows and examples
- [Structure](STRUCTURE.md) - Project layout and architecture

## 🔧 Development

### Running in Development Mode

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Access at http://127.0.0.1:8765
```

### Building macOS App from Source

```bash
cd platforms/macos
npm install
npm run build

# Output: dist/Receipt Manager.dmg
```

## 🔒 Security

See [SECURITY.md](SECURITY.md) for security policy and vulnerability reporting.

## 📄 License

MIT License - free to use, modify, and distribute.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📮 Support

- Create an issue: [GitHub Issues](https://github.com/SaVaGi-eu/receipts-manager/issues)
- Jira Board: [RM Project](https://savagi.atlassian.net/jira/software/c/projects/RM/boards/42)

## 🙏 Acknowledgments

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - OCR engine
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) - Alternative OCR
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Electron](https://www.electronjs.org/) - Desktop app framework
- [Pillow](https://python-pillow.org/) - Image processing

---

Built with ❤️ for better receipt and warranty management
