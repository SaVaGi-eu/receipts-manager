# Contributing to Receipts Manager

Thank you for your interest in contributing! This document provides guidelines and setup instructions.

## 🚀 Quick Start

### Prerequisites

- Python 3.9, 3.10, 3.11, or 3.12
- Git
- Tesseract OCR (for receipt scanning)

### Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/SaVaGi-eu/receipts-manager.git
   cd receipts-manager
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Install pre-commit hooks**

   ```bash
   pre-commit install
   ```

5. **Verify setup**

   ```bash
   pytest
   black --check .
   flake8 .
   ```

## 🔧 Development Workflow

### Code Quality Tools

We use several tools to maintain code quality:

#### Formatting

- **Black**: Code formatter (line length: 120)

  ```bash
  black .
  ```

- **isort**: Import sorter

  ```bash
  isort .
  ```

#### Linting

- **Flake8**: Style checker

  ```bash
  flake8 .
  ```

- **Pylint**: Static analyzer (optional)

  ```bash
  pylint app.py
  ```

- **Mypy**: Type checker (optional)

  ```bash
  mypy .
  ```

#### Security

- **Bandit**: Security issue scanner

  ```bash
  bandit -r . -c pyproject.toml
  ```

- **Safety**: Dependency vulnerability checker

  ```bash
  safety check
  ```

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific test file
pytest tests/test_app.py

# Verbose output
pytest -v
```

### Pre-commit Hooks

Pre-commit hooks run automatically before each commit:

```bash
# Run manually on all files
pre-commit run --all-files

# Update hooks
pre-commit autoupdate

# Skip hooks (not recommended)
git commit --no-verify
```

## 📝 Coding Standards

### Python Style

- Follow PEP 8 guidelines
- Line length: 120 characters
- Use type hints where appropriate
- Write docstrings for public functions/classes

### Security Guidelines

1. **Input Validation**: Always validate and sanitize user input
2. **Path Safety**: Use `safe_resolve_within()` for file operations
3. **No Secrets**: Never commit API keys, passwords, or tokens
4. **Dependencies**: Keep dependencies updated

### Git Commit Messages

Follow conventional commits:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**

```
feat(ocr): add support for Dutch language
fix(api): resolve path traversal vulnerability
docs(readme): update installation instructions
```

## 🧪 Testing Requirements

### Test Coverage

- Minimum 80% code coverage
- All new features must include tests
- Bug fixes should include regression tests

### Test Structure

```python
def test_feature_name():
    # Arrange
    expected = "value"

    # Act
    result = function_under_test()

    # Assert
    assert result == expected
```

## 🔒 Security

### Reporting Vulnerabilities

See [SECURITY.md](SECURITY.md) for vulnerability reporting process.

### Security Checklist

Before submitting:

- [ ] No hardcoded secrets
- [ ] Input validation implemented
- [ ] File paths validated
- [ ] Security tests included
- [ ] Dependencies scanned

## 📬 Pull Request Process

1. **Create a branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Write tests
   - Update documentation
   - Follow coding standards

3. **Run checks locally**

   ```bash
   pytest
   black --check .
   flake8 .
   bandit -r .
   ```

4. **Commit changes**

   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push and create PR**

   ```bash
   git push origin feature/your-feature-name
   ```

   Then create a pull request on GitHub

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts
- [ ] Security considerations addressed

## 🤝 Code Review

### What to Expect

- Reviews within 48 hours (usually faster)
- Constructive feedback
- Requests for changes if needed
- Approval and merge

### Review Criteria

- Code quality and style
- Test coverage
- Security implications
- Performance impact
- Documentation completeness

## 📚 Resources

- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Security Best Practices](SECURITY.md)

## 💬 Questions?

Feel free to:

- Open an issue for discussion
- Ask in pull request comments
- Check existing issues and PRs

## 📄 License

By contributing, you agree that your contributions will be licensed under the project's license.

---

Thank you for contributing! 🎉
