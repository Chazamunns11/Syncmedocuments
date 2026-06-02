"""Resilient HTTP with retries and exponential backoff.

A long-running, unattended bot must shrug off transient network failures, rate
limits (HTTP 429) and 5xx blips rather than crashing or — worse — silently
skipping a betting window. This wraps requests with bounded exponential backoff
and honours ``Retry-After``.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

log = logging.getLogger("value_bot.http")

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def request(
    method: str,
    url: str,
    *,
    retries: int = 4,
    backoff: float = 1.0,
    max_backoff: float = 30.0,
    timeout: float = 15.0,
    sleep_fn: Callable[[float], None] = time.sleep,
    session=None,
    **kwargs,
):
    """Perform an HTTP request, retrying on connection errors and retryable
    status codes with exponential backoff. Raises the last error if all
    attempts fail."""
    import requests

    sess = session or requests
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = sess.request(method, url, timeout=timeout, **kwargs)
            if resp.status_code in RETRYABLE_STATUS and attempt < retries:
                wait = _retry_after(resp) or min(max_backoff, backoff * (2 ** attempt))
                log.warning("HTTP %s from %s; retry %d/%d in %.1fs",
                            resp.status_code, url, attempt + 1, retries, wait)
                sleep_fn(wait)
                continue
            return resp
        except Exception as exc:  # ConnectionError, Timeout, etc.
            last_exc = exc
            if attempt >= retries:
                break
            wait = min(max_backoff, backoff * (2 ** attempt))
            log.warning("request error %s (%s); retry %d/%d in %.1fs",
                        type(exc).__name__, url, attempt + 1, retries, wait)
            sleep_fn(wait)
    raise last_exc if last_exc else RuntimeError(f"request to {url} failed")


def get_json(url: str, **kwargs):
    """GET and return parsed JSON, retrying as needed. Returns (json, headers)."""
    resp = request("GET", url, **kwargs)
    resp.raise_for_status()
    return resp.json(), resp.headers


def post_json(url: str, **kwargs):
    """POST and return parsed JSON, retrying as needed. Returns (json, headers)."""
    resp = request("POST", url, **kwargs)
    resp.raise_for_status()
    return resp.json(), resp.headers


def _retry_after(resp) -> Optional[float]:
    val = resp.headers.get("Retry-After")
    if not val:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
