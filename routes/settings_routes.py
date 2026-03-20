"""
Settings route handlers (RM-115).
Each function receives the ReceiptService instance and returns
(status_code: int, body: dict) for the caller to serialise.
"""

from typing import Dict, Tuple


def handle_get_settings(service) -> Tuple[int, Dict]:
    """GET /api/settings — return current app-level settings."""
    return 200, service.get_settings()


def handle_put_settings(service, updates: Dict) -> Tuple[int, Dict]:
    """PUT /api/settings — persist allowed settings fields and return updated values."""
    try:
        settings = service.update_settings(updates)
        return 200, settings
    except Exception:
        return 500, {"success": False, "error": "Internal server error"}
