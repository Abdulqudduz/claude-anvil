"""HTTP policy shared by every outbound client (OpenAlex and PDF downloads)."""

from __future__ import annotations

import httpx


def is_transient(exc: BaseException) -> bool:
    """True for failures worth retrying: connection errors, 429, and 5xx.

    Every other 4xx (403 paywall, 404, 400) is permanent; retrying only burns
    time and, for OpenAlex, budget.
    """
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return False
