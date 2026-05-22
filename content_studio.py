"""Content Studio — AI-powered multi-platform content generation.

Flow:
  Business Insight (RFM + metrics) → Claude API → Content Package
  Content Package → Platform Router → Scheduled Posts (per platform)
"""

from __future__ import annotations

import datetime as dt
import json
import re
from typing import Any

# ── Platform definitions ───────────────────────────────────────────────────────

PLATFORMS: dict[str, dict] = {
    "line_oa": {
        "name": "LINE OA",
        "icon": "💚",
        "color": "#06C755",
        "max_chars": 1000,
        "content_types": ["text", "image", "rich_menu"],
        "best_hours": [11, 17, 20],
        "routes": ["text", "image"],
        "description": "ส่งตรงหา follower ทันที อัตราเปิดอ่านสูงสุด",
    },
    "facebook": {
        "name": "Facebook",
        "icon": "🔵",
        "color": "#1877F2",
        "max_chars": 63206,
        "content_types": ["post", "reel", "story", "ad"],
        "best_hours": [9, 13, 20],
        "routes": ["text", "image", "video"],
        "description": "Reach กว้าง เหมาะ promotion และ awareness",
    },
    "instagram": {
        "name": "Instagram",
        "icon": "🟣",
        "color": "#E1306C",
        "max_chars": 2200,
        "content_types": ["feed", "reel", "story", "carousel"],
        "best_hours": [9, 17, 21],
        "routes": ["image", "video", "carousel"],
        "description": "Visual-first, เหมาะ product showcase และ branding",
    },
    "tiktok": {
        "name": "TikTok",
        "icon": "⬛",
        "color": "#000000",
        "max_chars": 2200,
        "content_types": ["video", "photo_mode", "live"],
        "best_hours": [19, 21, 22],
        "routes": ["video"],
        "description": "Viral potential สูง เหมาะ demo และ behind-the-scenes",
    },
    "youtube": {
        "name": "YouTube",
        "icon": "🔴",
        "color": "#FF0000",
        "max_chars": 5000,
        "content_types": ["video", "shorts", "community"],
        "best_hours": [12, 17, 20],
        "routes": ["video"],
        "description": "Long-form และ Shorts, SEO ดี ลูกค้าค้นหาผ่าน Google ได้",
    },
}

CAMPAIGN_TYPES = {
    "winback": {
        "label": "🔄 Win-back ลูกค้าหาย",
        "target": "At Risk / Lost",
        "goal": "กระตุ้นให้ลูกค้าที่ไม่มาซื้อ กลับมาใช้บริการ",
        "urgency": "high",
    },
    "flash_sale": {
        "label": "⚡ Flash Sale / Happy Hour",
        "target": "ช่วงยอดต่ำ",
        "goal": "เพิ่ม traffic ในช่วงเวลาที่ยอดอ่อน",
        "urgency": "very_high",
    },
    "hero_product": {
        "label": "⭐ Hero Product Spotlight",
        "target": "Potential Loyalists",
        "goal": "ดัน item ที่ margin สูงสุด ให้ลูกค้าสั่งมากขึ้น",
        "urgency": "medium",
    },
    "vip_reward": {
        "label": "👑 VIP Reward / Champions",
        "target": "Champions / Loyal",
        "goal": "รักษาและขยาย Champions ด้วย exclusive offer",
        "urgency": "low",
    },
    "new_customer": {
        "label": "🌟 Welcome ลูกค้าใหม่",
        "target": "Recent Customers",
        "goal": "กระตุ้นให้ซื้อครั้งที่ 2 ภายใน 7 วัน",
        "urgency": "medium",
    },
    "seasonal": {
        "label": "🎉 Seasonal / Event",
        "target": "All Customers",
        "goal": "สร้าง awareness โปรพิเศษตามเทศกาล",
        "urgency": "medium",
    },
}

TONES = {
    "friendly": "เป็นกันเอง อบอุ่น ใช้ภาษาง่าย",
    "urgent": "เร่งด่วน สร้าง FOMO เวลาจำกัด",
    "premium": "ดูพรีเมียม หรูหรา exclusive",
    "fun": "สนุกสนาน ขำขัน ใช้ emoji เยอะ",
}

# ── Local content templates (no API key needed) ────────────────────────────────

_LOCAL_TEMPLATES: dict[str, dict[str, str]] = {
    "winback": {
        "line_oa": (
            "🙏 {brand_name} คิดถึงคุณนะ!\n\n"
            "เราสังเกตว่าคุณยังไม่ได้แวะมาสักพักแล้ว 🥺\n\n"
            "✨ พิเศษสำหรับคุณโดยเฉพาะ:\n"
            "🎁 ส่วนลด {discount}% สำหรับออเดอร์ถัดไป\n"
            "⏰ ใช้ได้ถึง {expiry}\n\n"
            "กลับมาหาเราได้เลยนะ 💛\n"
            "👉 {cta}"
        ),
        "facebook": (
            "💌 เรารู้ว่าคุณอาจจะยุ่ง… แต่เราก็คิดถึงคุณอยู่นะ! 🤍\n\n"
            "มีหลายสิ่งที่อัปเดตตั้งแต่ครั้งล่าสุดที่คุณมาเยี่ยม:\n"
            "✅ เมนูใหม่ที่คุณน่าจะชอบ: {top_item}\n"
            "✅ บรรยากาศที่อุ่นเหมือนเดิม\n"
            "✅ และออฟเฟอร์พิเศษรอคุณอยู่ 🎁\n\n"
            "📍 {brand_name} รอคุณอยู่เสมอ\n"
            "🔗 จองโต๊ะหรือสั่งออนไลน์ได้ที่ลิงก์ในโปรไฟล์\n\n"
            "#WeCareAboutYou #{brand_tag} #กลับมาหาเราได้เลย"
        ),
        "instagram": (
            "We miss you. 🤍\n\n"
            "บางครั้งชีวิตยุ่งจนลืมหยุดพักชาร์จพลัง — "
            "แต่เรายังอยู่ตรงนี้เสมอนะ 🌿\n\n"
            "{top_item} ยังรอคุณอยู่ พร้อม offer พิเศษ\n\n"
            "📸 Tag เพื่อนมาด้วยกันเลย!\n\n"
            "#{brand_tag} #MissYou #ComeBack #ร้านดีต้องบอกต่อ "
            "#อาหารอร่อย #กรุงเทพ"
        ),
        "tiktok": (
            "[HOOK 0:00-0:03]\n"
            "\"POV: ร้านโปรดของคุณส่ง message หาหลังจากหายไป {days} วัน\"\n\n"
            "[SCENE 0:03-0:15]\n"
            "แสดงภาพ {top_item} ที่อร่อย เสียง ASMR\n"
            "Text overlay: 'เราคิดถึงคุณนะ 🥺'\n\n"
            "[CTA 0:15-0:20]\n"
            "\"ส่วนลด {discount}% รอคุณอยู่ — Link in bio!\"\n\n"
            "Caption: กลับมาหาเราได้เลยนะ {brand_name} คิดถึง 🤍\n"
            "#{brand_tag} #ร้านอาหาร #fyp #foryou #อาหารอร่อย"
        ),
        "youtube": (
            "Title: เราคิดถึงคุณ — {brand_name} มีอะไรใหม่รอคุณอยู่! 🎁\n\n"
            "Description:\n"
            "สวัสดีลูกค้าทุกคน! วันนี้เรามีอัปเดตสำคัญและ offer พิเศษ "
            "สำหรับลูกค้าที่ยังไม่ได้กลับมาเยี่ยมเราสักพัก\n\n"
            "ในวิดีโอนี้:\n"
            "00:00 - เราคิดถึงคุณ\n"
            "00:30 - เมนูใหม่ที่คุณต้องลอง: {top_item}\n"
            "01:00 - Offer พิเศษ {discount}% สำหรับคุณ\n"
            "01:30 - วิธีรับสิทธิ์\n\n"
            "Tags: {brand_name}, ร้านอาหาร, อาหารอร่อย, โปรโมชั่น, {brand_tag}"
        ),
        "image_prompt": (
            "Warm and inviting restaurant interior, soft golden lighting, "
            "beautifully plated {top_item} on a wooden table, "
            "steam rising, shallow depth of field, food photography style, "
            "cozy atmosphere, Thai restaurant aesthetic, 4K quality"
        ),
    },
    "flash_sale": {
        "line_oa": (
            "⚡ FLASH SALE วันนี้เท่านั้น!\n\n"
            "🕐 {start_time} - {end_time} น. วันนี้\n"
            "💥 ลด {discount}% ทุกเมนู\n\n"
            "🔥 {top_item} ราคาพิเศษสุดๆ!\n\n"
            "⏰ เวลาจำกัด! อย่าพลาด\n"
            "📞 โทรจองหรือสั่งผ่านแอปได้เลย"
        ),
        "facebook": (
            "⚡⚡ FLASH SALE เปิดแล้ว!! ⚡⚡\n\n"
            "🕐 วันนี้ {start_time}-{end_time} น. เท่านั้น!!!\n"
            "💥 ลด {discount}% ทุกรายการ\n\n"
            "🔥 HIGHLIGHT:\n"
            "• {top_item} — ราคาพิเศษสุด!\n"
            "• ไม่มีขั้นต่ำ\n"
            "• ใช้ได้ทุกโต๊ะ\n\n"
            "📍 {brand_name} ทุกสาขา\n"
            "⚠️ มาก่อนได้สิทธิ์ก่อน!\n\n"
            "#FlashSale #ลดราคา #{brand_tag} #วันนี้เท่านั้น"
        ),
        "instagram": (
            "⚡ FLASH SALE ⚡\n\n"
            "{start_time} - {end_time} วันนี้เท่านั้น!\n"
            "ลด {discount}% ทุกเมนู 🔥\n\n"
            "มาเลย! ก่อนหมด 💨\n\n"
            "#FlashSale #{brand_tag} #ลดราคา #อาหารอร่อย #กรุงเทพ #foodbangkok"
        ),
        "tiktok": (
            "[HOOK 0:00-0:02]\n"
            "\"ลด {discount}% อีก {countdown} ชั่วโมง!!\" (ข้อความใหญ่)\n\n"
            "[ACTION 0:02-0:12]\n"
            "Montage อาหารอร่อย เสียง trending\n"
            "Clock countdown overlay\n\n"
            "[CTA 0:12-0:15]\n"
            "\"วิ่งมาเลย! {brand_name} รออยู่!\"\n\n"
            "#FlashSale #ลดด่วน #{brand_tag} #fyp #อาหารอร่อย"
        ),
        "youtube": (
            "Title: FLASH SALE {discount}% OFF วันนี้เท่านั้น!! | {brand_name}\n\n"
            "Description:\n"
            "🔥 FLASH SALE ด่วน! {start_time}-{end_time} น. วันนี้เท่านั้น\n"
            "ลด {discount}% ทุกเมนูที่ {brand_name}\n\n"
            "อย่าพลาด! Subscribe เพื่อรับ notification โปรใหม่ทุกครั้ง\n\n"
            "Tags: flash sale, ลดราคา, {brand_name}, อาหารอร่อย, โปรโมชั่น"
        ),
        "image_prompt": (
            "Bold flash sale promotional banner, bright red and gold colors, "
            "{discount}% discount text in large font, "
            "{top_item} featured prominently, urgency design, "
            "countdown timer element, Thai restaurant style, vibrant"
        ),
    },
    "hero_product": {
        "line_oa": (
            "⭐ เมนูที่ต้องลอง!\n\n"
            "🍽️ {top_item}\n"
            "เมนูขายดี อันดับ 1 ของเรา!\n\n"
            "รสชาติที่ทุกคนพูดถึง 😋\n"
            "สั่งได้เลยทุกวัน เวลา {hours}\n\n"
            "📍 {brand_name} ทุกสาขา"
        ),
        "facebook": (
            "🌟 Have you tried our signature {top_item} yet?\n\n"
            "เมนูนี้เป็นที่รักของลูกค้าทุกคน เพราะ:\n"
            "✅ ทำจากวัตถุดิบคุณภาพ\n"
            "✅ รสชาติที่ลงตัว ไม่เหมือนใคร\n"
            "✅ คุ้มค่าทุกคำ\n\n"
            "📸 ลอง tag เพื่อนที่ต้องมาลองด้วยกัน!\n\n"
            "#MustTry #{brand_tag} #SignatureDish #อาหารอร่อย"
        ),
        "instagram": (
            "Meet your new obsession. 🌟\n\n"
            "{top_item} — เมนูที่ทุกคนพูดถึง\n\n"
            "🍽️ สั่งได้ทุกวัน\n"
            "📍 {brand_name}\n\n"
            "Double tap ถ้าอยากลอง! ❤️\n\n"
            "#FoodPorn #MustEat #{brand_tag} #Bangkok #Foodie #อาหารไทย #อร่อย"
        ),
        "tiktok": (
            "[HOOK 0:00-0:03]\n"
            "\"เมนูนี้ทำไมถึงขายดีที่สุด?\" (mystery hook)\n\n"
            "[REVEAL 0:03-0:15]\n"
            "ASMR การทำ {top_item} step by step\n"
            "Close-up วัตถุดิบและขั้นตอน\n\n"
            "[REACTION 0:15-0:25]\n"
            "ลูกค้าลองและ react\n\n"
            "[CTA 0:25-0:30]\n"
            "\"มาลองเองที่ {brand_name}!\"\n\n"
            "#FoodTikTok #{brand_tag} #MustTry #fyp #อาหารอร่อย #กรุงเทพ"
        ),
        "youtube": (
            "Title: ทำไม {top_item} ถึงเป็นเมนูขายดีที่สุดของ {brand_name}? 🌟\n\n"
            "Description:\n"
            "วันนี้เรามาเปิดเผยความลับของ {top_item} เมนูที่ลูกค้าสั่งมากที่สุด!\n\n"
            "00:00 - แนะนำเมนู\n"
            "01:00 - วัตถุดิบพิเศษ\n"
            "02:00 - ขั้นตอนการทำ\n"
            "03:30 - ลูกค้า review\n\n"
            "Tags: {brand_name}, {top_item}, อาหารอร่อย, สูตรอาหาร, ร้านอาหาร"
        ),
        "image_prompt": (
            "Professional food photography, {top_item} as hero dish, "
            "dramatic lighting, dark marble background, fresh ingredients arranged around, "
            "steam effect, restaurant quality plating, award-winning photo style, "
            "shallow depth of field, warm tones, appetizing"
        ),
    },
}


# ── Content generation ──────────────────────────────────────────────────────────

def _fill_template(template: str, context: dict) -> str:
    """Fill template placeholders with context values."""
    result = template
    for key, value in context.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result


def generate_local(campaign_type: str, context: dict) -> dict[str, str]:
    """Generate content from local templates (no API needed)."""
    templates = _LOCAL_TEMPLATES.get(campaign_type, _LOCAL_TEMPLATES["flash_sale"])
    return {platform: _fill_template(tmpl, context) for platform, tmpl in templates.items()}


def generate_with_claude(
    campaign_type: str,
    context: dict,
    api_key: str,
    tone: str = "friendly",
) -> dict[str, str]:
    """Generate content using Claude API for higher quality and customisation."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        campaign_meta = CAMPAIGN_TYPES.get(campaign_type, CAMPAIGN_TYPES["flash_sale"])
        tone_desc = TONES.get(tone, TONES["friendly"])

        system_prompt = (
            "คุณเป็น Content Marketing Expert สำหรับธุรกิจ F&B ไทย มีประสบการณ์ "
            "สร้างคอนเทนต์ที่ viral บนทุกแพลตฟอร์ม "
            "เขียนคอนเทนต์ที่กระตุ้นการซื้อ สร้าง engagement สูง และตรงกับ target audience "
            f"Tone: {tone_desc} | Campaign: {campaign_meta['label']} | Goal: {campaign_meta['goal']}"
        )

        user_prompt = f"""สร้าง content package สำหรับ campaign "{campaign_meta['label']}"

ข้อมูลธุรกิจ:
{json.dumps(context, ensure_ascii=False, indent=2)}

สร้าง content สำหรับทุก platform ด้านล่าง ในรูป JSON:
{{
  "line_oa": "ข้อความสำหรับ LINE OA (max 1000 ตัวอักษร ใช้ emoji)",
  "facebook": "โพสต์ Facebook (ยาวได้ ใส่ hashtag)",
  "instagram": "Caption IG + hashtag (max 2200 ตัวอักษร)",
  "tiktok": "Script วิดีโอ TikTok พร้อม hook + scene + CTA",
  "youtube": "Title + Description + Tags สำหรับ YouTube",
  "image_prompt": "Prompt ภาษาอังกฤษสำหรับ AI image generation (DALL-E/Midjourney)"
}}

กฎสำคัญ:
- LINE OA: กระชับ อ่านง่าย ใช้ emoji เยอะ CTA ชัดเจน
- Facebook: storytelling เล่าเรื่อง engagement สูง
- Instagram: visual-focused สั้นกระชับ hashtag เยอะ
- TikTok: hook 3 วินาทีแรกต้องดึงดูด มี scene direction
- YouTube: SEO-friendly title, description ครบถ้วน
- Image prompt: detailed, professional photography style

ตอบ JSON เท่านั้น ไม่มีข้อความอื่น"""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = message.content[0].text.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return generate_local(campaign_type, context)

    except Exception:
        return generate_local(campaign_type, context)


def get_content_package(
    campaign_type: str,
    context: dict,
    tone: str = "friendly",
    api_key: str = "",
) -> dict[str, str]:
    """Main entry point — use Claude if key available, else local templates."""
    if api_key.strip():
        return generate_with_claude(campaign_type, context, api_key, tone)
    return generate_local(campaign_type, context)


# ── Content Calendar / Queue ────────────────────────────────────────────────────

def build_posting_schedule(
    platforms: list[str],
    start_date: dt.date | None = None,
    days: int = 7,
) -> list[dict]:
    """Build a smart posting schedule based on platform best times."""
    if start_date is None:
        start_date = dt.date.today()

    schedule: list[dict] = []
    for d in range(days):
        post_date = start_date + dt.timedelta(days=d)
        for platform_key in platforms:
            platform = PLATFORMS.get(platform_key, {})
            best_hours = platform.get("best_hours", [9, 17])
            for hour in best_hours[:2]:  # max 2 posts/day/platform
                schedule.append({
                    "date": post_date,
                    "time": f"{hour:02d}:00",
                    "platform": platform.get("name", platform_key),
                    "platform_key": platform_key,
                    "icon": platform.get("icon", "📢"),
                    "color": platform.get("color", "#888"),
                    "status": "scheduled",
                })
    return sorted(schedule, key=lambda x: (str(x["date"]), x["time"]))


# ── Smart content router ────────────────────────────────────────────────────────

CONTENT_TYPE_ROUTES: dict[str, list[str]] = {
    "image": ["facebook", "instagram", "line_oa"],
    "carousel": ["instagram", "facebook"],
    "short_video": ["tiktok", "youtube", "instagram"],
    "long_video": ["youtube"],
    "text": ["line_oa", "facebook"],
    "story": ["instagram", "facebook"],
}


def route_content(content_type: str) -> list[str]:
    """Return recommended platforms for a given content type."""
    return CONTENT_TYPE_ROUTES.get(content_type, ["facebook", "line_oa"])
