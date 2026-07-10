"""Tests for the standalone HTTP application routes."""

import json
import urllib.error
import urllib.request


def _get(base_url, path):
    return urllib.request.urlopen(base_url + path, timeout=10)


def test_health_check(base_url):
    """Health endpoint is public and returns 200/ok."""
    resp = _get(base_url, "/health")
    assert resp.status == 200
    assert resp.read() == b"ok"


def test_auth_status(base_url):
    """Auth-status endpoint reports that auth is disabled in tests."""
    resp = _get(base_url, "/api/auth-status")
    assert json.loads(resp.read()) == {"auth_enabled": False}


def test_homepage(base_url):
    """Homepage loads and mentions the app name."""
    resp = _get(base_url, "/")
    assert resp.status == 200
    assert b"receipt" in resp.read().lower()


def test_api_data_endpoint(base_url):
    """/api/data returns the JSON data structure."""
    resp = _get(base_url, "/api/data")
    assert resp.status == 200
    assert resp.headers.get_content_type() == "application/json"
    data = json.loads(resp.read())
    assert "receipts" in data
    assert "items" in data


def test_security_headers_present(base_url):
    """Responses carry the hardening headers added during the security review."""
    resp = _get(base_url, "/api/data")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Content-Security-Policy")


def test_404_error(base_url):
    """Unknown paths return 404."""
    try:
        _get(base_url, "/nonexistent-page-xyz")
        raise AssertionError("expected HTTP 404")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
