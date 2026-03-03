# Development Guide

Comprehensive guide for developers working on Receipt Manager.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Debugging](#debugging)
- [Building](#building)
- [CI/CD](#cicd)

## Prerequisites

### Required
- Python 3.8 or higher
- Git
- Node.js 16+ (for macOS builds)
- Tesseract OCR 4.0+

### Recommended
- Docker (for testing containers)
- VS Code or PyCharm
- macOS (for building macOS app)

### Installation

**macOS:**
```bash
brew install python@3.12 node tesseract tesseract-lang git
```

**Ubuntu/Debian:**
```bash
sudo apt-get install python3 python3-venv python3-pip nodejs npm tesseract-ocr git
```

## Initial Setup

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/SaVaGi-eu/receipts-manager.git
cd receipts-manager

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file:

```bash
DEBUG=true
LOG_LEVEL=DEBUG
PORT=8765
DATA_DIR=./data_dev
STORAGE_DIR=./storage_dev
```

### 3. Run Application

```bash
python app.py
```

Access at: http://127.0.0.1:8765

## Development Workflow

### Creating a Feature

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes
# Edit files...

# 3. Run tests
pytest

# 4. Run linters
black .
isort .
flake8 .

# 5. Commit
git add .
git commit -m "feat: Add my feature"

# 6. Push and create PR
git push origin feature/my-feature
```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix  
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

**Examples:**
```
feat(ocr): Add Greek language support

fix(ui): Correct date formatting in receipt list

docs: Update installation instructions for Ubuntu

chore(deps): Update Flask to 3.0.0
```

## Code Style

### Python

**Formatting:**
- Line length: 120 characters
- Use Black for formatting
- Use isort for import sorting

**Example:**
```python
from typing import Dict, List, Optional

import flask
from PIL import Image

from config import DATABASE_PATH
from ocr_service import perform_ocr


def process_receipt(image_path: str, language: str = "eng") -> Dict[str, str]:
    """Process receipt image with OCR.
    
    Args:
        image_path: Path to image file
        language: OCR language code
        
    Returns:
        Dict containing extracted text and metadata
    """
    image = Image.open(image_path)
    text = perform_ocr(image, language)
    return {"text": text, "language": language}
```

**Run formatters:**
```bash
black .
isort .
```

### JavaScript (Electron)

```javascript
// Use 2-space indentation
// Single quotes for strings
const { app, BrowserWindow } = require('electron');

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });
  
  mainWindow.loadURL('http://localhost:8765');
}
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_ocr_service.py

# Run specific test
pytest tests/test_app.py::test_homepage

# Run with verbose output
pytest -v

# Run and show print statements
pytest -s
```

### Writing Tests

**Test file structure:**
```python
# tests/test_my_module.py
import pytest
from my_module import my_function


@pytest.fixture
def sample_data():
    return {"key": "value"}


def test_my_function(sample_data):
    result = my_function(sample_data)
    assert result is not None
    assert result["key"] == "expected"


def test_my_function_error():
    with pytest.raises(ValueError):
        my_function(None)
```

### Test Coverage

Aim for >80% code coverage:

```bash
pytest --cov=. --cov-report=term-missing
```

## Debugging

### Using ipdb

```python
import ipdb

def my_function():
    x = 42
    ipdb.set_trace()  # Breakpoint
    return x * 2
```

### Flask Debug Mode

```python
# app.py
if __name__ == "__main__":
    app.run(debug=True, port=8765)
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Docker Debugging

```bash
# View logs
docker-compose logs -f

# Execute commands in container
docker-compose exec receipts-manager bash

# Check Python environment
docker-compose exec receipts-manager python3 -c "import sys; print(sys.version)"
```

## Building

### macOS App

```bash
# Full build
./install.sh  # Choose option 1

# Or manually
cd platforms/macos
npm install
npm run build

# Output: dist/Receipt Manager.dmg
```

### Docker Image

```bash
# Build
cd platforms/docker
docker-compose build

# Test
docker-compose up

# Stop
docker-compose down
```

## CI/CD

### GitHub Actions

Workflows in `.github/workflows/`:

1. **tests.yml** - Run on every push/PR
   - Linting
   - Tests with coverage
   - Security checks
   - Docker build test

2. **release.yml** - Run on tag push
   - Build macOS app
   - Build Docker image
   - Create GitHub release
   - Upload artifacts

### Creating a Release

```bash
# 1. Update CHANGELOG.md
# 2. Commit changes
git add CHANGELOG.md
git commit -m "chore: Prepare release v1.1.0"

# 3. Create and push tag
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0

# GitHub Actions will automatically:
# - Build macOS app
# - Build Docker image
# - Create release
# - Upload artifacts
```

## Project Structure

```
receipts-manager/
├── app.py                  # Main Flask application
├── config.py               # Configuration
├── ocr_service.py          # OCR logic
├── check_deps.py           # Dependency checker
│
├── templates/              # Jinja2 templates
│   ├── index.html
│   ├── receipt_list.html
│   └── ...
│
├── static/                 # Static assets
│   ├── css/
│   ├── js/
│   └── images/
│
├── tests/                  # Test suite
│   ├── conftest.py
│   ├── test_app.py
│   └── ...
│
├── platforms/
│   ├── macos/              # Electron wrapper
│   └── docker/             # Docker config
│
├── docs/                   # Documentation
└── .github/                # GitHub config
```

## Common Tasks

### Adding a New Route

```python
# app.py
@app.route('/my-route', methods=['GET', 'POST'])
def my_route():
    if request.method == 'POST':
        data = request.form
        # Process data
        return jsonify({"status": "success"})
    return render_template('my_template.html')
```

### Adding a New OCR Language

1. Install Tesseract language pack:
   ```bash
   brew install tesseract-lang  # macOS
   sudo apt-get install tesseract-ocr-deu  # Linux (German example)
   ```

2. Update `.env.example`:
   ```bash
   OCR_LANGUAGE=eng+nld+ell+lav+deu
   ```

3. Update documentation

### Database Changes

The app uses JSON file storage in `data/database/data.json`:

```python
import json

# Read
with open('data/database/data.json', 'r') as f:
    data = json.load(f)

# Modify
data['receipts'].append(new_receipt)

# Write
with open('data/database/data.json', 'w') as f:
    json.dump(data, f, indent=2)
```

## Troubleshooting

### Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Port Already in Use

```bash
# Find process
lsof -i :8765

# Kill process
kill -9 <PID>
```

### Pre-commit Hooks Failing

```bash
# Run manually
pre-commit run --all-files

# Update hooks
pre-commit autoupdate
```

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Electron Documentation](https://www.electronjs.org/docs/latest/)
- [Tesseract Documentation](https://tesseract-ocr.github.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)

## Getting Help

- Read [CONTRIBUTING.md](../CONTRIBUTING.md)
- Check [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
- Ask on [GitHub Discussions](https://github.com/SaVaGi-eu/receipts-manager/discussions)
- Create an [Issue](https://github.com/SaVaGi-eu/receipts-manager/issues)

---

Happy coding! 🚀
