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


def test_login_page_renders_form(base_url):
    """GET /login serves the login form (the template used to be missing -> 500)."""
    resp = _get(base_url, "/login")
    assert resp.status == 200
    assert resp.headers.get_content_type() == "text/html"
    body = resp.read().decode("utf-8")
    assert '<form method="post" action="/login"' in body
    assert 'name="username"' in body
    assert 'name="password"' in body
    assert "__ERROR_BLOCK__" not in body
    assert "<script" not in body.lower()
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "frame-ancestors 'none'" in resp.headers.get("Content-Security-Policy", "")


def test_failed_login_shows_error(base_url):
    """A rejected POST /login re-renders the form with the error message."""
    req = urllib.request.Request(
        base_url + "/login",
        data=b"username=nobody&password=wrong",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=10)
    assert resp.status == 200
    body = resp.read().decode("utf-8")
    assert "Invalid username or password." in body
    assert 'name="password"' in body
    assert resp.headers.get("Content-Security-Policy")


def _head(base_url, path):
    req = urllib.request.Request(base_url + path, method="HEAD")
    return urllib.request.urlopen(req, timeout=10)


def test_head_matches_get_without_body(base_url):
    """HEAD returns GET's status and headers, including Content-Length, but no body."""
    get_resp = _get(base_url, "/login")
    get_body = get_resp.read()
    head_resp = _head(base_url, "/login")
    assert head_resp.status == 200
    assert head_resp.read() == b""
    assert head_resp.headers.get("Content-Length") == str(len(get_body))
    assert head_resp.headers.get("Content-Type") == get_resp.headers.get("Content-Type")
    assert head_resp.headers.get("Content-Security-Policy")


def test_head_unknown_path_is_404(base_url):
    """HEAD goes through the same routing as GET."""
    try:
        _head(base_url, "/nonexistent-page-xyz")
        raise AssertionError("expected HTTP 404")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404


def test_head_does_not_open_folder_picker(base_url, monkeypatch):
    """HEAD /api/browse/path must not trigger the native dialog (the route is POST-only)."""
    import app as app_module

    def fail():
        raise AssertionError("folder picker opened by HEAD")

    monkeypatch.setattr(app_module, "_open_file_dialog", fail)
    try:
        _head(base_url, "/api/browse/path")
        raise AssertionError("expected HTTP 404")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404


def test_404_error(base_url):
    """Unknown paths return 404."""
    try:
        _get(base_url, "/nonexistent-page-xyz")
        raise AssertionError("expected HTTP 404")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404


def _csrf_post(base_url, path, body=b"", ctype="application/json"):
    """POST with a matching double-submit CSRF cookie + header, like the frontend does."""
    req = urllib.request.Request(base_url + path, data=body, method="POST")
    req.add_header("Content-Type", ctype)
    req.add_header("Cookie", "rm_csrf=testtoken")
    req.add_header("X-CSRF-Token", "testtoken")
    return urllib.request.urlopen(req, timeout=10)


def test_browse_path_is_not_reachable_by_get(base_url):
    """The native folder dialog must not be triggerable by a cross-site <img> GET."""
    try:
        _get(base_url, "/api/browse/path")
        raise AssertionError("expected HTTP 404")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404


def test_browse_path_post_requires_csrf_token(base_url):
    req = urllib.request.Request(base_url + "/api/browse/path", data=b"", method="POST")
    try:
        urllib.request.urlopen(req, timeout=10)
        raise AssertionError("expected HTTP 403")
    except urllib.error.HTTPError as exc:
        assert exc.code == 403


def test_settings_rejects_unknown_currency(base_url):
    req = urllib.request.Request(
        base_url + "/api/settings", data=json.dumps({"currency": "<b>x</b>"}).encode(), method="PUT"
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Cookie", "rm_csrf=testtoken")
    req.add_header("X-CSRF-Token", "testtoken")
    try:
        urllib.request.urlopen(req, timeout=10)
        raise AssertionError("expected HTTP 400")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400


def test_login_is_throttled_after_repeated_failures(base_url):
    import app as app_module

    app_module._login_failures.clear()
    codes = []
    for _ in range(app_module._LOGIN_MAX_FAILURES + 1):
        try:
            codes.append(
                _csrf_post(base_url, "/login", b"username=a&password=b", "application/x-www-form-urlencoded").status
            )
        except urllib.error.HTTPError as exc:
            codes.append(exc.code)
    app_module._login_failures.clear()
    assert codes[:-1] == [200] * app_module._LOGIN_MAX_FAILURES
    assert codes[-1] == 429


def test_dev_origins_not_allowed_outside_dev_mode(base_url):
    import app as app_module

    assert "http://localhost:3000" not in app_module.ALLOWED_ORIGINS
