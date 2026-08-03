"""Turning a Graph API Explorer token into one that lasts.

The token you copy out of Graph API Explorer is short-lived — about an hour.
That is long enough to paste it, see the connection test go green, and believe
the setup is done; the failure arrives later, as a post that silently does not
publish.

The fix is two hops, both documented Graph API calls:

    1. exchange the short-lived token for a long-lived *user* token (60 days)
    2. read /me/accounts with it — the page tokens it returns do not expire

Step 2 also hands back the page's id, which otherwise has to be dug out of the
page's About tab by hand.

Every call takes the app secret. It travels as a query parameter because that is
the contract Graph publishes, over HTTPS, via `params=` so nothing is
hand-spliced into a URL — and it is never logged, here or anywhere else.
"""

from __future__ import annotations

import datetime as dt
import logging

import requests

logger = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com/v19.0"
TIMEOUT = 15


def _error_of(resp: requests.Response) -> str:
    """Facebook's own message beats a status code — it says what to fix."""
    try:
        err = resp.json().get("error", {})
        msg = err.get("message") or ""
        sub = err.get("error_user_msg") or ""
        detail = sub or msg
        if detail:
            return detail
    except Exception:  # noqa: BLE001
        pass
    return f"HTTP {resp.status_code}"


def exchange_long_lived(short_token: str, app_id: str,
                        app_secret: str) -> tuple[str, str]:
    """Short-lived user token → long-lived user token. Returns (token, error)."""
    if not (short_token and app_id and app_secret):
        return "", "ต้องมี App ID, App Secret และ token ปัจจุบันครบทั้งสามอย่าง"
    try:
        resp = requests.get(
            f"{GRAPH}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id.strip(),
                "client_secret": app_secret.strip(),
                "fb_exchange_token": short_token.strip(),
            },
            timeout=TIMEOUT,
        )
    except Exception as e:  # noqa: BLE001
        return "", f"ต่อ Facebook ไม่ได้: {e}"
    if resp.status_code != 200:
        return "", _error_of(resp)
    token = resp.json().get("access_token", "")
    return (token, "") if token else ("", "Facebook ไม่ได้ส่ง token กลับมา")


def list_pages(user_token: str) -> tuple[list[dict], str]:
    """Pages this user administers, each with its own non-expiring token.

    Returns [{id, name, access_token, tasks}], error.
    """
    if not user_token:
        return [], "ยังไม่มี user token"
    try:
        resp = requests.get(
            f"{GRAPH}/me/accounts",
            params={"access_token": user_token.strip(),
                    "fields": "id,name,access_token,tasks"},
            timeout=TIMEOUT,
        )
    except Exception as e:  # noqa: BLE001
        return [], f"ต่อ Facebook ไม่ได้: {e}"
    if resp.status_code != 200:
        return [], _error_of(resp)
    pages = resp.json().get("data", [])
    if not pages:
        return [], ("บัญชีนี้ไม่ได้เป็นแอดมินเพจไหนเลย หรือ token ยังไม่มีสิทธิ์ "
                    "pages_show_list")
    return pages, ""


def instagram_account_for(page_id: str, page_token: str) -> tuple[str, str]:
    """The IG business account linked to a page, if there is one."""
    try:
        resp = requests.get(
            f"{GRAPH}/{page_id}",
            params={"access_token": page_token,
                    "fields": "instagram_business_account"},
            timeout=TIMEOUT,
        )
    except Exception as e:  # noqa: BLE001
        return "", f"ต่อ Facebook ไม่ได้: {e}"
    if resp.status_code != 200:
        return "", _error_of(resp)
    acct = resp.json().get("instagram_business_account") or {}
    return acct.get("id", ""), ""


def describe_token(token: str, app_id: str, app_secret: str) -> tuple[dict, str]:
    """What this token is and when it dies.

    Returns {type, expires_at, expires_text, scopes, valid}, error.
    """
    if not (token and app_id and app_secret):
        return {}, "ต้องมี App ID และ App Secret ถึงจะเช็ค token ได้"
    try:
        resp = requests.get(
            f"{GRAPH}/debug_token",
            params={"input_token": token.strip(),
                    "access_token": f"{app_id.strip()}|{app_secret.strip()}"},
            timeout=TIMEOUT,
        )
    except Exception as e:  # noqa: BLE001
        return {}, f"ต่อ Facebook ไม่ได้: {e}"
    if resp.status_code != 200:
        return {}, _error_of(resp)

    data = resp.json().get("data", {})
    expires = data.get("expires_at", 0) or 0
    # Facebook reports a non-expiring token as expires_at 0, which is the whole
    # point of the exchange — say so rather than printing 1 Jan 1970.
    if not expires:
        text = "ไม่มีวันหมดอายุ"
        when = None
    else:
        when = dt.datetime.fromtimestamp(expires)
        left = when - dt.datetime.now()
        days, hours = left.days, left.seconds // 3600
        if left.total_seconds() <= 0:
            text = f"หมดอายุแล้วเมื่อ {when:%Y-%m-%d %H:%M}"
        elif days:
            text = f"เหลืออีก {days} วัน (หมด {when:%Y-%m-%d %H:%M})"
        else:
            text = f"เหลืออีก {hours} ชั่วโมง (หมด {when:%H:%M น. วันนี้})"
    return {
        "type": data.get("type", ""),
        "valid": bool(data.get("is_valid")),
        "expires_at": when,
        "expires_text": text,
        "scopes": data.get("scopes", []),
    }, ""
