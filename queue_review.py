"""Letting the approval queue look at the file instead of its name.

The queue has been scoring clips off their filename. That works because Flow
names each download after the prompt behind it, so the *intended* scene is
usually recoverable — but it says nothing about whether the clip that came back
actually shows that scene. A prompt asking for a gym at dawn and a clip that
rendered a bathroom at night score identically.

This module sends the file itself. The score it returns is about fit with the
brand as Mandala AI describes it, not a prediction of engagement, and the prompt
says so explicitly — a reviewer about to publish something needs the difference.

Provider support is not uniform and pretending otherwise would produce silent
failures:

    image   Gemini and Claude
    video   Gemini only — Claude's API takes no video
    text    either, no vision involved

Callers get `can_review()` to ask before spending anything.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

IMAGE_MIME_PREFIX = "image/"
VIDEO_MIME_PREFIX = "video/"

# Inline media travels base64 inside the request body. Gemini's ceiling for an
# inline request is 20MB total; a clip near that inflates past it, so the cap is
# set below the limit rather than at it. Flow clips land around 2-3MB.
MAX_IMAGE_BYTES = 6 * 1024 * 1024
MAX_VIDEO_BYTES = 15 * 1024 * 1024

REVIEW_SYSTEM = (
    "คุณเป็นผู้ตรวจคอนเทนต์ของแบรนด์ ดูไฟล์ที่ได้รับแล้วประเมินว่าเหมาะจะโพสต์ไหม\n"
    "กติกาสำคัญ:\n"
    "- พูดถึงเฉพาะสิ่งที่เห็นจริงในไฟล์ ห้ามเดาสิ่งที่มองไม่เห็น\n"
    "- คะแนน fit คือความเข้ากับแบรนด์ตามบริบทที่ให้มา ไม่ใช่การทำนายยอด engagement\n"
    "- ถ้าบริบทแบรนด์บอกว่าสินค้าเป็นรูปทรงหนึ่ง แต่ในไฟล์เป็นอีกรูปทรง ให้ถือเป็นปัญหาใหญ่\n"
    "- ตอบเป็นภาษาไทย และตอบเป็น JSON เท่านั้น ไม่ต้องมีคำอธิบายนอก JSON\n"
    "รูปแบบ JSON:\n"
    '{"fit": 1-5, "seen": "สิ่งที่เห็นในไฟล์ 1-2 ประโยค", '
    '"scene": "ชื่อฉาก/หมวดสั้น ๆ", '
    '"strengths": ["ข้อดี"], "fixes": ["สิ่งที่ควรแก้"], '
    '"risk": "ความเสี่ยงหรือสิ่งที่ขัดกับแบรนด์ ถ้าไม่มีให้เป็นค่าว่าง", '
    '"verdict": "post" หรือ "fix" หรือ "reject"}'
)

VERDICT_THAI = {
    "post": ("✅ โพสต์ได้", "ok"),
    "fix": ("🛠️ ควรแก้ก่อน", "on"),
    "reject": ("🚫 ไม่ควรโพสต์", ""),
}


@dataclass(frozen=True)
class Review:
    fit: int
    seen: str
    scene: str
    strengths: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)
    risk: str = ""
    verdict: str = "fix"
    provider: str = ""


def kind_of(mime: str) -> str:
    mime = (mime or "").lower()
    if mime.startswith(IMAGE_MIME_PREFIX):
        return "image"
    if mime.startswith(VIDEO_MIME_PREFIX):
        return "video"
    if mime.startswith("text/"):
        return "text"
    return "other"


def size_limit(mime: str) -> int:
    return MAX_VIDEO_BYTES if kind_of(mime) == "video" else MAX_IMAGE_BYTES


def can_review(mime: str, api_key: str, provider: str = "auto") -> tuple[bool, str]:
    """(allowed, reason). The reason is shown to the reviewer when it is False."""
    kind = kind_of(mime)
    if kind == "other":
        return False, "ยังตรวจไฟล์ชนิดนี้ไม่ได้"
    if not (api_key or "").strip():
        return False, "ต้องใส่ key Gemini หรือ Claude ที่หน้า ⚙️ ตั้งค่า ก่อนถึงจะดูไฟล์ได้"

    import ai_provider
    if provider in ("auto", "", None):
        provider = ai_provider.detect_provider(api_key)
    if provider not in ("gemini", "claude"):
        return False, "โหมด Local ดูไฟล์ไม่ได้ — ใส่ key Gemini หรือ Claude ที่ ⚙️ ตั้งค่า"
    if kind == "video" and provider != "gemini":
        return False, "Claude รับวิดีโอไม่ได้ — ใช้ key Gemini ถ้าอยากให้ตรวจคลิป"
    return True, ""


def _parse(raw: str) -> Review | None:
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None

    def as_list(v) -> list[str]:
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return [str(v).strip()] if v else []

    try:
        fit = int(float(data.get("fit", 0)))
    except (TypeError, ValueError):
        fit = 0
    verdict = str(data.get("verdict", "fix")).strip().lower()
    return Review(
        fit=max(0, min(5, fit)),
        seen=str(data.get("seen", "")).strip(),
        scene=str(data.get("scene", "")).strip(),
        strengths=as_list(data.get("strengths")),
        fixes=as_list(data.get("fixes")),
        risk=str(data.get("risk", "") or "").strip(),
        verdict=verdict if verdict in VERDICT_THAI else "fix",
    )


def review_file(name: str, mime: str, data: bytes, brand_context: str = "",
                api_key: str = "", provider: str = "auto",
                platform: str = "") -> tuple[Review | None, str]:
    """Look at one queued file. Returns (review, error message).

    Exactly one of the two is meaningful — a caller that gets None has a message
    worth showing, and a caller that gets a Review can ignore the second value.
    """
    ok, why = can_review(mime, api_key, provider)
    if not ok:
        return None, why

    limit = size_limit(mime)
    if len(data) > limit:
        return None, (f"ไฟล์ใหญ่ {len(data)/1024/1024:.1f} MB — "
                      f"ตรวจได้ไม่เกิน {limit // 1024 // 1024} MB")

    import ai_provider
    if provider in ("auto", "", None):
        provider = ai_provider.detect_provider(api_key)

    where = f" ไฟล์นี้จะลง {platform}" if platform else ""
    ask = (
        f"ตรวจไฟล์ชื่อ {name} ว่าเหมาะจะโพสต์ให้แบรนด์นี้ไหม{where}\n\n"
        f"บริบทแบรนด์:\n{brand_context[:2500] or '(ไม่มีบริบทแบรนด์ — ประเมินจากคุณภาพงานทั่วไป)'}"
    )

    if kind_of(mime) == "text":
        body = data.decode("utf-8", errors="replace")[:4000]
        raw = ai_provider.generate_text(
            REVIEW_SYSTEM, f"{ask}\n\nข้อความในไฟล์:\n{body}",
            api_key, provider=provider, max_tokens=900)
    else:
        raw = ai_provider.analyze_media(
            [(mime, data)], ask, api_key, system=REVIEW_SYSTEM,
            provider=provider, max_tokens=900)

    if not raw:
        return None, "เรียก AI ไม่สำเร็จ — ลองใหม่อีกครั้ง"
    review = _parse(raw)
    if not review:
        logger.warning("ตรวจไฟล์ %s แล้วอ่าน JSON ไม่ออก: %s", name, (raw or "")[:200])
        return None, "AI ตอบกลับมาในรูปแบบที่อ่านไม่ออก — ลองใหม่อีกครั้ง"
    return Review(**{**review.__dict__, "provider": provider}), ""
