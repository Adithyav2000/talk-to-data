"""In-memory TTL cache for report and data-call results.

Genie answers are slow and the underlying data changes at most daily, so a
successful first-question result is reused for REPORT_CACHE_TTL_HOURS. The cache
lives in process memory: it is cleared on restart and is per instance.
"""

import re
import threading
import time
from datetime import datetime, timezone

import config

_lock = threading.Lock()
_store: dict[str, tuple[float, dict]] = {}


def make_key(kind: str, *parts: str) -> str:
    norm = [re.sub(r"\s+", " ", str(p)).strip().lower() for p in parts]
    return "|".join([kind, *norm])


def cacheable(res: dict) -> bool:
    """Only cache real answers: no errors, and tabular data (not a clarifying question)."""
    return not res.get("error") and bool(res.get("columns")) and bool(res.get("rows"))


def get(key: str) -> dict | None:
    ttl = config.REPORT_CACHE_TTL_HOURS * 3600
    with _lock:
        hit = _store.get(key)
        if not hit:
            return None
        stored_at, value = hit
        if time.time() - stored_at > ttl:
            del _store[key]
            return None
    return {
        **value,
        "cached": True,
        "cachedAt": datetime.fromtimestamp(stored_at, timezone.utc).isoformat(),
    }


def put(key: str, value: dict) -> None:
    with _lock:
        _store[key] = (time.time(), value)
        if len(_store) > config.REPORT_CACHE_MAX:
            now, ttl = time.time(), config.REPORT_CACHE_TTL_HOURS * 3600
            for k in [k for k, (t, _) in _store.items() if now - t > ttl]:
                del _store[k]
            while len(_store) > config.REPORT_CACHE_MAX:  # still too big: drop oldest
                del _store[min(_store, key=lambda k: _store[k][0])]


def clear() -> int:
    with _lock:
        n = len(_store)
        _store.clear()
        return n
