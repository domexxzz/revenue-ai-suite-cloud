"""Reading what the user attaches to a chat message.

Three kinds of file reach the copilot, and only one of them needs a model:

    image / pdf   → the provider's vision API reads it
    csv / xlsx    → pandas summarises it here, offline, no key required
    txt / md      → the text is the summary

Splitting them this way matters because most sessions run on "Local Smart" with
no API key at all. A spreadsheet and a note still work in that mode; only
pictures genuinely need Gemini or Claude, and saying so plainly beats a silent
no-op.

The output of every path is Thai prose, because it is fed straight back into the
copilot's prompt as context alongside what the user typed.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

IMAGE_TYPES = {"png", "jpg", "jpeg", "webp", "gif"}
TABLE_TYPES = {"csv", "xlsx", "xls"}
TEXT_TYPES = {"txt", "md"}
DOC_TYPES = {"pdf"}

UPLOAD_TYPES = sorted(IMAGE_TYPES | TABLE_TYPES | TEXT_TYPES | DOC_TYPES)

# Two ceilings, because the two paths have different costs. An image or PDF is
# base64'd into the request body — a 6MB file becomes ~8MB of JSON, and both APIs
# reject much past that. A spreadsheet never leaves the machine: pandas reads it
# and only the aggregates travel, so it can be far larger before it hurts.
MAX_MEDIA_BYTES = 6 * 1024 * 1024
MAX_LOCAL_BYTES = 50 * 1024 * 1024

_MIME_BY_EXT = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "webp": "image/webp", "gif": "image/gif", "pdf": "application/pdf",
}

VISION_SYSTEM = (
    "คุณเป็นนักการตลาดคอนเทนต์ที่ดูภาพแล้วสรุปให้ทีมใช้งานต่อได้ "
    "ตอบเป็นภาษาไทย กระชับ ไม่เกิน 6 บรรทัด "
    "บอกสิ่งที่เห็นจริงในภาพเท่านั้น ห้ามเดารายละเอียดที่มองไม่เห็น "
    "ถ้าเป็นภาพสินค้า ให้บอกรูปทรง สี พื้นผิว ฉาก แสง และอารมณ์ของภาพ "
    "ถ้าเป็นภาพหน้าจอตัวเลข ให้อ่านตัวเลขสำคัญออกมา "
    "ถ้าเป็นโพสต์ของคู่แข่ง ให้บอกว่าเขาใช้มุมขายอะไร"
)


@dataclass(frozen=True)
class Attachment:
    name: str
    data: bytes

    @property
    def ext(self) -> str:
        return self.name.rsplit(".", 1)[-1].lower() if "." in self.name else ""

    @property
    def kind(self) -> str:
        if self.ext in IMAGE_TYPES:
            return "image"
        if self.ext in DOC_TYPES:
            return "pdf"
        if self.ext in TABLE_TYPES:
            return "table"
        if self.ext in TEXT_TYPES:
            return "text"
        return "unsupported"

    @property
    def mime(self) -> str:
        return _MIME_BY_EXT.get(self.ext, "application/octet-stream")

    @property
    def limit(self) -> int:
        return MAX_MEDIA_BYTES if self.kind in ("image", "pdf") else MAX_LOCAL_BYTES

    @property
    def too_big(self) -> bool:
        return len(self.data) > self.limit


def from_uploads(uploaded) -> list[Attachment]:
    """Streamlit UploadedFile objects → Attachment. Reads each file once."""
    out: list[Attachment] = []
    for f in uploaded or []:
        try:
            out.append(Attachment(name=f.name, data=f.getvalue()))
        except Exception as e:  # noqa: BLE001 — a broken upload must not kill the run
            logger.warning("อ่านไฟล์แนบ %s ไม่ได้: %s", getattr(f, "name", "?"), e)
    return out


# ── Offline readers ────────────────────────────────────────────────────────────

def summarize_table(att: Attachment) -> str:
    """Shape, columns and the headline numbers — not the rows themselves.

    Sending a 5,000-row CSV to a model costs a fortune and answers nothing the
    aggregates do not. What the copilot needs is what the columns *are* and
    roughly what the numbers *say*.
    """
    try:
        import pandas as pd

        buf = io.BytesIO(att.data)
        df = pd.read_csv(buf) if att.ext == "csv" else pd.read_excel(buf)
    except Exception as e:  # noqa: BLE001
        return f"ไฟล์ {att.name}: อ่านไม่ได้ ({e})"

    if df.empty:
        return f"ไฟล์ {att.name}: ไม่มีข้อมูลในไฟล์"

    lines = [f"ไฟล์ {att.name}: {len(df):,} แถว {len(df.columns)} คอลัมน์",
             "คอลัมน์: " + ", ".join(str(c) for c in df.columns[:20])]

    num = df.select_dtypes("number")
    for col in list(num.columns)[:6]:
        s = num[col].dropna()
        if s.empty:
            continue
        lines.append(f"- {col}: รวม {s.sum():,.0f} · เฉลี่ย {s.mean():,.1f} "
                     f"· ต่ำสุด {s.min():,.0f} · สูงสุด {s.max():,.0f}")

    # Category columns say more through their top values than through a count.
    for col in list(df.select_dtypes("object").columns)[:3]:
        top = df[col].value_counts().head(3)
        if top.empty:
            continue
        lines.append(f"- {col} ที่พบบ่อย: " +
                     ", ".join(f"{k} ({v})" for k, v in top.items()))
    return "\n".join(lines)


def read_text(att: Attachment, limit: int = 4000) -> str:
    try:
        body = att.data.decode("utf-8", errors="replace").strip()
    except Exception as e:  # noqa: BLE001
        return f"ไฟล์ {att.name}: อ่านไม่ได้ ({e})"
    if len(body) > limit:
        body = body[:limit] + "\n…(ตัดส่วนที่เหลือ)"
    return f"ไฟล์ {att.name}:\n{body}"


# ── Combined pass ──────────────────────────────────────────────────────────────

def analyze(atts: list[Attachment], question: str, api_key: str = "",
            provider: str = "auto") -> tuple[str, list[str]]:
    """Turn every attachment into Thai context. Returns (context, notes).

    `notes` carries anything the user needs to be told — a file that was too big,
    a picture that cannot be read without an API key. They are shown, not
    swallowed: an attachment that quietly did nothing is worse than a refusal.
    """
    context_parts: list[str] = []
    notes: list[str] = []
    media: list[tuple[str, bytes]] = []
    media_names: list[str] = []

    for att in atts:
        if att.too_big:
            notes.append(f"⚠️ {att.name} ใหญ่เกิน {att.limit // 1024 // 1024} MB — ข้ามไฟล์นี้")
            continue
        kind = att.kind
        if kind in ("image", "pdf"):
            media.append((att.mime, att.data))
            media_names.append(att.name)
        elif kind == "table":
            context_parts.append(summarize_table(att))
        elif kind == "text":
            context_parts.append(read_text(att))
        else:
            notes.append(f"⚠️ {att.name}: ยังอ่านไฟล์ชนิดนี้ไม่ได้")

    if media:
        import ai_provider

        if not ai_provider.can_read_media(api_key, provider):
            notes.append(
                "🔑 ดูรูป/PDF ต้องใช้ Gemini หรือ Claude — ตอนนี้เป็นโหมด Local "
                "ที่ทำงานในเครื่อง ไม่ได้ส่งอะไรออก ใส่ key ที่หน้า ⚙️ ตั้งค่า แล้วลองใหม่"
            )
        else:
            ask = question.strip() or "ช่วยอธิบายสิ่งที่เห็นในไฟล์นี้"
            said = ai_provider.analyze_media(
                media, ask, api_key, system=VISION_SYSTEM, provider=provider)
            if said:
                context_parts.append(
                    "สิ่งที่เห็นในไฟล์ " + ", ".join(media_names) + ":\n" + said)
            else:
                notes.append("⚠️ อ่านรูป/PDF ไม่สำเร็จ — ลองใหม่อีกครั้ง")

    return "\n\n".join(p for p in context_parts if p), notes
