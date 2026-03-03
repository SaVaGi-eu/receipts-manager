#!/usr/bin/env python3
"""
Dependency Update Checker - Informational Only

Checks if newer versions of installed packages are available on PyPI.
Displays recommendations but performs no installations.
"""

import sys
import json
from urllib.request import urlopen, Request
from urllib.error import URLError
import importlib.metadata

# Core dependencies to check
DEPENDENCIES = [
    'pdf2image',
    'easyocr',
    'Pillow',
    'torch',
    'torchvision',
    'opencv-python'
]

def get_installed_version(package_name):
    """Get currently installed version of a package."""
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None

def get_latest_version(package_name):
    """Get latest version from PyPI."""
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        req = Request(url, headers={'User-Agent': 'receipts-manager/1.0'})
        with urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
            return data['info']['version']
    except (URLError, KeyError, json.JSONDecodeError):
        return None

def compare_versions(current, latest):
    """Simple version comparison (works for semantic versioning)."""
    def normalize(v):
        return [int(x) for x in v.split('.')[:3] if x.isdigit()]
    
    try:
        c = normalize(current)
        l = normalize(latest)
        return l > c
    except (ValueError, AttributeError):
        return False

def main():
    print("\n🔍 Checking for dependency updates...\n")
    
    updates_available = []
    not_installed = []
    
    for package in DEPENDENCIES:
        installed = get_installed_version(package)
        
        if installed is None:
            not_installed.append(package)
            continue
        
        print(f"  Checking {package}... ", end='', flush=True)
        latest = get_latest_version(package)
        
        if latest is None:
            print("⚠️  Could not check")
            continue
        
        if compare_versions(installed, latest):
            print(f"📦 {installed} → {latest} (update available)")
            updates_available.append((package, installed, latest))
        else:
            print(f"✅ {installed} (up to date)")
    
    print()
    
    # Summary
    if not_installed:
        print("❌ Missing packages:")
        for pkg in not_installed:
            print(f"   - {pkg}")
        print(f"\n💡 Run: pip3 install --user {' '.join(not_installed)}\n")
    
    if updates_available:
        print("📦 Updates available:")
        for pkg, current, latest in updates_available:
            print(f"   - {pkg}: {current} → {latest}")
        
        packages_to_update = ' '.join([pkg for pkg, _, _ in updates_available])
        print(f"\n💡 To update, run:\n   pip3 install --user --upgrade {packages_to_update}\n")
    
    if not updates_available and not not_installed:
        print("✅ All dependencies are up to date!\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCheck cancelled.\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error checking dependencies: {e}\n")
        sys.exit(1)
