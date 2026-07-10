"""Pytest fixtures for the standalone (Flask-free) HTTP server in app.py.

The application resolves its data directory from the DATA_DIR environment
variable at import time, so each fixture sets DATA_DIR to a temporary directory
and reloads ``config``/``app`` before starting a real ThreadingHTTPServer on an
ephemeral port. Tests then talk to it over HTTP like any external client.
"""

import importlib
import json
import threading
from http.server import ThreadingHTTPServer

import pytest


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Create an isolated data directory and point DATA_DIR at it."""
    d = tmp_path / "data"
    (d / "database" / "backups").mkdir(parents=True)
    (d / "storage" / "_Receipts").mkdir(parents=True)
    (d / "database" / "data.json").write_text(
        json.dumps({"receipts": [], "items": [], "next_id": 1}),
        encoding="utf-8",
    )
    monkeypatch.setenv("DATA_DIR", str(d))
    return d


@pytest.fixture
def base_url(data_dir):
    """Start the real HTTP server on a random port and yield its base URL."""
    import config

    importlib.reload(config)
    import app as app_module

    importlib.reload(app_module)

    from services.receipt_service import ReceiptService

    app_module.service = ReceiptService(
        config.DATA_FILE,
        config.DATA_ROOT,
        config.RECEIPTS_DIR,
        config.STORAGE_DIR,
        config.BACKUP_DIR,
    )

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), app_module.Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
