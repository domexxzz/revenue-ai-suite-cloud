# 📊 F&B Growth Suite (AI Revenue Intelligence + Affiliate Autopilot)

ระบบ AI ครบวงจรสำหรับร้านอาหาร/คาเฟ่/ธุรกิจ F&B — **2 โหมดในแอปเดียว สลับได้จาก sidebar:**

- 🏪 **โหมดร้านของฉัน** — วิเคราะห์ยอดขาย (RFM, forecast), สร้างคอนเทนต์, โพสต์ทุกแพลตฟอร์ม, ตอบแชทลูกค้าอัตโนมัติ
- 🚀 **โหมดแอฟฟิลิเอต** — ดึงร้าน Shopee Food → AI ผลิตคอนเทนต์/วิดีโอ → โพสต์หลายแพลตฟอร์ม → A/B auto-optimize

**เว็บแอป (ใช้งานจริง):** https://ai-revenue-intelligence-4zroa95urtomyx8v5mmxuk.streamlit.app

---

## 🔀 สถาปัตยกรรมระบบรวม

```
            ┌───────────────────────────────────────────────┐
            │   Streamlit (แอปนี้) — UI รวม + สลับโหมด          │
            │   🏪 ร้านของฉัน      |     🚀 แอฟฟิลิเอต          │
            └───────┬───────────────────────────┬───────────┘
                    │ in-process                │ REST (offline-safe)
        RFM · content · chat · POS      affiliate_client.py
        (Loyverse/FB/IG/LINE/YT)                 │
                                                 ▼
                              Affiliate Autopilot backend (FastAPI/Docker :8088)
                              Shopee scrape · Gemini/Flow video · phone farm · A/B
```

- **โหมดร้าน** ใช้งานได้เต็มที่ทันที **ไม่ต้องมี backend** (rule-based fallback)
- **โหมดแอฟฟิลิเอต** ต่อกับ backend `affiliate-autopilot` ที่ `http://localhost:8088`
  (เปลี่ยน URL ได้ใน sidebar หรือ `st.secrets["affiliate"]["base_url"]` — ใช้ Cloudflare Funnel ได้)
  ถ้า backend ปิดอยู่ หน้าจะแสดงวิธีเปิดให้ และโหมดร้านยังใช้ได้ปกติ

```powershell
# เปิด backend แอฟฟิลิเอต (ครั้งเดียว บนเครื่อง server)
cd ../affiliate-autopilot
docker compose up -d --build      # → http://localhost:8088
```

---

## 🚀 เริ่มงานใน 5 นาที (สำหรับ dev ใหม่)

```bash
# 1. clone repo
git clone https://github.com/electiction/ai-revenue-intelligence
cd ai-revenue-intelligence

# 2. สร้าง virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. ติดตั้ง dependencies
pip install -r requirements.txt

# 4. รันแอป
streamlit run app.py
```

เปิดเบราว์เซอร์ที่ `http://localhost:8501` — เห็นแอปทันที (ใช้ข้อมูล mock ได้เลย ไม่ต้องตั้งค่าอะไร)

> 💡 ทุกฟีเจอร์ทำงานได้โดยไม่ต้องใส่ API key — โหมด **Local Smart** ใช้ rule-based logic
> ส่วนการโพสต์จริง/ตอบแชทจริง ค่อยใส่ token ทีหลัง (มีคู่มือในแอป กดปุ่ม 📖)

---

## 🗂️ โครงสร้างโปรเจกต์ — ไฟล์ไหนทำอะไร

| ไฟล์ | หน้าที่ |
|---|---|
| **`app.py`** | ไฟล์หลัก — UI ทุกหน้า + routing + sidebar (ใหญ่สุด เริ่มอ่านจากตรงนี้) |
| `rfm_engine.py` | คำนวณ RFM segmentation (แบ่งกลุ่มลูกค้า Champions / At Risk / Lost ฯลฯ) |
| `content_studio.py` | template + logic สร้างคอนเทนต์ทุกแพลตฟอร์ม (6 แคมเปญ × 5 platform) |
| `loyverse_connector.py` | ดึงข้อมูลยอดขายจริงจาก Loyverse POS API |
| `platform_poster.py` | โพสต์จริง: LINE OA, Facebook, Instagram + ฟังก์ชันเช็ค token |
| `google_drive.py` | upload ไฟล์/รูป/วิดีโอ ขึ้น Google Drive (OAuth2) |
| `youtube_uploader.py` | upload วิดีโอขึ้น YouTube |
| `chat_inbox.py` | อ่าน+ตอบแชท FB Messenger/IG DM + AI reply agent |
| `line_ai_bot.py` | webhook bot ตอบแชท LINE OA อัตโนมัติ (รันแยกด้วย FastAPI) |
| **`affiliate_client.py`** | REST client เรียก affiliate-autopilot backend (offline-safe) |
| **`affiliate_ui.py`** | หน้าโหมดแอฟฟิลิเอต (ภาพรวม/ร้านค้า/คอนเทนต์ A-B/โพสต์/ตั้งค่า) |
| `data/` | ข้อมูล mock + ข้อมูลลูกค้าจริง (yentafo excel) |

---

## 📱 หน้าหลักในแอป

1. **📊 Dashboard** — KPI, Sales Forecast, Top Items, Branch/Staff (mock 3 แบบ: General / หมูกระทะ / เย็นตาโฟ)
2. **📁 Upload Data** — อัปโหลด CSV ยอดขายเองเพื่อวิเคราะห์
3. **🔌 Connect POS** — ดึงข้อมูลจริงจาก Loyverse
4. **📣 Content Studio** — AI สร้างคอนเทนต์ → โพสต์ทุกแพลตฟอร์ม (รูป/วิดีโอได้)
5. **💬 AI Inbox** — อ่านแชทลูกค้า + AI ตอบอัตโนมัติ
6. **🧮 ROI Calculator** — คำนวณความคุ้มค่าก่อนขายลูกค้า

---

## 🔄 Workflow การทำงานร่วมกัน

```bash
# ก่อนเริ่มงานทุกครั้ง — ดึงโค้ดล่าสุด
git pull origin master

# แก้โค้ด แล้ว commit
git add .
git commit -m "อธิบายสิ่งที่แก้"

# push ขึ้น GitHub
git push origin master
```

**Streamlit Cloud จะ auto-deploy ทุกครั้งที่ push ขึ้น master** (รอ ~1-2 นาที เว็บอัปเดตเอง)

> ⚠️ ไฟล์ที่ **ห้าม commit** (อยู่ใน `.gitignore` แล้ว): `credentials.json`, `oauth_credentials.json`,
> `token.json`, `.env` — เป็น secret keys ห้ามขึ้น GitHub เด็ดขาด

---

## 🔑 การตั้งค่า API (ทำเมื่อต้องการโพสต์/ตอบแชทจริง)

ทุก platform มีปุ่ม **📖 วิธีขอ Token** อยู่ในแอป (sidebar) — กดดูได้เลย ละเอียดทุกขั้นตอน

| Platform | ต้องใช้ |
|---|---|
| LINE OA | Channel Access Token |
| Facebook | Page Access Token + Page ID |
| Instagram | FB Token + IG Business Account ID |
| YouTube | Google OAuth (login ครั้งเดียว) |
| Claude AI | Anthropic API key (สำหรับ AI ตอบแชท/สร้างคอนเทนต์คุณภาพสูง) |

**Streamlit Cloud secrets** (Google Drive/YouTube บน production) ตั้งที่
share.streamlit.io → app settings → Secrets

---

## 🛠️ Tech Stack

- **Frontend/Backend:** Streamlit (Python)
- **Data:** pandas, numpy
- **Charts:** Plotly
- **AI:** Anthropic Claude API (มี rule-based fallback)
- **Integrations:** Loyverse POS, LINE/Facebook/Instagram/YouTube APIs, Google Drive
- **Deploy:** Streamlit Community Cloud (auto-deploy จาก GitHub master)

---

## 👥 ทีม

- **electiction** (เบส) — owner
- **Domezzxx** (โดม) — admin

มีคำถามทักได้เลยครับ 🚀
