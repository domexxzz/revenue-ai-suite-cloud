"""LINE OA AI auto-reply webhook bot — standalone service.

LINE ไม่ให้ดึงแชทย้อนหลังผ่าน API จึงต้องรัน bot นี้รับ webhook แล้วตอบทันที

วิธีรัน (เครื่องตัวเอง + Cloudflare Tunnel):
    export LINE_CHANNEL_SECRET="..."        # จาก LINE Developers → Basic settings
    export LINE_CHANNEL_ACCESS_TOKEN="..."  # token ตัวเดียวกับใน app
    export ANTHROPIC_API_KEY="sk-ant-..."   # (ไม่ใส่ = ใช้ rule-based)
    export SHOP_PROFILE_JSON='{"shop_name":"ร้านของฉัน","hours":"10:00-22:00"}'
    uvicorn line_ai_bot:app --port 8001

    # เปิด tunnel (ติดตั้ง: brew install cloudflared)
    cloudflared tunnel --url http://localhost:8001
    # เอา URL ที่ได้ไปตั้งใน LINE Developers → Messaging API →
    # Webhook URL = https://<tunnel>/webhook  แล้วเปิด "Use webhook"

หรือ deploy ฟรีบน Render/Railway: start command = uvicorn line_ai_bot:app --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

import requests
from fastapi import FastAPI, HTTPException, Request

from chat_inbox import DEFAULT_PROFILE, generate_ai_reply

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
CHANNEL_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PROFILE = {**DEFAULT_PROFILE, **json.loads(os.getenv("SHOP_PROFILE_JSON", "{}") or "{}")}

app = FastAPI(title="LINE AI Auto-Reply Bot")


@app.get("/health")
def health():
    return {"status": "ok", "shop": PROFILE.get("shop_name"),
            "ai": "claude" if ANTHROPIC_KEY else "rule-based"}


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("X-Line-Signature", "")
    mac = base64.b64encode(
        hmac.new(CHANNEL_SECRET.encode(), body, hashlib.sha256).digest()
    ).decode()
    if not hmac.compare_digest(mac, sig):
        raise HTTPException(status_code=401, detail="bad signature")

    for ev in json.loads(body).get("events", []):
        if ev.get("type") == "message" and ev.get("message", {}).get("type") == "text":
            user_text = ev["message"]["text"]
            reply = generate_ai_reply(
                [{"from_customer": True, "text": user_text}], PROFILE, ANTHROPIC_KEY
            )
            requests.post(
                "https://api.line.me/v2/bot/message/reply",
                headers={"Authorization": f"Bearer {CHANNEL_TOKEN}",
                         "Content-Type": "application/json"},
                json={"replyToken": ev["replyToken"],
                      "messages": [{"type": "text", "text": reply[:5000]}]},
                timeout=10,
            )
    return {"ok": True}
