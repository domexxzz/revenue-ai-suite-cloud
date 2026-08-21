"""Content Copilot — natural-language chat → content brief → draft package.

Turns a plain chat message such as
    "อยากได้โพสต์ flash sale ลด 20% ลง IG + Facebook โทนพรีเมียม"
into a structured brief, then generates a multi-platform content package by
reusing content_studio.get_content_package().

Works with OR without a Claude API key:
  • with key   → Claude extracts a precise brief (campaign/platform/tone/…)
  • without key → keyword heuristics (Thai + English) give a sensible brief

The module is UI-agnostic: it returns plain dicts/strings. The Streamlit page
(render_copilot_page in app.py) handles chat rendering, approval and posting.
"""

from __future__ import annotations

import json
import re

from content_studio import (
    CAMPAIGN_TYPES,
    TONES,
    PLATFORMS,
    get_content_package,
)

# Mirror the model used by content_studio so behaviour stays consistent across
# the app. If Claude is unavailable or errors, callers fall back to local mode.
MODEL = "claude-sonnet-4-6"

_DEFAULT_PLATFORMS = ["facebook", "instagram", "line_oa"]
_DEFAULT_CAMPAIGN = "hero_product"
_DEFAULT_TONE = "friendly"

# ── Keyword maps for local (no-API) intent parsing ──────────────────────────────

_CAMPAIGN_KEYWORDS: dict[str, list[str]] = {
    "flash_sale":  ["flash", "แฟลช", "ลดราคา", "ลดล้าง", "sale", "happy hour",
                    "โปรวันนี้", "ลดกระหน่ำ", "ด่วนวันนี้", "ลดพิเศษ"],
    "winback":     ["หายไป", "คิดถึง", "กลับมา", "winback", "win-back", "ลูกค้าเก่า",
                    "ไม่ได้มา", "ไม่ได้แวะ", "ดึงลูกค้ากลับ"],
    "vip_reward":  ["vip", "สมาชิก", "ลูกค้าประจำ", "champions", "reward", "รางวัล",
                    "ขอบคุณลูกค้า", "ลูกค้าคนพิเศษ"],
    "new_customer": ["ลูกค้าใหม่", "ต้อนรับ", "welcome", "ครั้งแรก", "มาใหม่", "สมาชิกใหม่"],
    "seasonal":    ["เทศกาล", "สงกรานต์", "ปีใหม่", "คริสต์มาส", "ตรุษจีน", "วาเลนไทน์",
                    "seasonal", "ฮาโลวีน", "ลอยกระทง", "แม่", "พ่อ"],
    "hero_product": ["hero", "เมนูเด็ด", "สินค้าเด่น", "ตัวชูโรง", "signature", "แนะนำ",
                     "ขายดี", "เปิดตัว", "ตัวใหม่", "สินค้าใหม่", "รีวิว", "โชว์สินค้า"],
}

_TONE_KEYWORDS: dict[str, list[str]] = {
    "urgent":  ["ด่วน", "เร่ง", "รีบ", "วันนี้เท่านั้น", "urgent", "fomo", "เวลาจำกัด", "นับถอยหลัง"],
    "premium": ["พรีเมียม", "หรู", "luxury", "premium", "exclusive", "หรูหรา", "ระดับพรีเมียม", "ลักชัวรี"],
    "fun":     ["สนุก", "ขำ", "กวน", "fun", "ตลก", "playful", "อารมณ์ดี", "แซ่บ"],
    "friendly": ["เป็นกันเอง", "อบอุ่น", "friendly", "น่ารัก", "อ่อนโยน"],
}

_PLATFORM_KEYWORDS: dict[str, list[str]] = {
    "line_oa":   ["line oa", "line", "ไลน์", " oa"],
    "facebook":  ["facebook", "fb", "เฟส", "เฟซ"],
    "instagram": ["instagram", "ig", "ไอจี", "insta", "story", "สตอรี", "carousel", "คารูเซล"],
    "tiktok":    ["tiktok", "ติ๊กต็อก", "ทิกทอก", "tik tok", "ติกต็อก"],
    "youtube":   ["youtube", "yt", "ยูทูป", "ยูทูบ", "shorts", "ช็อต"],
}

# Product nouns worth surfacing as the "hero item" in local mode (skincare-leaning).
_ITEM_KEYWORDS = [
    "เซรั่ม", "ครีมกันแดด", "กันแดด", "ครีมบำรุง", "ครีม", "โฟมล้างหน้า", "โฟม",
    "สบู่", "โทนเนอร์", "มาส์ก", "เอสเซนส์", "เอสเซ้นส์", "แชมพู", "ลิป",
    "อาหารเสริม", "วิตามิน", "เมนู", "สินค้า",
]


# ── Local extraction helpers ────────────────────────────────────────────────────

def _match_first(text: str, mapping: dict[str, list[str]], default: str) -> str:
    for key, keywords in mapping.items():
        if any(kw in text for kw in keywords):
            return key
    return default


def _extract_discount(text: str) -> int:
    m = re.search(r"(\d{1,3})\s*%", text)
    if m:
        return max(5, min(int(m.group(1)), 90))
    m = re.search(r"ลด\s*(\d{1,3})", text)
    if m:
        return max(5, min(int(m.group(1)), 90))
    return 20


def product_from_context(brand_context: str) -> str:
    """The product the brand actually sells, read from its brief.

    LEMED sells one thing — a soap bar — but the extractor below happily picked
    "เซรั่ม" out of a prompt and the whole pipeline then advertised a serum that
    does not exist. The brand brief is the authority on what is for sale.
    """
    if not brand_context:
        return ""
    # "ชื่อสินค้า: LEMED Soap Anti-Acne 60g (สบู่ลดสิว เลอเมด)"
    m = re.search(r"ชื่อสินค้า\s*[:：]\s*(.+)", brand_context)
    line = m.group(1) if m else brand_context
    for kw in _ITEM_KEYWORDS:
        if kw in line:
            return kw
    # Fall back to any product word anywhere in the brief.
    for kw in _ITEM_KEYWORDS:
        if kw in brand_context:
            return kw
    return ""


def _constrain_item(item: str, brand_context: str) -> str:
    """Keep a proposed product inside the brand's catalogue. Default to soap bar for LEMED."""
    brand_product = product_from_context(brand_context)
    if not brand_product:
        if not item or item in ("สินค้าเด่น", "the product", "product", "สกินแคร์", "เซรั่ม"):
            return "สบู่ก้อน"
        return item
    if brand_product in (item or ""):
        return item
    return brand_product


def _extract_item(text: str, brand_context: str = "") -> str:
    """Product named in the request, constrained to what the brand sells."""
    brand_product = product_from_context(brand_context)

    # A brand with a known catalogue only offers what is in it — otherwise a
    # passing mention of another product type invents a line that does not exist.
    allowed = [brand_product] if brand_product else _ITEM_KEYWORDS
    for kw in allowed:
        if kw and kw in text:
            return kw

    return brand_product or "สินค้าเด่น"


def _extract_brand(text: str, default_brand: str) -> str:
    if re.search(r"\blemed\b", text, re.IGNORECASE):
        return "LEMED"
    return default_brand or "ร้านของคุณ"


def _extract_platforms(text: str) -> list[str]:
    found = [pid for pid, kws in _PLATFORM_KEYWORDS.items() if any(kw in text for kw in kws)]
    return found or list(_DEFAULT_PLATFORMS)


# ── Interpretation ──────────────────────────────────────────────────────────────

def _interpret_local(prompt: str, default_brand: str, brand_context: str = "") -> dict:
    """Keyword-based intent parsing — no API key required."""
    p = f" {prompt.lower()} "
    campaign = _match_first(p, _CAMPAIGN_KEYWORDS, _DEFAULT_CAMPAIGN)
    tone = _match_first(p, _TONE_KEYWORDS, _DEFAULT_TONE)
    return {
        "campaign": campaign,
        "tone": tone,
        "platforms": _extract_platforms(p),
        "brand_name": _extract_brand(prompt, default_brand),
        "top_item": _extract_item(prompt, brand_context),
        "discount": _extract_discount(prompt),
        "summary": "",
        "source": "local",
    }


def _interpret_ai(prompt: str, api_key: str, default_brand: str,
                  brand_context: str = "", provider: str = "auto") -> dict | None:
    """Ask an AI provider to extract a structured brief. None on any failure."""
    try:
        import ai_provider
    except ImportError:
        return None

    system_prompt = (
        "คุณเป็นผู้เชี่ยวชาญด้านคอนเทนต์การตลาดเวชสำอางสำหรับแบรนด์ LEMED (เลอเมด) "
        "คอนเซปต์หลัก: 'ดูแลปัญหาสิวด้วยความเข้าใจ ไม่ใช่แค่การล้างให้สะอาด' (Dermatological Cleansing Care) "
        "สโลแกน: 'ผิวสะอาดอย่างสมดุล เพื่อวันที่มั่นใจขึ้น' "
        "สินค้า: สบู่เวชสำอางลดสิว LEMED Acne Oil-Control 60g (ผสาน 7 สารสำคัญ: ใบชุมเห็ดเทศ, Encapsulated BHA, ชะเอมเทศ, ใบบัวบก Cica, ไนอะซินาไมด์, วิตามิน E, Hyaluronic Acid) "
        "มาตรฐาน: 5-FREE Clean Standard (0% Paraben, SLS, Formaldehyde, Mineral Oil, Cruelty Free) "
        "แปลงคำสั่งภาษาคนให้เป็น JSON ที่ถูกต้อง ห้ามโอเวอร์เคลม "
        f"ค่า campaign ต้องเป็นหนึ่งใน {list(CAMPAIGN_TYPES.keys())} "
        f"ค่า tone ต้องเป็นหนึ่งใน {list(TONES.keys())} "
        f"ค่า platforms ต้องเป็น subset ของ {list(PLATFORMS.keys())}"
    )
    if brand_context:
        system_prompt += "\n\nบริบทแบรนด์ (ใช้เติมค่าที่ผู้ใช้ไม่ได้ระบุ):\n" + brand_context[:2000]
        known = product_from_context(brand_context)
        if known:
            system_prompt += (
                f"\n\nสำคัญ: แบรนด์นี้ขาย **{known}** เท่านั้น "
                f'ค่า top_item ต้องเป็น "{known}" เสมอ '
                "ห้ามตั้งชื่อสินค้าประเภทอื่นที่แบรนด์ไม่ได้ขาย "
                "(เช่น เซรั่ม ครีม โทนเนอร์) แม้ผู้ใช้จะพิมพ์มาก็ตาม"
            )

    user_prompt = (
        f'คำสั่งจากผู้ใช้: "{prompt}"\n\n'
        "ตอบกลับเป็น JSON เท่านั้น รูปแบบ:\n"
        "{\n"
        '  "campaign": "<หนึ่งค่า>",\n'
        '  "platforms": ["<platform>", ...],\n'
        '  "tone": "<หนึ่งค่า>",\n'
        '  "brand_name": "<ชื่อแบรนด์>",\n'
        '  "top_item": "<สินค้า/เมนูหลัก>",\n'
        '  "discount": <ตัวเลข % ถ้าไม่มีใส่ 20>,\n'
        '  "summary": "<สรุปสั้นๆ ภาษาไทยว่าจะทำอะไร>"\n'
        "}\n"
        f'ถ้าไม่ระบุแบรนด์ ใช้ "{default_brand}". ถ้าไม่ระบุแพลตฟอร์ม เลือกที่เหมาะสมกับงาน'
    )

    data = ai_provider.generate_json(
        system_prompt, user_prompt, api_key, provider=provider, max_tokens=600
    )
    if not isinstance(data, dict):
        return None
    return _sanitize_brief(data, default_brand, brand_context)


def _sanitize_brief(data: dict, default_brand: str, brand_context: str = "") -> dict:
    """Clamp Claude's output to valid enum values so downstream never breaks."""
    campaign = data.get("campaign")
    if campaign not in CAMPAIGN_TYPES:
        campaign = _DEFAULT_CAMPAIGN
    tone = data.get("tone")
    if tone not in TONES:
        tone = _DEFAULT_TONE
    platforms = [p for p in (data.get("platforms") or []) if p in PLATFORMS]
    if not platforms:
        platforms = list(_DEFAULT_PLATFORMS)
    try:
        discount = max(5, min(int(data.get("discount") or 20), 90))
    except (TypeError, ValueError):
        discount = 20
    return {
        "campaign": campaign,
        "tone": tone,
        "platforms": platforms,
        "brand_name": (data.get("brand_name") or default_brand or "ร้านของคุณ").strip(),
        # Hold the model to the catalogue too — asked for a campaign it may
        # otherwise name a product the brand has never sold.
        "top_item": _constrain_item((data.get("top_item") or "").strip(), brand_context),
        "discount": discount,
        "summary": (data.get("summary") or "").strip(),
        "source": "claude",
    }


def load_brand_context() -> str:
    """Pull the Mandala AI brand brief, if mandala-bot is available locally."""
    try:
        import mandala_client
        return mandala_client.build_context_block(include_samples=1)
    except Exception:  # noqa: BLE001 — context is a bonus, never a hard dependency
        return ""


def interpret(prompt: str, api_key: str = "", default_brand: str = "ร้านของคุณ",
              brand_context: str = "", provider: str = "auto") -> dict:
    """Turn a chat message into a validated content brief."""
    if api_key and api_key.strip():
        brief = _interpret_ai(prompt, api_key.strip(), default_brand, brand_context, provider)
        if brief:
            return brief
    return _interpret_local(prompt, default_brand, brand_context)


# ── Brief → context → package ───────────────────────────────────────────────────

def build_context(brief: dict) -> dict:
    """Map a brief onto the context dict that content_studio templates expect."""
    brand = (brief.get("brand_name") or "ร้านของคุณ").strip()
    hero = (brief.get("top_item") or "สินค้าเด่น").strip()
    discount = brief.get("discount", 20)
    return {
        "brand_name": brand,
        "brand_tag": brand.replace(" ", "").replace("ร้าน", "") or "brand",
        "top_item": hero,
        "discount": discount,
        "expiry": brief.get("expiry", "เร็ว ๆ นี้"),
        "cta": brief.get("cta", "ทักแชทเพื่อรับสิทธิ์"),
        "days": brief.get("days", 30),
        "hours": "10:00-22:00",
        "start_time": brief.get("start_time", "17:00"),
        "end_time": brief.get("end_time", "20:00"),
        "countdown": brief.get("countdown", 24),
        # legacy-compatible keys used elsewhere in content_studio
        "business_name": brand,
        "hero_product": hero,
        "target_segment": brief.get("target_segment", "ทุกกลุ่ม"),
        "days_inactive": brief.get("days", 30),
        "urgency_hours": brief.get("countdown", 24),
    }


# Local content_studio templates are F&B-flavoured ("food photography",
# "hero dish"). That reads wrong for a skincare brand, so in local mode we build
# a product-photography prompt from the brief instead.
_FOOD_MARKERS = ("food photography", "hero dish", "appetizing", "restaurant quality")

_TONE_LOOKS = {
    "premium": "luxurious minimal styling, marble and soft shadow, elegant, high-end beauty campaign",
    "urgent":  "bold vivid colours, high contrast, energetic promotional styling",
    "fun":     "bright playful colours, cheerful props, lively composition",
    "friendly": "warm natural light, soft pastel tones, approachable lifestyle styling",
}


def build_image_prompt(brief: dict) -> str:
    """Short product-photography prompt (kept for compatibility / quick use)."""
    brand = brief.get("brand_name") or "the brand"
    item = english_item(brief.get("top_item") or "the product")
    look = _TONE_LOOKS.get(brief.get("tone", ""), _TONE_LOOKS["friendly"])
    return (
        f"Professional product photography of {item} by {brand}, "
        f"{look}, clean uncluttered background, studio lighting with soft gradient, "
        "shallow depth of field, crisp detail on the packaging, "
        "commercial advertising quality, 4K, no text overlay"
    )


# ── Master prompts ──────────────────────────────────────────────────────────────
# Full production-grade prompts meant to be pasted straight into Google Flow,
# Midjourney, or any image/video model — every lever spelled out rather than
# left to the model's defaults.

_TONE_GRADE = {
    "premium": ("desaturated elegant palette, deep blacks, subtle warm highlights, "
                "editorial luxury grade"),
    "urgent":  ("high-saturation punchy palette, strong contrast, vivid accent colours, "
                "energetic commercial grade"),
    "fun":     ("bright cheerful palette, playful pastel accents, high-key airy grade"),
    "friendly": ("soft natural palette, warm skin-friendly tones, gentle lifted shadows"),
}

_TONE_LIGHT = {
    "premium": ("single large softbox at 45 degrees with a subtle rim light, "
                "controlled falloff, deep soft shadows"),
    "urgent":  ("bright even key light with a hard accent kick, crisp defined shadows"),
    "fun":     ("bright diffused daylight, colourful bounce fill, minimal shadow"),
    "friendly": ("soft window light from the side, white bounce fill, natural gentle shadow"),
}

# Product-only scenes must say so out loud. If the cast is simply omitted, models
# happily invent a hand reaching in from off-frame with no body attached.
_NO_CAST = ("ไม่มีคนในเฟรม — product-only shot. No people, no hands, no fingers, "
            "no arms, no reflections of people, no body parts of any kind visible. "
            "The product stands or rests on its own.")

_IMAGE_AVOID = ("no text, no logos, no watermark, no distorted packaging, no extra hands, "
                "no clutter, no harsh blown-out highlights, no plastic-looking skin")

_VIDEO_AVOID = ("no on-screen text, no watermark, no logo distortion, no jarring cuts, "
                "no warped product geometry, no flickering, no bottle, no dropper, no serum, "
                "no pump, no jar, no liquid container, no squeeze tube — the product is a solid bar of soap only")


# ── Product form ────────────────────────────────────────────────────────────────
# A soap bar cannot pour and a bottle cannot lather. Getting the physical form
# wrong is the single biggest source of implausible generations, so the form is
# detected from the item name and drives both the subject line and the physics
# notes the model is held to.

_PRODUCT_FORMS: dict[str, dict] = {
    "bar": {
        "keywords": ["สบู่", "soap", "ก้อน", "bar"],
        "avoid": "no round soap, no circular puck, no disk, no purple soap, no purple box, "
                 "no cardboard carton box, no petri dish, no laboratory glassware, no chemical flasks, "
                 "no beakers, no test tubes, no science lab, no tube, no squeeze tube, no bottle, "
                 "no pump, no dropper, no serum, no jar, no pouch, no liquid container of any kind — "
                 "the product is an authentic rectangular solid herbal soap bar with a white paper belly-band wrapper only",
        "desc": "an authentic rectangular solid herbal soap bar with softly chamfered beveled edges, "
                "warm honey-amber and natural herbal beige translucent tone with delicate organic flecks, "
                "wrapped around the middle with a crisp clean matte white paper sleeve belly-band "
                "featuring the botanical leaf emblem, crisp black LEMED logo, and gold-ochre accent band, "
                "resting flat and stable",
        "physics": "a solid dense bar of soap that never pours, drips or squeezes. It produces rich, "
                   "creamy white micro-lather foam when wet. Natural water beads rest with surface tension "
                   "on the bar. The rectangular bar maintains its exact shape, bevels and label throughout",
        "texture": "subtle waxy herbal matte surface, micro-droplets of water, and fine rich white foam",
        "handling": "held flat in an open palm or between both hands — never tipped, squeezed or poured",
    },
    "bottle": {
        "keywords": ["เซรั่ม", "serum", "โทนเนอร์", "toner", "แชมพู", "shampoo",
                     "เอสเซนส์", "เอสเซ้นส์", "essence", "ขวด", "bottle", "น้ำตบ"],
        "avoid": "no soap bar, no tube, no jar, no sachet — the product is a "
                 "bottle and nothing else",
        "desc": "a slim glass bottle with a dropper or pump, label facing camera, "
                "standing upright and stable",
        "physics": "liquid inside settles level and stays level. A drop forms, hangs, "
                   "then falls straight down under gravity and spreads on contact. "
                   "The bottle stands upright unless a hand tips it, and glass shows "
                   "consistent refraction and reflection",
        "texture": "a clear viscous droplet catching light as it falls",
        "handling": "gripped around the body, dropper squeezed from the top",
    },
    "tube": {
        "keywords": ["ครีม", "cream", "โฟม", "foam", "เจล", "gel", "หลอด", "tube",
                     "กันแดด", "sunscreen"],
        "avoid": "no soap bar, no bottle, no jar — the product is a squeeze tube "
                 "and nothing else",
        "desc": "a soft squeeze tube with a flip cap, label facing camera, "
                "standing or lying flat",
        "physics": "product only appears when the tube is squeezed — it extrudes in a "
                   "continuous ribbon that holds its shape briefly then slowly settles. "
                   "The tube body deforms where fingers press and does not refill itself",
        "texture": "a smooth extruded ribbon with soft peaks holding their shape",
        "handling": "squeezed from the base with the cap open",
    },
    "jar": {
        "keywords": ["มาส์ก", "mask", "กระปุก", "jar", "บาล์ม", "balm", "สครับ", "scrub"],
        "avoid": "no soap bar, no tube, no bottle — the product is a jar and "
                 "nothing else",
        "desc": "a wide round jar with the lid set beside it, contents visible, "
                "sitting level",
        "physics": "the thick contents hold a scooped indentation once disturbed and do "
                   "not flow back level. The lid rests where it was placed. Nothing "
                   "pours from a jar",
        "texture": "a thick creamy surface with a clean scoop mark and soft peaks",
        "handling": "scooped with a fingertip or small spatula",
    },
}

# Thai product words → English. Image and video models read these prompts in
# English; leaving a Thai noun in the middle of one invites a phonetic guess.
# "สบู่" came back as "soup" from Veo — close enough in sound, wrong product
# entirely — even though "soap bar" appeared later in the same sentence.
_ITEM_EN: list[tuple[str, str]] = [
    ("สบู่", "soap bar"),
    ("เซรั่ม", "serum"),
    ("ครีมกันแดด", "sunscreen"),
    ("กันแดด", "sunscreen"),
    ("ครีมบำรุง", "moisturiser cream"),
    ("ครีม", "cream"),
    ("โฟมล้างหน้า", "facial cleansing foam"),
    ("โฟม", "cleansing foam"),
    ("โทนเนอร์", "toner"),
    ("มาส์ก", "face mask"),
    ("เอสเซนส์", "essence"),
    ("เอสเซ้นส์", "essence"),
    ("แชมพู", "shampoo"),
    ("ลิป", "lip balm"),
    ("อาหารเสริม", "supplement"),
    ("วิตามิน", "vitamin supplement"),
    ("เมนู", "dish"),
    ("สินค้าเด่น", "signature product"),
    ("สินค้า", "product"),
]


def name_the_product(text: str, item: str) -> str:
    """Replace generic "the product" in shot directions with the real name.

    Scene shots are written generically so they suit any brand, but a model
    reading "the product" five times in a skincare setting draws the shape it
    sees most often — it returned a squeeze tube for a soap bar. Naming the
    product in the directions the model actually renders settles it.
    """
    if not item:
        return text

    # Case-insensitive, keeping the original capitalisation. A sentence opening
    # "The product settles centred…" was slipping past a case-sensitive match, so
    # the very shot that decides the final frame kept saying "product" — which is
    # the exact wording that rendered a squeeze tube instead of a bar of soap.
    def sub(m: re.Match) -> str:
        out = f"the {item}"
        return out[0].upper() + out[1:] if m.group(0)[0].isupper() else out

    text = re.sub(r"\bthe product\b", sub, text, flags=re.I)
    return re.sub(r"\bproduct in frame\b", f"{item} in frame", text, flags=re.I)


def english_item(item: str) -> str:
    """English name for the product, for use inside English prompts.

    Falls back to the original text when nothing matches — better a word the
    model may not know than a silent mistranslation.
    """
    low = (item or "").lower()
    for thai, eng in _ITEM_EN:
        if thai in low:
            return eng
    return (item or "the product").strip()


_DEFAULT_FORM = {
    "desc": "the product with its label facing camera, resting stable and level",
    "physics": "the product keeps a consistent shape, size and label across every "
               "frame, rests stably on the surface, and obeys gravity",
    "texture": "the product's surface texture in fine detail",
    "handling": "held naturally and securely",
}


def detect_product_form(item: str, brand_context: str = "") -> dict:
    """Infer the physical form of the product so prompts stay plausible.

    The item the user named wins; the brand brief is only consulted when the item
    itself gives no signal. Otherwise a soap-focused brand brief would describe a
    serum as a bar of soap.
    """
    for source in (item, brand_context):
        low = (source or "").lower()
        if not low:
            continue
        for form in _PRODUCT_FORMS.values():
            if any(kw in low for kw in form["keywords"]):
                return form
    return _DEFAULT_FORM


def _master_scene(brief: dict) -> tuple[str, str, str]:
    """(subject, setting, styling) tuned to the exact physical identity of LEMED Soap."""
    brand = "LEMED"
    top_item = "สบู่ก้อน"
    item = "rectangular solid herbal soap bar"

    return (
        f"A single hero {item} by {brand} — authentic rectangular solid soap bar with softly beveled edges, "
        "natural warm honey-amber and beige herbal soap body with subtle natural herbal specks, "
        "wrapped around the center with a crisp matte white paper sleeve belly-band with botanical leaf emblem, "
        "bold crisp black 'LEMED' logo, and a gold-ochre horizontal accent banner, resting stable and flat, "
        "hero front-facing angle, label crisp and 100% legible",
        "a warm natural wooden desk or modern minimalist bathroom counter with warm afternoon sunlight and soft organic shadows",
        "a few fresh green botanical leaves (Centella/Cica) and delicate natural clear water droplets, perfectly clean and uncluttered",
    )


# ── Thai voiceover / narrative beats ────────────────────────────────────────────
# Every clip follows Hook → Decision → CTA. Lines stay claim-light on purpose:
# the LEMED brief explicitly warns against over-claiming skincare results.

_VO_LINES: dict[str, dict[str, str]] = {
    "hero_product": {
        "hook": "สิวขึ้นซ้ำ ๆ ทั้งที่ล้างหน้าสะอาดทุกวัน เพราะผิวขาดสมดุล",
        "decision": "สบู่เวชสำอาง {brand} Acne Oil-Control ผสาน 7 สารสำคัญ ใบชุมเห็ดเทศและ BHA สลายสิวอุดตัน คุมมัน โดยไม่ทิ้งความแห้งตึง",
        "cta": "ดูแลสิวด้วยความเข้าใจ ทักแชทรับโปรพิเศษวันนี้",
    },
    "acne_care": {
        "hook": "ใช้สบู่ลดสิวทั่วไปแล้วหน้าแห้ง แสบตึง ลอกเป็นขุยหรือเปล่า?",
        "decision": "LEMED ยึดมาตรฐาน 5-FREE อ่อนโยนต่อเกราะป้องกันผิว ล้างสะอาดคุมมัน แต่ผิวคงความนุ่มชุ่มชื้น",
        "cta": "เพื่อผิวสะอาดอย่างสมดุล ทักแชทปรึกษาเราได้เลย",
    },
    "flash_sale": {
        "hook": "ลดแรงที่สุด เฉพาะวันนี้เท่านั้น",
        "decision": "{item} ลด {discount} เปอร์เซ็นต์ ของมีจำนวนจำกัด",
        "cta": "กดสั่งเลย ก่อนหมดเวลา",
    },
    "winback": {
        "hook": "ไม่ได้เจอกันนาน ผิวคุณเป็นยังไงบ้าง",
        "decision": "เรามีส่วนลด {discount} เปอร์เซ็นต์ รอให้คุณกลับมาดูแลตัวเองอีกครั้ง",
        "cta": "กลับมาเริ่มใหม่วันนี้ ทักแชทรับสิทธิ์ได้เลย",
    },
    "vip_reward": {
        "hook": "ขอบคุณที่ให้เราดูแลผิวคุณมาตลอด",
        "decision": "ลูกค้าคนพิเศษรับส่วนลด {discount} เปอร์เซ็นต์ ก่อนใคร",
        "cta": "รับสิทธิ์ของคุณได้เลยวันนี้",
    },
    "new_customer": {
        "hook": "เพิ่งเริ่มดูแลผิว ไม่รู้จะเลือกอะไรดี",
        "decision": "เริ่มจาก {item} อ่อนโยน ใช้ง่าย ทำได้ทุกวัน",
        "cta": "ลูกค้าใหม่รับส่วนลด {discount} เปอร์เซ็นต์ ทักเลย",
    },
    "seasonal": {
        "hook": "เทศกาลนี้ อยากให้ของขวัญที่คนสำคัญได้ใช้จริง",
        "decision": "เซ็ต {item} พร้อมกล่องของขวัญ ลด {discount} เปอร์เซ็นต์",
        "cta": "สั่งก่อน {expiry} กดลิงก์ได้เลย",
    },
}

_VO_VOICE = {
    "premium": "เสียงผู้หญิงไทย น้ำเสียงนุ่ม สุขุม พูดช้า ชัดถ้อยชัดคำ โทนพรีเมียม",
    "urgent":  "เสียงไทย กระฉับกระเฉง เร่งเร้า จังหวะเร็ว เน้นคำสำคัญให้หนักแน่น",
    "fun":     "เสียงไทย สดใส เป็นกันเอง มีพลัง ยิ้มขณะพูด",
    "friendly": "เสียงผู้หญิงไทย อบอุ่น เป็นมิตร พูดเหมือนคุยกับเพื่อน",
}


def build_voiceover(brief: dict, angle: dict | None = None) -> dict:
    """Thai voiceover script for the Hook → Decision → CTA arc.

    An angle may rewrite the hook and decision lines to match how it tells the
    story. It never touches the CTA: that is where a discount and its deadline
    live, and losing them would quietly turn a flash sale into a brand film.
    """
    lines = dict(_VO_LINES.get(brief.get("campaign", ""), _VO_LINES["hero_product"]))
    if angle and angle.get("vo"):
        lines.update({k: v for k, v in angle["vo"].items() if k in ("hook", "decision")})
    fields = {
        "item": brief.get("top_item") or "สินค้าของเรา",
        "brand": brief.get("brand_name") or "แบรนด์ของเรา",
        "discount": brief.get("discount", 20),
        "expiry": brief.get("expiry", "สิ้นเดือนนี้"),
    }
    return {
        "hook": lines["hook"].format(**fields),
        "decision": lines["decision"].format(**fields),
        "cta": lines["cta"].format(**fields),
        "voice": _VO_VOICE.get(brief.get("tone", ""), _VO_VOICE["friendly"]),
    }


def _scene_preset(scene: str) -> dict:
    """Look up a scene preset; falls back to the studio default."""
    try:
        import scene_presets
        return scene_presets.get(scene)
    except Exception:  # noqa: BLE001 — scene library is optional
        return {}


def _video_angle(key: str) -> dict:
    """Look up a storytelling angle; an unset or unknown key means no rewrite."""
    if not key:
        return {}
    try:
        import scene_presets
        return scene_presets.ANGLES.get(key, {})
    except Exception:  # noqa: BLE001 — scene library is optional
        return {}


def _still_angle(key: str) -> dict:
    """Single-frame overrides for an angle; empty means shoot the scene as-is."""
    if not key:
        return {}
    try:
        import scene_presets
        return scene_presets.still_for(key)
    except Exception:  # noqa: BLE001
        return {}


def _carousel_arc(key: str) -> list:
    """Five-slide arc for an angle; empty means the default Hook→Problem→… arc."""
    if not key:
        return []
    try:
        import scene_presets
        return scene_presets.carousel_arc(key)
    except Exception:  # noqa: BLE001
        return []


def build_master_image_prompt(brief: dict, scene: str = "", angle: str = "") -> str:
    """Structured master prompt for image generation — ready to paste into Flow.

    `scene` selects a preset from scene_presets (lab, student, UGC, …); without
    one the prompt falls back to a clean studio treatment derived from the brief.
    `angle` reframes that scene into a different single shot — a macro texture
    proof, a split before/after, an arm's-length phone photo.
    """
    tone = brief.get("tone", "friendly")
    subject, setting, styling = _master_scene(brief)
    aspect = video_aspect_for(brief)
    preset = _scene_preset(scene) if scene else {}
    still = _still_angle(angle)

    lighting = preset.get("lighting") or _TONE_LIGHT.get(tone, _TONE_LIGHT["friendly"])
    camera = preset.get("camera") or (
        "85mm macro lens, f/2.8, eye-level three-quarter angle, "
        "shallow depth of field with the product tack-sharp")
    mood = _TONE_GRADE.get(tone, _TONE_GRADE["friendly"])
    if preset.get("mood"):
        mood = f"{mood}; overall feeling {preset['mood']}"

    # Every block the model renders from names the product. The scene library is
    # written generically so it suits any brand, and "the product" left standing
    # anywhere in the description is enough for the model to draw whatever shape
    # it sees most often in that setting.
    item = english_item(brief.get("top_item") or "the product")
    named = lambda t: name_the_product(t, item)  # noqa: E731

    fields = {"item": item, "brand": brief.get("brand_name") or "the brand"}
    lines = [
        # The angle decides what the frame is of; the scene still decides where it
        # is and what it looks like, so setting, lighting and styling carry through.
        "[SUBJECT]",
        named(still["subject"].format(**fields)) if still.get("subject") else named(subject),
        "",
        "[SCENE & SETTING]", named(preset.get("setting") or setting), "",
        "[STYLING & PROPS]", named(preset.get("styling") or styling), "",
    ]
    # State the cast either way. Leaving it unsaid is how a disembodied hand ends
    # up reaching in from off-frame with nobody attached to it.
    lines += ["[CAST]", named(preset.get("cast") or _NO_CAST), ""]
    form = detect_product_form(brief.get("top_item", ""), brief.get("brand_context", ""))
    lines += [
        "[LIGHTING]", lighting, "",
        "[CAMERA & LENS]", named(camera), "",
        "[COMPOSITION]",
        named(f"{still['composition']}, framed for {aspect}") if still.get("composition")
        else f"hero composition with generous negative space for caption overlay, "
             f"framed for {aspect}", "",
        "[COLOUR & MOOD]", mood, "",
        "[PHYSICS & PLAUSIBILITY]",
        named(form["physics"] + ". Shadows fall away from the light source and match "
              "the objects casting them; reflections match the surface material; every "
              "item rests on the surface with its full weight — nothing floats or hovers"
              + (". Hands grip the product plausibly with five fingers, natural joints "
                 "and realistic contact pressure" if preset.get("cast") else "")), "",
        "[STYLE]",
        "photorealistic commercial advertising photography, award-winning campaign quality, "
        "clean modern aesthetic", "",
        "[TECHNICAL]",
        f"aspect ratio {aspect}, 4K resolution, sharp focus, natural texture detail", "",
        "[AVOID]",
        _IMAGE_AVOID + ", no floating objects, no impossible shadows, no melted or "
        "warped product shape"
        + (", no extra fingers, no distorted faces, no uncanny expressions"
           if preset.get("cast") else "")
        # Naming the wrong packaging outright — describing the right one was not
        # enough on its own.
        + (f". {form['avoid']}" if form.get("avoid") else ""),
    ]
    return "\n".join(lines)


def build_master_video_prompt(brief: dict, scene: str = "", seconds: int = 10,
                              angle: str = "") -> str:
    """Master video prompt: Hook → Decision → CTA with a Thai voiceover script.

    Defaults to a 10-second spot. Veo caps a single generation at 8 seconds, so
    the 10s version is meant for Google Flow (which can extend); the in-app
    generator passes seconds=8.

    `scene` picks the setting, `angle` picks how the story is told within it. An
    empty angle keeps the scene's own three shots, which is what every clip did
    before angles existed.
    """
    tone = brief.get("tone", "friendly")
    subject, setting, styling = _master_scene(brief)
    aspect = video_aspect_for(brief)
    motion = _TONE_MOTION.get(tone, _TONE_MOTION["friendly"])
    item = english_item(brief.get("top_item") or "the product")
    preset = _scene_preset(scene) if scene else {}
    ang = _video_angle(angle)
    vo = build_voiceover(brief, ang)

    shots = preset.get("shots") or [
        f"Extreme close-up detail of the subject. {subject}.",
        f"Wider hero shot showing the full scene: {setting}, with {styling}.",
        "Final settle on the product centred in frame, held steady for a caption overlay.",
    ]
    shots = list(shots)

    # The angle rewrites the first two beats and leaves the third alone — the
    # scene's payoff is the whole point of choosing that scene.
    fields = {"item": item, "brand": brief.get("brand_name") or "the brand"}
    for i, slot in enumerate(("hook", "decision")):
        # An angle may carry a product-only rewrite of a beat, for scenes where
        # the [CAST] block bans the person the default wording assumes.
        text = (ang.get(f"{slot}_nocast") if not preset.get("cast") else "") \
            or ang.get(slot)
        if text and i < len(shots):
            shots[i] = text.format(**fields)

    shots = [name_the_product(s, item) for s in shots]
    lighting = preset.get("lighting") or _TONE_LIGHT.get(tone, _TONE_LIGHT["friendly"])
    mood = _TONE_GRADE.get(tone, _TONE_GRADE["friendly"])
    if preset.get("mood"):
        mood = f"{mood}; overall feeling {preset['mood']}"

    # Beat timings scale with the requested runtime (roughly 30% / 40% / 30%).
    h_end = max(2, round(seconds * 0.3))
    d_end = max(h_end + 1, round(seconds * 0.7))

    # The CTA is deliberately a silent-performance beat: generated lip-sync reads
    # as fake, so the closing line is narration over a warm look to camera.
    # It builds on the scene's own final shot rather than replacing it — otherwise
    # a before/after loses its side-by-side payoff and a flat lay never resolves.
    closing = shots[2] if len(shots) > 2 else shots[-1]
    # Preset shots are written without terminal punctuation, so appending the CTA
    # ran two sentences together: "…product on the shelf beside Ends with:".
    if closing and closing[-1] not in ".!?":
        closing += "."
    if preset.get("cast"):
        cta_visual = (
            f"{closing} Ends with: the person looks straight into the lens and smiles "
            "warmly — genuine, relaxed, closed mouth or a soft natural smile — "
            "holding the product so its label faces camera. "
            "IMPORTANT: they are NOT speaking — lips stay still, no talking, no "
            "lip-sync. The voiceover plays over this shot as narration."
        )
    else:
        cta_visual = (
            f"{closing} The product settles centred and steady with its label facing "
            "camera and clear space around it for the call-to-action overlay. "
            "No hands enter the frame. The voiceover plays over this shot as narration."
        )
    cta_visual = name_the_product(cta_visual, item)

    beats = [
        ("HOOK", f"0:00-0:0{h_end}" if h_end < 10 else f"0:00-0:{h_end}",
         shots[0], vo["hook"],
         "หยุดนิ้วคนดูให้ได้ใน 3 วินาทีแรก — ตั้งคำถามหรือชี้ปัญหาที่ตรงใจทันที"),
        ("DECISION", f"0:0{h_end}-0:0{d_end}" if d_end < 10 else f"0:0{h_end}-0:{d_end}",
         shots[1] if len(shots) > 1 else shots[0], vo["decision"],
         "ให้เหตุผลว่าทำไมต้องเป็นสินค้านี้ — จุดขาย/ส่วนผสม/ข้อพิสูจน์"),
        ("CTA", f"0:0{d_end}-0:{seconds}" if d_end < 10 else f"0:{d_end}-0:{seconds}",
         cta_visual, vo["cta"],
         "ปิดจบแบบธรรมชาติ — ไม่ขยับปากพูด ใช้เสียงพากย์ทับ ยิ้มให้กล้อง โชว์สินค้าให้ชัด "
         "เว้นที่ว่างสำหรับปุ่ม/ข้อความ CTA"),
    ]

    lines = [
        "[CONCEPT]",
        f"A {seconds}-second vertical commercial spot for {item}, "
        "structured as Hook → Decision → CTA, with a Thai voiceover.", "",
        "[SUBJECT]", subject, "",
    ]
    if preset.get("setting"):
        lines += ["[SCENE & SETTING]", name_the_product(preset["setting"], item), ""]
    lines += ["[CAST]", name_the_product(preset.get("cast") or _NO_CAST, item), ""]
    if ang.get("structure"):
        lines += ["[โครงเรื่อง / STRUCTURE]", f"{ang['label']} — {ang['structure']}", ""]

    for name, timing, visual, vo_line, purpose in beats:
        lines += [
            f"[{name} — {timing}]",
            f"VISUAL: {visual}",
            f"เสียงพากย์ (ไทย): “{vo_line}”",
            f"จุดประสงค์: {purpose}",
            "",
        ]

    form = detect_product_form(brief.get("top_item", ""), brief.get("brand_context", ""))
    continuity = [
        "ทั้ง 3 ช่วงคือฉากเดียวกันต่อเนื่อง ไม่ใช่ 3 คลิปแยก:",
        "• สินค้าชิ้นเดิม รูปทรง สี ฉลาก และขนาดเท่ากันทุกเฟรม",
        "• ทิศทางแสงและอุณหภูมิสีเดิมตลอด เงาทอดไปทางเดียวกัน",
        "• ฉากหลัง พื้นผิว และพร็อพอยู่ตำแหน่งเดิม ไม่สลับที่เอง",
        "• การเคลื่อนไหวต่อเนื่องตามเวลาจริง ไม่กระโดดข้ามหรือย้อนกลับ",
    ]
    if preset.get("cast"):
        continuity.insert(4, "• ตัวแสดงคนเดิม ทรงผม เสื้อผ้า เครื่องประดับเหมือนเดิมทุกช่วง")

    lines += [
        "[STORYBOARD CONTINUITY]",
        *continuity, "",
        # English throughout: this block is read by the model, and mixing scripts
        # is what turned "สบู่" into a bowl of soup.
        "[PHYSICS & PLAUSIBILITY]",
        name_the_product(
            form["physics"] + ". "
            "Water and foam always run downward under gravity. Everything rests on a "
            "real surface — nothing floats. Shadows and reflections match the objects "
            "and the light direction. Camera motion stays continuous and physical."
            # Handling notes only make sense when someone is there to do the handling —
            # describing a grip in a product-only scene invites a stray hand into frame.
            + (f" Handling: {form['handling']}. Hands have five fingers, natural "
               "joints, and realistic contact pressure on the product."
               if preset.get("cast")
               else " The product stands or rests on its own — no hands enter the "
                    "frame to hold or steady it."), item), "",
        "[VOICEOVER DIRECTION]",
        f"{vo['voice']} — พากย์ภาษาไทยทั้งคลิป ออกเสียงชัด "
        "จังหวะพอดีกับความยาวแต่ละช่วง ไม่รีบจนฟังไม่ทัน",
        "เสียงพากย์เป็น narration ทับภาพ ไม่ใช่บทพูดของตัวแสดง — "
        "ตัวแสดงในคลิปไม่ต้องขยับปากพูดตามเสียง โดยเฉพาะช่วง CTA "
        "(voiceover narration over B-roll, no on-camera dialogue, no lip-sync)", "",
        # Labelled as post-production so it does not fight the "no on-screen
        # text" rule below. Generated Thai lettering comes out malformed, so the
        # model must render none — subtitles get added in the edit.
        "[SUBTITLES — ใส่ตอนตัดต่อ ไม่ต้องเรนเดอร์ในคลิป / do NOT render this text]",
        f"HOOK: {vo['hook']}",
        f"DECISION: {vo['decision']}",
        f"CTA: {vo['cta']}",
        "(ซับไตเติลไทยตรงกับเสียงพากย์ วางล่างกลางเฟรม — เป็นงานขั้นตัดต่อ)", "",
        "[CAMERA MOVEMENT]",
        # A scene that specifies its own movement wins, over the angle as well as
        # the tone. Those overrides exist to settle real contradictions — a
        # locked-off before/after, a deliberately unstable UGC clip — and letting
        # an angle's "slow cinematic push-in" through would reopen them.
        name_the_product(
            preset.get("movement") or ang.get("movement")
            or f"{motion}; smooth controlled moves, no handheld shake", item),
        "",
        "[LIGHTING]", lighting, "",
        "[COLOUR & MOOD]", mood, "",
        "[AUDIO]",
        "Thai voiceover as scripted above, mixed clearly on top; "
        "soft ambient background music matching the mood at low level; "
        "subtle foley (gentle liquid and fabric sounds)", "",
        "[STYLE]",
        "photorealistic, high production value commercial film, "
        "shot on cinema camera, 24fps motion cadence", "",
        "[TECHNICAL]",
        f"aspect ratio {aspect}, {seconds} seconds total, 4K, continuous consistent "
        "lighting and product design across all beats", "",
        "[AVOID]",
        _VIDEO_AVOID + (", no extra fingers, no distorted faces, no morphing between shots"
                        if preset.get("cast") else "")
        + ", no lip-sync, no talking-head dialogue, no mouth movement matching the "
          "voiceover, no forced or exaggerated smile"
        + ", no floating or hovering objects, no impossible shadows, no product "
          "changing shape size or label between shots, no liquid flowing upward, "
          "no objects teleporting or appearing from nowhere, no background swapping "
          "mid-clip"
        + (f". {form['avoid']}" if form.get("avoid") else "")
        + ", ห้ามพากย์ภาษาอื่นนอกจากไทย, ห้ามเสียงหุ่นยนต์",
    ]
    return "\n".join(lines)


# ── Carousel / poster set ───────────────────────────────────────────────────────

# Slide roles that put the product in frame. The others — the scroll-stopping
# headline, the pain being named — deliberately keep it small or absent, so their
# prompts describe a brand visual instead of a hero shot.
_CAROUSEL_HERO_ROLES = {
    "SOLUTION", "PROOF", "CTA",
    "REASON1", "REASON2", "REASON3", "STEP1", "STEP2", "STEP3",
    "TRUTH", "WHY", "DURING", "AFTER", "TURN", "RESULT",
    "SURFACE", "FOAM", "SHADOW", "REVEAL", "DETAIL",
}

_CAROUSEL_ROLES = [
    ("HOOK", "🪝 สะดุดตา",
     "ข้อความใหญ่เต็มเฟรม ตั้งคำถามหรือชี้ปัญหา ภาพเรียบ ไม่แย่งความสนใจจากตัวหนังสือ",
     "bold minimal composition with a very large clear area for a single big headline, "
     "product small or absent, high contrast background"),
    ("PROBLEM", "😣 ปัญหาที่เจอ",
     "ขยายความเจ็บปวดให้คนดูพยักหน้าตาม",
     "relatable close-up illustrating the problem, muted desaturated grade, "
     "space at the bottom for two lines of text"),
    ("SOLUTION", "✨ ทางออก",
     "แนะนำสินค้าเป็นคำตอบ",
     "clean hero shot of the product taking centre stage, bright optimistic grade, "
     "clear space beside the product for a short headline"),
    ("PROOF", "🔬 ข้อพิสูจน์",
     "ส่วนผสม/รีวิว/ผลลัพธ์ ที่ทำให้เชื่อ",
     "detail shot showing ingredients or texture evidence, informative layout with "
     "room for three short bullet labels"),
    ("CTA", "🎯 ลงมือ",
     "บอกสิ่งที่ต้องทำต่อ พร้อมข้อเสนอ",
     "product with a bold offer banner area, strong colour block reserved for the "
     "price and call-to-action button, centred and unmissable"),
]


def build_carousel(brief: dict, scene: str = "", slides: int = 5,
                   angle: str = "") -> list[dict]:
    """Poster carousel: one master prompt + Thai on-slide copy per slide.

    Follows the same Hook → Decision → CTA arc as the video, expanded across
    slides so the set reads as one story. `angle` swaps that arc for another
    argument told over the same five slides — three reasons, a how-to, a myth
    corrected — while the scene keeps deciding how every slide looks.
    """
    vo = build_voiceover(brief, _video_angle(angle))
    preset = _scene_preset(scene) if scene else {}
    tone = brief.get("tone", "friendly")
    subject, setting, styling = _master_scene(brief)
    brand = brief.get("brand_name") or "แบรนด์ของเรา"
    item = brief.get("top_item") or "สินค้าของเรา"
    discount = brief.get("discount", 20)
    aspect = "4:5"  # the carousel ratio that performs best on IG/Facebook

    # Visual direction is English so the model does not phonetically misread a
    # Thai noun; the on-slide copy is Thai because a human reads it.
    en_item = english_item(item)
    named = lambda t: name_the_product(t, en_item)  # noqa: E731
    fields = {"item": item, "brand": brand, "discount": discount}

    copy_map = {
        "HOOK": (vo["hook"], "เลื่อนดูต่อ →"),
        "PROBLEM": ("ล้างหน้าสะอาดแล้ว แต่ปัญหายังอยู่",
                    "เพราะการดูแลผิวไม่ได้จบแค่ความสะอาด"),
        "SOLUTION": (f"{item}", vo["decision"]),
        "PROOF": ("ทำไมลูกค้าถึงบอกต่อ",
                  "• ส่วนผสมที่อ่อนโยน  • ใช้ได้ทุกวัน  • ไม่ทิ้งความแห้งตึง"),
        "CTA": (f"ลด {discount}%", vo["cta"]),
    }

    # An angle brings its own five slides, copy included. Roles the default arc
    # never had — REASON2, MYTH, STEP3 — carry their text with them.
    arc = _carousel_arc(angle) or [(*r, None, None) for r in _CAROUSEL_ROLES]

    out: list[dict] = []
    for i, row in enumerate(arc[:slides], 1):
        role, th_label, purpose, comp = row[:4]
        head, sub_t = (row[4], row[5]) if len(row) > 5 else (None, None)
        if head is None:
            headline, sub = copy_map.get(role, ("", ""))
        else:
            headline = head.format(**fields)
            # An arc slide may leave its sub blank to inherit the campaign line —
            # that is how the shared CTA slide keeps a flash sale's deadline.
            sub = sub_t.format(**fields) if sub_t else copy_map.get(role, ("", ""))[1]

        lines = [
            "[SUBJECT]",
            named(subject) if role in _CAROUSEL_HERO_ROLES
            else f"Brand visual for {brand}, product not the focus of this slide", "",
            "[SCENE & SETTING]", named(preset.get("setting") or setting), "",
            "[STYLING & PROPS]", named(preset.get("styling") or styling), "",
        ]
        lines += ["[CAST]", named(preset.get("cast") or _NO_CAST), ""]
        lines += [
            "[LIGHTING]",
            preset.get("lighting") or _TONE_LIGHT.get(tone, _TONE_LIGHT["friendly"]), "",
            "[CAMERA & LENS]",
            named(preset.get("camera") or "50mm lens, f/4, straight-on angle"), "",
            "[COMPOSITION]", named(comp), "",
            "[COLOUR & MOOD]", _TONE_GRADE.get(tone, _TONE_GRADE["friendly"]), "",
            "[STYLE]",
            "photorealistic commercial advertising photography, cohesive with the other "
            "slides in this carousel — same lighting, palette and product styling", "",
            "[TECHNICAL]",
            f"aspect ratio {aspect}, 4K, slide {i} of {slides} in one carousel set", "",
            "[AVOID]",
            _IMAGE_AVOID + (", no extra fingers, no distorted faces" if preset.get("cast") else ""),
        ]
        out.append({
            "n": i,
            "role": role,
            "label": th_label,
            "purpose": purpose,
            "headline_th": headline,
            "sub_th": sub,
            "prompt": "\n".join(lines),
        })
    return out


_TONE_MOTION = {
    "premium": "slow elegant camera push-in, shallow depth of field, calm luxurious mood",
    "urgent":  "quick punchy cuts, dynamic camera moves, energetic promotional pace",
    "fun":     "playful bouncy motion, bright lively pacing, upbeat feel",
    "friendly": "gentle smooth camera drift, warm natural light, relaxed inviting pace",
}

# Vertical platforms want 9:16; everything else reads better as 16:9.
_VERTICAL_PLATFORMS = {"tiktok", "instagram"}


def video_aspect_for(brief: dict) -> str:
    """Pick an aspect ratio that suits the target platforms."""
    plats = set(brief.get("platforms") or [])
    return "9:16" if plats & _VERTICAL_PLATFORMS else "16:9"


def build_video_prompt(brief: dict) -> str:
    """Short cinematic prompt for Veo, derived from the brief."""
    brand = brief.get("brand_name") or "the brand"
    item = brief.get("top_item") or "the product"
    motion = _TONE_MOTION.get(brief.get("tone", ""), _TONE_MOTION["friendly"])
    if brief.get("vertical") == "product":
        scene = (
            f"Cinematic product commercial for {item} by {brand}. "
            "The product sits on a clean minimal surface with soft studio lighting, "
            "delicate water droplets and fresh botanical accents around it"
        )
    else:
        scene = (
            f"Cinematic food commercial for {item} at {brand}. "
            "Freshly served dish with steam rising, warm inviting restaurant lighting"
        )
    return (
        f"{scene}. {motion}. Photorealistic, high production value, "
        "crisp focus on the product, no text overlay, no watermark."
    )


def describe(brief: dict) -> str:
    """One-line human summary of a brief (used when Claude gives no summary)."""
    campaign_label = CAMPAIGN_TYPES.get(brief.get("campaign", ""), {}).get(
        "label", brief.get("campaign", "")
    )
    plats = ", ".join(
        PLATFORMS[p]["name"] for p in brief.get("platforms", []) if p in PLATFORMS
    )
    tone = brief.get("tone", "")
    tone_label = f"โทน {tone}" if tone else ""
    parts = [x for x in (campaign_label, tone_label, f"ลง {plats}" if plats else "") if x]
    return " · ".join(parts)


def generate(prompt: str, api_key: str = "", default_brand: str = "ร้านของคุณ",
             use_brand_context: bool = True, provider: str = "auto",
             vertical: str = "auto") -> tuple[dict, dict]:
    """Full pipeline: chat message → (brief, content package).

    Returns:
        brief:   the interpreted intent (campaign/platforms/tone/…)
        package: {platform: content_str, ..., "image_prompt": "..."}
    """
    brand_context = load_brand_context() if use_brand_context else ""
    brief = interpret(prompt, api_key, default_brand, brand_context, provider)
    brief["used_brand_context"] = bool(brand_context)
    context = build_context(brief)

    # Decide the vertical from everything we know — the user's own words count too,
    # so this still works when mandala-bot (and its brand brief) isn't available.
    # An explicit setting always wins, which covers prompts too vague to classify.
    if vertical in ("auto", "", None):
        from content_studio import detect_vertical
        # What the user actually typed wins; the brand brief only breaks ties,
        # otherwise a skincare brand brief would mislabel a one-off F&B request.
        vertical = detect_vertical(prompt, default="") or detect_vertical(
            f"{brand_context} {brief.get('top_item', '')}")
    brief["vertical"] = vertical
    # Keep the brief around so prompt builders can infer the physical product form
    # (a soap bar cannot pour; a bottle cannot lather).
    brief["brand_context"] = brand_context[:1500]

    package = get_content_package(
        campaign_type=brief["campaign"],
        context=context,
        tone=brief["tone"],
        api_key=api_key.strip() if api_key else "",
        brand_context=brand_context,
        provider=provider,
        vertical=vertical,
    )

    # Master prompts are the deliverable the user pastes into Google Flow, so they
    # always come from the structured builder — the model's own one-liner is kept
    # only as a short alternative.
    package["image_prompt_short"] = package.get("image_prompt") or build_image_prompt(brief)
    package["image_prompt"] = build_master_image_prompt(brief)
    package["video_prompt"] = build_master_video_prompt(brief)

    return brief, package
