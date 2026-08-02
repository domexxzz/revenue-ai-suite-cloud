"""AI provider abstraction — Claude, Gemini, or local fallback.

One entry point (`generate_text`) so every feature (Copilot, Brain Storm,
Content Studio) can run on whichever key the user has. Gemini is reached over
plain REST via `requests`, which is already a dependency — no extra SDK needed,
which also keeps Streamlit Cloud deploys simple.

Provider is auto-detected from the key shape:
    sk-ant-…  → Claude      AIza…  → Gemini      (empty) → local templates
"""

from __future__ import annotations

import base64
import json
import logging
import re

import requests

logger = logging.getLogger(__name__)

# ── Model IDs ───────────────────────────────────────────────────────────────────
# Verified Aug 2026. Gemini text: 3.6 Flash is the current cheap/fast default.
# Gemini image: "Nano Banana" family — Imagen was retired 17 Aug 2026, so image
# generation must go through the gemini-*-image models.
GEMINI_TEXT_MODEL = "gemini-3.6-flash"
GEMINI_TEXT_FALLBACKS = ["gemini-3-flash", "gemini-2.5-flash"]
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"          # stable, free tier 500/day
GEMINI_IMAGE_FALLBACKS = ["gemini-3.1-flash-image-preview", "gemini-3-pro-image-preview"]

CLAUDE_MODEL = "claude-sonnet-4-6"

# Veo video generation. Veo 3.0 was shut down 30 Jun 2026 — 3.1 is the live line.
# Standard = best fidelity, Fast = lower latency/cost. Priced per second of output,
# so callers should surface the estimate before spending anything.
VEO_MODELS = {
    "fast":     "veo-3.1-fast-generate-preview",
    "standard": "veo-3.1-generate-preview",
}
VEO_PRICE_PER_SEC = {"fast": 0.10, "standard": 0.40}
VEO_DEFAULT_TIER = "fast"
VEO_POLL_TIMEOUT_SEC = 420   # Veo jobs usually land in 1-3 min; cap the wait
VEO_POLL_MAX_INTERVAL = 10

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

PROVIDER_LABELS = {
    "claude": "🤖 Claude",
    "gemini": "✨ Gemini",
    "local": "⚡ Local",
}


def detect_provider(api_key: str) -> str:
    """Infer the provider from an API key. Returns 'claude' | 'gemini' | 'local'."""
    key = (api_key or "").strip()
    if not key:
        return "local"
    if key.startswith("sk-ant"):
        return "claude"
    if key.startswith("AIza"):
        return "gemini"
    # Unknown shape — assume Gemini keys that don't follow the AIza prefix.
    return "gemini" if len(key) < 60 else "claude"


# ── Text generation ─────────────────────────────────────────────────────────────

def _gemini_text(system: str, user: str, api_key: str, max_tokens: int) -> str | None:
    payload = {
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    for model in [GEMINI_TEXT_MODEL, *GEMINI_TEXT_FALLBACKS]:
        try:
            resp = requests.post(
                f"{GEMINI_BASE}/{model}:generateContent",
                params={"key": api_key},
                json=payload,
                timeout=90,
            )
            if resp.status_code == 404:
                continue  # model retired / not enabled on this key — try the next
            resp.raise_for_status()
            parts = (
                resp.json()
                .get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [])
            )
            text = "".join(p.get("text", "") for p in parts).strip()
            if text:
                return text
        except Exception as e:  # noqa: BLE001 — any failure falls through to next model
            logger.warning("Gemini text (%s) failed: %s", model, e)
    return None


def _claude_text(system: str, user: str, api_key: str, max_tokens: int) -> str | None:
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system or "",
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text.strip()
    except Exception as e:  # noqa: BLE001
        logger.warning("Claude text failed: %s", e)
        return None


def generate_text(system: str, user: str, api_key: str,
                  provider: str = "auto", max_tokens: int = 1500) -> str | None:
    """Generate text with whichever provider the key belongs to.

    Returns None on any failure so callers can fall back to local templates.
    """
    if not api_key or not api_key.strip():
        return None
    if provider in ("auto", "", None):
        provider = detect_provider(api_key)
    key = api_key.strip()
    if provider == "gemini":
        return _gemini_text(system, user, key, max_tokens)
    if provider == "claude":
        return _claude_text(system, user, key, max_tokens)
    return None


def generate_json(system: str, user: str, api_key: str, provider: str = "auto",
                  max_tokens: int = 1500, expect_list: bool = False):
    """generate_text + tolerant JSON extraction. Returns dict/list or None."""
    text = generate_text(system, user, api_key, provider, max_tokens)
    if not text:
        return None
    pattern = r"\[.*\]" if expect_list else r"\{.*\}"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


# ── Vision / document reading ───────────────────────────────────────────────────
#
# The opposite direction from generate_image: the user hands the model a picture
# or a PDF and asks about it. Both providers take the bytes inline, base64, in
# the same message as the question — no upload step, no file IDs to clean up.

VISION_MIME = {
    "image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif",
    "application/pdf",
}
# Inline attachments are capped by the request body, not by us — but a 20MB photo
# base64s to ~27MB and both APIs reject it. Refuse early with a clear message
# rather than after a 60-second upload.
MAX_ATTACHMENT_BYTES = 6 * 1024 * 1024


def can_read_media(api_key: str, provider: str = "auto") -> bool:
    """True when the key belongs to a provider that can look at an image."""
    if not api_key or not api_key.strip():
        return False
    if provider in ("auto", "", None):
        provider = detect_provider(api_key)
    return provider in ("gemini", "claude")


def _gemini_vision(parts_media: list[tuple[str, bytes]], system: str, user: str,
                   api_key: str, max_tokens: int) -> str | None:
    parts: list[dict] = [
        {"inline_data": {"mime_type": mime,
                         "data": base64.b64encode(raw).decode("ascii")}}
        for mime, raw in parts_media
    ]
    parts.append({"text": user})
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    for model in [GEMINI_TEXT_MODEL, *GEMINI_TEXT_FALLBACKS]:
        try:
            resp = requests.post(
                f"{GEMINI_BASE}/{model}:generateContent",
                params={"key": api_key}, json=payload, timeout=120,
            )
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            blocks = (resp.json().get("candidates", [{}])[0]
                      .get("content", {}).get("parts", []))
            text = "".join(b.get("text", "") for b in blocks).strip()
            if text:
                return text
        except Exception as e:  # noqa: BLE001
            logger.warning("Gemini vision (%s) failed: %s", model, e)
    return None


def _claude_vision(parts_media: list[tuple[str, bytes]], system: str, user: str,
                   api_key: str, max_tokens: int) -> str | None:
    try:
        import anthropic

        content: list[dict] = []
        for mime, raw in parts_media:
            b64 = base64.b64encode(raw).decode("ascii")
            if mime == "application/pdf":
                content.append({"type": "document", "source": {
                    "type": "base64", "media_type": "application/pdf", "data": b64}})
            else:
                # Claude names the type "image/jpeg"; "image/jpg" is rejected.
                media = "image/jpeg" if mime == "image/jpg" else mime
                content.append({"type": "image", "source": {
                    "type": "base64", "media_type": media, "data": b64}})
        content.append({"type": "text", "text": user})

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=CLAUDE_MODEL, max_tokens=max_tokens, system=system or "",
            messages=[{"role": "user", "content": content}],
        )
        return message.content[0].text.strip()
    except Exception as e:  # noqa: BLE001
        logger.warning("Claude vision failed: %s", e)
        return None


def analyze_media(media: list[tuple[str, bytes]], question: str, api_key: str,
                  system: str = "", provider: str = "auto",
                  max_tokens: int = 1200) -> str | None:
    """Ask the model about attached images/PDFs. None when it cannot be done.

    `media` is [(mime_type, raw_bytes), ...]. Anything the provider cannot read
    is dropped by the caller, not here — this fails loudly if handed nothing.
    """
    if not media or not api_key or not api_key.strip():
        return None
    if provider in ("auto", "", None):
        provider = detect_provider(api_key)
    key = api_key.strip()
    if provider == "gemini":
        return _gemini_vision(media, system, question, key, max_tokens)
    if provider == "claude":
        return _claude_vision(media, system, question, key, max_tokens)
    return None


# ── Image generation (Gemini only) ──────────────────────────────────────────────

def can_generate_images(api_key: str, provider: str = "auto") -> bool:
    """True when the key can actually render images (Gemini keys only)."""
    if not api_key or not api_key.strip():
        return False
    if provider in ("auto", "", None):
        provider = detect_provider(api_key)
    return provider == "gemini"


def generate_image(prompt: str, api_key: str) -> tuple[bytes | None, str]:
    """Render an image from a prompt using Gemini (Nano Banana).

    Returns (image_bytes, message). image_bytes is None on failure, with the
    reason in message so the UI can show something actionable.
    """
    if not api_key or not api_key.strip():
        return None, "ต้องใส่ Gemini API key ก่อนถึงจะสร้างรูปได้"

    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    last_error = "สร้างรูปไม่สำเร็จ"

    for model in [GEMINI_IMAGE_MODEL, *GEMINI_IMAGE_FALLBACKS]:
        try:
            resp = requests.post(
                f"{GEMINI_BASE}/{model}:generateContent",
                params={"key": api_key.strip()},
                json=payload,
                timeout=180,
            )
            if resp.status_code == 404:
                last_error = f"โมเดล {model} ใช้ไม่ได้กับ key นี้"
                continue
            if resp.status_code == 429:
                return None, "โควตา Gemini เต็มแล้ว — รอสักครู่แล้วลองใหม่"
            resp.raise_for_status()

            parts = (
                resp.json()
                .get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [])
            )
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"]), f"สร้างรูปด้วย {model} สำเร็จ"
            last_error = "โมเดลไม่ได้ส่งรูปกลับมา — ลองปรับ prompt ให้ชัดขึ้น"
        except Exception as e:  # noqa: BLE001
            logger.warning("Gemini image (%s) failed: %s", model, e)
            last_error = f"เรียก {model} ไม่สำเร็จ: {e}"

    return None, last_error


# ── Video generation (Veo via Gemini) ───────────────────────────────────────────

def estimate_video_cost(seconds: int = 8, tier: str = VEO_DEFAULT_TIER) -> float:
    """Estimated USD cost for one generated clip."""
    return round(VEO_PRICE_PER_SEC.get(tier, VEO_PRICE_PER_SEC["fast"]) * max(1, seconds), 2)


def _veo_extract_uri(op: dict) -> str:
    """Pull the video URI out of a finished operation payload."""
    resp = op.get("response") or {}
    samples = (resp.get("generateVideoResponse") or {}).get("generatedSamples") or []
    if samples:
        uri = ((samples[0] or {}).get("video") or {}).get("uri")
        if uri:
            return uri
    # Some responses nest the clip under predictions instead.
    for pred in resp.get("predictions") or []:
        uri = (pred.get("video") or {}).get("uri") or pred.get("videoUri")
        if uri:
            return uri
    return ""


def _veo_extract_inline(op: dict) -> bytes | None:
    """Some operations return the clip inline as base64 instead of a URI."""
    resp = op.get("response") or {}
    samples = (resp.get("generateVideoResponse") or {}).get("generatedSamples") or []
    for sample in samples:
        data = ((sample or {}).get("video") or {}).get("bytesBase64Encoded")
        if data:
            try:
                return base64.b64decode(data)
            except Exception:  # noqa: BLE001
                return None
    return None


def generate_video(prompt: str, api_key: str, tier: str = VEO_DEFAULT_TIER,
                   seconds: int = 8, aspect_ratio: str = "9:16",
                   on_progress=None) -> tuple[bytes | None, str]:
    """Generate a video clip with Veo. Blocks until the job finishes or times out.

    Veo is long-running: submit → poll the operation → download the result.
    `on_progress(text)` is called with status updates so the UI can show them.

    Returns (video_bytes, message); video_bytes is None on failure.
    """
    if not api_key or not api_key.strip():
        return None, "ต้องใส่ Gemini API key ก่อนถึงจะสร้างวิดีโอได้"

    key = api_key.strip()
    model = VEO_MODELS.get(tier, VEO_MODELS[VEO_DEFAULT_TIER])

    def _progress(msg: str) -> None:
        if on_progress:
            try:
                on_progress(msg)
            except Exception:  # noqa: BLE001 — never let UI callbacks break generation
                pass

    # 1) Submit the job
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"aspectRatio": aspect_ratio, "durationSeconds": seconds},
    }
    try:
        _progress("กำลังส่งคำสั่งไปที่ Veo...")
        resp = requests.post(
            f"{GEMINI_BASE}/{model}:predictLongRunning",
            params={"key": key}, json=payload, timeout=90,
        )
        if resp.status_code == 404:
            return None, f"โมเดล {model} ใช้ไม่ได้กับ key นี้ (อาจต้องเปิดสิทธิ์ Veo ก่อน)"
        if resp.status_code == 429:
            return None, "โควตา Veo เต็มแล้ว — รอสักครู่แล้วลองใหม่"
        if resp.status_code in (401, 403):
            return None, "Gemini key ไม่มีสิทธิ์ใช้ Veo — ต้องเปิด billing ในโปรเจกต์ Google"
        resp.raise_for_status()
        op_name = resp.json().get("name", "")
        if not op_name:
            return None, "Veo ไม่ได้คืนหมายเลขงานกลับมา"
    except Exception as e:  # noqa: BLE001
        logger.warning("Veo submit failed: %s", e)
        return None, f"ส่งคำสั่งไม่สำเร็จ: {e}"

    # 2) Poll with backoff until done
    import time

    waited, interval = 0.0, 2.0
    op: dict = {}
    while waited < VEO_POLL_TIMEOUT_SEC:
        time.sleep(interval)
        waited += interval
        interval = min(interval * 1.5, VEO_POLL_MAX_INTERVAL)
        try:
            poll = requests.get(
                f"{GEMINI_BASE.rsplit('/models', 1)[0]}/{op_name}",
                params={"key": key}, timeout=60,
            )
            poll.raise_for_status()
            op = poll.json()
        except Exception as e:  # noqa: BLE001
            logger.warning("Veo poll failed: %s", e)
            continue

        if op.get("done"):
            break
        _progress(f"Veo กำลังเรนเดอร์... ({int(waited)} วินาที)")
    else:
        return None, f"รอเกิน {VEO_POLL_TIMEOUT_SEC // 60} นาทีแล้วยังไม่เสร็จ — ลองใหม่อีกครั้ง"

    if op.get("error"):
        return None, f"Veo แจ้งข้อผิดพลาด: {op['error'].get('message', 'ไม่ทราบสาเหตุ')}"

    # 3) Fetch the clip — inline bytes if present, otherwise download the URI
    inline = _veo_extract_inline(op)
    if inline:
        return inline, f"สร้างวิดีโอด้วย {model} สำเร็จ"

    uri = _veo_extract_uri(op)
    if not uri:
        return None, "Veo ทำงานเสร็จแต่ไม่พบไฟล์วิดีโอในผลลัพธ์"

    try:
        _progress("กำลังดาวน์โหลดวิดีโอ...")
        dl = requests.get(uri, params={"key": key}, timeout=300)
        dl.raise_for_status()
        return dl.content, f"สร้างวิดีโอด้วย {model} สำเร็จ"
    except Exception as e:  # noqa: BLE001
        logger.warning("Veo download failed: %s", e)
        return None, f"ดาวน์โหลดวิดีโอไม่สำเร็จ: {e}"
