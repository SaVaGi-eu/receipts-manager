# Security Policy

## Supported Versions

We actively maintain and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| develop | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of receipts-manager seriously. If you discover a security vulnerability, please follow these steps:

### 🔒 Private Disclosure (Preferred)

1. **DO NOT** open a public GitHub issue
2. Use GitHub's Security Advisories:
   - Go to: https://github.com/SaVaGi-eu/receipts-manager/security/advisories
   - Click "New draft security advisory"
   - Provide detailed information about the vulnerability

3. Alternatively, email: 101175436+v-giannakopoulos@users.noreply.github.com
   - Subject: "[SECURITY] Receipts Manager Vulnerability"
   - Include: Description, reproduction steps, potential impact

### 📋 What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact/severity
- Suggested fix (if available)
- Your contact information

### ⏱️ Response Timeline

- **Initial Response:** Within 48 hours
- **Status Update:** Within 7 days
- **Fix Timeline:** Depends on severity
  - Critical: 1-7 days
  - High: 7-30 days
  - Medium/Low: 30-90 days

### 🎁 Recognition

We appreciate security researchers and will:
- Credit you in the security advisory (if desired)
- Acknowledge your contribution in release notes
- Keep you informed throughout the fix process

## Security Best Practices

When using receipts-manager:

### 🔐 Access Control
- Run with least-privilege user accounts
- Use strong authentication for production deployments
- Restrict network access appropriately

### 📁 Data Protection
- Store receipts in encrypted storage when possible
- Regular backups of receipt data
- Proper file permissions on data directories

### 🔄 Updates
- Keep dependencies up-to-date (Dependabot enabled)
- Monitor security advisories
- Apply security patches promptly

### 🐳 Container Security
- Use official Docker images only
- Scan images for vulnerabilities regularly
- Don't run containers as root

## Security Features

This project implements:

- ✅ **Path Traversal Protection** - Validated file operations
- ✅ **Input Sanitization** - All user inputs sanitized
- ✅ **CORS Protection** - Configured allowed origins
- ✅ **CSP Headers** - Content Security Policy enabled
- ✅ **Dependency Scanning** - Automated with Dependabot
- ✅ **Code Scanning** - CodeQL for vulnerability detection
- ✅ **Static Analysis** - Bandit security linting

## Automated Security

- **CodeQL:** Runs on every push and PR
- **Dependabot:** Weekly dependency updates
- **Bandit:** Python security linting in CI
- **Safety:** Known vulnerability checking

## Contact

For security concerns: 101175436+v-giannakopoulos@users.noreply.github.com

For general issues: https://github.com/SaVaGi-eu/receipts-manager/issues
