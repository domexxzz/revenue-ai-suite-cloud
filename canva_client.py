"""Canva Connect API client — brand-template autofill and asset upload.

Two capability tiers, because Canva gates them differently:

  • Autofill + Brand Templates  → requires a **Canva Enterprise** subscription.
    This is the carousel/poster factory: one branded template, filled with
    different copy and images, exported as PNG/PDF.

  • Assets + Designs + Exports  → available on ordinary paid plans.
    Fallback path: push a generated image into Canva as an asset so the owner
    can drop it into a design by hand.

`capabilities()` probes which tier the connected account actually has, so the UI
can show the right thing instead of failing at the point of use.

Auth is OAuth 2.0 with PKCE. Streamlit has no callback server here, so the flow
is the manual variant: show the authorize URL, the user approves, then pastes the
redirected URL back and we exchange the code for tokens.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import time
from urllib.parse import urlencode, urlparse, parse_qs

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.canva.com/rest/v1"
AUTH_URL = "https://www.canva.com/api/oauth/authorize"
TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"

# Scopes needed for the two tiers above. Canva rejects scopes the integration
# wasn't configured for, so keep this list in sync with the app's settings.
SCOPES = [
    "design:content:read",
    "design:content:write",
    "design:meta:read",
    "brandtemplate:meta:read",
    "brandtemplate:content:read",
    "asset:read",
    "asset:write",
]

POLL_TIMEOUT_SEC = 180
POLL_INTERVAL_SEC = 2


# ── PKCE / OAuth ────────────────────────────────────────────────────────────────

def make_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for a PKCE flow."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def build_auth_url(client_id: str, redirect_uri: str, code_challenge: str,
                   state: str = "") -> str:
    """Authorization URL the owner opens to grant access."""
    params = {
        "code_challenge": code_challenge,
        "code_challenge_method": "s256",
        "scope": " ".join(SCOPES),
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state or secrets.token_urlsafe(16),
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def extract_code(redirected_url: str) -> str:
    """Pull the ?code= value out of the URL Canva redirected the owner to."""
    try:
        qs = parse_qs(urlparse(redirected_url.strip()).query)
        return (qs.get("code") or [""])[0]
    except Exception:  # noqa: BLE001
        return ""


def exchange_code(client_id: str, client_secret: str, code: str,
                  code_verifier: str, redirect_uri: str) -> tuple[dict | None, str]:
    """Swap an authorization code for tokens. Returns (token_dict, message)."""
    try:
        resp = requests.post(
            TOKEN_URL,
            auth=(client_id, client_secret),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return None, f"แลก token ไม่สำเร็จ ({resp.status_code}): {resp.text[:200]}"
        data = resp.json()
        data["obtained_at"] = time.time()
        return data, "เชื่อม Canva สำเร็จ"
    except Exception as e:  # noqa: BLE001
        return None, f"แลก token ไม่สำเร็จ: {e}"


def refresh_token(client_id: str, client_secret: str, refresh: str) -> tuple[dict | None, str]:
    """Canva access tokens are short-lived; trade the refresh token for a new one."""
    try:
        resp = requests.post(
            TOKEN_URL,
            auth=(client_id, client_secret),
            data={"grant_type": "refresh_token", "refresh_token": refresh},
            timeout=30,
        )
        if resp.status_code != 200:
            return None, f"ต่ออายุ token ไม่สำเร็จ ({resp.status_code})"
        data = resp.json()
        data["obtained_at"] = time.time()
        return data, "ต่ออายุ token แล้ว"
    except Exception as e:  # noqa: BLE001
        return None, f"ต่ออายุ token ไม่สำเร็จ: {e}"


def token_expired(token: dict, skew_sec: int = 120) -> bool:
    """True when the access token is at (or near) its expiry."""
    if not token:
        return True
    obtained = token.get("obtained_at", 0)
    expires_in = token.get("expires_in", 0)
    if not obtained or not expires_in:
        return False
    return time.time() >= (obtained + expires_in - skew_sec)


# ── Low-level request helper ────────────────────────────────────────────────────

def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def _get(path: str, access_token: str, **kwargs):
    return requests.get(f"{API_BASE}{path}", headers=_headers(access_token),
                        timeout=60, **kwargs)


def _post(path: str, access_token: str, **kwargs):
    return requests.post(f"{API_BASE}{path}", headers=_headers(access_token),
                         timeout=60, **kwargs)


# ── Capability probe ────────────────────────────────────────────────────────────

def capabilities(access_token: str) -> dict:
    """Probe what this account can actually do.

    Autofill/brand templates need Canva Enterprise; a non-Enterprise account gets
    401/403 on those endpoints. Probing up front means the UI can say so plainly
    rather than blowing up mid-carousel.
    """
    result = {"connected": False, "brand_templates": False, "assets": False, "note": ""}
    try:
        me = _get("/users/me", access_token)
        result["connected"] = me.status_code == 200
        if not result["connected"]:
            result["note"] = f"token ใช้ไม่ได้ ({me.status_code})"
            return result
    except Exception as e:  # noqa: BLE001
        result["note"] = f"ต่อ Canva ไม่ได้: {e}"
        return result

    try:
        bt = _get("/brand-templates", access_token, params={"limit": 1})
        if bt.status_code == 200:
            result["brand_templates"] = True
        elif bt.status_code in (401, 403):
            result["note"] = "บัญชีนี้ไม่ใช่ Canva Enterprise — ใช้ Autofill/Brand Template ไม่ได้"
        else:
            result["note"] = f"เช็ค brand templates ไม่ได้ ({bt.status_code})"
    except Exception as e:  # noqa: BLE001
        result["note"] = f"เช็ค brand templates ไม่ได้: {e}"

    result["assets"] = True  # asset upload is available on ordinary paid plans
    return result


# ── Brand templates + autofill (Enterprise) ─────────────────────────────────────

def list_brand_templates(access_token: str, limit: int = 50) -> tuple[list[dict], str]:
    """List brand templates the connected user can autofill."""
    try:
        resp = _get("/brand-templates", access_token, params={"limit": limit})
        if resp.status_code in (401, 403):
            return [], "บัญชีนี้ไม่มีสิทธิ์ Brand Template (ต้องเป็น Canva Enterprise)"
        if resp.status_code != 200:
            return [], f"ดึง brand templates ไม่ได้ ({resp.status_code})"
        items = resp.json().get("items", [])
        return [{"id": t.get("id"), "title": t.get("title", "(ไม่มีชื่อ)")} for t in items], ""
    except Exception as e:  # noqa: BLE001
        return [], f"ดึง brand templates ไม่ได้: {e}"


def get_template_dataset(access_token: str, template_id: str) -> tuple[dict, str]:
    """Fields this template exposes for autofill: {field_name: {"type": ...}}."""
    try:
        resp = _get(f"/brand-templates/{template_id}/dataset", access_token)
        if resp.status_code != 200:
            return {}, f"ดึง dataset ไม่ได้ ({resp.status_code})"
        return resp.json().get("dataset", {}), ""
    except Exception as e:  # noqa: BLE001
        return {}, f"ดึง dataset ไม่ได้: {e}"


def build_autofill_data(fields: dict, values: dict) -> dict:
    """Shape {field: value} into the typed payload the autofill endpoint expects."""
    data: dict = {}
    for name, meta in (fields or {}).items():
        if name not in values:
            continue
        ftype = (meta or {}).get("type", "text")
        if ftype == "image":
            data[name] = {"type": "image", "asset_id": values[name]}
        elif ftype == "chart":
            data[name] = {"type": "chart", "chart_data": values[name]}
        else:
            data[name] = {"type": "text", "text": str(values[name])}
    return data


def autofill(access_token: str, template_id: str, data: dict,
             title: str = "") -> tuple[dict | None, str]:
    """Run an autofill job and wait for the finished design."""
    payload = {"brand_template_id": template_id, "data": data}
    if title:
        payload["title"] = title
    try:
        resp = _post("/autofills", access_token, json=payload)
        if resp.status_code in (401, 403):
            return None, "บัญชีนี้ไม่มีสิทธิ์ Autofill (ต้องเป็น Canva Enterprise)"
        if resp.status_code not in (200, 202):
            return None, f"สร้าง autofill ไม่สำเร็จ ({resp.status_code}): {resp.text[:200]}"
        job = resp.json().get("job", {})
        job_id = job.get("id")
        if not job_id:
            return None, "Canva ไม่ได้คืนหมายเลขงานกลับมา"
    except Exception as e:  # noqa: BLE001
        return None, f"สร้าง autofill ไม่สำเร็จ: {e}"

    waited = 0
    while waited < POLL_TIMEOUT_SEC:
        time.sleep(POLL_INTERVAL_SEC)
        waited += POLL_INTERVAL_SEC
        try:
            poll = _get(f"/autofills/{job_id}", access_token)
            if poll.status_code != 200:
                continue
            job = poll.json().get("job", {})
            status = job.get("status")
            if status == "success":
                return job.get("result", {}).get("design", {}), "สร้างดีไซน์สำเร็จ"
            if status == "failed":
                err = (job.get("error") or {}).get("message", "ไม่ทราบสาเหตุ")
                return None, f"autofill ล้มเหลว: {err}"
        except Exception as e:  # noqa: BLE001
            logger.warning("autofill poll failed: %s", e)
    return None, "รอ autofill นานเกินไป — ลองใหม่อีกครั้ง"


# ── Assets (any paid plan) ──────────────────────────────────────────────────────

def upload_asset(access_token: str, file_bytes: bytes, name: str) -> tuple[str, str]:
    """Upload an image into Canva. Returns (asset_id, message)."""
    try:
        meta = base64.b64encode(name.encode()).decode()
        resp = requests.post(
            f"{API_BASE}/asset-uploads",
            headers={
                **_headers(access_token),
                "Content-Type": "application/octet-stream",
                "Asset-Upload-Metadata": '{"name_base64":"%s"}' % meta,
            },
            data=file_bytes,
            timeout=180,
        )
        if resp.status_code not in (200, 202):
            return "", f"อัปโหลดไม่สำเร็จ ({resp.status_code}): {resp.text[:200]}"
        job = resp.json().get("job", {})
        if job.get("status") == "success":
            return job.get("asset", {}).get("id", ""), "อัปโหลดสำเร็จ"
        job_id = job.get("id")
    except Exception as e:  # noqa: BLE001
        return "", f"อัปโหลดไม่สำเร็จ: {e}"

    waited = 0
    while waited < POLL_TIMEOUT_SEC:
        time.sleep(POLL_INTERVAL_SEC)
        waited += POLL_INTERVAL_SEC
        try:
            poll = _get(f"/asset-uploads/{job_id}", access_token)
            if poll.status_code != 200:
                continue
            job = poll.json().get("job", {})
            if job.get("status") == "success":
                return job.get("asset", {}).get("id", ""), "อัปโหลดสำเร็จ"
            if job.get("status") == "failed":
                return "", "อัปโหลดล้มเหลว"
        except Exception as e:  # noqa: BLE001
            logger.warning("asset poll failed: %s", e)
    return "", "รออัปโหลดนานเกินไป"


# ── Export ──────────────────────────────────────────────────────────────────────

def export_design(access_token: str, design_id: str,
                  fmt: str = "png") -> tuple[list[str], str]:
    """Export a design. Returns (download_urls, message)."""
    payload = {"design_id": design_id, "format": {"type": fmt}}
    try:
        resp = _post("/exports", access_token, json=payload)
        if resp.status_code not in (200, 202):
            return [], f"สั่ง export ไม่สำเร็จ ({resp.status_code})"
        job = resp.json().get("job", {})
        job_id = job.get("id")
        if not job_id:
            return [], "Canva ไม่ได้คืนหมายเลข export"
    except Exception as e:  # noqa: BLE001
        return [], f"สั่ง export ไม่สำเร็จ: {e}"

    waited = 0
    while waited < POLL_TIMEOUT_SEC:
        time.sleep(POLL_INTERVAL_SEC)
        waited += POLL_INTERVAL_SEC
        try:
            poll = _get(f"/exports/{job_id}", access_token)
            if poll.status_code != 200:
                continue
            job = poll.json().get("job", {})
            if job.get("status") == "success":
                return job.get("urls", []), "export สำเร็จ"
            if job.get("status") == "failed":
                return [], "export ล้มเหลว"
        except Exception as e:  # noqa: BLE001
            logger.warning("export poll failed: %s", e)
    return [], "รอ export นานเกินไป"


def download(url: str) -> bytes | None:
    """Fetch an exported file. Canva export URLs are pre-signed and short-lived."""
    try:
        resp = requests.get(url, timeout=180)
        resp.raise_for_status()
        return resp.content
    except Exception as e:  # noqa: BLE001
        logger.warning("download failed: %s", e)
        return None


def get_credentials() -> tuple[str, str, str]:
    """Read Canva app credentials from Streamlit secrets or the environment."""
    client_id = client_secret = redirect_uri = ""
    try:
        import streamlit as st
        cfg = st.secrets.get("canva", {})
        client_id = cfg.get("client_id", "")
        client_secret = cfg.get("client_secret", "")
        redirect_uri = cfg.get("redirect_uri", "")
    except Exception:  # noqa: BLE001
        pass
    client_id = client_id or os.getenv("CANVA_CLIENT_ID", "")
    client_secret = client_secret or os.getenv("CANVA_CLIENT_SECRET", "")
    redirect_uri = redirect_uri or os.getenv("CANVA_REDIRECT_URI", "http://127.0.0.1:8502/")
    return client_id, client_secret, redirect_uri
