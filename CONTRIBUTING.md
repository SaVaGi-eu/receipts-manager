# Contributing to Receipt Manager

Thank you for your interest in contributing to Receipt Manager! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- Python 3.8 or higher
- Node.js 16 or higher (for macOS builds)
- Git
- Tesseract OCR (for OCR features)
- Docker (optional, for container testing)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/receipts-manager.git
cd receipts-manager
```

3. Add upstream remote:

```bash
git remote add upstream https://github.com/SaVaGi-eu/receipts-manager.git
```

## Development Setup

### Quick Setup

Use the installer in development mode:

```bash
chmod +x install.sh
./install.sh
# Choose option: Run Application Directly
```

### Manual Setup

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # Create this file if it doesn't exist
pip install pre-commit black flake8 isort pytest

# Set up pre-commit hooks
pre-commit install

# Copy environment template
cp .env.example .env

# Run the application
python app.py
```

### Development Environment Variables

Create a `.env` file (copy from `.env.example`) and customize:

```bash
DEBUG=true
LOG_LEVEL=DEBUG
PORT=8765
DATA_DIR=./data_dev
STORAGE_DIR=./storage_dev
```

## Code Style

### Python

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 120 characters (not 80)
- **Formatter**: Black
- **Import sorter**: isort
- **Linter**: flake8

#### Auto-formatting

```bash
# Format all Python files
black .

# Sort imports
isort .

# Check code style
flake8 .
```

### JavaScript (Electron)

- **Indentation**: 2 spaces
- **Semicolons**: Required
- **Quotes**: Single quotes for strings

### Commit Messages

Follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```
feat(ocr): Add support for Greek language

fix(ui): Correct date formatting in receipt list

docs: Update installation instructions

chore(deps): Update Flask to 3.0.0
```

## Project Structure

```
receipts-manager/
├── app.py                  # Main Flask application
├── config.py               # Configuration management
├── ocr_service.py          # OCR processing logic
├── check_deps.py           # Dependency checker
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── .editorconfig           # Editor configuration
├── .pre-commit-config.yaml # Pre-commit hooks
├── pyproject.toml          # Python project config
│
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS, JavaScript, images
│
├── platforms/
│   ├── macos/              # macOS Electron app
│   └── docker/             # Docker configuration
│
├── tests/                  # Test files
├── docs/                   # Additional documentation
└── data/                   # Runtime data (not in git)
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

# Run with verbose output
pytest -v
```

### Writing Tests

Create test files in the `tests/` directory:

```python
# tests/test_example.py
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_homepage(client):
    response = client.get('/')
    assert response.status_code == 200
```

## Submitting Changes

### Before Submitting

1. **Update from upstream:**

```bash
git fetch upstream
git rebase upstream/main
```

2. **Run pre-commit checks:**

```bash
pre-commit run --all-files
```

3. **Test your changes:**

```bash
pytest
```

4. **Update documentation** if needed

### Creating a Pull Request

1. Push to your fork:

```bash
git push origin feature/your-feature-name
```

2. Go to GitHub and create a Pull Request

3. Fill in the PR template:
   - **Description**: What does this PR do?
   - **Motivation**: Why is this change needed?
   - **Testing**: How was this tested?
   - **Screenshots**: For UI changes
   - **Breaking changes**: Any breaking changes?

4. Link related issues: `Closes #123`

### PR Review Process

- Maintainers will review your PR
- Address any feedback
- Once approved, it will be merged

## Reporting Issues

### Bug Reports

When reporting bugs, include:

- **Description**: Clear description of the bug
- **Steps to reproduce**: Detailed steps
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**:
  - OS: macOS 14.0, Ubuntu 22.04, etc.
  - Python version: 3.11.5
  - Installation method: Direct, Docker, or macOS app
- **Logs**: Any relevant error messages
- **Screenshots**: If applicable

### Feature Requests

When requesting features, include:

- **Description**: Clear description of the feature
- **Use case**: Why is this needed?
- **Proposed solution**: How should it work?
- **Alternatives**: Other approaches considered

## Development Tips

### Debugging

```python
# Enable debug mode in .env
DEBUG=true
LOG_LEVEL=DEBUG
```

### Hot Reload

Flask's debug mode enables auto-reload:

```bash
export FLASK_ENV=development
python app.py
```

### Database Reset

```bash
# Backup first!
cp data/database/data.json data/database/data.json.backup

# Remove database
rm data/database/data.json

# App will create fresh database on next start
```

### Testing Docker Locally

```bash
cd platforms/docker
docker-compose build
docker-compose up
```

### Testing macOS Build

```bash
cd platforms/macos
npm install
npm run build
```

## Code of Conduct

Be respectful and constructive:

- Be welcoming to newcomers
- Respect differing viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community

## Questions?

- **Jira Board**: [RM Project](https://savagi.atlassian.net/jira/software/c/projects/RM/boards/42)
- **GitHub Issues**: [Create an issue](https://github.com/SaVaGi-eu/receipts-manager/issues)
- **Discussions**: Use GitHub Discussions for questions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🎉
