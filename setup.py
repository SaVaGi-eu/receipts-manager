"""
py2app setup script for Receipt Manager
Builds a standalone macOS .app bundle
"""

from setuptools import setup

APP = ['app.py']
DATA_FILES = [
    ('templates', ['templates/index.html']),
    ('static', ['static/']),
]

OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'flask',
        'pytesseract',
        'PIL',
        'werkzeug',
        'jinja2',
        'click',
        'itsdangerous',
        'markupsafe',
        'easyocr',
        'pdf2image',
    ],
    'includes': [
        'ocr_service',
        'config',
    ],
    'excludes': [
        'matplotlib',
        'numpy.distutils',
        'scipy',
        'tkinter',
        'test',
        'unittest',
    ],
    'plist': {
        'CFBundleName': 'Receipt Manager',
        'CFBundleDisplayName': 'Receipt Manager',
        'CFBundleIdentifier': 'eu.savagi.receipts-manager',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Receipt Image',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': ['public.image'],
            }
        ],
    },
    'site_packages': True,
}

setup(
    app=APP,
    name='ReceiptManager',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
