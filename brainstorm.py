"""Brain Storm — Business Model Canvas → content ideas → Copilot prompts.

The strategy stage of the pipeline. Takes a short business description (and,
later, live insight data) and:
  1. drafts a Business Model Canvas (9 blocks), and
  2. proposes concrete content ideas grounded in that canvas.

Each idea carries a ready-to-use Thai prompt that can be handed straight to the
Chat Copilot, closing the loop: Brain Storm → Copilot → Drive → Approve → Post.

Works with OR without a Claude API key (keyword/template fallback).
"""

from __future__ import annotations

import json
import re

from content_studio import CAMPAIGN_TYPES, TONES, PLATFORMS

MODEL = "claude-sonnet-4-6"  # mirror content_studio / content_copilot

# key, English label, Thai guiding question — order matches the printed canvas.
BMC_BLOCKS: list[tuple[str, str, str]] = [
    ("key_partners",           "Key Partners",           "พันธมิตรที่ให้เปรียบเชิงแข่งขัน"),
    ("key_activities",         "Key Activities",         "ก้าวสำคัญที่พาไปหาลูกค้า"),
    ("key_resources",          "Key Resources",          "ทรัพยากรที่ต้องใช้ให้ไอเดียเวิร์ก"),
    ("key_propositions",       "Key Propositions",       "ทำให้ชีวิตลูกค้าดีขึ้นอย่างไร"),
    ("customer_relationships", "Customer Relationships", "จะ interact กับลูกค้าบ่อยแค่ไหน"),
    ("channels",               "Channels",               "เข้าถึงลูกค้าผ่านช่องทางไหน"),
    ("customer_segments",      "Customer Segments",      "ลูกค้าคือใคร กลุ่มเป้าหมาย"),
    ("cost_structure",         "Cost Structure",         "งบพัฒนา + การตลาดต่อรอบ"),
    ("revenue_streams",        "Revenue Streams",        "รายได้ที่ตั้งเป้า เทียบต้นทุน"),
]

_BMC_KEYS = [b[0] for b in BMC_BLOCKS]

DEFAULT_BUSINESS = (
    "LEMED — แบรนด์สกินแคร์ เน้นดูแลผิวด้วยส่วนผสมที่อ่อนโยนและมีงานวิจัยรองรับ "
    "กลุ่มเป้าหมายคนเมืองอายุ 20-40 ที่ใส่ใจสุขภาพผิว ขายผ่านออนไลน์เป็นหลัก"
)


# ── Business Model Canvas ───────────────────────────────────────────────────────

def _bmc_local(business_desc: str) -> dict:
    """Template BMC — no API key needed. Skincare-leaning, generic enough for F&B."""
    return {
        "key_partners":           "ผู้ผลิต/โรงงานได้มาตรฐาน, KOL/รีวิวเวอร์, แพลตฟอร์มขายออนไลน์, ขนส่ง",
        "key_activities":         "ผลิตคอนเทนต์สม่ำเสมอ, ให้ความรู้, ดูแลลูกค้า, เก็บรีวิว/UGC",
        "key_resources":          "แบรนด์ + คอนเทนต์, ฐานลูกค้า/CRM, ทีมครีเอทีฟ, ข้อมูลการขาย",
        "key_propositions":       "ผลลัพธ์ที่พิสูจน์ได้ + ปลอดภัย/อ่อนโยน + คุ้มค่า ทำให้ลูกค้ามั่นใจในผิวตัวเอง",
        "customer_relationships": "ตอบเร็ว เป็นกันเอง ผ่านแชท, ติดตามหลังการขาย, โปรสำหรับสมาชิก",
        "channels":               "Facebook, Instagram, TikTok, LINE OA, YouTube",
        "customer_segments":      "คนเมือง 20-40 ใส่ใจสุขภาพผิว, ลูกค้าเก่าที่รอโปร, มือใหม่ที่กำลังเลือกแบรนด์",
        "cost_structure":         "ต้นทุนสินค้า, ค่าโฆษณา/คอนเทนต์, ค่า KOL, ค่าขนส่ง/แพลตฟอร์ม",
        "revenue_streams":        "ขายปลีกออนไลน์, ชุดเซ็ต/บันเดิล, สมาชิก/ซื้อซ้ำ, โปรตามเทศกาล",
    }


def _bmc_ai(business_desc: str, api_key: str, brand_context: str = "",
            provider: str = "auto") -> dict | None:
    try:
        import ai_provider
    except ImportError:
        return None

    system_prompt = (
        "คุณเป็นที่ปรึกษากลยุทธ์ธุรกิจ ช่วยร่าง Business Model Canvas สั้น กระชับ "
        "เป็นภาษาไทย แต่ละช่องตอบ 1-2 ประโยคหรือ bullet สั้น ๆ อิงข้อมูลธุรกิจที่ให้"
    )
    if brand_context:
        system_prompt += "\n\nบริบทแบรนด์จริง (อิงข้อมูลนี้ อย่าแต่งเพิ่ม):\n" + brand_context

    keys_desc = "\n".join(f'- "{k}": {label} ({q})' for k, label, q in BMC_BLOCKS)
    user_prompt = (
        f"ธุรกิจ: {business_desc}\n\n"
        "ตอบ JSON เท่านั้น โดยมีคีย์เหล่านี้ (ค่าทุกช่องเป็นสตริงภาษาไทย):\n"
        f"{keys_desc}"
    )

    data = ai_provider.generate_json(
        system_prompt, user_prompt, api_key, provider=provider, max_tokens=1500
    )
    if not isinstance(data, dict):
        return None
    # Fill any missing block from the local template so the UI never has holes.
    local = _bmc_local(business_desc)
    return {k: str(data.get(k) or local[k]).strip() for k in _BMC_KEYS}


def load_brand_context() -> str:
    """Pull the Mandala AI brand brief, if mandala-bot is available locally."""
    try:
        import mandala_client
        return mandala_client.build_context_block(include_samples=1)
    except Exception:  # noqa: BLE001 — context is a bonus, never a hard dependency
        return ""


def generate_bmc(business_desc: str, api_key: str = "", brand_context: str = "",
                 provider: str = "auto") -> dict:
    """Draft a Business Model Canvas from a business description."""
    business_desc = (business_desc or DEFAULT_BUSINESS).strip()
    if api_key and api_key.strip():
        bmc = _bmc_ai(business_desc, api_key.strip(), brand_context, provider)
        if bmc:
            return bmc
    return _bmc_local(business_desc)


# ── Content ideas ───────────────────────────────────────────────────────────────

def _sanitize_idea(raw: dict) -> dict:
    campaign = raw.get("campaign")
    if campaign not in CAMPAIGN_TYPES:
        campaign = "hero_product"
    tone = raw.get("tone")
    if tone not in TONES:
        tone = "friendly"
    platforms = [p for p in (raw.get("platforms") or []) if p in PLATFORMS]
    if not platforms:
        platforms = ["facebook", "instagram", "line_oa"]
    title = (raw.get("title") or CAMPAIGN_TYPES[campaign]["label"]).strip()
    rationale = (raw.get("rationale") or CAMPAIGN_TYPES[campaign].get("goal", "")).strip()
    prompt = (raw.get("prompt") or "").strip()
    if not prompt:
        pnames = " + ".join(PLATFORMS[p]["name"] for p in platforms)
        prompt = f"{title} ลง {pnames} โทน {tone}"
    return {
        "title": title,
        "campaign": campaign,
        "platforms": platforms,
        "tone": tone,
        "prompt": prompt,
        "rationale": rationale,
    }


def _ideas_local(bmc: dict, business_desc: str, n: int) -> list[dict]:
    segment = bmc.get("customer_segments", "ลูกค้าทั่วไป").split(",")[0].strip()
    brand = "LEMED" if "lemed" in (business_desc or "").lower() else "แบรนด์"
    picks = [
        ("hero_product", ["instagram", "facebook"], "premium"),
        ("flash_sale",   ["line_oa", "facebook"],   "urgent"),
        ("new_customer", ["instagram", "line_oa"],  "friendly"),
        ("seasonal",     ["facebook", "instagram", "tiktok"], "fun"),
        ("vip_reward",   ["line_oa"],               "premium"),
        ("winback",      ["line_oa", "facebook"],   "friendly"),
    ]
    ideas: list[dict] = []
    for campaign, platforms, tone in picks[:max(1, n)]:
        label = CAMPAIGN_TYPES[campaign]["label"]
        pnames = " + ".join(PLATFORMS[p]["name"] for p in platforms)
        ideas.append(_sanitize_idea({
            "title": label,
            "campaign": campaign,
            "platforms": platforms,
            "tone": tone,
            "prompt": f"{label} ของ {brand} สำหรับกลุ่ม {segment} ลง {pnames} โทน {tone}",
            "rationale": CAMPAIGN_TYPES[campaign].get("goal", ""),
        }))
    return ideas


def _ideas_ai(bmc: dict, business_desc: str, api_key: str, n: int,
              brand_context: str = "", provider: str = "auto") -> list[dict] | None:
    try:
        import ai_provider
    except ImportError:
        return None

    system_prompt = (
        "คุณเป็นนักวางแผนคอนเทนต์การตลาด แปลง Business Model Canvas เป็นไอเดียคอนเทนต์ "
        "ที่ลงมือทำได้จริง อิง Key propositions / Customer segments / Channels เป็นหลัก "
        f"campaign ต้องเป็นหนึ่งใน {list(CAMPAIGN_TYPES.keys())} "
        f"tone ต้องเป็นหนึ่งใน {list(TONES.keys())} "
        f"platforms เป็น subset ของ {list(PLATFORMS.keys())}"
    )
    if brand_context:
        system_prompt += "\n\nบริบทแบรนด์จริง (อิงข้อมูลนี้ อย่าแต่งสรรพคุณเพิ่ม):\n" + brand_context

    user_prompt = (
        f"ธุรกิจ: {business_desc}\n"
        f"BMC: {json.dumps(bmc, ensure_ascii=False)}\n\n"
        f"เสนอ {n} ไอเดียคอนเทนต์ ตอบ JSON เป็น array เท่านั้น แต่ละอันมีคีย์:\n"
        '{"title":"ชื่อไอเดียสั้น ๆ","campaign":"...","platforms":["..."],"tone":"...",'
        '"prompt":"ประโยคภาษาไทยพร้อมสั่งใน chat copilot","rationale":"เหตุผลสั้น ๆ ว่าทำไมไอเดียนี้เวิร์ก"}'
    )

    data = ai_provider.generate_json(
        system_prompt, user_prompt, api_key, provider=provider,
        max_tokens=2000, expect_list=True,
    )
    if not isinstance(data, list):
        return None
    ideas = [_sanitize_idea(x) for x in data if isinstance(x, dict)]
    return ideas or None


def generate_ideas(bmc: dict, business_desc: str = "", api_key: str = "", n: int = 4,
                   brand_context: str = "", provider: str = "auto") -> list[dict]:
    """Propose content ideas grounded in the BMC."""
    if api_key and api_key.strip():
        ideas = _ideas_ai(bmc, business_desc, api_key.strip(), n, brand_context, provider)
        if ideas:
            return ideas[:n]
    return _ideas_local(bmc, business_desc, n)
