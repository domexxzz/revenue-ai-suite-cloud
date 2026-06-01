"""Real platform posting — LINE OA and Facebook."""
from __future__ import annotations
import requests
import logging

logger = logging.getLogger(__name__)


def post_line_oa(message: str, token: str) -> tuple[bool, str]:
    """Broadcast message to all LINE OA followers."""
    if not token:
        return False, "ไม่มี LINE OA Token"
    try:
        resp = requests.post(
            "https://api.line.me/v2/bot/message/broadcast",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"messages": [{"type": "text", "text": message[:5000]}]},
            timeout=15,
        )
        if resp.status_code == 200:
            return True, "ส่งถึง LINE OA followers แล้ว ✅"
        return False, f"Error {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, f"Error: {e}"


def post_facebook(message: str, token: str, page_id: str) -> tuple[bool, str]:
    """Post to Facebook Page feed."""
    if not token or not page_id:
        return False, "ไม่มี Facebook Token หรือ Page ID"
    try:
        resp = requests.post(
            f"https://graph.facebook.com/v19.0/{page_id}/feed",
            params={"access_token": token},
            json={"message": message},
            timeout=15,
        )
        if resp.status_code == 200:
            post_id = resp.json().get("id", "")
            return True, f"โพสต์ Facebook สำเร็จ ✅ (ID: {post_id})"
        return False, f"Error {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, f"Error: {e}"


def test_line_token(token: str) -> tuple[bool, str]:
    """Verify LINE OA token is valid."""
    try:
        resp = requests.get(
            "https://api.line.me/v2/bot/info",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            name = resp.json().get("displayName", "Unknown")
            return True, f"LINE OA: {name}"
        return False, f"Token ไม่ถูกต้อง ({resp.status_code})"
    except Exception as e:
        return False, f"Error: {e}"
