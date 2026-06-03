"""Normalize user-facing filenames from uploads."""

from urllib.parse import unquote


def normalize_filename(name: str) -> str:
    """Decode percent-encoded names (common when files come from download URLs)."""
    if not name:
        return name
    decoded = name
    for _ in range(2):
        if "%" not in decoded:
            break
        try:
            next_decoded = unquote(decoded)
        except Exception:
            break
        if next_decoded == decoded:
            break
        decoded = next_decoded
    return decoded
