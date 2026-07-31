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
    "vip_reward": {
        "line_oa": (
            "👑 ขอบคุณที่เป็นลูกค้าคนพิเศษของเรา!\n\n"
            "คุณคือ Top Customer ของ {brand_name} 💛\n\n"
            "🎁 สิทธิพิเศษเฉพาะ VIP:\n"
            "✨ ส่วนลด {discount}% ทุกออเดอร์\n"
            "🍽️ {top_item} ฟรี เมื่อมาครั้งถัดไป\n"
            "⏰ ถึง {expiry}\n\n"
            "👉 {cta}"
        ),
        "facebook": (
            "👑 TO OUR VIP CUSTOMERS 👑\n\n"
            "ขอบคุณที่อยู่กับ {brand_name} เสมอมา\n"
            "ความภักดีของคุณมีค่ากับเราที่สุด 💛\n\n"
            "สิทธิพิเศษที่เตรียมไว้ให้:\n"
            "🎁 ส่วนลด {discount}% สำหรับสมาชิก VIP\n"
            "⭐ สิทธิ์จองก่อนใครทุกเมนูใหม่\n"
            "🍽️ {top_item} ฟรีในเดือนเกิด\n\n"
            "#VIPOnly #{brand_tag} #ThankYou"
        ),
        "instagram": (
            "For our VIPs only 👑\n\n"
            "ขอบคุณที่รัก {brand_name} เสมอมา\n"
            "ส่วนลด {discount}% + {top_item} ฟรี รอคุณอยู่\n\n"
            "#VIP #{brand_tag} #LoyaltyRewards #ขอบคุณลูกค้า"
        ),
        "tiktok": (
            "[HOOK 0:00-0:03]\n"
            "\"ร้านนี้รัก VIP แค่ไหน? ดูนี่!\"\n\n"
            "[SCENE 0:03-0:15]\n"
            "โชว์สิทธิพิเศษ VIP ทีละข้อ พร้อม text overlay\n\n"
            "[CTA 0:15-0:20]\n"
            "\"อยากเป็น VIP? มาบ่อยๆ สิ!\"\n\n"
            "#{brand_tag} #VIP #fyp"
        ),
        "youtube": (
            "Title: ขอบคุณลูกค้า VIP — สิทธิพิเศษจาก {brand_name} 👑\n\n"
            "Description:\n"
            "ขอบคุณลูกค้าคนพิเศษทุกท่าน! วิดีโอนี้รวมสิทธิพิเศษ VIP ทั้งหมด\n"
            "ส่วนลด {discount}% | {top_item} ฟรี | สิทธิ์จองก่อนใคร\n\n"
            "Tags: {brand_name}, VIP, loyalty program"
        ),
        "image_prompt": (
            "Luxury VIP card design, gold and black premium colors, elegant typography, "
            "{top_item} subtly featured, exclusive membership aesthetic, high-end restaurant branding"
        ),
    },
    "new_customer": {
        "line_oa": (
            "🌟 ยินดีต้อนรับสู่ครอบครัว {brand_name}!\n\n"
            "ขอบคุณที่มาลองครั้งแรก 💛\n\n"
            "🎁 ของขวัญต้อนรับ:\n"
            "ส่วนลด {discount}% สำหรับครั้งที่ 2\n"
            "⏰ ใช้ได้ภายใน 7 วัน\n\n"
            "เมนูห้ามพลาด: {top_item} ⭐\n\n"
            "👉 {cta}"
        ),
        "facebook": (
            "🌟 WELCOME TO {brand_name}! 🌟\n\n"
            "ขอบคุณลูกค้าใหม่ทุกท่านที่แวะมาหาเรา\n\n"
            "ครั้งแรกอาจจะยังลองไม่ครบ — กลับมาอีกนะ!\n"
            "🎁 รับส่วนลด {discount}% สำหรับการมาครั้งที่ 2\n"
            "⭐ อย่าลืมลอง {top_item} เมนูที่ทุกคนหลงรัก\n\n"
            "#Welcome #{brand_tag} #ลูกค้าใหม่"
        ),
        "instagram": (
            "First time? Welcome! 🌟\n\n"
            "มาครั้งแรกต้องลอง {top_item}\n"
            "ครั้งที่ 2 รับส่วนลด {discount}% เลย\n\n"
            "#{brand_tag} #Welcome #FirstVisit #ร้านใหม่ต้องลอง"
        ),
        "tiktok": (
            "[HOOK 0:00-0:03]\n"
            "\"มาครั้งแรกต้องสั่งอะไร? เดี๋ยวบอก!\"\n\n"
            "[SCENE 0:03-0:15]\n"
            "พาทัวร์ร้าน + โชว์ {top_item} แบบ close-up\n\n"
            "[CTA 0:15-0:20]\n"
            "\"มาครั้งแรกรับส่วนลดครั้งหน้า {discount}%!\"\n\n"
            "#{brand_tag} #ร้านใหม่ #fyp #มาลอง"
        ),
        "youtube": (
            "Title: มาครั้งแรกต้องสั่งอะไร? คู่มือ {brand_name} ฉบับมือใหม่ 🌟\n\n"
            "Description:\n"
            "คู่มือสำหรับลูกค้าใหม่! เมนูแนะนำ วิธีสั่ง และโปรต้อนรับ\n"
            "00:00 - แนะนำร้าน\n"
            "00:45 - เมนูห้ามพลาด: {top_item}\n"
            "01:30 - โปรลูกค้าใหม่ {discount}%\n\n"
            "Tags: {brand_name}, ร้านอาหาร, เมนูแนะนำ"
        ),
        "image_prompt": (
            "Welcoming restaurant entrance, warm inviting atmosphere, friendly staff greeting, "
            "{top_item} on display, bright cheerful lighting, first-impression aesthetic"
        ),
    },
    "seasonal": {
        "line_oa": (
            "🎉 เทศกาลพิเศษที่ {brand_name}!\n\n"
            "ฉลองด้วยกันกับโปรสุดพิเศษ\n\n"
            "🎁 ส่วนลด {discount}% ทุกเมนู\n"
            "⭐ เมนูพิเศษเฉพาะเทศกาล: {top_item}\n"
            "⏰ ถึง {expiry} เท่านั้น\n\n"
            "👉 {cta}"
        ),
        "facebook": (
            "🎉 เทศกาลแห่งความสุขมาถึงแล้ว! 🎉\n\n"
            "{brand_name} ขอร่วมฉลองกับทุกคน\n\n"
            "✨ ไฮไลท์เทศกาลนี้:\n"
            "🎁 ส่วนลด {discount}% ทุกเมนู\n"
            "⭐ {top_item} เวอร์ชันพิเศษ limited!\n"
            "📅 ถึง {expiry} เท่านั้น\n\n"
            "ชวนครอบครัวมาฉลองด้วยกันนะ 💛\n\n"
            "#เทศกาล #{brand_tag} #Celebration"
        ),
        "instagram": (
            "'Tis the season! 🎉\n\n"
            "{top_item} ฉบับเทศกาล limited edition\n"
            "พร้อมส่วนลด {discount}% ถึง {expiry}\n\n"
            "#{brand_tag} #Seasonal #LimitedEdition #เทศกาล"
        ),
        "tiktok": (
            "[HOOK 0:00-0:03]\n"
            "\"เมนูนี้มีแค่ช่วงเทศกาล!\" (FOMO hook)\n\n"
            "[SCENE 0:03-0:15]\n"
            "โชว์ {top_item} ฉบับเทศกาล + บรรยากาศตกแต่งร้าน\n\n"
            "[CTA 0:15-0:20]\n"
            "\"หมดเขต {expiry} — รีบมา!\"\n\n"
            "#{brand_tag} #เทศกาล #limited #fyp"
        ),
        "youtube": (
            "Title: ฉลองเทศกาลกับ {brand_name} — เมนูพิเศษ limited! 🎉\n\n"
            "Description:\n"
            "เทศกาลนี้เรามีอะไรพิเศษ? มาดูกัน!\n"
            "00:00 - บรรยากาศเทศกาลที่ร้าน\n"
            "00:40 - เมนูพิเศษ: {top_item}\n"
            "01:20 - โปรโมชั่น {discount}% ถึง {expiry}\n\n"
            "Tags: {brand_name}, เทศกาล, เมนูพิเศษ, โปรโมชั่น"
        ),
        "image_prompt": (
            "Festive restaurant scene, seasonal decorations, {top_item} as centerpiece, "
            "celebration atmosphere, warm festive lighting, holiday color palette, joyful mood"
        ),
    },
}


# ── Product / beauty templates ─────────────────────────────────────────────────
# The pack above is written for restaurants ("เมนู", "รสชาติ", "#อาหารอร่อย").
# Brands that sell a product rather than a meal need their own voice, so this
# second pack keeps the same placeholders but speaks about products and results.
# Deliberately claim-light: describe care and confidence, not medical outcomes.

_PRODUCT_TEMPLATES: dict[str, dict[str, str]] = {
    "hero_product": {
        "line_oa": (
            "⭐ ตัวช่วยที่หลายคนบอกต่อ\n\n"
            "✨ {top_item}\n"
            "สินค้าขายดีที่สุดของ {brand_name}\n\n"
            "ดูแลผิวคุณอย่างเข้าใจ ใช้ได้ทุกวัน 💛\n\n"
            "👉 {cta}"
        ),
        "facebook": (
            "🌟 ยังไม่ได้ลอง {top_item} ใช่ไหม?\n\n"
            "ทำไมลูกค้าถึงบอกต่อ:\n"
            "✅ คัดส่วนผสมที่อ่อนโยนต่อผิว\n"
            "✅ ใช้ง่าย เข้ากับกิจวัตรประจำวัน\n"
            "✅ คุ้มค่า ดูแลได้ต่อเนื่อง\n\n"
            "💬 แท็กเพื่อนที่กำลังมองหาตัวช่วยอยู่\n\n"
            "#{brand_tag} #รีวิวของดี #ดูแลผิว"
        ),
        "instagram": (
            "ตัวช่วยใหม่ที่ผิวคุณรอ ✨\n\n"
            "{top_item} — จาก {brand_name}\n\n"
            "อ่อนโยน ใช้ได้ทุกวัน 🤍\n"
            "Double tap ถ้าอยากลอง!\n\n"
            "#{brand_tag} #สกินแคร์ #ดูแลผิว #ของดีบอกต่อ #beauty"
        ),
        "tiktok": (
            "[HOOK 0:00-0:03]\n"
            "\"ทำไม {top_item} ถึงขายดีที่สุด?\"\n\n"
            "[SHOW 0:03-0:15]\n"
            "โชว์เนื้อสัมผัส close-up + วิธีใช้ทีละสเต็ป\n\n"
            "[PROOF 0:15-0:25]\n"
            "รีวิวจากผู้ใช้จริง / ภาพก่อน-หลัง\n\n"
            "[CTA 0:25-0:30]\n"
            "\"ลองเองได้ที่ {brand_name}\"\n\n"
            "#{brand_tag} #สกินแคร์ #fyp #รีวิวสกินแคร์"
        ),
        "youtube": (
            "Title: รีวิว {top_item} จาก {brand_name} — ดีจริงไหม? ✨\n\n"
            "Description:\n"
            "พาดูละเอียดว่า {top_item} คืออะไร เหมาะกับใคร และใช้ยังไงให้ได้ผล\n\n"
            "00:00 - แนะนำสินค้า\n"
            "01:00 - ส่วนผสมสำคัญ\n"
            "02:00 - วิธีใช้\n"
            "03:30 - รีวิวจากผู้ใช้จริง\n\n"
            "Tags: {brand_name}, {top_item}, สกินแคร์, ดูแลผิว, รีวิว"
        ),
        "image_prompt": (
            "Professional product photography of {top_item} by {brand_name}, "
            "clean minimal background, soft studio lighting with gentle gradient, "
            "water droplets and fresh botanical accents, shallow depth of field, "
            "crisp detail on packaging, premium skincare advertising style, 4K, no text overlay"
        ),
    },
    "flash_sale": {
        "line_oa": (
            "⚡ ดีลพิเศษวันนี้เท่านั้น!\n\n"
            "🕐 {start_time} - {end_time} น.\n"
            "💥 ลด {discount}% ทุกชิ้น\n\n"
            "🔥 {top_item} ราคาพิเศษสุด!\n\n"
            "⏰ จำนวนจำกัด — {cta}"
        ),
        "facebook": (
            "⚡⚡ FLASH SALE เริ่มแล้ว! ⚡⚡\n\n"
            "🕐 วันนี้ {start_time}-{end_time} น. เท่านั้น\n"
            "💥 ลด {discount}% ทุกรายการ\n\n"
            "🔥 ไฮไลต์: {top_item} — ราคาดีที่สุดของเดือน\n"
            "✅ ส่งไว ของแท้ 100%\n\n"
            "⚠️ ของมีจำนวนจำกัด หมดแล้วหมดเลย\n\n"
            "#FlashSale #{brand_tag} #ลดราคา #วันนี้เท่านั้น"
        ),
        "instagram": (
            "⚡ FLASH SALE ⚡\n\n"
            "{start_time} - {end_time} วันนี้เท่านั้น\n"
            "ลด {discount}% ทุกชิ้น 🔥\n\n"
            "{top_item} รอคุณอยู่ 💨\n\n"
            "#FlashSale #{brand_tag} #ลดราคา #สกินแคร์ #ของดีราคาดี"
        ),
        "tiktok": (
            "[HOOK 0:00-0:02]\n"
            "\"ลด {discount}% เหลืออีก {countdown} ชั่วโมง!\"\n\n"
            "[SHOW 0:02-0:12]\n"
            "โชว์สินค้า + ป้ายราคา countdown overlay\n\n"
            "[CTA 0:12-0:15]\n"
            "\"กดสั่งเลย ก่อนหมด!\"\n\n"
            "#FlashSale #{brand_tag} #fyp #ลดราคา"
        ),
        "youtube": (
            "Title: FLASH SALE ลด {discount}% วันนี้เท่านั้น | {brand_name}\n\n"
            "Description:\n"
            "🔥 ดีลด่วน {start_time}-{end_time} น. วันนี้เท่านั้น\n"
            "{top_item} และทุกรายการ ลด {discount}%\n\n"
            "Tags: flash sale, ลดราคา, {brand_name}, สกินแคร์"
        ),
        "image_prompt": (
            "Bold promotional banner for a skincare flash sale, {discount}% off in large type, "
            "{top_item} featured prominently as the hero product, vibrant gradient background, "
            "clean modern e-commerce design, high contrast, studio product lighting"
        ),
    },
    "winback": {
        "line_oa": (
            "🙏 {brand_name} คิดถึงคุณนะ\n\n"
            "ไม่ได้เจอกันสักพักเลย 🥺\n\n"
            "✨ พิเศษสำหรับคุณ:\n"
            "🎁 ส่วนลด {discount}% สำหรับออเดอร์ถัดไป\n"
            "⏰ ใช้ได้ถึง {expiry}\n\n"
            "👉 {cta}"
        ),
        "facebook": (
            "💌 เราคิดถึงคุณนะ 🤍\n\n"
            "ตั้งแต่ครั้งล่าสุดที่คุณแวะมา เรามีอะไรใหม่หลายอย่าง:\n"
            "✅ {top_item} ที่ลูกค้าบอกต่อ\n"
            "✅ รีวิวจากผู้ใช้จริงเพิ่มขึ้นเรื่อย ๆ\n"
            "✅ และส่วนลดพิเศษรอคุณอยู่ 🎁\n\n"
            "การดูแลผิวที่ดีคือความต่อเนื่อง — กลับมาเริ่มใหม่ด้วยกันนะ 💛\n\n"
            "#{brand_tag} #ดูแลผิว #กลับมาหาเรา"
        ),
        "instagram": (
            "We miss you 🤍\n\n"
            "บางครั้งชีวิตยุ่งจนลืมดูแลตัวเอง —\n"
            "แต่ผิวคุณยังรออยู่นะ 🌿\n\n"
            "{top_item} + ส่วนลด {discount}% พิเศษสำหรับคุณ\n\n"
            "#{brand_tag} #ดูแลผิว #สกินแคร์ #กลับมาดูแลตัวเอง"
        ),
        "tiktok": (
            "[HOOK 0:00-0:03]\n"
            "\"POV: แบรนด์โปรดทักมาหลังจากหายไป {days} วัน\"\n\n"
            "[SHOW 0:03-0:15]\n"
            "โชว์ {top_item} + ข้อความ 'เราคิดถึงคุณนะ 🥺'\n\n"
            "[CTA 0:15-0:20]\n"
            "\"ส่วนลด {discount}% รออยู่ — กดลิงก์เลย!\"\n\n"
            "#{brand_tag} #สกินแคร์ #fyp"
        ),
        "youtube": (
            "Title: เราคิดถึงคุณ — {brand_name} มีอะไรใหม่รออยู่ 🎁\n\n"
            "Description:\n"
            "อัปเดตสำคัญและส่วนลดพิเศษ {discount}% สำหรับลูกค้าที่ห่างหายไป\n\n"
            "Tags: {brand_name}, สกินแคร์, โปรโมชั่น"
        ),
        "image_prompt": (
            "Warm inviting skincare flat lay, {top_item} surrounded by soft towels and green botanicals, "
            "morning natural light, calm self-care mood, muted warm tones, lifestyle photography, 4K"
        ),
    },
    "vip_reward": {
        "line_oa": (
            "👑 ขอบคุณที่เป็นลูกค้าคนพิเศษ\n\n"
            "คุณคือ Top Customer ของ {brand_name} 💛\n\n"
            "🎁 สิทธิพิเศษเฉพาะคุณ:\n"
            "✨ ส่วนลด {discount}% ทุกออเดอร์\n"
            "🎀 ของแถมพิเศษเมื่อสั่งครั้งถัดไป\n"
            "⏰ ถึง {expiry}\n\n"
            "👉 {cta}"
        ),
        "facebook": (
            "👑 TO OUR VIP CUSTOMERS 👑\n\n"
            "ขอบคุณที่ให้ {brand_name} ดูแลผิวคุณเสมอมา\n"
            "ความไว้วางใจของคุณมีค่ากับเราที่สุด 💛\n\n"
            "สิทธิพิเศษที่เตรียมไว้:\n"
            "🎁 ส่วนลด {discount}% สำหรับสมาชิก VIP\n"
            "⭐ สิทธิ์สั่งก่อนใครทุกสินค้าใหม่\n"
            "🎀 ของแถมพิเศษในเดือนเกิด\n\n"
            "#VIPOnly #{brand_tag} #ขอบคุณลูกค้า"
        ),
        "instagram": (
            "For our VIPs only 👑\n\n"
            "ขอบคุณที่อยู่กับ {brand_name} เสมอมา\n"
            "ส่วนลด {discount}% + ของแถมพิเศษ รอคุณอยู่\n\n"
            "#VIP #{brand_tag} #ขอบคุณลูกค้า #สกินแคร์"
        ),
        "tiktok": (
            "[HOOK 0:00-0:03]\n"
            "\"แบรนด์นี้ดูแล VIP ยังไง? ดูนี่\"\n\n"
            "[SHOW 0:03-0:15]\n"
            "ไล่สิทธิพิเศษทีละข้อ พร้อม text overlay\n\n"
            "[CTA 0:15-0:20]\n"
            "\"อยากเป็น VIP? เริ่มจากออเดอร์แรกเลย!\"\n\n"
            "#{brand_tag} #VIP #fyp"
        ),
        "youtube": (
            "Title: ขอบคุณลูกค้า VIP — สิทธิพิเศษจาก {brand_name} 👑\n\n"
            "Description:\n"
            "รวมสิทธิพิเศษสำหรับลูกค้า VIP ส่วนลด {discount}% และของแถมพิเศษ\n\n"
            "Tags: {brand_name}, VIP, สกินแคร์, loyalty"
        ),
        "image_prompt": (
            "Luxury skincare gift set arrangement, gold and soft cream tones, elegant premium packaging, "
            "{top_item} as centerpiece, silk fabric background, high-end beauty campaign lighting, 4K"
        ),
    },
    "new_customer": {
        "line_oa": (
            "🌟 ยินดีต้อนรับสู่ครอบครัว {brand_name}!\n\n"
            "ขอบคุณที่ให้เราได้ดูแลผิวคุณ 💛\n\n"
            "🎁 ของขวัญต้อนรับ:\n"
            "ส่วนลด {discount}% สำหรับออเดอร์ที่ 2\n"
            "⏰ ใช้ได้ภายใน 7 วัน\n\n"
            "เริ่มจาก {top_item} ได้เลย ⭐\n\n"
            "👉 {cta}"
        ),
        "facebook": (
            "🌟 ยินดีต้อนรับลูกค้าใหม่ทุกท่าน! 🌟\n\n"
            "การดูแลผิวที่ดีคือความต่อเนื่อง —\n"
            "ครั้งแรกอาจยังไม่เห็นผลเต็มที่ ให้เวลาผิวคุณสักหน่อยนะ\n\n"
            "🎁 รับส่วนลด {discount}% สำหรับออเดอร์ที่ 2\n"
            "⭐ เริ่มต้นง่าย ๆ กับ {top_item}\n\n"
            "มีคำถามเรื่องผิว ทักมาถามได้เลย เรายินดีให้คำแนะนำ 💬\n\n"
            "#Welcome #{brand_tag} #ลูกค้าใหม่ #ดูแลผิว"
        ),
        "instagram": (
            "First time? Welcome! 🌟\n\n"
            "เริ่มดูแลผิวกับ {brand_name} ง่าย ๆ ด้วย {top_item}\n"
            "ออเดอร์ที่ 2 รับส่วนลด {discount}% เลย\n\n"
            "#{brand_tag} #Welcome #สกินแคร์ #เริ่มดูแลผิว"
        ),
        "tiktok": (
            "[HOOK 0:00-0:03]\n"
            "\"มือใหม่ควรเริ่มจากอะไรดี? เดี๋ยวบอก\"\n\n"
            "[SHOW 0:03-0:15]\n"
            "แนะนำ {top_item} + วิธีใช้ทีละสเต็ป\n\n"
            "[CTA 0:15-0:20]\n"
            "\"ลูกค้าใหม่รับส่วนลดครั้งหน้า {discount}%!\"\n\n"
            "#{brand_tag} #สกินแคร์มือใหม่ #fyp"
        ),
        "youtube": (
            "Title: มือใหม่เริ่มยังไงดี? คู่มือ {brand_name} ฉบับเริ่มต้น 🌟\n\n"
            "Description:\n"
            "แนะนำสินค้าเริ่มต้น วิธีใช้ และโปรต้อนรับลูกค้าใหม่\n"
            "00:00 - แนะนำแบรนด์\n"
            "00:45 - เริ่มจาก {top_item}\n"
            "01:30 - โปรลูกค้าใหม่ {discount}%\n\n"
            "Tags: {brand_name}, สกินแคร์มือใหม่, รีวิว"
        ),
        "image_prompt": (
            "Fresh clean skincare starter set on white marble, {top_item} in focus, "
            "bright airy natural lighting, minimal Scandinavian styling, soft shadows, "
            "welcoming friendly mood, product photography, 4K"
        ),
    },
    "seasonal": {
        "line_oa": (
            "🎉 เทศกาลพิเศษที่ {brand_name}!\n\n"
            "ฉลองด้วยกันกับดีลสุดพิเศษ\n\n"
            "🎁 ส่วนลด {discount}% ทุกชิ้น\n"
            "⭐ เซ็ตพิเศษเฉพาะเทศกาล: {top_item}\n"
            "⏰ ถึง {expiry} เท่านั้น\n\n"
            "👉 {cta}"
        ),
        "facebook": (
            "🎉 เทศกาลแห่งความสุขมาถึงแล้ว! 🎉\n\n"
            "{brand_name} ขอร่วมฉลองกับทุกคน\n\n"
            "✨ ไฮไลต์เทศกาลนี้:\n"
            "🎁 ส่วนลด {discount}% ทุกรายการ\n"
            "⭐ เซ็ตของขวัญ {top_item} จำนวนจำกัด\n"
            "📅 ถึง {expiry} เท่านั้น\n\n"
            "ให้ของขวัญคนที่คุณรัก ด้วยการดูแลที่ดี 💛\n\n"
            "#เทศกาล #{brand_tag} #ของขวัญ"
        ),
        "instagram": (
            "'Tis the season! 🎉\n\n"
            "เซ็ต {top_item} ฉบับเทศกาล limited edition\n"
            "พร้อมส่วนลด {discount}% ถึง {expiry}\n\n"
            "#{brand_tag} #Seasonal #LimitedEdition #ของขวัญ #สกินแคร์"
        ),
        "tiktok": (
            "[HOOK 0:00-0:03]\n"
            "\"เซ็ตนี้มีแค่ช่วงเทศกาล!\"\n\n"
            "[SHOW 0:03-0:15]\n"
            "แกะกล่องเซ็ต {top_item} + โชว์แพ็กเกจ\n\n"
            "[CTA 0:15-0:20]\n"
            "\"หมดเขต {expiry} — รีบเลย!\"\n\n"
            "#{brand_tag} #เทศกาล #limited #fyp"
        ),
        "youtube": (
            "Title: เซ็ตเทศกาล limited จาก {brand_name} 🎉\n\n"
            "Description:\n"
            "แกะกล่องเซ็ตพิเศษเฉพาะเทศกาล พร้อมโปร {discount}% ถึง {expiry}\n\n"
            "Tags: {brand_name}, เทศกาล, ของขวัญ, สกินแคร์"
        ),
        "image_prompt": (
            "Festive skincare gift box flat lay, {top_item} with seasonal ribbon and ornaments, "
            "warm celebratory lighting, holiday colour palette, premium unboxing aesthetic, 4K"
        ),
    },
}

# Signals that a brand sells products (skincare/beauty/retail) rather than meals.
_PRODUCT_SIGNALS = (
    "สกินแคร์", "skincare", "ผิว", "เซรั่ม", "serum", "ครีม", "cream", "สบู่", "soap",
    "เครื่องสำอาง", "cosmetic", "beauty", "บำรุง", "โทนเนอร์", "toner", "มาส์ก", "mask",
    "แชมพู", "ยาสระผม", "อาหารเสริม", "วิตามิน", "เวชสำอาง", "สิว", "acne", "กันแดด",
)
_FNB_SIGNALS = (
    "ร้านอาหาร", "คาเฟ่", "cafe", "restaurant", "เมนู", "หมูกระทะ", "ชาบู", "เย็นตาโฟ",
    "ก๋วยเตี๋ยว", "กาแฟ", "เบเกอรี่", "บาร์", "อาหาร", "ครัว", "บุฟเฟ่ต์",
)


def detect_vertical(text: str, default: str = "fnb") -> str:
    """Guess the business vertical from free text. Returns 'product' or 'fnb'.

    `default` is returned when the text carries no signal either way, which lets
    callers layer detection (the user's own words first, brand brief second).
    """
    low = (text or "").lower()
    product_hits = sum(1 for s in _PRODUCT_SIGNALS if s in low)
    fnb_hits = sum(1 for s in _FNB_SIGNALS if s in low)
    if product_hits == fnb_hits == 0:
        return default
    return "product" if product_hits > fnb_hits else "fnb"


# ── Content generation ──────────────────────────────────────────────────────────

def _fill_template(template: str, context: dict) -> str:
    """Fill template placeholders with context values."""
    result = template
    for key, value in context.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result


def generate_local(campaign_type: str, context: dict, vertical: str = "fnb") -> dict[str, str]:
    """Generate content from local templates (no API needed).

    `vertical` picks the voice: 'product' for skincare/retail brands, 'fnb' for
    restaurants. Falls back to the F&B pack for unknown values.
    """
    pack = _PRODUCT_TEMPLATES if vertical == "product" else _LOCAL_TEMPLATES
    templates = pack.get(campaign_type) or pack.get("flash_sale") or _LOCAL_TEMPLATES["flash_sale"]
    return {platform: _fill_template(tmpl, context) for platform, tmpl in templates.items()}


def generate_with_ai(
    campaign_type: str,
    context: dict,
    api_key: str,
    tone: str = "friendly",
    brand_context: str = "",
    provider: str = "auto",
    vertical: str = "fnb",
) -> dict[str, str]:
    """Generate content with Claude or Gemini. Falls back to local templates."""
    try:
        import ai_provider
    except ImportError:
        return generate_local(campaign_type, context, vertical)

    campaign_meta = CAMPAIGN_TYPES.get(campaign_type, CAMPAIGN_TYPES["flash_sale"])
    tone_desc = TONES.get(tone, TONES["friendly"])

    system_prompt = (
        "คุณเป็น Content Marketing Expert สำหรับแบรนด์ไทย มีประสบการณ์ "
        "สร้างคอนเทนต์ที่ viral บนทุกแพลตฟอร์ม "
        "เขียนคอนเทนต์ที่กระตุ้นการซื้อ สร้าง engagement สูง และตรงกับ target audience "
        f"Tone: {tone_desc} | Campaign: {campaign_meta['label']} | Goal: {campaign_meta['goal']}"
    )
    if vertical == "product":
        system_prompt += (
            "\n\nสำคัญ: แบรนด์นี้ขายสินค้า ไม่ใช่ร้านอาหาร "
            "ห้ามใช้คำที่เกี่ยวกับอาหารเด็ดขาด เช่น เมนู รสชาติ อร่อย สั่งอาหาร โต๊ะ สาขา "
            "และห้ามใช้ hashtag แนวอาหาร เช่น #อาหารอร่อย #foodie #FoodPorn"
        )
    if brand_context:
        system_prompt += (
            "\n\nอิงบริบทแบรนด์ต่อไปนี้อย่างเคร่งครัด "
            "ห้ามแต่งสรรพคุณหรือตัวเลขเกินจากที่ให้:\n" + brand_context
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
  "image_prompt": "Prompt ภาษาอังกฤษสำหรับสร้างภาพด้วย AI — ละเอียด ระบุ subject/แสง/มุมกล้อง/สไตล์"
}}

กฎสำคัญ:
- LINE OA: กระชับ อ่านง่าย ใช้ emoji เยอะ CTA ชัดเจน
- Facebook: storytelling เล่าเรื่อง engagement สูง
- Instagram: visual-focused สั้นกระชับ hashtag เยอะ
- TikTok: hook 3 วินาทีแรกต้องดึงดูด มี scene direction
- YouTube: SEO-friendly title, description ครบถ้วน
- Image prompt: detailed, professional photography style, ภาษาอังกฤษเท่านั้น

ตอบ JSON เท่านั้น ไม่มีข้อความอื่น"""

    data = ai_provider.generate_json(
        system_prompt, user_prompt, api_key, provider=provider, max_tokens=3000
    )
    if isinstance(data, dict) and data:
        local = generate_local(campaign_type, context, vertical)
        # Keep every platform populated even if the model skipped one.
        return {k: (str(data.get(k) or local.get(k, "")).strip() or local.get(k, ""))
                for k in local}
    return generate_local(campaign_type, context, vertical)


# Backwards-compatible alias — older call sites used the Claude-specific name.
generate_with_claude = generate_with_ai


def get_content_package(
    campaign_type: str,
    context: dict,
    tone: str = "friendly",
    api_key: str = "",
    brand_context: str = "",
    provider: str = "auto",
    vertical: str = "",
) -> dict[str, str]:
    """Main entry point — use an AI provider if a key is available, else templates."""
    # Infer the vertical from the brand brief when the caller didn't specify one.
    if not vertical:
        vertical = detect_vertical(f"{brand_context} {context.get('top_item', '')}")
    if api_key and api_key.strip():
        return generate_with_ai(campaign_type, context, api_key, tone,
                                brand_context, provider, vertical)
    return generate_local(campaign_type, context, vertical)


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
