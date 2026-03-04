"""Tests for OCR service."""

import os
from unittest.mock import Mock, patch

import pytest


def test_ocr_service_import():
    """Test that OCR service can be imported."""
    import ocr_service

    assert ocr_service is not None


def test_check_dependencies():
    """Test dependency checking."""
    from ocr_service import check_dependencies

    # This should return a dict or similar
    deps = check_dependencies()
    assert isinstance(deps, dict)
    assert "tesseract" in deps or "easyocr" in deps


@patch("ocr_service.pytesseract")
def test_tesseract_ocr_mock(mock_pytesseract):
    """Test Tesseract OCR with mock."""
    from ocr_service import perform_ocr_tesseract

    # Mock Tesseract to return test text
    mock_pytesseract.image_to_string.return_value = "Test Receipt\nTotal: $42.00"

    # Create a dummy image path (doesn't need to exist with mock)
    result = perform_ocr_tesseract("/fake/path/to/image.jpg")

    assert "Test Receipt" in result
    assert "42.00" in result


def test_ocr_language_config():
    """Test OCR language configuration."""
    import ocr_service

    # Check if language configuration exists
    assert hasattr(ocr_service, "OCR_LANGUAGE") or hasattr(ocr_service, "get_ocr_language")
