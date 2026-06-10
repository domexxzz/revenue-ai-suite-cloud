"""chat_inbox.py — read & reply customer chats (FB Messenger / IG DM) + AI reply agent.

Pure module (no streamlit import) so the LINE webhook bot can reuse the AI agent.
"""
from __future__ import annotations

import logging
import requests

logger = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com/v19.0"

DEFAULT_PROFILE = {
    "shop_name": "ร้านของคุณ",
    "hours": "เปิดทุกวัน 10:00-22:00",
    "address": "กรุงเทพฯ",
    "menu": "เมนูแนะนำของร้าน สอบถามได้เลย",
    "promo": "สอบถามโปรล่าสุดได้เลย",
    "booking": "ทักแชทจองโต๊ะได้เลย แจ้งวัน เวลา จำนวนคน",
}


# ── Read & send (Facebook Messenger / Instagram DM via Graph API) ──────────────

def fetch_conversations(token: str, page_id: str, platform: str = "messenger",
                        limit: int = 15) -> tuple[list[dict] | None, str]:
    """Fetch recent conversations. platform: 'messenger' | 'instagram'."""
    try:
        r = requests.get(
            f"{GRAPH}/{page_id}/conversations",
            params={
                "access_token": token,
                "platform": platform,
                "limit": limit,
                "fields": "participants,updated_time,"
                          "messages.limit(8){message,from,created_time}",
            },
            timeout=20,
        )
        if r.status_code != 200:
            return None, f"Error {r.status_code}: {r.text[:250]}"
        convs = []
        for c in r.json().get("data", []):
            parts = c.get("participants", {}).get("data", [])
            customer = next((p for p in parts if str(p.get("id")) != str(page_id)), {})
            msgs = list(reversed(c.get("messages", {}).get("data", [])))  # oldest → newest
            convs.append({
                "conversation_id": c.get("id", ""),
                "customer_id": customer.get("id", ""),
                "customer_name": customer.get("name") or customer.get("username") or "ลูกค้า",
                "updated": c.get("updated_time", ""),
                "messages": [{
                    "from_customer": str(m.get("from", {}).get("id")) != str(page_id),
                    "text": m.get("message", "") or "",
                    "time": m.get("created_time", ""),
                    "id": m.get("id", ""),
                } for m in msgs],
            })
        return convs, "ok"
    except Exception as e:
        return None, f"Error: {e}"


def send_message(token: str, page_id: str, recipient_id: str, text: str) -> tuple[bool, str]:
    """Send a reply via Messenger Send API (works for FB + IG-scoped IDs)."""
    if not text.strip():
        return False, "ข้อความว่าง"
    try:
        r = requests.post(
            f"{GRAPH}/{page_id}/messages",
            params={"access_token": token},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": text[:1900]},
                "messaging_type": "RESPONSE",
            },
            timeout=20,
        )
        if r.status_code == 200:
            return True, "ส่งแล้ว ✅"
        err = r.json().get("error", {}).get("message", r.text[:160])
        return False, f"ส่งไม่ได้: {err}"
    except Exception as e:
        return False, f"Error: {e}"


# ── AI reply agent ──────────────────────────────────────────────────────────────

def generate_ai_reply(messages: list[dict], profile: dict, api_key: str = "") -> str:
    """Draft the shop's next reply. Claude if api_key given, else rule-based."""
    history = "\n".join(
        ("ลูกค้า: " if m["from_customer"] else "ร้าน: ") + m["text"]
        for m in messages[-8:] if m.get("text")
    )
    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            system = (
                f"คุณคือแอดมินร้าน {profile.get('shop_name')} ตอบแชทลูกค้าแบบสุภาพ "
                "เป็นกันเอง กระชับ ใช้อีโมจิพอประมาณ\n"
                f"ข้อมูลร้าน:\n"
                f"- เวลาเปิด: {profile.get('hours')}\n"
                f"- ที่อยู่: {profile.get('address')}\n"
                f"- เมนูแนะนำ: {profile.get('menu')}\n"
                f"- โปรตอนนี้: {profile.get('promo')}\n"
                f"- การจองโต๊ะ: {profile.get('booking')}\n"
                "กฎ: ตอบไม่เกิน 3 ประโยค ถ้าไม่รู้คำตอบจริงๆ ให้บอกว่า "
                "จะให้แอดมินมาตอบโดยเร็ว ห้ามแต่งข้อมูลเอง"
            )
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=300,
                system=[{"type": "text", "text": system,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content":
                           f"บทสนทนา:\n{history}\n\n"
                           "เขียนคำตอบถัดไปของร้าน (ตอบข้อความล่าสุดของลูกค้า):"}],
            )
            return msg.content[0].text.strip()
        except Exception as e:
            logger.warning("Claude reply failed, fallback to rules: %s", e)
    return _rule_based_reply(messages, profile)


def _rule_based_reply(messages: list[dict], profile: dict) -> str:
    last = next((m["text"] for m in reversed(messages)
                 if m.get("from_customer") and m.get("text")), "")
    t = last.lower()
    if any(k in t for k in ["เปิด", "ปิด", "กี่โมง", "เวลา"]):
        return f"ร้านเปิด {profile.get('hours')} ครับ/ค่ะ 😊"
    if any(k in t for k in ["ที่อยู่", "อยู่ไหน", "เดินทาง", "แผนที่", "พิกัด"]):
        return f"ร้านอยู่ที่ {profile.get('address')} ครับ/ค่ะ 📍"
    if any(k in t for k in ["จอง", "โต๊ะ", "ที่นั่ง"]):
        return f"{profile.get('booking')} 🙏"
    if any(k in t for k in ["โปร", "ส่วนลด", "ลดราคา"]):
        return f"โปรตอนนี้: {profile.get('promo')} 🎉"
    if any(k in t for k in ["ราคา", "เท่าไหร่", "กี่บาท", "เมนู", "อร่อย"]):
        return f"เมนูแนะนำ: {profile.get('menu')} 😋 สนใจเมนูไหนสอบถามได้เลยครับ/ค่ะ"
    return (f"สวัสดีครับ/ค่ะ 🙏 ขอบคุณที่ทักมาหา {profile.get('shop_name')} "
            f"แอดมินจะรีบตอบกลับโดยเร็วที่สุดนะครับ/คะ (ร้านเปิด {profile.get('hours')})")
