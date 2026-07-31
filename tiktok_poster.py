"""TikTok Content Posting API — upload a video from the app.

Flow (FILE_UPLOAD, single chunk):
    query creator info → init the post → PUT the bytes → poll publish status

⚠️ Visibility gate: TikTok restricts *unaudited* API clients to SELF_ONLY posts,
and the target account must be private at post time. Publishing publicly needs
the app to pass TikTok's audit. `describe_limits()` spells this out so the UI can
warn before the owner assumes a post went public.

Auth is a user access token carrying the `video.publish` scope. Tokens are
short-lived (~24h), so the app takes one by paste rather than implementing a
second OAuth flow.
"""

from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://open.tiktokapis.com/v2"
POLL_TIMEOUT_SEC = 300
POLL_INTERVAL_SEC = 5

# Privacy levels TikTok accepts. SELF_ONLY is the only one an unaudited client
# may use; the rest require a passed audit.
PRIVACY_LEVELS = {
    "SELF_ONLY": "🔒 เฉพาะฉัน (ใช้ได้แม้ยังไม่ผ่าน audit)",
    "MUTUAL_FOLLOW_FRIENDS": "👥 เพื่อนที่ติดตามกันเท่านั้น",
    "FOLLOWER_OF_CREATOR": "👤 ผู้ติดตาม",
    "PUBLIC_TO_EVERYONE": "🌍 สาธารณะ (ต้องผ่าน audit ก่อน)",
}


def describe_limits() -> str:
    return (
        "TikTok จำกัดให้แอปที่ยังไม่ผ่าน audit โพสต์ได้เฉพาะ **SELF_ONLY (เฉพาะฉัน)** "
        "และบัญชีต้องตั้งเป็นส่วนตัวขณะโพสต์ · โพสต์ได้ไม่เกิน 5 ผู้ใช้ต่อ 24 ชม. "
        "ถ้าต้องการโพสต์สาธารณะ ต้องยื่นแอปให้ TikTok ตรวจก่อน"
    )


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def creator_info(token: str) -> tuple[dict | None, str]:
    """Query the creator's posting limits. Also a cheap token validity check."""
    if not token:
        return None, "ยังไม่ได้ใส่ TikTok Access Token"
    try:
        resp = requests.post(
            f"{API_BASE}/post/publish/creator_info/query/",
            headers=_headers(token), timeout=30,
        )
        if resp.status_code in (401, 403):
            return None, "Token ไม่ถูกต้องหรือหมดอายุ — ขอ token ใหม่"
        if resp.status_code != 200:
            return None, f"ดึงข้อมูลผู้ใช้ไม่ได้ ({resp.status_code}): {resp.text[:200]}"
        payload = resp.json()
        err = (payload.get("error") or {}).get("code", "ok")
        if err not in ("ok", "", None):
            return None, f"TikTok แจ้ง: {(payload.get('error') or {}).get('message', err)}"
        return payload.get("data", {}), "เชื่อม TikTok สำเร็จ"
    except Exception as e:  # noqa: BLE001
        return None, f"ต่อ TikTok ไม่ได้: {e}"


def post_video(video_bytes: bytes, caption: str, token: str,
               privacy: str = "SELF_ONLY",
               disable_comment: bool = False,
               on_progress=None) -> tuple[bool, str]:
    """Upload and publish a video. Returns (ok, message)."""
    if not token:
        return False, "ยังไม่ได้ใส่ TikTok Access Token"
    if not video_bytes:
        return False, "ไม่มีไฟล์วิดีโอ"

    def _progress(msg: str) -> None:
        if on_progress:
            try:
                on_progress(msg)
            except Exception:  # noqa: BLE001
                pass

    size = len(video_bytes)

    # 1) Initialise the post — TikTok returns a one-time upload URL.
    payload = {
        "post_info": {
            "title": (caption or "")[:2200],
            "privacy_level": privacy if privacy in PRIVACY_LEVELS else "SELF_ONLY",
            "disable_comment": disable_comment,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": size,      # single chunk keeps this simple
            "total_chunk_count": 1,
        },
    }
    try:
        _progress("กำลังเริ่มอัปโหลดไป TikTok...")
        init = requests.post(
            f"{API_BASE}/post/publish/video/init/",
            headers=_headers(token), json=payload, timeout=60,
        )
        if init.status_code in (401, 403):
            return False, "Token ไม่มีสิทธิ์ video.publish หรือหมดอายุแล้ว"
        if init.status_code != 200:
            return False, f"เริ่มอัปโหลดไม่สำเร็จ ({init.status_code}): {init.text[:250]}"
        body = init.json()
        err = body.get("error") or {}
        if err.get("code") not in ("ok", "", None):
            return False, f"TikTok แจ้ง: {err.get('message', err.get('code'))}"
        data = body.get("data", {})
        upload_url = data.get("upload_url")
        publish_id = data.get("publish_id")
        if not upload_url or not publish_id:
            return False, "TikTok ไม่ได้คืน upload_url/publish_id"
    except Exception as e:  # noqa: BLE001
        return False, f"เริ่มอัปโหลดไม่สำเร็จ: {e}"

    # 2) PUT the bytes to the signed URL.
    try:
        _progress(f"กำลังส่งไฟล์ ({size/1024/1024:.1f} MB)...")
        put = requests.put(
            upload_url,
            data=video_bytes,
            headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{size - 1}/{size}",
            },
            timeout=600,
        )
        if put.status_code not in (200, 201, 204):
            return False, f"ส่งไฟล์ไม่สำเร็จ ({put.status_code}): {put.text[:200]}"
    except Exception as e:  # noqa: BLE001
        return False, f"ส่งไฟล์ไม่สำเร็จ: {e}"

    # 3) Poll until TikTok finishes processing.
    waited = 0
    while waited < POLL_TIMEOUT_SEC:
        time.sleep(POLL_INTERVAL_SEC)
        waited += POLL_INTERVAL_SEC
        try:
            status = requests.post(
                f"{API_BASE}/post/publish/status/fetch/",
                headers=_headers(token),
                json={"publish_id": publish_id},
                timeout=30,
            )
            if status.status_code != 200:
                continue
            data = status.json().get("data", {})
            state = data.get("status", "")
            if state in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
                where = ("ส่งเข้ากล่องร่างในแอป TikTok แล้ว"
                         if state == "SEND_TO_USER_INBOX" else "โพสต์สำเร็จ")
                note = " (โหมดเฉพาะฉัน)" if privacy == "SELF_ONLY" else ""
                return True, f"TikTok: {where}{note} ✅"
            if state == "FAILED":
                reason = data.get("fail_reason", "ไม่ทราบสาเหตุ")
                return False, f"TikTok ประมวลผลไม่สำเร็จ: {reason}"
            _progress(f"TikTok กำลังประมวลผล... ({waited} วินาที)")
        except Exception as e:  # noqa: BLE001
            logger.warning("tiktok status poll failed: %s", e)

    return False, "รอ TikTok ประมวลผลนานเกินไป — ตรวจสอบในแอป TikTok อีกครั้ง"
