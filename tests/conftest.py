"""Pytest configuration and fixtures."""

import json
import os
import tempfile

import pytest

# Set test environment variables before importing app
os.environ["TESTING"] = "1"
os.environ["DEBUG"] = "False"


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create subdirectories
    (data_dir / "database").mkdir()
    (data_dir / "backups").mkdir()

    # Create empty database
    db_file = data_dir / "database" / "data.json"
    db_file.write_text(json.dumps({"receipts": [], "warranties": []}))

    return data_dir


@pytest.fixture
def test_storage_dir(tmp_path):
    """Create a temporary storage directory for tests."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def client(test_data_dir, test_storage_dir, monkeypatch):
    """Create a test client for the Flask app."""
    # Set environment variables
    monkeypatch.setenv("DATA_DIR", str(test_data_dir))
    monkeypatch.setenv("STORAGE_DIR", str(test_storage_dir))
    monkeypatch.setenv("TESTING", "1")

    # Import app after setting env vars
    from app import app

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_receipt_data():
    """Sample receipt data for testing."""
    return {
        "id": "test-receipt-001",
        "merchant": "Test Store",
        "date": "2026-03-03",
        "total": 42.50,
        "currency": "€",
        "category": "Groceries",
        "tags": ["food", "monthly"],
        "items": [{"description": "Test Item 1", "price": 20.00}, {"description": "Test Item 2", "price": 22.50}],
    }


@pytest.fixture
def sample_warranty_data():
    """Sample warranty data for testing."""
    return {
        "id": "test-warranty-001",
        "product": "Test Product",
        "manufacturer": "Test Manufacturer",
        "purchase_date": "2026-01-01",
        "expiry_date": "2027-01-01",
        "serial_number": "SN123456",
        "receipt_id": "test-receipt-001",
    }
