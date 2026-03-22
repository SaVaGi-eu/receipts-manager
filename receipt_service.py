"""
Backward-compatibility shim (RM-115).
The implementation has moved to services/receipt_service.py.
This module re-exports everything so existing external imports keep working.
"""

from services.receipt_service import (
    ReceiptService,
    calculate_guarantee_end_date,
    format_date_for_filename,
    safe_move_file,
    safe_resolve_within,
    sanitize_filename,
    sanitize_full_filename,
    validate_path_within_root,
)

__all__ = [
    "ReceiptService",
    "calculate_guarantee_end_date",
    "format_date_for_filename",
    "safe_move_file",
    "safe_resolve_within",
    "sanitize_filename",
    "sanitize_full_filename",
    "validate_path_within_root",
]
