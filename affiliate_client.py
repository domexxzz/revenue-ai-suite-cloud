"""affiliate_client.py — REST client to the Affiliate Autopilot FastAPI backend.

The unified app uses ai-revenue-intelligence (Streamlit) as the front-end and the
affiliate-autopilot (FastAPI + Docker, default port 8088) as the heavy engine for
Shopee Food scraping, AI video generation, multi-platform posting and A/B auto-optimize.

Every call is **offline-safe**: it returns ``(ok: bool, data_or_error)`` and never
raises, so the Streamlit UI stays usable when the backend container is not running.
"""
from __future__ import annotations

import os

import requests

DEFAULT_BASE = "https://busload-uncloak-rehydrate.ngrok-free.dev"


def base_url() -> str:
    """Resolve backend base URL. Priority: session override → secrets → env → default."""
    try:
        import streamlit as st

        v = st.session_state.get("aff_base_url")
        if v:
            return str(v).rstrip("/")
        sv = st.secrets.get("affiliate", {}).get("base_url", "")
        if sv:
            return str(sv).rstrip("/")
    except Exception:
        pass
    return (os.getenv("AFFILIATE_BACKEND_URL") or DEFAULT_BASE).rstrip("/")


def api_token() -> str:
    """Shared token for the backend (when it runs behind a public Funnel).
    Priority: session override → secrets → env. Empty = backend has no auth."""
    try:
        import streamlit as st

        v = st.session_state.get("aff_token")
        if v:
            return str(v)
        sv = st.secrets.get("affiliate", {}).get("token", "")
        if sv:
            return str(sv)
    except Exception:
        pass
    return os.getenv("AFFILIATE_BACKEND_TOKEN", "")


def _req(method: str, path: str, timeout: int = 20, **kw) -> tuple[bool, object]:
    url = base_url() + path
    headers = dict(kw.pop("headers", {}) or {})
    # skip the ngrok free-tier browser interstitial so API calls return JSON
    headers.setdefault("ngrok-skip-browser-warning", "true")
    tok = api_token()
    if tok:
        headers["X-API-Token"] = tok
    try:
        r = requests.request(method, url, timeout=timeout, headers=headers, **kw)
        if r.status_code >= 400:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        try:
            return True, r.json()
        except ValueError:
            return True, r.text
    except requests.exceptions.ConnectionError:
        return False, "OFFLINE"
    except requests.exceptions.Timeout:
        return False, "TIMEOUT"
    except Exception as e:  # pragma: no cover - defensive
        return False, f"ERR: {e}"


# ── reads ────────────────────────────────────────────────────────────────────

def health() -> tuple[bool, object]:
    return _req("GET", "/health", timeout=4)


def is_online() -> bool:
    ok, _ = health()
    return ok


def dashboard() -> tuple[bool, object]:
    return _req("GET", "/api/dashboard")


def keys_status() -> tuple[bool, object]:
    return _req("GET", "/api/keys/status")


def system_status() -> tuple[bool, object]:
    return _req("GET", "/api/system")


def list_stores(status: str | None = None) -> tuple[bool, object]:
    params = {"status": status} if status else None
    return _req("GET", "/api/stores", params=params)


def get_content(store_id: int) -> tuple[bool, object]:
    return _req("GET", f"/api/content/{store_id}")


def list_posts() -> tuple[bool, object]:
    return _req("GET", "/api/posts")


def abtest(store_id: int) -> tuple[bool, object]:
    return _req("GET", f"/api/abtest/{store_id}")


def progress() -> tuple[bool, object]:
    return _req("GET", "/api/progress")


def scrape_status() -> tuple[bool, object]:
    return _req("GET", "/api/scrape/status")


# ── writes / actions ─────────────────────────────────────────────────────────

def scrape(keyword: str | None = None, limit: int | None = None) -> tuple[bool, object]:
    params: dict[str, object] = {}
    if keyword:
        params["keyword"] = keyword
    if limit:
        params["limit"] = limit
    return _req("POST", "/api/scrape", params=params, timeout=60)


def run_all(limit: int = 20) -> tuple[bool, object]:
    return _req("POST", "/api/run-all", params={"limit": limit}, timeout=60)


def run_store(store_id: int) -> tuple[bool, object]:
    return _req("POST", f"/api/stores/{store_id}/run", timeout=60)


def add_store(
    name: str,
    area: str = "",
    menu: list[str] | None = None,
    shopee_url: str = "",
    affiliate_link: str = "",
    rating: float = 0.0,
    review_count: int = 0,
) -> tuple[bool, object]:
    payload = {
        "name": name,
        "area": area,
        "menu": menu or [],
        "shopee_url": shopee_url,
        "affiliate_link": affiliate_link,
        "rating": rating,
        "review_count": review_count,
    }
    return _req("POST", "/api/stores/add", json=payload, timeout=30)


def system_toggle(enable: bool) -> tuple[bool, object]:
    return _req("POST", "/api/system/toggle", params={"enable": str(enable).lower()})


def system_autopilot(enable: bool) -> tuple[bool, object]:
    return _req("POST", "/api/system/autopilot", params={"enable": str(enable).lower()})


def auto_optimize() -> tuple[bool, object]:
    return _req("POST", "/api/auto-optimize", timeout=30)


def simulate_metrics() -> tuple[bool, object]:
    return _req("POST", "/api/metrics/simulate", timeout=30)


def restaurant_reel(store_id: int, voice: str = "male") -> tuple[bool, object]:
    """Ask the backend to produce an AI promo video (montage reel) for a restaurant."""
    return _req("POST", f"/api/stores/{store_id}/restaurant-reel", params={"voice": voice}, timeout=60)


def media_url(path_or_rel: str) -> str:
    """Turn a backend media path ('/media/x.mp4') into an absolute URL the browser can load."""
    if not path_or_rel:
        return ""
    if path_or_rel.startswith("http"):
        return path_or_rel
    if not path_or_rel.startswith("/"):
        path_or_rel = "/" + path_or_rel
    return base_url() + path_or_rel
