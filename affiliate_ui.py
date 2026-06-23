"""affiliate_ui.py — Streamlit pages for the Affiliate Autopilot mode.

These pages are the front-end for the affiliate-autopilot FastAPI backend
(Shopee Food scrape → AI content/video → multi-platform post → A/B optimize).
Everything degrades gracefully when the backend is offline.
"""
from __future__ import annotations

import streamlit as st

import affiliate_client as ac

PAGES = ["📈 ภาพรวม", "🏬 ร้านค้า", "🎬 คอนเทนต์ A/B", "📤 โพสต์", "⚙️ ตั้งค่า/เชื่อมต่อ"]


# ── shared helpers ────────────────────────────────────────────────────────────

def sidebar_controls() -> None:
    """Backend URL input + live online/offline chip. Called from the app sidebar."""
    st.markdown("**🚀 Affiliate Backend**")
    cur = st.session_state.get("aff_base_url", ac.base_url())
    val = st.text_input(
        "Backend URL",
        value=cur,
        help="ที่อยู่ของ affiliate-autopilot (FastAPI/Docker) — ปกติ http://localhost:8088",
        label_visibility="collapsed",
        placeholder="http://localhost:8088",
    )
    if val:
        st.session_state["aff_base_url"] = val.rstrip("/")
    online = ac.is_online()
    if online:
        st.success("🟢 เชื่อมต่อ backend แล้ว")
    else:
        st.error("🔴 ยังไม่เชื่อมต่อ backend")


def _offline_card() -> None:
    st.warning("🔴 ยังเชื่อมต่อ Affiliate Backend ไม่ได้")
    st.markdown(
        f"""
ระบบส่วนแอฟฟิลิเอตทำงานบน **backend แยก** (FastAPI + Docker) ตอนนี้เรียกที่
`{ac.base_url()}` ไม่ติด

**วิธีเปิด backend (บนเครื่อง server):**
```powershell
cd affiliate-autopilot
docker compose up -d --build
# Dashboard backend → http://localhost:8088
```
- รันที่เครื่องเดียวกับ Streamlit → ใช้ `http://localhost:8088`
- รันคนละเครื่อง / ผ่าน Cloudflare Funnel → ใส่ URL ของ Funnel ในช่อง **Backend URL** (sidebar) หรือ
  ตั้งใน `st.secrets["affiliate"]["base_url"]`

> โหมด **🏪 ร้านของฉัน** ใช้งานได้เต็มที่โดยไม่ต้องมี backend นี้
        """
    )
    if st.button("🔄 ลองเชื่อมต่ออีกครั้ง", key="aff_retry"):
        st.rerun()


def _config_chips(cfg: dict) -> None:
    chips = [
        ("Claude", cfg.get("has_claude")),
        ("Gemini", cfg.get("has_gemini")),
        ("Meta", cfg.get("has_meta")),
        ("วิดีโอ", cfg.get("video")),
    ]
    cols = st.columns(len(chips) + 1)
    for col, (label, on) in zip(cols, chips):
        col.markdown(f"{'🟢' if on else '⚪'} {label}")
    real = cfg.get("real_mode") or cfg.get("content_ready")
    cols[-1].markdown(("🟢 Live" if real else "🟡 Mock"))


# ── pages ─────────────────────────────────────────────────────────────────────

def _page_overview() -> None:
    st.title("🚀 Affiliate Autopilot — ภาพรวม")
    st.caption("ดึงร้าน Shopee Food → AI ผลิตคอนเทนต์/วิดีโอ → โพสต์หลายแพลตฟอร์ม → A/B auto-optimize")

    ok, data = ac.dashboard()
    if not ok:
        _offline_card()
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ร้านทั้งหมด", data.get("stores_total", 0),
              f"active {data.get('stores_active', 0)} · paused {data.get('stores_paused', 0)}")
    c2.metric("โพสต์", data.get("posts_total", 0), f"fail {data.get('posts_failed', 0)}")
    c3.metric("คลิก (Impr.)", f"{data.get('clicks', 0):,}", f"{data.get('impressions', 0):,} impressions")
    c4.metric("CTR", f"{data.get('ctr', 0) * 100:.2f}%")

    r1, r2, r3 = st.columns(3)
    r1.metric("รายได้ (ประมาณ)", f"฿{data.get('revenue_baht', 0):,.0f}")
    r2.metric("ต้นทุนคอนเทนต์", f"฿{data.get('content_cost_baht', 0):,.0f}")
    r3.metric("กำไร", f"฿{data.get('profit_baht', 0):,.0f}")

    cfg = data.get("config", {})
    if cfg:
        st.divider()
        st.caption("สถานะการเชื่อมต่อ engine")
        _config_chips(cfg)

    by_plat = data.get("by_platform", {})
    if by_plat:
        st.divider()
        st.subheader("ผลตามแพลตฟอร์ม")
        rows = [
            {"platform": p, "impressions": d.get("impressions", 0),
             "clicks": d.get("clicks", 0), "ctr": f"{d.get('ctr', 0) * 100:.2f}%"}
            for p, d in by_plat.items()
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("ควบคุมระบบ")
    _system_controls()


def _system_controls() -> None:
    sok, sys = ac.system_status()
    enabled = bool(sys.get("enabled")) if sok and isinstance(sys, dict) else False

    a, b, c, d = st.columns(4)
    with a:
        if enabled:
            if st.button("⏸️ ปิดระบบอัตโนมัติ", use_container_width=True):
                ac.system_toggle(False); st.rerun()
        else:
            if st.button("▶️ เปิดระบบอัตโนมัติ", use_container_width=True, type="primary"):
                ac.system_toggle(True); st.rerun()
    with b:
        if st.button("🎲 จำลองผล (เดโม)", use_container_width=True,
                     help="สุ่ม impressions/clicks ให้โพสต์ เพื่อเห็น A/B + auto-optimize ทำงาน"):
            ok, r = ac.simulate_metrics()
            st.toast(f"จำลองแล้ว {r.get('simulated', 0)} โพสต์" if ok else f"ผิดพลาด: {r}")
    with c:
        if st.button("⚙️ Auto-optimize", use_container_width=True,
                     help="หยุดร้านที่ CTR ต่ำติดต่อกันอัตโนมัติ"):
            ok, r = ac.auto_optimize()
            st.toast("รัน auto-optimize แล้ว" if ok else f"ผิดพลาด: {r}")
    with d:
        if st.button("🔄 รีเฟรช", use_container_width=True):
            st.rerun()
    st.caption(f"สถานะระบบ: {'🟢 เปิดอยู่' if enabled else '⚪ ปิดอยู่'}")


def _page_stores() -> None:
    st.title("🏬 ร้านค้า")
    if not ac.is_online():
        _offline_card()
        return

    # scrape + run controls
    with st.container(border=True):
        st.markdown("**ดึงร้านจาก Shopee Food แล้วรันครบวง**")
        cc1, cc2, cc3 = st.columns([2, 1, 1])
        kw = cc1.text_input("คำค้น", placeholder="เช่น ก๋วยเตี๋ยว, ชาบู, คาเฟ่", label_visibility="collapsed")
        limit = cc2.number_input("จำนวน", 1, 100, 20, label_visibility="collapsed")
        if cc3.button("🔍 ดึงร้าน", use_container_width=True):
            ok, r = ac.scrape(kw or None, int(limit))
            st.toast("เริ่มดึงร้านแล้ว…" if ok else f"ผิดพลาด: {r}")
        if st.button("▶ รันครบวงร้านใหม่ทั้งหมด", type="primary"):
            ok, r = ac.run_all(int(limit))
            st.toast("เริ่มรัน pipeline แล้ว (ทำเบื้องหลัง)" if ok else f"ผิดพลาด: {r}")

    ok, stores = ac.list_stores()
    if not ok:
        st.error(f"โหลดร้านไม่ได้: {stores}")
        return
    if not stores:
        st.info("ยังไม่มีร้านในระบบ — กด 'ดึงร้าน' ด้านบน หรือเพิ่มเองด้านล่าง")
    else:
        st.caption(f"ทั้งหมด {len(stores)} ร้าน")
        table = [
            {"id": s["id"], "ร้าน": s["name"], "ย่าน": s.get("area", ""),
             "เรตติ้ง": s.get("rating", 0), "สถานะ": s.get("status", ""),
             "คลิก": s.get("clicks", 0), "รายได้": f"฿{s.get('revenue', 0):,.0f}",
             "กำไร": f"฿{s.get('profit', 0):,.0f}"}
            for s in stores
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)

        ids = [s["id"] for s in stores]
        names = {s["id"]: s["name"] for s in stores}
        sel = st.selectbox("เลือกร้านเพื่อรัน/ดูคอนเทนต์", ids,
                           format_func=lambda i: f"#{i} · {names.get(i, '')}")
        b1, b2 = st.columns(2)
        if b1.button("▶ รันครบวงร้านนี้", use_container_width=True):
            ok, r = ac.run_store(int(sel))
            st.toast("เริ่มรันร้านนี้แล้ว (ทำเบื้องหลัง)" if ok else f"ผิดพลาด: {r}")
        if b2.button("🎬 ดูคอนเทนต์ร้านนี้", use_container_width=True):
            st.session_state["aff_view_store"] = int(sel)
            st.session_state["aff_menu"] = "🎬 คอนเทนต์ A/B"
            st.rerun()

    with st.expander("➕ เพิ่มร้านเอง"):
        n = st.text_input("ชื่อร้าน")
        ar = st.text_input("ย่าน/พื้นที่")
        mn = st.text_input("เมนูเด่น (คั่นด้วย ,)")
        su = st.text_input("ลิงก์ Shopee / affiliate")
        if st.button("เพิ่มร้าน"):
            if not n:
                st.warning("ใส่ชื่อร้านก่อน")
            else:
                menu = [m.strip() for m in mn.split(",") if m.strip()]
                ok, r = ac.add_store(n, ar, menu, shopee_url=su, affiliate_link=su)
                st.toast("เพิ่มร้านแล้ว" if ok else f"ผิดพลาด: {r}")
                if ok:
                    st.rerun()


def _page_content() -> None:
    st.title("🎬 คอนเทนต์ A/B")
    if not ac.is_online():
        _offline_card()
        return

    ok, stores = ac.list_stores()
    if not ok or not stores:
        st.info("ยังไม่มีร้าน — ไปที่หน้า 🏬 ร้านค้า เพื่อดึง/เพิ่มร้านก่อน")
        return

    ids = [s["id"] for s in stores]
    names = {s["id"]: s["name"] for s in stores}
    default = st.session_state.pop("aff_view_store", ids[0])
    idx = ids.index(default) if default in ids else 0
    store_id = st.selectbox("เลือกร้าน", ids, index=idx, format_func=lambda i: f"#{i} · {names.get(i, '')}")

    ok, content = ac.get_content(int(store_id))
    if not ok:
        st.error(f"โหลดคอนเทนต์ไม่ได้: {content}")
        return

    reel = content.get("reel_url")
    if reel:
        st.subheader("คลิปรวม (Reel)")
        st.video(ac.media_url(reel))

    variants = content.get("variants", [])
    if not variants:
        st.info("ร้านนี้ยังไม่มีคอนเทนต์ที่พร้อม — กด '▶ รันครบวงร้านนี้' ในหน้าร้านค้า แล้วรอ AI ผลิต")
        return

    st.caption(f"{len(variants)} variant")
    cols = st.columns(min(2, len(variants)))
    for i, v in enumerate(variants):
        with cols[i % len(cols)].container(border=True):
            st.markdown(f"**Variant {v.get('label', '?')} · {v.get('platform', '')}**")
            murl = ac.media_url(v.get("media_url", ""))
            if murl:
                if v.get("media_type") == "video":
                    st.video(murl)
                else:
                    st.image(murl, use_container_width=True)
            if v.get("video_title"):
                st.markdown(f"🎯 **{v['video_title']}**")
            if v.get("hook"):
                st.write(v["hook"])
            if v.get("caption"):
                st.caption(v["caption"])
            tags = v.get("hashtags", [])
            if tags:
                st.markdown(" ".join(f"`{t}`" for t in tags))
            if v.get("cta"):
                st.markdown(f"➡️ {v['cta']}")
            if v.get("first_comment"):
                st.info(f"💬 คอมเมนต์แรก: {v['first_comment']}")

    # A/B result
    ok, ab = ac.abtest(int(store_id))
    if ok and isinstance(ab, dict) and ab:
        st.divider()
        st.subheader("ผล A/B")
        st.json(ab)


def _page_posts() -> None:
    st.title("📤 โพสต์")
    if not ac.is_online():
        _offline_card()
        return
    ok, posts = ac.list_posts()
    if not ok:
        st.error(f"โหลดโพสต์ไม่ได้: {posts}")
        return
    if not posts:
        st.info("ยังไม่มีโพสต์")
        return
    table = [
        {"id": p["id"], "ร้าน": p.get("store_id"), "แพลตฟอร์ม": p.get("platform"),
         "วิธี": p.get("method"), "สถานะ": p.get("status"),
         "คอมเมนต์": p.get("comment_status", ""), "เมื่อ": (p.get("posted_at") or "")[:16],
         "error": (p.get("error") or "")[:60]}
        for p in posts
    ]
    st.dataframe(table, use_container_width=True, hide_index=True)


def _page_setup() -> None:
    st.title("⚙️ ตั้งค่า / เชื่อมต่อ Backend")
    st.markdown(f"Backend ปัจจุบัน: `{ac.base_url()}`")

    new = st.text_input("เปลี่ยน Backend URL", value=ac.base_url())
    if st.button("บันทึก URL"):
        st.session_state["aff_base_url"] = new.rstrip("/")
        st.rerun()

    ok, _ = ac.health()
    (st.success if ok else st.error)("🟢 เชื่อมต่อได้" if ok else "🔴 เชื่อมต่อไม่ได้")

    if not ok:
        _offline_card()
        return

    st.divider()
    st.subheader("สถานะ key / engine")
    kok, keys = ac.keys_status()
    if kok and isinstance(keys, dict):
        rows = [
            ("Claude (เขียนคอนเทนต์)", keys.get("claude")),
            ("Gemini (ภาพ/วิดีโอ)", keys.get("gemini")),
            ("Meta (FB/IG โพสต์)", keys.get("meta")),
            ("YouTube", keys.get("youtube")),
            ("วิดีโอจริง", keys.get("video")),
        ]
        for label, on in rows:
            st.markdown(f"{'🟢' if on else '⚪'} {label}")
        st.caption(f"โหมดเนื้อหา: {keys.get('content_provider', '?')} · "
                   f"การโพสต์: {keys.get('posting_mode', '?')} · "
                   f"มือถือ farm: {keys.get('phones', 0)} เครื่อง · "
                   f"{'🟢 Live' if keys.get('real_mode') else '🟡 Mock'}")

    st.divider()
    st.subheader("ควบคุมระบบ")
    _system_controls()


# ── entry ─────────────────────────────────────────────────────────────────────

def render(page: str) -> None:
    {
        "📈 ภาพรวม": _page_overview,
        "🏬 ร้านค้า": _page_stores,
        "🎬 คอนเทนต์ A/B": _page_content,
        "📤 โพสต์": _page_posts,
        "⚙️ ตั้งค่า/เชื่อมต่อ": _page_setup,
    }.get(page, _page_overview)()
