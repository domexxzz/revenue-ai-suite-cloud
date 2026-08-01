import datetime as dt
import io
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from google_drive import (
        upload_file, upload_text, upload_excel, needs_auth, run_first_time_auth,
        list_child_folders, list_files_in_folder, download_file,
        ensure_subfolder, move_file,
    )
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False

try:
    from platform_poster import post_line_oa, post_line_oa_with_image, post_facebook, post_instagram
    POSTER_AVAILABLE = True
except ImportError:
    POSTER_AVAILABLE = False

try:
    from youtube_uploader import upload_video as upload_youtube
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

try:
    from chat_inbox import fetch_conversations, send_message, generate_ai_reply, DEFAULT_PROFILE
    CHAT_INBOX_AVAILABLE = True
except ImportError:
    CHAT_INBOX_AVAILABLE = False

try:
    import affiliate_ui
    AFFILIATE_AVAILABLE = True
except ImportError:
    AFFILIATE_AVAILABLE = False

try:
    import content_copilot
    COPILOT_AVAILABLE = True
except ImportError:
    COPILOT_AVAILABLE = False

try:
    import brainstorm
    BRAINSTORM_AVAILABLE = True
except ImportError:
    BRAINSTORM_AVAILABLE = False

try:
    import canva_client
    CANVA_AVAILABLE = True
except ImportError:
    CANVA_AVAILABLE = False

try:
    import scene_presets
    SCENES_AVAILABLE = True
except ImportError:
    SCENES_AVAILABLE = False

try:
    import tiktok_poster
    TIKTOK_AVAILABLE = True
except ImportError:
    TIKTOK_AVAILABLE = False

try:
    import flow_sync
    FLOW_SYNC_AVAILABLE = True
except ImportError:
    FLOW_SYNC_AVAILABLE = False

# Top-level mode switch labels (shop owner vs affiliate marketing)
MODE_SHOP = "🏪 ร้านของฉัน"
MODE_AFFILIATE = "🚀 แอฟฟิลิเอต"


def _upload_to_drive_public(file_bytes: bytes, name: str, mime: str) -> str | None:
    """Helper: upload bytes to Drive, return public URL."""
    try:
        from google_drive import upload_image_public
        return upload_image_public(file_bytes, name, GDRIVE_FOLDER_ID, mime_type=mime)
    except Exception as e:
        return None


PLATFORM_THAI_NAMES = {
    "line_oa": "💚 LINE OA", "facebook": "🔵 Facebook", "instagram": "🟣 Instagram",
    "tiktok": "⬛ TikTok", "youtube": "🔴 YouTube",
}


def _record_post(platform_key: str, ok: bool, detail: str) -> None:
    """Append a post attempt to session history."""
    st.session_state.setdefault("post_history", []).append({
        "เวลา": dt.datetime.now().strftime("%d/%m %H:%M"),
        "แพลตฟอร์ม": PLATFORM_THAI_NAMES.get(platform_key, platform_key),
        "สถานะ": "✅ สำเร็จ" if ok else "❌ ไม่สำเร็จ",
        "รายละเอียด": detail[:160],
    })


def _do_post(platform_key: str, content: str,
             line_token: str, fb_token: str, fb_page_id: str,
             ig_business_id: str = "",
             image_bytes: bytes | None = None, image_name: str = "image.jpg",
             video_bytes: bytes | None = None, video_name: str = "video.mp4",
             quiet: bool = False) -> tuple[bool, str]:
    """Post to one platform. Returns (ok, message) and records history."""
    ok, msg = False, ""

    if platform_key == "line_oa":
        if not line_token:
            msg = "ใส่ LINE OA Token ในแถบซ้ายก่อน"
        else:
            with st.spinner("กำลังส่งไป LINE OA..."):
                if image_bytes:
                    if not GDRIVE_AVAILABLE or needs_auth():
                        msg = "ต้อง authorize Google Drive ก่อนส่งภาพ"
                    else:
                        img_url = _upload_to_drive_public(image_bytes, image_name, "image/jpeg")
                        if not img_url:
                            msg = "Upload ภาพไม่ได้"
                        else:
                            ok, msg = post_line_oa_with_image(content, img_url, line_token)
                else:
                    ok, msg = post_line_oa(content, line_token)

    elif platform_key == "facebook":
        if not fb_token or not fb_page_id:
            msg = "ใส่ Facebook Token และ Page ID ก่อน"
        else:
            with st.spinner("กำลังโพสต์ Facebook..."):
                ok, msg = post_facebook(content, fb_token, fb_page_id,
                                        image_bytes=image_bytes, image_name=image_name)

    elif platform_key == "instagram":
        if not fb_token or not ig_business_id:
            msg = "ใส่ FB Token + IG Business ID ก่อน"
        elif not image_bytes and not video_bytes:
            msg = "IG ต้องมีรูปหรือวิดีโอ"
        elif not GDRIVE_AVAILABLE or needs_auth():
            msg = "ต้อง authorize Google Drive ก่อน"
        else:
            with st.spinner("กำลังโพสต์ Instagram (วิดีโออาจใช้เวลานาน)..."):
                img_url = vid_url = None
                if video_bytes:
                    vid_url = _upload_to_drive_public(video_bytes, video_name, "video/mp4")
                elif image_bytes:
                    img_url = _upload_to_drive_public(image_bytes, image_name, "image/jpeg")
                if not img_url and not vid_url:
                    msg = "Upload media ไม่ได้"
                else:
                    ok, msg = post_instagram(content, img_url, vid_url, ig_business_id, fb_token)

    elif platform_key == "youtube":
        if not video_bytes:
            msg = "YouTube ต้องมีวิดีโอ — อัปโหลดวิดีโอก่อน"
        elif not YOUTUBE_AVAILABLE:
            msg = "YouTube module ไม่ได้ติดตั้ง"
        else:
            title = content.split("\n")[0][:100] or "REVENUE AI Post"
            with st.spinner("กำลังอัปโหลด YouTube (อาจใช้เวลา 1-3 นาที)..."):
                ok, result = upload_youtube(video_bytes, title=title, description=content)
            msg = result
            if ok and not quiet:
                st.success("YouTube สำเร็จ ✅")
                st.markdown(f"[🔗 เปิดวิดีโอ]({result})")

    elif platform_key == "tiktok":
        tt_token = st.session_state.get("tiktok_token", "")
        if not video_bytes:
            msg = "TikTok ต้องมีวิดีโอ"
        elif not TIKTOK_AVAILABLE or not tt_token:
            # No token configured — fall back to the manual hand-off.
            ok, msg = True, "วิดีโอพร้อม — ดาวน์โหลดแล้วอัปโหลดในแอป TikTok"
            if not quiet:
                st.info("📥 TikTok: ใส่ Access Token ในแถบซ้ายเพื่อโพสต์อัตโนมัติ "
                        "หรือดาวน์โหลดวิดีโอไปอัปเองในแอป")
            st.session_state["tiktok_video_ready"] = True
        else:
            privacy = st.session_state.get("tiktok_privacy", "SELF_ONLY")
            with st.spinner("กำลังอัปโหลดไป TikTok (อาจใช้เวลาหลายนาที)..."):
                ok, msg = tiktok_poster.post_video(
                    video_bytes, content, tt_token, privacy=privacy)
    else:
        ok, msg = True, "บันทึกคอนเทนต์แล้ว"

    _record_post(platform_key, ok, msg)
    if not quiet and platform_key != "youtube":
        st.toast(("✅ " if ok else "❌ ") + msg, icon="✅" if ok else "❌")
    return ok, msg

def _get_gdrive_folder_id() -> str:
    """Read folder ID from Streamlit secrets, fall back to default."""
    try:
        import streamlit as st
        return st.secrets.get("google_drive", {}).get("folder_id", "") or "1-Kc-3l6C781lav4emTLCbZ202JVjExux"
    except Exception:
        return "1-Kc-3l6C781lav4emTLCbZ202JVjExux"


GDRIVE_FOLDER_ID = _get_gdrive_folder_id()


def _get_queue_root_id() -> str:
    """Root Drive folder that holds the per-platform queue subfolders
    (Facebook Post / Facebook VDO / Instragram Post / ... / TikTok VDO)."""
    try:
        import streamlit as st
        return st.secrets.get("google_drive", {}).get("queue_root_id", "") or "12sVv5PEq9KNk7JlPq0sKVUAfqvIf8Nzb"
    except Exception:
        return "12sVv5PEq9KNk7JlPq0sKVUAfqvIf8Nzb"


QUEUE_ROOT_FOLDER_ID = _get_queue_root_id()


def _get_shortcut(key: str, fallback: str) -> str:
    """Quick-link URL from secrets, falling back to the team's own workspace."""
    try:
        import streamlit as st
        return st.secrets.get("shortcuts", {}).get(key, "") or fallback
    except Exception:
        return fallback


# Where the team actually works — surfaced as one-click links so nobody has to
# hunt for the tab. Override per deployment via [shortcuts] in secrets.toml.
FLOW_PROJECT_URL = _get_shortcut(
    "flow_project",
    "https://labs.google/fx/th/tools/flow/project/c9bfbfd9-88ea-4c56-b6b5-7711df26d9b8",
)
DRIVE_FOLDER_URL = _get_shortcut(
    "drive_folder",
    f"https://drive.google.com/drive/folders/{QUEUE_ROOT_FOLDER_ID}",
)

try:
    from loyverse_connector import LoyverseConnector
    LOYVERSE_AVAILABLE = True
except ImportError:
    LOYVERSE_AVAILABLE = False

try:
    from content_studio import (
        PLATFORMS, CAMPAIGN_TYPES, TONES,
        get_content_package, build_posting_schedule, route_content,
    )
    CONTENT_STUDIO_AVAILABLE = True
except ImportError:
    CONTENT_STUDIO_AVAILABLE = False

from rfm_engine import (
    SEGMENT_META,
    compute_rfm,
    label_transactions,
    rfm_summary,
)

# ── Chart templates ────────────────────────────────────────────────────────────
_COLORWAY = ["#F59E0B", "#3B82F6", "#10B981", "#8B5CF6", "#EF4444", "#EC4899", "#06B6D4"]

pio.templates["premium_dark"] = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="#0F172A",
        plot_bgcolor="#111827",
        font=dict(family="Inter, sans-serif", color="#9CA3AF", size=12),
        colorway=_COLORWAY,
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.08)",
            tickfont=dict(color="#6B7280", size=11), zerolinecolor="rgba(255,255,255,0.06)",
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.04)", linecolor="rgba(255,255,255,0.08)",
            tickfont=dict(color="#6B7280", size=11), zerolinecolor="rgba(255,255,255,0.06)",
        ),
        legend=dict(
            bgcolor="rgba(17,24,39,0.85)", bordercolor="rgba(255,255,255,0.08)",
            borderwidth=1, font=dict(color="#9CA3AF", size=11),
        ),
        title=dict(font=dict(family="Plus Jakarta Sans, sans-serif", color="#E5E7EB", size=14), x=0),
        margin=dict(l=0, r=0, t=44, b=0),
        hoverlabel=dict(
            bgcolor="#1F2937", bordercolor="rgba(255,255,255,0.1)",
            font=dict(family="Inter, sans-serif", size=12, color="#F9FAFB"),
        ),
    )
)

pio.templates["premium_light"] = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#F8F7F4",
        font=dict(family="Inter, sans-serif", color="#6B7280", size=12),
        colorway=_COLORWAY,
        xaxis=dict(
            gridcolor="rgba(0,0,0,0.06)", linecolor="rgba(0,0,0,0.08)",
            tickfont=dict(color="#9CA3AF", size=11), zerolinecolor="rgba(0,0,0,0.06)",
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0.06)", linecolor="rgba(0,0,0,0.08)",
            tickfont=dict(color="#9CA3AF", size=11), zerolinecolor="rgba(0,0,0,0.06)",
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.95)", bordercolor="rgba(0,0,0,0.08)",
            borderwidth=1, font=dict(color="#6B7280", size=11),
        ),
        title=dict(font=dict(family="Plus Jakarta Sans, sans-serif", color="#111827", size=14), x=0),
        margin=dict(l=0, r=0, t=44, b=0),
        hoverlabel=dict(
            bgcolor="#FFFFFF", bordercolor="rgba(0,0,0,0.1)",
            font=dict(family="Inter, sans-serif", size=12, color="#111827"),
        ),
    )
)

pio.templates.default = "premium_dark"


def apply_premium_theme(theme: str = "dark") -> None:
    is_dark = theme == "dark"

    # ── Shared token values per theme ──────────────────────────────────────
    if is_dark:
        # Lifted off near-black (#080C14). At that level text edges bloom against
        # the background and long reading gets tiring; a few points of lightness
        # keeps the dark look without the glare.
        bg          = "#0E141F"
        bg2         = "#1A2332"
        bg3         = "#151E2B"
        sidebar_bg  = "linear-gradient(180deg,#141C28 0%,#0E141F 100%)"
        border      = "rgba(255,255,255,0.05)"
        border2     = "rgba(255,255,255,0.06)"
        border3     = "rgba(255,255,255,0.08)"
        txt1        = "#F9FAFB"
        txt2        = "#E5E7EB"
        txt3        = "#9CA3AF"
        txt4        = "#6B7280"
        txt5        = "#4B5563"
        txt6        = "#374151"
        h1_grad     = "linear-gradient(135deg,#FFFFFF 0%,#F59E0B 60%,#FBBF24 100%)"
        card_bg     = "linear-gradient(145deg,#111827 0%,#0F172A 100%)"
        card_hover  = "0 16px 48px rgba(0,0,0,0.5),0 0 0 1px rgba(245,158,11,0.18)"
        tab_hover   = "#D1D5DB"
        input_bg    = "#111827"
        exp_bg      = "#111827"
        alert_mult  = "0.07"
        alert_p_ok  = "#A7F3D0"; alert_p_info = "#BFDBFE"
        alert_p_war = "#FEF3C7"; alert_p_err  = "#FEE2E2"
        scroll_thumb= "rgba(255,255,255,0.08)"; scroll_thumbh="rgba(255,255,255,0.14)"
        lbl_color   = "#9CA3AF"
        hr_color    = "rgba(255,255,255,0.06)"
        hover_label = "#1F2937"
        chart_bg    = "rgba(17,24,39,0.5)"
    else:
        bg          = "#F8F7F4"
        bg2         = "#FFFFFF"
        bg3         = "#F3F4F6"
        sidebar_bg  = "linear-gradient(180deg,#FFFFFF 0%,#F9FAFB 100%)"
        border      = "rgba(0,0,0,0.06)"
        border2     = "rgba(0,0,0,0.07)"
        border3     = "rgba(0,0,0,0.09)"
        txt1        = "#111827"
        txt2        = "#1F2937"
        txt3        = "#374151"
        txt4        = "#6B7280"
        txt5        = "#9CA3AF"
        txt6        = "#D1D5DB"
        h1_grad     = "linear-gradient(135deg,#111827 0%,#B45309 60%,#F59E0B 100%)"
        card_bg     = "#FFFFFF"
        card_hover  = "0 16px 48px rgba(0,0,0,0.1),0 0 0 1px rgba(245,158,11,0.2)"
        tab_hover   = "#374151"
        input_bg    = "#FFFFFF"
        exp_bg      = "#FFFFFF"
        alert_mult  = "0.08"
        alert_p_ok  = "#065F46"; alert_p_info = "#1E40AF"
        alert_p_war = "#92400E"; alert_p_err  = "#991B1B"
        scroll_thumb= "rgba(0,0,0,0.12)";  scroll_thumbh="rgba(0,0,0,0.2)"
        lbl_color   = "#6B7280"
        hr_color    = "rgba(0,0,0,0.07)"
        hover_label = "#FFFFFF"
        chart_bg    = "rgba(248,247,244,0.6)"

    card_shadow = (
        "0 1px 3px rgba(0,0,0,0.04),0 4px 16px rgba(0,0,0,0.04)"
        if not is_dark else "none"
    )

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

/* ── Keyframes ─────────────────────────────────────────────────────────── */
@keyframes fadeUp {{
  from {{ opacity:0; transform:translateY(10px); }}
  to   {{ opacity:1; transform:translateY(0); }}
}}
@keyframes gradientFlow {{
  0%   {{ background-position: 0% 50%; }}
  50%  {{ background-position: 100% 50%; }}
  100% {{ background-position: 0% 50%; }}
}}
@keyframes shimmer {{
  0%   {{ background-position: -200% center; }}
  100% {{ background-position: 200% center; }}
}}
@keyframes pulseGlow {{
  0%,100% {{ box-shadow: 0 0 0 0 rgba(245,158,11,0.25); }}
  50%      {{ box-shadow: 0 0 0 6px rgba(245,158,11,0); }}
}}

/* ── Base ──────────────────────────────────────────────────────────────── */
html, body, .stApp {{ font-family:'Inter',-apple-system,sans-serif !important; }}
/* Both selectors: current Streamlit marks this container with a data-testid and
   the .stApp class no longer reaches it, which left the whole page frame dark
   behind a light body — the dark border showing around the content. */
/* Prefixed with html body to outrank Streamlit's own emotion classes, which
   carry the palette from config.toml and were winning on specificity — the rule
   was present and correct but never applied. */
html body .stApp, html body [data-testid="stApp"],
html body [data-testid="stAppViewContainer"] {{
  background:{bg} !important; transition:background 0.35s ease;
}}
html body [data-testid="stSidebar"] {{ background:{sidebar_bg} !important; }}
[data-testid="stAppViewContainer"] > .main {{ background:{bg} !important; }}

/* Streamlit paints its own chrome from config.toml, which is pinned to the dark
   palette. Without these the header and the bar holding the chat box stayed
   black in light mode — a dark band across the top and bottom of a light page.
   The text colour has to follow too: config also pins that, so switching to the
   light theme left near-white type sitting on the new near-white background. */
html, body {{ background:{bg} !important; color:{txt1} !important; }}
[data-testid="stAppHeader"], header[data-testid="stHeader"] {{
  background:{bg} !important; color:{txt2} !important;
  border-bottom:1px solid {border} !important;
}}
[data-testid="stAppHeader"] *, [data-testid="stAppHeader"] svg {{
  color:{txt2} !important; fill:{txt2} !important;
}}
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {{
  background:{bg} !important; color:{txt1} !important;
}}
[data-testid="stBottom"] * {{ color:{txt1} !important; }}
[data-testid="stChatInput"] {{
  background:{input_bg} !important; border:1px solid {border3} !important;
  border-radius:14px !important;
}}
[data-testid="stChatInput"] textarea {{
  background:transparent !important; color:{txt1} !important; font-size:1rem !important;
}}
[data-testid="stChatInput"] textarea::placeholder {{ color:{txt4} !important; }}
[data-testid="stChatMessage"] {{ background:{card_bg} !important; border:1px solid {border2} !important; }}

/* Readability: body copy was rendering at 13.4px, which is hard work at arm's
   length — measured, not assumed. The html body prefix is needed here for the
   same reason as the background rules above. */
html body [data-testid="stMarkdownContainer"] p,
html body [data-testid="stMarkdownContainer"] li {{
  font-size:1rem !important; line-height:1.65 !important;
}}
html body [data-testid="stCaptionContainer"],
html body [data-testid="stCaptionContainer"] p {{ font-size:0.9rem !important; }}
html body [data-testid="stChatInput"] textarea {{ font-size:1rem !important; }}
html body button p, html body [data-testid="stBaseButton-secondary"] p,
html body [data-testid="stBaseButton-primary"] p {{ font-size:0.95rem !important; }}
.block-container {{ padding-top:2rem !important; padding-bottom:3rem !important; }}
.main .block-container > div > div > div {{ animation: fadeUp 0.4s ease both; }}

/* ── Sidebar ───────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
  background:{sidebar_bg} !important;
  border-right:1px solid {border} !important;
  transition:background 0.35s ease;
}}
[data-testid="stSidebar"] hr {{ border-color:{border2} !important; margin:0.75rem 0 !important; }}
[data-testid="stSidebar"] .stMarkdown strong {{
  font-size:0.68rem !important; font-weight:600 !important;
  text-transform:uppercase !important; letter-spacing:0.12em !important; color:{txt5} !important;
}}
[data-testid="stSidebar"] [data-testid="stTextInput"] input {{
  background:{input_bg} !important; border-color:{border3} !important;
  color:{txt1} !important; border-radius:8px !important; font-size:0.8rem !important;
}}
[data-testid="stSidebar"] .stCaption p {{ color:{txt6} !important; font-size:0.72rem !important; }}

/* ── Theme toggle buttons ──────────────────────────────────────────────── */
button[kind="secondary"] {{
  background:{bg3} !important; border:1px solid {border2} !important;
  color:{txt3} !important; border-radius:8px !important; font-size:0.78rem !important;
  font-weight:500 !important; transition:all 0.18s ease !important;
}}
button[kind="secondary"]:hover {{
  border-color:rgba(245,158,11,0.5) !important; color:#F59E0B !important;
  background:{bg2} !important;
}}

/* ── Typography ────────────────────────────────────────────────────────── */
h1 {{
  font-family:'Plus Jakarta Sans',sans-serif !important; font-weight:800 !important;
  letter-spacing:-0.04em !important; line-height:1.15 !important;
  background:{h1_grad} !important; background-size:200% auto !important;
  -webkit-background-clip:text !important; -webkit-text-fill-color:transparent !important;
  background-clip:text !important;
  animation: gradientFlow 6s ease infinite !important;
}}
h2 {{
  font-family:'Plus Jakarta Sans',sans-serif !important; font-weight:700 !important;
  color:{txt2} !important; letter-spacing:-0.02em !important;
}}
h3 {{
  font-family:'Plus Jakarta Sans',sans-serif !important; font-weight:600 !important;
  color:{txt2} !important;
}}
p, .stMarkdown p {{ color:{txt3} !important; font-size:0.875rem !important; line-height:1.6 !important; }}
.stCaption p, [data-testid="stCaptionContainer"] p {{
  color:{txt4} !important; font-size:0.775rem !important;
}}

/* ── Metric Cards ──────────────────────────────────────────────────────── */
[data-testid="metric-container"], [data-testid="stMetric"] {{
  background:{card_bg} !important;
  border:1px solid {border} !important;
  border-top:2px solid #F59E0B !important;
  border-radius:16px !important;
  padding:1.25rem 1.5rem !important;
  box-shadow:{card_shadow} !important;
  transition:transform 0.22s cubic-bezier(.34,1.56,.64,1), box-shadow 0.22s ease !important;
  position:relative !important; overflow:hidden !important;
}}
[data-testid="metric-container"]::after, [data-testid="stMetric"]::after {{
  content:"" !important; position:absolute !important;
  top:0; left:-100%; width:60%; height:100% !important;
  background:linear-gradient(90deg,transparent,rgba(245,158,11,0.04),transparent) !important;
  transition:left 0.5s ease !important;
}}
[data-testid="metric-container"]:hover::after, [data-testid="stMetric"]:hover::after {{
  left:150% !important;
}}
[data-testid="metric-container"]:hover, [data-testid="stMetric"]:hover {{
  transform:translateY(-3px) !important;
  box-shadow:{card_hover} !important;
}}
[data-testid="stMetricValue"] > div, [data-testid="stMetricValue"] {{
  font-family:'Plus Jakarta Sans',sans-serif !important;
  font-size:1.875rem !important; font-weight:700 !important;
  color:{txt1} !important; letter-spacing:-0.04em !important;
}}
[data-testid="stMetricLabel"] > div, [data-testid="stMetricLabel"] {{
  font-size:0.68rem !important; font-weight:600 !important;
  text-transform:uppercase !important; letter-spacing:0.12em !important; color:{txt4} !important;
}}

/* ── Tabs ──────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
  background:transparent !important;
  border-bottom:1px solid {border2} !important; gap:0 !important;
}}
.stTabs [data-baseweb="tab"] {{
  background:transparent !important; color:{txt4} !important;
  font-size:0.875rem !important; font-weight:500 !important;
  padding:0.75rem 1.25rem !important;
  border-bottom:2px solid transparent !important; border-radius:0 !important;
  transition:color 0.15s ease !important;
}}
.stTabs [data-baseweb="tab"]:hover {{ color:{tab_hover} !important; }}
.stTabs [aria-selected="true"] {{ color:#F59E0B !important; border-bottom-color:#F59E0B !important; font-weight:600 !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background:#F59E0B !important; height:2px !important; }}
.stTabs [data-baseweb="tab-border"] {{ background:{border2} !important; }}

/* ── Alert / Insight Cards ─────────────────────────────────────────────── */
[data-testid="stAlert"] {{
  border-radius:12px !important; border:1px solid {border} !important;
  padding:0.9rem 1rem 0.9rem 1.25rem !important; font-size:0.875rem !important;
  animation:fadeUp 0.35s ease both !important;
}}
div.stSuccess {{
  background:rgba(16,185,129,{alert_mult}) !important; border-left:3px solid #10B981 !important;
}}
div.stInfo {{
  background:rgba(59,130,246,{alert_mult}) !important; border-left:3px solid #3B82F6 !important;
}}
div.stWarning {{
  background:rgba(245,158,11,{alert_mult}) !important; border-left:3px solid #F59E0B !important;
}}
div.stError {{
  background:rgba(239,68,68,{alert_mult}) !important; border-left:3px solid #EF4444 !important;
}}
div.stSuccess p,div.stSuccess [data-testid="stMarkdownContainer"] p{{ color:{alert_p_ok} !important; }}
div.stInfo p,   div.stInfo [data-testid="stMarkdownContainer"] p   {{ color:{alert_p_info} !important; }}
div.stWarning p,div.stWarning [data-testid="stMarkdownContainer"] p{{ color:{alert_p_war} !important; }}
div.stError p,  div.stError [data-testid="stMarkdownContainer"] p  {{ color:{alert_p_err} !important; }}

/* ── Buttons ───────────────────────────────────────────────────────────── */
[data-testid="stDownloadButton"] button {{
  background:linear-gradient(135deg,#B45309,#F59E0B) !important;
  color:#000 !important; font-weight:700 !important; font-size:0.8125rem !important;
  border:none !important; border-radius:10px !important; letter-spacing:0.02em !important;
  box-shadow:0 4px 15px rgba(245,158,11,0.3),inset 0 1px 0 rgba(255,255,255,0.18) !important;
  transition:all 0.2s cubic-bezier(.34,1.56,.64,1) !important;
  animation:pulseGlow 2.5s ease-in-out infinite !important;
}}
[data-testid="stDownloadButton"] button:hover {{
  transform:translateY(-2px) scale(1.01) !important;
  box-shadow:0 10px 30px rgba(245,158,11,0.45) !important;
}}

/* ── Inputs ────────────────────────────────────────────────────────────── */
[data-testid="stMultiSelect"] > div > div {{
  background:{input_bg} !important; border-color:{border3} !important; color:{txt1} !important;
  border-radius:10px !important;
}}
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
  background:rgba(245,158,11,0.12) !important; color:#F59E0B !important;
  border:1px solid rgba(245,158,11,0.25) !important; border-radius:6px !important; font-weight:500 !important;
}}
[data-testid="stNumberInput"] input, [data-testid="stTextInput"] input {{
  background:{input_bg} !important; border-color:{border3} !important;
  color:{txt1} !important; border-radius:10px !important;
  transition:border-color 0.15s ease,box-shadow 0.15s ease !important;
}}
[data-testid="stNumberInput"] input:focus, [data-testid="stTextInput"] input:focus {{
  border-color:rgba(245,158,11,0.5) !important;
  box-shadow:0 0 0 3px rgba(245,158,11,0.1) !important;
}}

/* ── Charts ────────────────────────────────────────────────────────────── */
.stPlotlyChart {{
  border-radius:16px !important; overflow:hidden !important;
  border:1px solid {border} !important;
  box-shadow:{card_shadow} !important;
  transition:box-shadow 0.22s ease !important;
}}
.stPlotlyChart:hover {{
  box-shadow:{"0 12px 40px rgba(0,0,0,0.4)" if is_dark else "0 8px 32px rgba(0,0,0,0.1)"} !important;
}}

/* ── Table ─────────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {{
  border:1px solid {border} !important; border-radius:14px !important;
  overflow:hidden !important; box-shadow:{card_shadow} !important;
}}

/* ── Expander ──────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {{
  background:{exp_bg} !important; border:1px solid {border2} !important;
  border-radius:14px !important; overflow:hidden !important;
  box-shadow:{card_shadow} !important;
  transition:box-shadow 0.2s ease !important;
}}
[data-testid="stExpander"]:hover {{ box-shadow:{card_hover} !important; }}
[data-testid="stExpander"] summary {{ color:{txt2} !important; font-weight:500 !important; }}
[data-testid="stExpander"] summary:hover {{ color:{txt1} !important; }}

/* ── File uploader ─────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] > div {{
  background:{bg2} !important; border:1.5px dashed {border3} !important;
  border-radius:14px !important; transition:all 0.2s ease !important;
}}
[data-testid="stFileUploader"] > div:hover {{
  border-color:rgba(245,158,11,0.45) !important;
  box-shadow:0 0 0 3px rgba(245,158,11,0.06) !important;
}}

/* ── Divider ───────────────────────────────────────────────────────────── */
hr {{ border:none !important; border-top:1px solid {hr_color} !important; margin:2rem 0 !important; }}

/* ── Scrollbar ─────────────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width:5px; height:5px; }}
::-webkit-scrollbar-track {{ background:transparent; }}
::-webkit-scrollbar-thumb {{ background:{scroll_thumb}; border-radius:3px; }}
::-webkit-scrollbar-thumb:hover {{ background:{scroll_thumbh}; }}

/* ── Form labels ───────────────────────────────────────────────────────── */
.stSelectbox label, .stMultiSelect label, .stDateInput label,
.stSlider label, .stNumberInput label, .stCheckbox label p {{
  color:{lbl_color} !important; font-size:0.8125rem !important; font-weight:500 !important;
}}

/* ── Date input ────────────────────────────────────────────────────────── */
[data-testid="stDateInput"] input {{
  background:{input_bg} !important; border-color:{border3} !important; color:{txt1} !important;
  border-radius:10px !important;
}}

/* ── Slider ────────────────────────────────────────────────────────────── */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {{
  background:#F59E0B !important; border-color:#F59E0B !important;
}}

/* ── Radio (main area, default look) ───────────────────────────────────── */
[data-testid="stRadio"] label p {{ color:{txt3} !important; font-size:0.875rem !important; }}
[data-testid="stRadio"] [data-baseweb="radio"] div:first-child {{
  border-color:{border3} !important;
}}

/* ── Sidebar nav: radios rendered as big, full-width tappable buttons ───── */
section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {{
  gap:7px !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label {{
  width:100% !important;
  margin:0 !important;
  padding:11px 14px !important;
  min-height:44px !important;
  border:1px solid {border2} !important;
  border-radius:11px !important;
  background:{bg2} !important;
  cursor:pointer !important;
  transition:background .15s ease, border-color .15s ease, transform .12s ease, box-shadow .15s ease !important;
  display:flex !important;
  align-items:center !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:hover {{
  border-color:rgba(245,158,11,0.55) !important;
  background:{bg3} !important;
  transform:translateX(2px) !important;
}}
/* hide the tiny radio circle — the whole row is the click target */
section[data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {{
  display:none !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] label p {{
  font-size:1.02rem !important;
  font-weight:600 !important;
  letter-spacing:-0.01em !important;
  line-height:1.3 !important;
  color:{txt2} !important;
  margin:0 !important;
}}
/* make the leading emoji icon read a touch larger than the text */
section[data-testid="stSidebar"] [data-testid="stRadio"] label p::first-letter {{
  font-size:1.2em !important;
}}
/* selected option — amber highlight */
section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {{
  background:linear-gradient(135deg,rgba(245,158,11,0.20),rgba(245,158,11,0.08)) !important;
  border-color:#F59E0B !important;
  box-shadow:0 2px 12px rgba(245,158,11,0.18) !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) p {{
  color:{txt1} !important;
  font-weight:700 !important;
}}

/* ── Mode switch → 2-button segmented control (side by side) ────────────── */
section[data-testid="stSidebar"] .st-key-app_mode [data-testid="stRadio"] [role="radiogroup"] {{
  flex-direction:row !important;
  gap:8px !important;
}}
section[data-testid="stSidebar"] .st-key-app_mode [data-testid="stRadio"] [role="radiogroup"] > label {{
  flex:1 1 0 !important;
  width:auto !important;
  justify-content:center !important;
  text-align:center !important;
  padding:12px 6px !important;
}}
section[data-testid="stSidebar"] .st-key-app_mode [data-testid="stRadio"] [role="radiogroup"] > label:hover {{
  transform:translateY(-1px) !important;
}}
section[data-testid="stSidebar"] .st-key-app_mode [data-testid="stRadio"] label p {{
  font-size:0.84rem !important;
  white-space:nowrap !important;
}}
/* keep the mode-switch icon modest so the label fits on one line */
section[data-testid="stSidebar"] .st-key-app_mode [data-testid="stRadio"] label p::first-letter {{
  font-size:1.05em !important;
}}

/* ── Themed tables (affiliate pages) — light/dark safe, unlike st.dataframe ─ */
.fnb-table-wrap {{
  overflow-x:auto;
  border:1px solid {border2} !important;
  border-radius:12px;
  margin:0.25rem 0 0.75rem;
}}
.fnb-table {{
  width:100%;
  border-collapse:collapse;
  font-size:0.9rem;
  background:{bg2} !important;
}}
.fnb-table thead th {{
  background:{bg3} !important;
  color:{txt3} !important;
  text-align:left;
  font-weight:600;
  padding:10px 14px;
  border-bottom:1px solid {border2} !important;
  white-space:nowrap;
}}
.fnb-table tbody td {{
  color:{txt2} !important;
  padding:9px 14px;
  border-bottom:1px solid {border} !important;
  white-space:nowrap;
}}
.fnb-table tbody tr:last-child td {{ border-bottom:none !important; }}
.fnb-table tbody tr:hover td {{ background:{bg3} !important; }}

/* ── Spinner ───────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] > div {{ border-top-color:#F59E0B !important; }}

/* ── Selectbox / Dropdown ──────────────────────────────────────────────── */
[data-baseweb="select"] > div {{
  background:{input_bg} !important;
  border-color:{border3} !important;
  color:{txt1} !important;
  border-radius:10px !important;
}}
[data-baseweb="select"] span {{ color:{txt1} !important; }}
[data-baseweb="popover"] > div,
[data-baseweb="popover"] ul {{
  background:{bg2} !important;
  border:1px solid {border2} !important;
  border-radius:12px !important;
  box-shadow:0 8px 32px rgba(0,0,0,{"0.4" if is_dark else "0.12"}) !important;
}}
/* dropdown options — newer Streamlit renders them as <li role="option"> whose
   text color comes from the hardcoded dark native theme (config.toml textColor
   = near-white), making them invisible on the light popover. Force the active
   theme's text color, covering nested text nodes too. */
[data-baseweb="option"],
[data-baseweb="popover"] li[role="option"],
[role="listbox"] li[role="option"] {{
  background:{bg2} !important;
  color:{txt2} !important;
}}
[data-baseweb="popover"] li[role="option"] *,
[role="listbox"] li[role="option"] * {{
  color:{txt2} !important;
}}
[data-baseweb="option"]:hover,
[data-baseweb="popover"] li[role="option"]:hover,
[data-baseweb="popover"] li[role="option"][aria-selected="true"],
[role="listbox"] li[role="option"]:hover {{
  background:{bg3} !important;
  color:{txt1} !important;
}}
[data-baseweb="popover"] li[role="option"]:hover *,
[data-baseweb="popover"] li[role="option"][aria-selected="true"] * {{
  color:{txt1} !important;
}}

/* ── Text Area ─────────────────────────────────────────────────────────── */
[data-testid="stTextArea"] textarea {{
  background:{input_bg} !important;
  border-color:{border3} !important;
  color:{txt1} !important;
  border-radius:10px !important;
}}
[data-testid="stTextArea"] textarea:focus {{
  border-color:rgba(245,158,11,0.5) !important;
  box-shadow:0 0 0 3px rgba(245,158,11,0.1) !important;
}}

/* ── File uploader inner ───────────────────────────────────────────────── */
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploaderDropzoneInput"] + div {{
  background:{bg2} !important;
  color:{txt3} !important;
}}
[data-testid="stFileUploaderDropzone"] button {{
  background:{bg3} !important;
  color:{txt2} !important;
  border:1px solid {border2} !important;
  border-radius:8px !important;
}}
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] span {{
  color:{txt4} !important;
}}

/* ── Checkbox ──────────────────────────────────────────────────────────── */
[data-baseweb="checkbox"] > div:first-child {{
  background:{input_bg} !important;
  border-color:{border3} !important;
  border-radius:5px !important;
}}
[data-testid="stCheckbox"] label p {{ color:{txt3} !important; }}

/* ── Main content area text ────────────────────────────────────────────── */
.main [data-testid="stMarkdownContainer"] p {{ color:{txt3} !important; }}
.main label {{ color:{lbl_color} !important; }}
</style>
""", unsafe_allow_html=True)


st.set_page_config(
    page_title="REVENUE AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Theme initialisation — must happen before any st.* call other than set_page_config
#
# Defaults to light so the components match the app frame. Streamlit paints that
# frame — background, sidebar, header — from config.toml, and in this version
# nothing injected at runtime overrides it (tested: higher specificity, layered
# and unlayered !important, even an inline style). A dark default therefore
# produced dark buttons and cards sitting inside a light window.
if "theme" not in st.session_state:
    st.session_state["theme"] = "light"
_theme = st.session_state["theme"]
_chart_tpl = "premium_light" if _theme == "light" else "premium_dark"
pio.templates.default = _chart_tpl
px.defaults.template = _chart_tpl
apply_premium_theme(_theme)


def _chart(fig: go.Figure, stretch: bool = True, **kw) -> None:
    """Render a Plotly chart with correct theme colours, bypassing Streamlit's override."""
    if _theme == "light":
        fig.update_layout(
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F8F7F4",
            font=dict(color="#6B7280"),
            xaxis=dict(gridcolor="rgba(0,0,0,0.06)", tickfont=dict(color="#9CA3AF")),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)", tickfont=dict(color="#9CA3AF")),
            legend=dict(bgcolor="rgba(255,255,255,0.95)", font=dict(color="#6B7280")),
            hoverlabel=dict(bgcolor="#FFFFFF", font=dict(color="#111827")),
            title=dict(font=dict(color="#111827")),
        )
    st.plotly_chart(fig, width="stretch" if stretch else "content", theme=None, **kw)

DATA_PATH = Path("data/sample_transactions.csv")
YENTAFO_DIR = Path("data/client-yentafo")


# ── Data generation ────────────────────────────────────────────────────────────

def generate_sample_data(rows: int = 2500) -> pd.DataFrame:
    np.random.seed(42)
    now = dt.datetime.now()
    start = now - dt.timedelta(days=90)
    branches = ["Siam", "Ari", "Thonglor"]
    staff = ["Nok", "Mek", "Ploy", "Bank", "Jane", "Tum"]
    items = ["Signature Latte", "Craft Beer", "Protein Shake", "Classic Burger", "Set Menu", "Cocktail"]
    segments = ["new", "active", "at_risk"]
    records = []
    for i in range(rows):
        order_time = start + dt.timedelta(minutes=np.random.randint(0, int((now - start).total_seconds() // 60)))
        branch = np.random.choice(branches, p=[0.4, 0.3, 0.3])
        customer_id = f"C{np.random.randint(1, 700):04d}"
        customer_segment = np.random.choice(segments, p=[0.20, 0.50, 0.30])
        item = np.random.choice(items)
        qty = np.random.choice([1, 1, 1, 2, 2, 3])
        base_price = np.random.choice([90, 120, 150, 180, 220, 260])
        discount = np.random.choice([0, 0, 10, 20, 30])
        gross = base_price * qty
        net = max(gross - discount, 50)
        cost = round(net * np.random.uniform(0.38, 0.62), 2)
        margin = round(net - cost, 2)
        staff_name = np.random.choice(staff)
        records.append({
            "order_id": f"O{i+1:05d}", "order_time": order_time,
            "branch": branch, "staff": staff_name,
            "customer_id": customer_id, "customer_segment": customer_segment,
            "item": item, "qty": qty, "gross": gross,
            "discount": discount, "net_sales": net, "cost": cost, "margin": margin,
        })
    df = pd.DataFrame(records)
    df["order_time"] = pd.to_datetime(df["order_time"])
    return df.sort_values("order_time")


def generate_mookrata_data(rows: int = 3000) -> pd.DataFrame:
    np.random.seed(7)
    now = dt.datetime.now()
    start = now - dt.timedelta(days=90)
    branches = ["ลาดพร้าว", "บางนา", "รัชดา"]
    staff = ["เอ", "บี", "ซี", "ดี", "ออม", "นัท", "มุก", "ต้น"]
    ala_items = ["ชุดหมูรวม", "ชุดเนื้อรวม", "ซีฟู้ดรวม", "หมูสไลซ์", "ชีสยืด", "น้ำจิ้มสูตรเด็ด"]
    segments = ["new", "active", "at_risk"]
    records = []
    for i in range(rows):
        day_offset = np.random.randint(0, 90)
        hour = np.random.choice(
            [11, 12, 13, 17, 18, 19, 20, 21, 22],
            p=[0.03, 0.05, 0.05, 0.12, 0.2, 0.22, 0.18, 0.1, 0.05],
        )
        minute = np.random.randint(0, 60)
        order_time = (start + dt.timedelta(days=day_offset)).replace(hour=hour, minute=minute)
        branch = np.random.choice(branches, p=[0.45, 0.3, 0.25])
        customer_segment = np.random.choice(segments, p=[0.22, 0.5, 0.28])
        customer_id = f"M{np.random.randint(1, 900):04d}"
        staff_name = np.random.choice(staff)
        service_type = np.random.choice(["buffet", "alacarte"], p=[0.58, 0.42])
        if service_type == "buffet":
            item = np.random.choice(["บุฟเฟ่ต์ผู้ใหญ่", "บุฟเฟ่ต์เด็ก", "บุฟเฟ่ต์พรีเมียม"], p=[0.68, 0.08, 0.24])
            qty = np.random.choice([1, 2, 2, 3, 4])
            base_price = np.random.choice([199, 239, 299, 359], p=[0.35, 0.35, 0.2, 0.1])
            discount = np.random.choice([0, 0, 20, 30, 40], p=[0.55, 0.2, 0.12, 0.08, 0.05])
        else:
            item = np.random.choice(ala_items)
            qty = np.random.choice([1, 1, 2, 2, 3, 4])
            base_price = np.random.choice([69, 89, 119, 149, 179, 219])
            discount = np.random.choice([0, 0, 10, 20], p=[0.65, 0.2, 0.1, 0.05])
        gross = base_price * qty
        net = max(gross - discount, 50)
        cost_ratio = np.random.uniform(0.43, 0.66) if service_type == "buffet" else np.random.uniform(0.35, 0.58)
        cost = round(net * cost_ratio, 2)
        margin = round(net - cost, 2)
        records.append({
            "order_id": f"MOO{i+1:05d}", "order_time": order_time,
            "branch": branch, "staff": staff_name,
            "customer_id": customer_id, "customer_segment": customer_segment,
            "service_type": service_type, "item": item, "qty": qty, "gross": gross,
            "discount": discount, "net_sales": net, "cost": cost, "margin": margin,
        })
    df = pd.DataFrame(records)
    df["order_time"] = pd.to_datetime(df["order_time"])
    return df.sort_values("order_time")


def load_data() -> pd.DataFrame:
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH)
        df["order_time"] = pd.to_datetime(df["order_time"])
        return df
    df = generate_sample_data()
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_PATH, index=False)
    return df


def load_yentafo_aggregates(base_dir: Path) -> dict[str, pd.DataFrame]:
    data: dict[str, pd.DataFrame] = {
        "hourly": pd.DataFrame(), "weekday": pd.DataFrame(),
        "order_type": pd.DataFrame(), "channel": pd.DataFrame(),
        "hour_by_weekday": pd.DataFrame(),
    }
    if not base_dir.exists():
        return data
    files = sorted(base_dir.glob("*.xlsx")) + sorted(base_dir.glob("*.xls"))
    for file in files:
        if file.name.startswith("~$"):
            continue
        try:
            xls = pd.ExcelFile(file)
        except (PermissionError, Exception):
            continue
        for sheet in xls.sheet_names:
            df = xls.parse(sheet)
            if df.empty:
                continue
            df.columns = [str(c).strip() for c in df.columns]
            lower_cols = {c.lower() for c in df.columns}
            sheet_lower = sheet.lower()
            if {"ordertype", "sales", "orders"}.issubset(lower_cols):
                data["order_type"] = df.copy()
            elif {"dayofweek", "sales", "orders"}.issubset(lower_cols):
                data["weekday"] = df.copy()
            elif {"time", "sales", "orders"}.issubset(lower_cols):
                channel_df = df.copy()
                channel_df["channel"] = sheet
                data["channel"] = pd.concat([data["channel"], channel_df], ignore_index=True)
            elif {"hour", "daycount", "sales", "orders"}.issubset(lower_cols):
                if sheet_lower in {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}:
                    weekday_hour = df.copy()
                    weekday_hour["weekday"] = sheet
                    data["hour_by_weekday"] = pd.concat([data["hour_by_weekday"], weekday_hour], ignore_index=True)
                else:
                    data["hourly"] = df.copy()
    return data


# ── AI Insights ────────────────────────────────────────────────────────────────

def get_ai_insights_local(df: pd.DataFrame) -> list[str]:
    insights = []

    # Revenue trend: recent 30 days vs prior 30 days
    now = df["order_time"].max()
    recent_rev = df[df["order_time"] >= now - dt.timedelta(days=30)]["net_sales"].sum()
    prev_rev = df[
        (df["order_time"] >= now - dt.timedelta(days=60)) &
        (df["order_time"] < now - dt.timedelta(days=30))
    ]["net_sales"].sum()
    if prev_rev > 0:
        trend = (recent_rev - prev_rev) / prev_rev
        if trend > 0.02:
            insights.append(f"📈 ยอดขาย 30 วันล่าสุดโต {trend:.1%} จากเดือนก่อน — momentum ดี ลองดัน upsell ตอนนี้")
        elif trend < -0.02:
            insights.append(f"📉 ยอดขาย 30 วันล่าสุดลด {abs(trend):.1%} — ควรเปิด retention campaign ทันที")

    # Weak vs peak hours
    by_hour = df.groupby(df["order_time"].dt.hour)["net_sales"].sum()
    weak_hours = sorted(by_hour.nsmallest(3).index.tolist())
    peak_hours = sorted(by_hour.nlargest(2).index.tolist())
    insights.append(f"⏰ ช่วงยอดต่ำ: {', '.join(f'{h:02d}:00' for h in weak_hours)} → เปิด Flash Sale หรือ Happy Hour")
    insights.append(f"🔥 ช่วงพีค: {', '.join(f'{h:02d}:00' for h in peak_hours)} → เพิ่มพนักงาน + ดัน Upsell")

    # At-risk customers
    if "customer_segment" in df.columns:
        seg = df.groupby("customer_segment")["customer_id"].nunique()
        at_risk = seg.get("at_risk", 0)
        total = seg.sum()
        if total > 0:
            pct = at_risk / total
            if pct > 0.2:
                insights.append(f"⚠️ ลูกค้าเสี่ยงหาย {pct:.1%} ({at_risk:,} คน) → เปิด Win-back Campaign ทันที")
            else:
                insights.append(f"✅ ลูกค้าเสี่ยงหาย {pct:.1%} — ระดับปกติ ควรมี automated follow-up ทุก 14 วัน")

    # Top margin item
    if "item" in df.columns:
        top_item = df.groupby("item")["margin"].sum().idxmax()
        top_margin = df.groupby("item")["margin"].sum().max()
        insights.append(f"⭐ '{top_item}' สร้าง margin สูงสุด ฿{top_margin:,.0f} → ดันเป็น Hero Product")

    # Branch gap
    if "branch" in df.columns and df["branch"].nunique() > 1:
        by_branch = df.groupby("branch")["margin"].sum()
        best_b = by_branch.idxmax()
        worst_b = by_branch.idxmin()
        gap = (by_branch[best_b] - by_branch[worst_b]) / by_branch[best_b]
        insights.append(f"🏪 สาขา '{best_b}' margin ดีกว่า '{worst_b}' ถึง {gap:.1%} → ศึกษา best practice แล้ว replicate")

    return insights


def get_ai_insights_claude(df: pd.DataFrame, api_key: str) -> list[str]:
    if not ANTHROPIC_AVAILABLE:
        return ["❌ ต้องติดตั้ง anthropic ก่อน: pip install anthropic"]
    try:
        client = anthropic.Anthropic(api_key=api_key)

        now = df["order_time"].max()
        recent_rev = df[df["order_time"] >= now - dt.timedelta(days=30)]["net_sales"].sum()
        prev_rev = df[
            (df["order_time"] >= now - dt.timedelta(days=60)) &
            (df["order_time"] < now - dt.timedelta(days=30))
        ]["net_sales"].sum()
        trend_pct = (recent_rev - prev_rev) / prev_rev * 100 if prev_rev > 0 else 0

        context = {
            "summary": {
                "total_revenue": round(float(df["net_sales"].sum()), 0),
                "total_margin": round(float(df["margin"].sum()), 0),
                "aov": round(float(df["net_sales"].mean()), 0),
                "transactions": int(len(df)),
                "revenue_trend_30d_pct": round(trend_pct, 1),
            },
            "customer_segments": (
                df.groupby("customer_segment")["customer_id"].nunique().to_dict()
                if "customer_segment" in df.columns else {}
            ),
            "hourly_revenue": {
                f"{h:02d}:00": round(float(v), 0)
                for h, v in df.groupby(df["order_time"].dt.hour)["net_sales"].sum().items()
            },
            "top_items_by_margin": (
                {k: round(float(v), 0) for k, v in df.groupby("item")["margin"].sum().nlargest(5).items()}
                if "item" in df.columns else {}
            ),
            "branch_revenue": (
                {k: round(float(v), 0) for k, v in df.groupby("branch")["net_sales"].sum().items()}
                if "branch" in df.columns else {}
            ),
        }

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=[{
                "type": "text",
                "text": (
                    "คุณเป็น AI Business Analyst ที่มีประสบการณ์ทำงานเป็น CFO และ CMO "
                    "ในธุรกิจร้านอาหาร คาเฟ่ และ F&B ไทยมาก่อน "
                    "วิเคราะห์ข้อมูลแล้วให้ insights ที่ actionable จริงๆ "
                    "แต่ละ insight ต้องระบุ: 1) fact จากตัวเลข 2) action ที่ทำได้ภายใน 24-48 ชม. "
                    "3) expected impact ที่วัดได้ "
                    "ห้ามพูด generic เช่น 'ควรปรับปรุง' หรือ 'ควรวิเคราะห์เพิ่มเติม' "
                    "ตอบเป็นภาษาไทย สั้นกระชับ ไม่เกิน 2 ประโยคต่อ insight"
                ),
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": (
                    f"ข้อมูลธุรกิจ:\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
                    "ให้ 5 insights ที่ actionable ที่สุด ห้ามซ้ำกัน\n"
                    "ตอบในรูปแบบ JSON array เท่านั้น: [\"insight 1\", \"insight 2\", ...]"
                ),
            }],
        )
        text = message.content[0].text.strip()
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return [text]
    except Exception as e:
        return [f"❌ Claude API Error: {e}", "💡 ลองเช็ค API key หรือเปลี่ยนกลับ Local mode"]


def get_ai_insights(df: pd.DataFrame, mode: str, api_key: str = "") -> list[str]:
    if mode == "Claude API" and api_key.strip():
        return get_ai_insights_claude(df, api_key.strip())
    return get_ai_insights_local(df)


def get_sales_forecast(df: pd.DataFrame, days: int = 7) -> pd.DataFrame:
    # Group by date
    daily = df.assign(date=df["order_time"].dt.date).groupby("date")["net_sales"].sum().reset_index()
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date")

    if len(daily) < 7:
        return pd.DataFrame()

    # Simple Moving Average for trend
    daily["sma_7"] = daily["net_sales"].rolling(window=7).mean()

    # Simple linear trend on the last 14 days
    recent = daily.tail(14)
    x = np.arange(len(recent))
    y = recent["net_sales"].values
    if len(x) > 1:
        slope, intercept = np.polyfit(x, y, 1)
    else:
        slope, intercept = 0, y[0]

    # Project future
    last_date = daily["date"].max()
    future_dates = [last_date + dt.timedelta(days=i) for i in range(1, days + 1)]

    # Forecast calculation (Trend + SMA weight)
    last_sma = daily["sma_7"].iloc[-1]
    forecast_values = []
    for i in range(1, days + 1):
        # Forecast = Last SMA + (slope * i)
        val = max(last_sma + (slope * (i / 2)), 0) # dampened slope
        forecast_values.append(val)

    forecast_df = pd.DataFrame({
        "date": future_dates,
        "net_sales": forecast_values,
        "type": "Forecast"
    })

    # Prepare historical for plotting
    historical_df = daily[["date", "net_sales"]].copy()
    historical_df["type"] = "Actual"

    return pd.concat([historical_df, forecast_df], ignore_index=True)


def content_suggestions(df: pd.DataFrame) -> list[str]:
    by_hour = df.groupby(df["order_time"].dt.hour)["net_sales"].sum()
    weak_hour = int(by_hour.idxmin()) if not by_hour.empty else 15
    top_item = df.groupby("item")["margin"].sum().idxmax() if "item" in df.columns else "เมนูยอดนิยม"
    return [
        f"โปรด่วน {weak_hour:02d}:00-{weak_hour+2:02d}:00 วันนี้: ซื้อ 2 แถม 1 เฉพาะ '{top_item}'",
        "LINE OA: คิดถึงนะ! กลับมาใช้สิทธิ์ลูกค้าประจำวันนี้ รับส่วนลด 15%",
        "IG Story: ช่วงบ่ายจัดโปร time-based เพิ่ม traffic หน้าร้านทันที",
        "Facebook: แชร์ review ลูกค้าจริงพร้อม limited offer เฉพาะวันนี้",
    ]


@st.cache_data
def generate_excel_report(df: pd.DataFrame) -> bytes:
    insights = get_ai_insights_local(df)
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: KPI Summary
        now = df["order_time"].max()
        recent_rev = df[df["order_time"] >= now - dt.timedelta(days=30)]["net_sales"].sum()
        prev_rev = df[
            (df["order_time"] >= now - dt.timedelta(days=60)) &
            (df["order_time"] < now - dt.timedelta(days=30))
        ]["net_sales"].sum()
        trend = (recent_rev - prev_rev) / prev_rev * 100 if prev_rev > 0 else 0
        repeat = (df["customer_segment"] != "new").mean() if "customer_segment" in df.columns else 0

        pd.DataFrame({
            "Metric": ["Revenue (Total)", "Margin (Total)", "AOV", "Transactions",
                       "Revenue Trend (30d vs prior 30d)", "Repeat Rate"],
            "Value": [
                f"฿{df['net_sales'].sum():,.0f}",
                f"฿{df['margin'].sum():,.0f}",
                f"฿{df['net_sales'].mean():,.0f}",
                f"{len(df):,}",
                f"{trend:+.1f}%",
                f"{repeat:.1%}",
            ],
        }).to_excel(writer, sheet_name="KPI Summary", index=False)

        # Sheet 2: Daily Sales
        (
            df.assign(Date=df["order_time"].dt.date)
            .groupby("Date", as_index=False)
            .agg(Revenue=("net_sales", "sum"), Margin=("margin", "sum"), Transactions=("order_id", "count"))
        ).to_excel(writer, sheet_name="Daily Sales", index=False)

        # Sheet 3: Top Items by Margin
        if "item" in df.columns:
            (
                df.groupby("item", as_index=False)
                .agg(Revenue=("net_sales", "sum"), Margin=("margin", "sum"), Orders=("order_id", "count"))
                .sort_values("Margin", ascending=False)
            ).to_excel(writer, sheet_name="Top Items", index=False)

        # Sheet 4: Branch Performance
        if "branch" in df.columns and df["branch"].nunique() > 1:
            (
                df.groupby("branch", as_index=False)
                .agg(Revenue=("net_sales", "sum"), Margin=("margin", "sum"), Transactions=("order_id", "count"))
                .sort_values("Revenue", ascending=False)
            ).to_excel(writer, sheet_name="Branch Performance", index=False)

        # Sheet 5: Customer Segments
        if "customer_segment" in df.columns:
            (
                df.groupby("customer_segment", as_index=False)
                .agg(Customers=("customer_id", "nunique"), Revenue=("net_sales", "sum"))
            ).to_excel(writer, sheet_name="Customer Segments", index=False)

        # Sheet 6: Hourly Revenue
        (
            df.assign(Hour=df["order_time"].dt.hour)
            .groupby("Hour", as_index=False)
            .agg(Revenue=("net_sales", "sum"), Transactions=("order_id", "count"))
        ).to_excel(writer, sheet_name="Hourly Revenue", index=False)

        # Sheet 7: AI Insights
        pd.DataFrame({
            "#": range(1, len(insights) + 1),
            "Insight & Recommendation": insights,
        }).to_excel(writer, sheet_name="AI Insights", index=False)

    return output.getvalue()


# ── Connect POS Page ───────────────────────────────────────────────────────────

def render_connect_pos_page(lv_token: str, lv_days: int, ai_mode: str, api_key: str) -> None:
    st.title("🔌 Connect POS — Loyverse")
    st.caption("ดึงข้อมูลยอดขายจริงจาก Loyverse POS เข้าสู่ REVENUE AI")

    with st.expander("วิธีรับ API Token จาก Loyverse", expanded=False):
        st.markdown("""
1. เข้า [Loyverse Back Office](https://r.loyverse.com/dashboard/) (Back Office → Settings)
2. ไปที่ **API access tokens** → **Create new token**
3. ตั้งชื่อ token (เช่น `ai-revenue-intelligence`) แล้ว copy
4. วาง token ในช่องด้านซ้าย แล้วกด **เชื่อมต่อ & ดึงข้อมูล**

Token จะถูกใช้เฉพาะในเซสชั่นนี้เท่านั้น ไม่ถูกบันทึกลงเซิร์ฟเวอร์ใด
        """)

    if not LOYVERSE_AVAILABLE:
        st.error("ไม่พบ loyverse_connector.py — ตรวจสอบว่าไฟล์อยู่ในโฟลเดอร์เดียวกับ app.py")
        return

    if not lv_token:
        st.info("ใส่ Loyverse API Token ในแถบซ้ายเพื่อเริ่มต้น")
        _render_loyverse_demo_preview()
        return

    col_btn, col_status = st.columns([1, 3])
    with col_btn:
        connect_btn = st.button("🔄 เชื่อมต่อ & ดึงข้อมูล")

    if not connect_btn and "loyverse_df" not in st.session_state:
        st.info("กด 'เชื่อมต่อ & ดึงข้อมูล' เพื่อดึงข้อมูลจาก Loyverse")
        return

    if connect_btn:
        with st.spinner("กำลังเชื่อมต่อ Loyverse API..."):
            try:
                connector = LoyverseConnector(lv_token)
                if not connector.test_connection():
                    st.error("Token ไม่ถูกต้องหรือหมดอายุ — ตรวจสอบใน Loyverse Back Office")
                    return

                merchant = connector.get_merchant_info()
                merchant_name = merchant.get("name", "ร้านของคุณ") if merchant else "ร้านของคุณ"

                date_from = dt.datetime.now() - dt.timedelta(days=lv_days)
                with st.spinner(f"ดึงข้อมูล {lv_days} วัน จาก {merchant_name}..."):
                    raw_df = connector.to_standard_df(date_from=date_from)

                if raw_df.empty:
                    st.warning("ไม่พบข้อมูลในช่วงเวลาที่เลือก ลองขยายช่วงวันให้กว้างขึ้น")
                    return

                # Apply RFM segmentation
                rfm_df = compute_rfm(raw_df)
                raw_df = label_transactions(raw_df, rfm_df)

                st.session_state["loyverse_df"] = raw_df
                st.session_state["loyverse_rfm"] = rfm_df
                st.session_state["loyverse_merchant"] = merchant_name
                st.success(f"เชื่อมต่อสำเร็จ: **{merchant_name}** | {len(raw_df):,} รายการ | {raw_df['order_time'].min().date()} ถึง {raw_df['order_time'].max().date()}")
            except Exception as e:
                st.error(f"เชื่อมต่อไม่ได้: {e}")
                return

    if "loyverse_df" not in st.session_state:
        return

    df = st.session_state["loyverse_df"]
    rfm = st.session_state.get("loyverse_rfm", pd.DataFrame())
    merchant_name = st.session_state.get("loyverse_merchant", "ร้านของคุณ")

    st.subheader(f"ข้อมูลจริง: {merchant_name}")

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Revenue", f"฿{df['net_sales'].sum():,.0f}")
    k2.metric("Margin", f"฿{df['margin'].sum():,.0f}")
    k3.metric("Transactions", f"{len(df):,}")
    k4.metric("Unique Customers", f"{df['customer_id'].nunique():,}")

    tab_sales, tab_rfm, tab_ai = st.tabs(["ยอดขาย", "RFM Segments", "AI Insights"])

    with tab_sales:
        daily = df.assign(date=df["order_time"].dt.date).groupby("date", as_index=False)["net_sales"].sum()
        fig = px.line(daily, x="date", y="net_sales", title=f"ยอดขายรายวัน — {merchant_name}", markers=True)
        _chart(fig)

        if "branch" in df.columns and df["branch"].nunique() > 1:
            by_branch = df.groupby("branch", as_index=False).agg(Revenue=("net_sales", "sum"), Margin=("margin", "sum"), Transactions=("order_id", "count"))
            _chart(px.bar(by_branch, x="branch", y="Revenue", title="Revenue by Branch"))

    with tab_rfm:
        _render_rfm_tab(df, rfm)

    with tab_ai:
        st.subheader(f"AI Insights ({ai_mode})")
        with st.spinner("กำลังวิเคราะห์..."):
            for insight in get_ai_insights(df, ai_mode, api_key):
                st.success(insight)

    st.divider()
    dl_col, _ = st.columns([1, 2])
    with dl_col:
        st.download_button(
            label="📥 Download Report (.xlsx)",
            data=generate_excel_report(df),
            file_name=f"loyverse_{merchant_name}_{dt.datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )


def _render_rfm_tab(df: pd.DataFrame, rfm: pd.DataFrame) -> None:
    """Shared RFM visualisation used in both Connect POS and Customer Intelligence tabs."""
    if rfm.empty:
        rfm = compute_rfm(df)
    if rfm.empty:
        st.warning("ไม่สามารถคำนวณ RFM ได้ — ต้องการข้อมูลอย่างน้อย 10 ลูกค้า")
        return

    summary = rfm_summary(rfm)

    # Treemap
    fig_tree = px.treemap(
        summary,
        path=["segment"],
        values="customers",
        color="total_revenue",
        color_continuous_scale=["#1F2937", "#F59E0B"],
        title="Customer Segments — Treemap (ขนาด = จำนวนลูกค้า, สี = Revenue)",
        custom_data=["avg_recency", "avg_frequency", "avg_monetary", "total_revenue", "action"],
    )
    fig_tree.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "ลูกค้า: %{value:,} คน<br>"
            "Revenue รวม: ฿%{customdata[3]:,.0f}<br>"
            "Avg Recency: %{customdata[0]} วัน<br>"
            "Avg Frequency: %{customdata[1]:.1f} ครั้ง<br>"
            "Avg Spend: ฿%{customdata[2]:,.0f}<br>"
            "<b>Action: %{customdata[4]}</b><extra></extra>"
        )
    )
    _chart(fig_tree)

    # Scatter: Frequency vs Monetary coloured by segment
    fig_scatter = px.scatter(
        rfm,
        x="frequency",
        y="monetary",
        color="segment",
        color_discrete_map={s: m["color"] for s, m in SEGMENT_META.items()},
        size="rfm_total",
        title="Customer Scatter — Frequency vs Lifetime Value",
        labels={"frequency": "จำนวนครั้งที่ซื้อ", "monetary": "Lifetime Value (฿)"},
        hover_data=["customer_id", "recency_days", "rfm_score"],
    )
    fig_scatter.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    _chart(fig_scatter)

    # Action table
    st.subheader("Action Plan ตาม Segment")
    for _, row in summary.iterrows():
        seg = row["segment"]
        meta = SEGMENT_META.get(seg, {})
        color = meta.get("color", "#6B7280")
        st.markdown(
            f'<div style="border-left:3px solid {color};padding:0.6rem 1rem;margin-bottom:0.5rem;'
            f'background:rgba(255,255,255,0.02);border-radius:0 8px 8px 0;">'
            f'<strong style="color:{color};">{seg}</strong> '
            f'<span style="color:#6B7280;font-size:0.8rem;">({row["customers"]:,} คน | ฿{row["total_revenue"]:,.0f})</span><br>'
            f'<span style="color:#9CA3AF;font-size:0.875rem;">{meta.get("action","")}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_loyverse_demo_preview() -> None:
    st.divider()
    st.markdown("**ตัวอย่างข้อมูลที่จะได้เมื่อเชื่อมต่อ Loyverse:**")
    c1, c2, c3 = st.columns(3)
    c1.info("**ยอดขายรายวัน** แยกสาขา แยก shift")
    c2.info("**RFM Segmentation** Champions / At Risk / Lost ฯลฯ")
    c3.info("**AI Win-back Trigger** อัตโนมัติเมื่อลูกค้าหาย 14 วัน")


# ── CSV Upload Page ─────────────────────────────────────────────────────────────

def render_csv_upload_page(ai_mode: str, api_key: str) -> None:
    st.title("📁 อัปโหลดข้อมูลของคุณ")
    st.caption("ทดลองวิเคราะห์กับข้อมูล POS จริงของธุรกิจคุณ")

    with st.expander("ดูรูปแบบ CSV ที่รองรับ", expanded=False):
        st.markdown("""
**คอลัมน์บังคับ:**
| คอลัมน์ | ตัวอย่าง |
|---|---|
| `order_id` | O00001 |
| `order_time` | 2026-01-15 18:30:00 |
| `net_sales` | 350 |
| `customer_id` | C0042 |

**คอลัมน์เสริม (ถ้ามีจะวิเคราะห์ได้ลึกขึ้น):**
`branch`, `staff`, `item`, `margin`, `customer_segment` (new/active/at_risk)
        """)
        sample = pd.DataFrame({
            "order_id": ["O00001", "O00002"],
            "order_time": ["2026-01-15 18:30:00", "2026-01-15 19:15:00"],
            "net_sales": [350, 220],
            "customer_id": ["C0042", "C0010"],
            "branch": ["สาขาหลัก", "สาขาหลัก"],
            "item": ["Set Menu", "Latte"],
            "margin": [140, 88],
            "customer_segment": ["active", "new"],
        })
        st.dataframe(sample)

    uploaded = st.file_uploader("เลือกไฟล์ CSV", type=["csv"])

    if "uploaded_df" in st.session_state and uploaded is None:
        st.info("ใช้ข้อมูลที่อัปโหลดครั้งก่อน — อัปโหลดไฟล์ใหม่เพื่อเปลี่ยน")
        _render_upload_analysis(st.session_state["uploaded_df"], ai_mode, api_key)
        return

    if uploaded is not None:
        try:
            df_up = pd.read_csv(uploaded)
            required = {"order_id", "order_time", "net_sales", "customer_id"}
            missing = required - set(df_up.columns)
            if missing:
                st.error(f"ไม่พบคอลัมน์: {', '.join(missing)}")
                return
            df_up["order_time"] = pd.to_datetime(df_up["order_time"], errors="coerce")
            df_up = df_up.dropna(subset=["order_time"])
            if df_up.empty:
                st.error("ไม่พบข้อมูลที่อ่านได้ในไฟล์นี้")
                return
            if "branch" not in df_up.columns:
                df_up["branch"] = "สาขาหลัก"
            if "margin" not in df_up.columns:
                df_up["margin"] = (df_up["net_sales"] * 0.35).round(2)
            if "customer_segment" not in df_up.columns:
                df_up["customer_segment"] = "active"
            if "item" not in df_up.columns:
                df_up["item"] = "สินค้า"
            st.session_state["uploaded_df"] = df_up
            st.success(f"โหลดข้อมูลสำเร็จ: {len(df_up):,} รายการ | {df_up['order_time'].min().date()} ถึง {df_up['order_time'].max().date()}")
            _render_upload_analysis(df_up, ai_mode, api_key)
        except Exception as e:
            st.error(f"อ่านไฟล์ไม่ได้: {e}")


def _render_upload_analysis(df: pd.DataFrame, ai_mode: str, api_key: str) -> None:
    st.divider()
    sales = df["net_sales"].sum()
    margin = df["margin"].sum()
    aov = df["net_sales"].mean()
    repeat = (df["customer_segment"] != "new").mean() if "customer_segment" in df.columns else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Revenue", f"฿{sales:,.0f}")
    k2.metric("Margin", f"฿{margin:,.0f}")
    k3.metric("AOV", f"฿{aov:,.0f}")
    k4.metric("Repeat Rate", f"{repeat:.1%}")

    tab1, tab2 = st.tabs(["ยอดขายรายวัน", "AI Insights"])
    with tab1:
        daily = df.assign(date=df["order_time"].dt.date).groupby("date", as_index=False)["net_sales"].sum()
        fig = px.line(daily, x="date", y="net_sales", title="ยอดขายรายวัน (ข้อมูลของคุณ)", markers=True)
        _chart(fig)
    with tab2:
        st.subheader("AI Insights สำหรับธุรกิจของคุณ")
        with st.spinner("กำลังวิเคราะห์..."):
            for insight in get_ai_insights(df, ai_mode, api_key):
                st.success(insight)


# ── ROI Calculator ──────────────────────────────────────────────────────────────

def render_roi_calculator() -> None:
    st.title("🧮 ROI Calculator")
    st.caption("คำนวณผลตอบแทนที่คาดได้จากการใช้ระบบ AI for Business")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("ข้อมูลธุรกิจปัจจุบัน")
        monthly_revenue = st.number_input(
            "ยอดขายต่อเดือน (บาท)", min_value=10_000, max_value=10_000_000,
            value=500_000, step=10_000, format="%d",
        )
        current_repeat = st.slider("Repeat Rate ปัจจุบัน (%)", 0, 100, 30)
        avg_margin_pct = st.slider("Margin เฉลี่ย (%)", 10, 80, 35)
        num_branches = st.number_input("จำนวนสาขา", min_value=1, max_value=50, value=1, step=1)
        hours_report = st.slider("ชั่วโมงทำรายงาน/เดือน", 0, 200, 40)
        hourly_rate = st.number_input("ค่าแรงเฉลี่ย (บาท/ชม.)", min_value=50, max_value=1000, value=150, step=50)

    with col2:
        st.subheader("ผลลัพธ์ที่คาดได้")

        repeat_gain_pct = 10
        waste_reduction = 0.15
        report_saving = 0.8

        new_repeat = current_repeat + repeat_gain_pct
        repeat_revenue = monthly_revenue * repeat_gain_pct / 100
        waste_saving = monthly_revenue * avg_margin_pct / 100 * waste_reduction
        labor_saving = hours_report * hourly_rate * report_saving

        monthly_gain = repeat_revenue + waste_saving + labor_saving
        annual_gain = monthly_gain * 12

        if num_branches <= 1:
            setup_cost, monthly_cost, pkg_name = 45_000, 12_000, "Base Analytics"
        elif num_branches <= 3:
            setup_cost, monthly_cost, pkg_name = 95_000, 28_000 * num_branches, "Growth Automation"
        else:
            setup_cost, monthly_cost, pkg_name = 180_000, 55_000 * num_branches, "Scale & Control Tower"

        annual_cost = setup_cost + monthly_cost * 12
        net_roi = annual_gain - annual_cost
        roi_pct = net_roi / annual_cost * 100 if annual_cost > 0 else 0
        payback = annual_cost / monthly_gain if monthly_gain > 0 else 999

        m1, m2 = st.columns(2)
        m1.metric("รายได้เพิ่มจาก Repeat Rate", f"฿{repeat_revenue:,.0f}/เดือน", f"+{repeat_gain_pct}%")
        m2.metric("ประหยัด Waste/Cost", f"฿{waste_saving:,.0f}/เดือน", f"-{waste_reduction:.0%}")
        m3, m4 = st.columns(2)
        m3.metric("ประหยัดเวลารายงาน", f"฿{labor_saving:,.0f}/เดือน", f"-{report_saving:.0%} ชั่วโมง")
        m4.metric("Payback Period", f"{payback:.1f} เดือน")

        st.divider()
        if net_roi > 0:
            st.success(f"**ROI ปีแรก (สุทธิ): ฿{net_roi:,.0f} ({roi_pct:.0f}%)**")
            st.info(f"ลงทุน ฿{annual_cost:,.0f}/ปี → ได้คืน ฿{annual_gain:,.0f}/ปี")
        else:
            st.warning(f"ROI ติดลบปีแรก: ฿{net_roi:,.0f} — ลองปรับค่า input หรือเลือกแพ็กเกจเล็กกว่า")

        st.markdown(f"**แพ็กเกจแนะนำ:** {pkg_name}")
        st.caption(f"Setup ฿{setup_cost:,.0f} + ฿{monthly_cost:,.0f}/เดือน")

    st.divider()
    st.markdown("**สมมติฐานที่ใช้คำนวณ** (อิงจาก case studies ลูกค้าจริง)")
    c1, c2, c3 = st.columns(3)
    c1.info(f"Repeat Rate เพิ่ม +{repeat_gain_pct}%")
    c2.info(f"Waste/Overstock ลด {waste_reduction:.0%}")
    c3.info(f"เวลาทำรายงานลด {report_saving:.0%}")


# ── Yentafo Dashboard (unchanged) ──────────────────────────────────────────────

def render_yentafo_dashboard(y_data: dict[str, pd.DataFrame]) -> None:
    hourly = y_data["hourly"]
    weekday = y_data["weekday"]
    order_type = y_data["order_type"]
    channel = y_data["channel"]
    hour_by_weekday = y_data["hour_by_weekday"]

    if hourly.empty and weekday.empty and order_type.empty:
        st.error("ยังไม่พบข้อมูลรายงานที่อ่านได้ในโฟลเดอร์ลูกค้า")
        st.stop()

    sales_total = float(hourly["sales"].sum()) if not hourly.empty else float(weekday["sales"].sum())
    orders_total = float(hourly["orders"].sum()) if not hourly.empty else float(weekday["orders"].sum())
    aov = sales_total / orders_total if orders_total else 0
    peak_hour = int(hourly.loc[hourly["sales"].idxmax(), "hour"]) if not hourly.empty else 0
    peak_day = str(weekday.loc[weekday["sales"].idxmax(), "dayOfWeek"]) if not weekday.empty else "-"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Sales", f"฿{sales_total:,.0f}")
    m2.metric("Total Orders", f"{orders_total:,.0f}")
    m3.metric("AOV", f"฿{aov:,.0f}")
    m4.metric("Peak Time", f"{peak_hour:02d}:00 / {peak_day}")

    t1, t2, t3, t4 = st.tabs(["Executive Dashboard", "Customer Intelligence", "Real-time Marketing", "Operations"])

    with t1:
        st.subheader("มุมมองยอดขายตามช่วงเวลา")
        time_granularity = st.radio("เลือกระดับเวลา", ["รายชั่วโมง", "รายวัน", "รายเดือน"], horizontal=True)
        daily_ts = pd.DataFrame()
        monthly_ts = pd.DataFrame()
        if not channel.empty and {"time", "sales"}.issubset(set(channel.columns)):
            ts = channel.copy()
            ts["time"] = pd.to_datetime(ts["time"], errors="coerce")
            ts = ts.dropna(subset=["time"])
            if "channel" in ts.columns and (ts["channel"] == "TOTAL").any():
                ts = ts[ts["channel"] == "TOTAL"].copy()
            ts = ts.groupby("time", as_index=False)["sales"].sum()
            daily_ts = ts.sort_values("time")
            if not daily_ts.empty:
                monthly_ts = (
                    daily_ts.assign(month=daily_ts["time"].dt.to_period("M").astype(str))
                    .groupby("month", as_index=False)["sales"].sum()
                )
        if time_granularity == "รายชั่วโมง":
            if not hourly.empty:
                _chart(px.bar(hourly, x="hour", y="sales", title="ยอดขายตามชั่วโมง"))
            else:
                st.warning("ไม่พบข้อมูลรายชั่วโมง")
        elif time_granularity == "รายวัน":
            if not daily_ts.empty:
                _chart(px.line(daily_ts, x="time", y="sales", markers=True, title="ยอดขายรายวัน"))
            else:
                st.warning("ไม่พบข้อมูลรายวัน")
        else:
            if not monthly_ts.empty:
                _chart(px.bar(monthly_ts, x="month", y="sales", title="ยอดขายรายเดือน"))
            else:
                st.warning("ไม่พบข้อมูลรายเดือน")
        if not hourly.empty:
            top_h = hourly.sort_values("sales", ascending=False).head(1)["hour"].tolist()
            if top_h:
                st.caption(f"Insight: ชั่วโมงขายดีที่สุดคือ {int(top_h[0]):02d}:00")
        if not weekday.empty:
            _chart(px.bar(weekday, x="dayOfWeek", y="sales", title="ยอดขายตามวันในสัปดาห์"))

    with t2:
        if not order_type.empty:
            _chart(px.pie(order_type, values="sales", names="orderType", title="สัดส่วนยอดขายตามประเภทออเดอร์"))
        if not channel.empty:
            ch_sum = channel.groupby("channel", as_index=False)[["sales", "orders"]].sum()
            _chart(px.bar(ch_sum, x="channel", y="sales", title="ยอดขายตามช่องทาง"))
        st.info("หมายเหตุ: ไฟล์ชุดนี้ยังไม่มี customer-level ID จึงวิเคราะห์รายบุคคลได้บางส่วน")

    with t3:
        if not hourly.empty:
            weak_h = hourly.sort_values("sales").head(3)["hour"].tolist()
            strong_h = hourly.sort_values("sales", ascending=False).head(2)["hour"].tolist()
            st.success(f"ช่วงยอดต่ำที่ควรกระตุ้น: {', '.join(f'{int(h):02d}:00' for h in weak_h)}")
            st.success(f"ช่วงพีคที่ควรทำ upsell: {', '.join(f'{int(h):02d}:00' for h in strong_h)}")
        if not order_type.empty and "avgBasketSize" in order_type.columns:
            best_type = order_type.sort_values("avgBasketSize", ascending=False).iloc[0]["orderType"]
            st.info(f"ประเภทออเดอร์ที่มูลค่าต่อบิลสูงสุด: {best_type}")
        st.markdown("**Recommended Actions:**")
        st.write("- ยิงโปรช่วงบ่ายก่อนพีค (15:00-17:00) เพื่อดึงทราฟฟิกก่อนดินเนอร์")
        st.write("- ทำคอนเทนต์ 'ชุดคุ้ม + ท็อปปิ้งเพิ่ม' ในช่วงพีคเพื่อดัน AOV")
        st.write("- รีมาร์เก็ตลูกค้าที่เคยสั่งช่วงพีค ให้กลับมาในวันยอดอ่อน")

    with t4:
        if not hour_by_weekday.empty:
            heat = hour_by_weekday.pivot_table(index="weekday", columns="hour", values="sales", aggfunc="sum").fillna(0)
            _chart(px.imshow(heat, aspect="auto", title="Heatmap ยอดขาย (วัน x ชั่วโมง)"))
        st.caption("ไฟล์ชุดนี้เน้นยอดขายเชิงรวม ยังไม่มีข้อมูลพนักงานรายคน")

    st.divider()
    st.markdown("**Next step:** เพิ่มไฟล์ลูกค้ารายบุคคล/พนักงาน เพื่อเปิด AI retention + staff intelligence แบบเต็ม")


# ── Content Studio ──────────────────────────────────────────────────────────────

def render_content_studio_page(ai_mode: str, api_key: str, line_token: str = "", fb_token: str = "", fb_page_id: str = "", ig_business_id: str = "") -> None:
    st.title("📣 Content Studio")
    st.caption("AI สร้างคอนเทนต์จากข้อมูลธุรกิจ → Google Drive → โพสต์ทุกแพลตฟอร์ม")

    if not CONTENT_STUDIO_AVAILABLE:
        st.error("ไม่พบ content_studio.py — กรุณาตรวจสอบไฟล์ในโฟลเดอร์โปรเจกต์")
        return

    # ── Flowchart ──────────────────────────────────────────────────────────────
    is_dark = _theme == "dark"
    fc_bg   = "#111827" if is_dark else "#FFFFFF"
    fc_bdr  = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.08)"
    fc_txt  = "#E5E7EB" if is_dark else "#1F2937"
    fc_sub  = "#9CA3AF" if is_dark else "#6B7280"
    arrow   = "#F59E0B"

    st.markdown(f"""
<style>
@keyframes flowPulse {{
  0%,100% {{ opacity:0.5; transform:scaleX(1); }}
  50%      {{ opacity:1;   transform:scaleX(1.08); }}
}}
.cs-flow {{ display:flex; align-items:center; gap:0; overflow-x:auto; padding:1.2rem 0 0.5rem; }}
.cs-node {{
  background:{fc_bg}; border:1px solid {fc_bdr}; border-radius:14px;
  padding:14px 18px; min-width:130px; text-align:center; flex-shrink:0;
  transition:transform .18s,box-shadow .18s;
}}
.cs-node:hover {{ transform:translateY(-3px); box-shadow:0 8px 24px rgba(245,158,11,.18); }}
.cs-node-icon {{ font-size:1.6rem; line-height:1; margin-bottom:4px; }}
.cs-node-label {{ font-size:12.5px; font-weight:600; color:{fc_txt}; }}
.cs-node-sub   {{ font-size:10.5px; color:{fc_sub}; margin-top:2px; }}
.cs-arrow {{ color:{arrow}; font-size:1.3rem; padding:0 6px; flex-shrink:0;
             animation:flowPulse 2s ease-in-out infinite; }}
</style>
<div class="cs-flow">
  <div class="cs-node">
    <div class="cs-node-icon">📊</div>
    <div class="cs-node-label">Business Data</div>
    <div class="cs-node-sub">ยอดขาย / Segment</div>
  </div>
  <div class="cs-arrow">→</div>
  <div class="cs-node">
    <div class="cs-node-icon">🤖</div>
    <div class="cs-node-label">AI Generate</div>
    <div class="cs-node-sub">Text / ไอเดียภาพ</div>
  </div>
  <div class="cs-arrow">→</div>
  <div class="cs-node" style="border-color:#F59E0B40;background:{'#1C1B15' if is_dark else '#FFFBEB'};">
    <div class="cs-node-icon">📁</div>
    <div class="cs-node-label">Google Drive</div>
    <div class="cs-node-sub">Content Hub</div>
  </div>
  <div class="cs-arrow">→</div>
  <div class="cs-node">
    <div class="cs-node-icon">💚</div>
    <div class="cs-node-label">LINE OA</div>
    <div class="cs-node-sub">Text + Image</div>
  </div>
  <div class="cs-arrow" style="font-size:1rem;">+</div>
  <div class="cs-node">
    <div class="cs-node-icon">🔵</div>
    <div class="cs-node-label">Facebook</div>
    <div class="cs-node-sub">Post / Reel</div>
  </div>
  <div class="cs-arrow" style="font-size:1rem;">+</div>
  <div class="cs-node">
    <div class="cs-node-icon">🟣</div>
    <div class="cs-node-label">Instagram</div>
    <div class="cs-node-sub">Feed / Story</div>
  </div>
  <div class="cs-arrow" style="font-size:1rem;">+</div>
  <div class="cs-node">
    <div class="cs-node-icon">⬛</div>
    <div class="cs-node-label">TikTok</div>
    <div class="cs-node-sub">Short Video</div>
  </div>
  <div class="cs-arrow" style="font-size:1rem;">+</div>
  <div class="cs-node">
    <div class="cs-node-icon">🔴</div>
    <div class="cs-node-label">YouTube</div>
    <div class="cs-node-sub">Shorts / Video</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # ── Campaign setup ─────────────────────────────────────────────────────────
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("🎯 ตั้งค่า Campaign")

        campaign_key = st.selectbox(
            "ประเภท Campaign",
            options=list(CAMPAIGN_TYPES.keys()),
            format_func=lambda k: CAMPAIGN_TYPES[k]["label"],
        )
        campaign_info = CAMPAIGN_TYPES[campaign_key]
        st.caption(campaign_info.get("goal", ""))

        tone_key = st.selectbox(
            "โทนเสียง",
            options=list(TONES.keys()),
            format_func=lambda k: f"{k.capitalize()} — {TONES[k]}",
        )

        st.markdown("**แพลตฟอร์มที่ต้องการ**")
        selected_platforms: list[str] = []
        pcols = st.columns(3)
        for i, (pid, pmeta) in enumerate(PLATFORMS.items()):
            with pcols[i % 3]:
                if st.checkbox(f"{pmeta['icon']} {pmeta['name']}", value=True, key=f"plat_{pid}"):
                    selected_platforms.append(pid)

    with col_right:
        st.subheader("📋 ข้อมูลธุรกิจ")

        biz_name = st.text_input("ชื่อร้าน / แบรนด์", value="ร้านของคุณ", placeholder="เช่น Café Bloom")
        hero_product = st.text_input("สินค้า / เมนู Hero", value="เมนูเด็ด", placeholder="เช่น ชาไทยเย็น, หมูกระทะ unlimited")
        discount_pct = st.number_input("ส่วนลด (%)", min_value=5, max_value=80, value=20, step=5)
        expiry_date = st.text_input("วันหมดอายุโปร", value="31 ธ.ค.", placeholder="เช่น 31 ธ.ค.")
        cta_text = st.text_input("CTA / ลิงก์", value="ทักแชทเพื่อรับสิทธิ์", placeholder="เช่น คลิก https://...")

        target_segment = st.selectbox(
            "Target Segment",
            ["Champions", "Loyal Customers", "At Risk", "Potential Loyalists", "Recent Customers", "ทุกกลุ่ม"],
        )

        if campaign_key in ("flash_sale", "winback"):
            days_inactive = st.slider("ลูกค้าหายไปกี่วัน", 7, 90, 30)
        else:
            days_inactive = 0

        if campaign_key == "flash_sale":
            urgency = st.slider("ความเร่งด่วน (ชั่วโมง)", 1, 72, 24)
            start_time = st.text_input("เวลาเริ่ม", value="17:00")
            end_time = st.text_input("เวลาจบ", value="20:00")
        else:
            urgency = 0
            start_time = "17:00"
            end_time = "20:00"

        st.markdown("**🖼️ รูปภาพประกอบ (ไม่บังคับ)**")
        uploaded_image = st.file_uploader(
            "อัปโหลดรูป",
            type=["jpg", "jpeg", "png"],
            help="ภาพจะแนบไปกับ Facebook + LINE OA + Instagram (feed)",
            key="cs_image_upload",
            label_visibility="collapsed",
        )
        if uploaded_image is not None:
            st.session_state["cs_image_bytes"] = uploaded_image.getvalue()
            st.session_state["cs_image_name"] = uploaded_image.name
            st.image(uploaded_image, caption="✅ ภาพพร้อมโพสต์", width=200)
        elif "cs_image_bytes" in st.session_state:
            if st.button("🗑️ ลบรูป", width="stretch", key="del_img"):
                del st.session_state["cs_image_bytes"]
                del st.session_state["cs_image_name"]
                st.rerun()

        st.markdown("**🎬 วิดีโอ (ไม่บังคับ)**")
        uploaded_video = st.file_uploader(
            "อัปโหลดวิดีโอ",
            type=["mp4", "mov"],
            help="วิดีโอจะใช้กับ Instagram Reels + YouTube + TikTok",
            key="cs_video_upload",
            label_visibility="collapsed",
        )
        if uploaded_video is not None:
            st.session_state["cs_video_bytes"] = uploaded_video.getvalue()
            st.session_state["cs_video_name"] = uploaded_video.name
            size_mb = len(st.session_state["cs_video_bytes"]) / 1024 / 1024
            st.success(f"✅ วิดีโอพร้อม ({size_mb:.1f} MB)")
        elif "cs_video_bytes" in st.session_state:
            if st.button("🗑️ ลบวิดีโอ", width="stretch", key="del_vid"):
                del st.session_state["cs_video_bytes"]
                del st.session_state["cs_video_name"]
                st.rerun()

    st.divider()

    # ── Generate ───────────────────────────────────────────────────────────────
    use_claude = ai_mode == "Claude API" and api_key.strip() and ANTHROPIC_AVAILABLE
    btn_label = "🤖 Generate with Claude AI" if use_claude else "⚡ Generate with Local AI"

    if st.button(btn_label, type="primary", width="stretch"):
        # Keys must match placeholders in content_studio.py templates
        _brand = biz_name or "ร้านของคุณ"
        _hero = hero_product or "เมนูเด็ด"
        context = {
            "brand_name": _brand,
            "brand_tag": _brand.replace(" ", "").replace("ร้าน", ""),
            "top_item": _hero,
            "discount": discount_pct,
            "expiry": expiry_date,
            "cta": cta_text,
            "days": days_inactive,
            "hours": "10:00-22:00",
            "start_time": start_time,
            "end_time": end_time,
            "countdown": urgency,
            # also keep old keys for compatibility
            "business_name": _brand,
            "hero_product": _hero,
            "target_segment": target_segment,
            "days_inactive": days_inactive,
            "urgency_hours": urgency,
        }
        with st.spinner("กำลังสร้างคอนเทนต์..."):
            package = get_content_package(
                campaign_type=campaign_key,
                context=context,
                tone=tone_key,
                api_key=api_key.strip() if use_claude else "",
            )
        st.session_state["cs_package"] = package
        st.session_state["cs_campaign"] = campaign_key
        st.session_state["cs_platforms"] = selected_platforms
        st.success("สร้างคอนเทนต์สำเร็จ! เลื่อนลงเพื่อดูและโพสต์")

    # ── Content display ────────────────────────────────────────────────────────
    if "cs_package" not in st.session_state:
        _notice_bg = "#1C1B15" if is_dark else "#FFFBEF"
        _notice_bd = "#F59E0B40"
        _notice_tx = "#D97706" if is_dark else "#92400E"
        st.markdown(
            f'<div style="background:{_notice_bg};border:1px solid {_notice_bd};border-radius:12px;'
            f'padding:1.2rem 1.5rem;margin-top:0.5rem;">'
            f'<p style="color:{_notice_tx};margin:0;font-size:0.9rem;">💡 กรอกข้อมูลด้านบนแล้วกด Generate เพื่อสร้างคอนเทนต์พร้อมโพสต์</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    package   = st.session_state["cs_package"]
    sel_plats = st.session_state.get("cs_platforms", list(PLATFORMS.keys()))

    st.divider()
    st.subheader("📝 คอนเทนต์ที่สร้างแล้ว")

    # tabs per platform
    visible = [p for p in sel_plats if p in package]
    if not visible:
        st.warning("ไม่พบคอนเทนต์สำหรับแพลตฟอร์มที่เลือก — ลองกด Generate ใหม่")
        return

    tab_labels = [f"{PLATFORMS[p]['icon']} {PLATFORMS[p]['name']}" for p in visible]
    tabs = st.tabs(tab_labels)

    for tab, pid in zip(tabs, visible):
        content = package.get(pid, "")
        # content is a plain string from get_content_package()
        full_text = content if isinstance(content, str) else ""
        pmeta   = PLATFORMS[pid]
        with tab:
            c_txt_col, c_act_col = st.columns([2, 1])
            with c_txt_col:
                edited = st.text_area(
                    f"คอนเทนต์ {pmeta['name']}",
                    value=full_text,
                    height=220,
                    key=f"cs_text_{pid}",
                )
                char_count = len(edited)
                max_chars  = pmeta.get("max_chars", 2200)
                bar_pct    = min(char_count / max_chars, 1.0)
                bar_color  = "#EF4444" if bar_pct > 0.9 else "#10B981"
                st.markdown(
                    f'<div style="height:4px;border-radius:2px;background:rgba(128,128,128,.15);">'
                    f'<div style="height:4px;border-radius:2px;width:{bar_pct*100:.0f}%;background:{bar_color};transition:width .3s;"></div>'
                    f'</div>'
                    f'<p style="font-size:11px;color:#9CA3AF;margin:3px 0 0;">{char_count:,} / {max_chars:,} ตัวอักษร</p>',
                    unsafe_allow_html=True,
                )

            with c_act_col:
                st.markdown(f"**Best Post Time**")
                best_hours = pmeta.get("best_hours", [])
                for h in best_hours:
                    st.markdown(f"🕐 `{h:02d}:00 น.`")

                routes = pmeta.get("routes", [])
                st.markdown(f"**Content Types**")
                for r in routes:
                    icons = {"text": "📝", "image": "🖼️", "video": "🎬", "carousel": "🎠"}
                    st.markdown(f"{icons.get(r, '•')} {r.capitalize()}")

                st.markdown("---")
                # Mock publish button
                col_save, col_post = st.columns(2)
                with col_save:
                    st.download_button(
                        "📁 Save",
                        data=edited.encode("utf-8"),
                        file_name=f"{pid}_content.txt",
                        mime="text/plain",
                        width="stretch",
                        key=f"dl_{pid}",
                    )
                with col_post:
                    if st.button(
                        f"🚀 Post",
                        width="stretch",
                        key=f"post_{pid}",
                        type="primary",
                    ):
                        _do_post(
                            pid, edited, line_token, fb_token, fb_page_id,
                            ig_business_id=ig_business_id,
                            image_bytes=st.session_state.get("cs_image_bytes"),
                            image_name=st.session_state.get("cs_image_name", "image.jpg"),
                            video_bytes=st.session_state.get("cs_video_bytes"),
                            video_name=st.session_state.get("cs_video_name", "video.mp4"),
                        )

                    # TikTok download helper (always shown for tiktok tab)
                    if pid == "tiktok" and st.session_state.get("cs_video_bytes"):
                        st.download_button(
                            "📥 Download วิดีโอ (สำหรับ TikTok)",
                            data=st.session_state["cs_video_bytes"],
                            file_name=st.session_state.get("cs_video_name", "video.mp4"),
                            mime="video/mp4",
                            key=f"dl_tiktok_{pid}",
                            width="stretch",
                        )
                        st.markdown("[🔗 เปิด TikTok เพื่ออัปโหลด](https://www.tiktok.com/upload)")

    # ── Post All ───────────────────────────────────────────────────────────────
    st.divider()
    pa_left, pa_right = st.columns([2, 1])
    with pa_left:
        st.markdown("**⚡ โพสต์ทุกแพลตฟอร์มในคลิกเดียว**")
        st.caption("ใช้คอนเทนต์ของแต่ละ tab (รวมที่แก้ไขแล้ว) — TikTok จะเตรียมไฟล์ให้ดาวน์โหลด")
    with pa_right:
        post_all_clicked = st.button("🚀 Post All", type="primary", width="stretch", key="post_all")

    if post_all_clicked:
        results = []
        progress = st.progress(0.0, text="เริ่มโพสต์...")
        for i, pid in enumerate(visible):
            pname = PLATFORM_THAI_NAMES.get(pid, pid)
            progress.progress(i / len(visible), text=f"กำลังโพสต์ {pname}...")
            content_i = st.session_state.get(f"cs_text_{pid}") or package.get(pid, "")
            ok, msg = _do_post(
                pid, content_i, line_token, fb_token, fb_page_id,
                ig_business_id=ig_business_id,
                image_bytes=st.session_state.get("cs_image_bytes"),
                image_name=st.session_state.get("cs_image_name", "image.jpg"),
                video_bytes=st.session_state.get("cs_video_bytes"),
                video_name=st.session_state.get("cs_video_name", "video.mp4"),
                quiet=True,
            )
            results.append((pname, ok, msg))
        progress.progress(1.0, text="เสร็จแล้ว!")

        n_ok = sum(1 for _, ok, _ in results if ok)
        if n_ok == len(results):
            st.success(f"🎉 โพสต์สำเร็จครบ {n_ok}/{len(results)} แพลตฟอร์ม")
        else:
            st.warning(f"สำเร็จ {n_ok}/{len(results)} แพลตฟอร์ม — ดูรายละเอียดด้านล่าง")
        for pname, ok, msg in results:
            st.markdown(f"{'✅' if ok else '❌'} **{pname}** — {msg}")

    # ── Posting schedule ───────────────────────────────────────────────────────
    st.divider()
    st.subheader("📅 ตารางโพสต์ที่แนะนำ")

    schedule_df = build_posting_schedule(visible, start_date=dt.date.today(), days=7)
    if schedule_df:
        sched_display = pd.DataFrame(schedule_df)
        sched_display["แพลตฟอร์ม"] = sched_display["platform_key"].map(
            lambda p: f"{PLATFORMS[p]['icon']} {PLATFORMS[p]['name']}" if p in PLATFORMS else p
        )
        sched_display["เวลาโพสต์"] = sched_display["date"].astype(str) + " " + sched_display["time"]
        sched_display["สถานะ"] = sched_display["status"]
        st.dataframe(sched_display[["แพลตฟอร์ม", "เวลาโพสต์", "สถานะ"]], width="stretch", hide_index=True)
    else:
        st.info("เลือกแพลตฟอร์มอย่างน้อย 1 แพลตฟอร์มเพื่อดูตารางโพสต์")

    # ── Google Drive export ────────────────────────────────────────────────────
    st.divider()
    st.subheader("📁 Export ไป Google Drive")

    all_content = "\n\n".join(
        f"=== {PLATFORMS[p]['name'].upper()} ===\n{package.get(p, '')}"
        for p in visible
    )
    filename = f"content_package_{dt.datetime.now().strftime('%Y%m%d_%H%M')}.txt"

    drive_col, dl_col = st.columns([1, 1])
    with drive_col:
        if GDRIVE_AVAILABLE:
            if needs_auth():
                st.warning("ยังไม่ได้ authorize Google Drive")
                if st.button("🔐 Authorize Google Drive", width="stretch"):
                    with st.spinner("กำลังเปิด browser..."):
                        run_first_time_auth()
                    st.success("Authorized แล้ว! กด Upload ได้เลย")
                    st.rerun()
            else:
                if st.button("☁️ Upload ไป Google Drive", type="primary", width="stretch"):
                    with st.spinner("กำลัง upload..."):
                        link = upload_text(all_content, filename, GDRIVE_FOLDER_ID)
                    if link:
                        st.success("Upload สำเร็จ!")
                        st.markdown(f"[📄 เปิดไฟล์ใน Drive]({link})")
                        st.session_state["last_drive_link"] = link
                    else:
                        st.error("Upload ไม่สำเร็จ")
                if "last_drive_link" in st.session_state:
                    st.markdown(f"[🔗 ไฟล์ล่าสุด]({st.session_state['last_drive_link']})")
        else:
            st.warning("ไม่พบ google_drive.py")

    with dl_col:
        st.download_button(
            label="💾 Download ไฟล์",
            data=all_content.encode("utf-8"),
            file_name=filename,
            mime="text/plain",
            width="stretch",
        )

    # ── Post history ───────────────────────────────────────────────────────────
    history = st.session_state.get("post_history", [])
    if history:
        st.divider()
        st.subheader("🕐 ประวัติการโพสต์ (เซสชันนี้)")
        st.dataframe(pd.DataFrame(reversed(history)), width="stretch", hide_index=True)
        if st.button("🗑️ ล้างประวัติ", key="clear_history"):
            st.session_state["post_history"] = []
            st.rerun()


# ── AI provider helpers ──────────────────────────────────────────────────────────

def _resolve_ai(ai_mode: str, api_key: str) -> tuple[str, str, str]:
    """Return (key, provider, label) for the selected AI mode.

    key is "" whenever the mode/credentials aren't usable, which makes every
    caller fall back to local templates automatically.
    """
    key = (api_key or "").strip()
    if ai_mode == "Gemini API" and key:
        return key, "gemini", "✨ Gemini"
    if ai_mode == "Claude API" and key and ANTHROPIC_AVAILABLE:
        return key, "claude", "🤖 Claude"
    return "", "local", "⚡ Local AI"


def _mandala_badge() -> None:
    """Show whether the Mandala brand context is wired in."""
    try:
        import mandala_client
        info = mandala_client.status()
    except Exception:  # noqa: BLE001
        return
    if info.get("has_context"):
        st.caption(
            f"🔗 ใช้บริบทแบรนด์จาก Mandala AI ({info['context_chars']:,} ตัวอักษร"
            f" · {info['runs']} รอบที่ผลิตไว้)"
        )
    elif info.get("found"):
        st.caption("🔗 เจอ mandala-bot แต่ยังไม่มี context.txt")


@st.cache_data(ttl=600, show_spinner=False)
def _scene_scores() -> dict:
    """How well each scene angle fits this brand, scored off Mandala's own material.

    Reading the context files costs a disk hit per rerun and the answer only
    changes when Mandala produces a new run, so it is cached. Returns an empty
    dict when there is nothing to score against — callers then show no stars
    rather than an invented number.
    """
    if not SCENES_AVAILABLE:
        return {}
    try:
        import mandala_client
        text = mandala_client.build_context_block(include_samples=4, max_chars=20000)
    except Exception:  # noqa: BLE001
        return {}
    if not text:
        return {}
    try:
        return scene_presets.score_scenes(text)
    except Exception:  # noqa: BLE001
        return {}


# ── Approval queue (reads back from Google Drive) ────────────────────────────────

# How many files to draw per folder before offering "show more".
QUEUE_PAGE_SIZE = 15

# Listing the queue costs one Drive round trip per folder — measured at 6.5s for
# eight folders. Streamlit reruns the whole script on every click, so without a
# cache each approve, each "show more", each checkbox pays that again. The TTL
# keeps it fresh enough for a review queue; "โหลดใหม่" clears it outright.
QUEUE_CACHE_TTL = 60


@st.cache_data(ttl=QUEUE_CACHE_TTL, show_spinner=False)
def _cached_child_folders(root_id: str) -> dict:
    return list_child_folders(root_id)


@st.cache_data(ttl=QUEUE_CACHE_TTL, show_spinner=False)
def _cached_files(folder_id: str, oldest_first: bool) -> list[dict]:
    return list_files_in_folder(folder_id, oldest_first=oldest_first)


def _clear_queue_cache() -> None:
    _cached_child_folders.clear()
    _cached_files.clear()

# Folder name fragment → platform key, so a file's location decides where it posts.
_FOLDER_PLATFORM_HINTS = [
    (("facebook", "fb"), "facebook"),
    (("instagram", "instragram", "ig"), "instagram"),
    (("tiktok", "tik tok"), "tiktok"),
    (("youtube", "yt"), "youtube"),
    (("line",), "line_oa"),
]


def _platform_from_folder(name: str) -> str:
    low = (name or "").lower()
    for fragments, key in _FOLDER_PLATFORM_HINTS:
        if any(f in low for f in fragments):
            return key
    return ""


def _queue_caption_for(file: dict) -> str:
    """Text files in the queue are captions — read them for preview/posting."""
    if not (file.get("mimeType") or "").startswith("text/"):
        return ""
    data = download_file(file["id"])
    if not data:
        return ""
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""


def _render_queue_file(folder_name: str, platform: str, file: dict,
                       line_token: str, fb_token: str, fb_page_id: str,
                       ig_business_id: str) -> None:
    """One queued item: preview, then approve-and-post or reject."""
    mime = file.get("mimeType", "")
    fid = file["id"]
    size_mb = int(file.get("size") or 0) / 1024 / 1024

    with st.container(border=True):
        top, act = st.columns([3, 1])
        with top:
            st.markdown(f"**{file['name']}**")
            st.caption(f"{PLATFORM_THAI_NAMES.get(platform, folder_name)} · "
                       f"{mime.split('/')[-1]} · {size_mb:.1f} MB · "
                       f"{file.get('createdTime', '')[:16].replace('T', ' ')}")
        with act:
            if file.get("webViewLink"):
                st.markdown(f"[🔗 เปิดใน Drive]({file['webViewLink']})")

        media_bytes = None
        caption = ""

        if mime.startswith("image/"):
            if st.button("👁️ ดูรูป", key=f"q_prev_{fid}", width="stretch"):
                st.session_state[f"q_data_{fid}"] = download_file(fid)
            media_bytes = st.session_state.get(f"q_data_{fid}")
            if media_bytes:
                st.image(media_bytes, width="stretch")
        elif mime.startswith("video/"):
            st.caption("วิดีโอไฟล์ใหญ่ — กดโหลดเมื่อต้องการดู")
            if st.button("▶️ โหลดวิดีโอมาดู", key=f"q_prev_{fid}", width="stretch"):
                st.session_state[f"q_data_{fid}"] = download_file(fid)
            media_bytes = st.session_state.get(f"q_data_{fid}")
            if media_bytes:
                st.video(media_bytes)
        else:
            caption = _queue_caption_for(file)
            if caption:
                st.text_area("แคปชัน", value=caption, height=140, key=f"q_cap_{fid}")

        text_to_post = st.session_state.get(f"q_cap_{fid}", caption)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ อนุมัติ + โพสต์", key=f"q_ok_{fid}",
                         type="primary", width="stretch"):
                if not platform:
                    st.error("ไม่รู้ว่าไฟล์นี้ควรลงแพลตฟอร์มไหน — "
                             "ตั้งชื่อโฟลเดอร์ให้มีชื่อแพลตฟอร์ม")
                    return
                data = media_bytes or (download_file(fid)
                                       if mime.startswith(("image/", "video/")) else None)
                ok, msg = _do_post(
                    platform, text_to_post or file["name"],
                    line_token, fb_token, fb_page_id,
                    ig_business_id=ig_business_id,
                    image_bytes=data if mime.startswith("image/") else None,
                    image_name=file["name"],
                    video_bytes=data if mime.startswith("video/") else None,
                    video_name=file["name"],
                )
                if ok:
                    dest = ensure_subfolder(QUEUE_ROOT_FOLDER_ID, "POSTED")
                    if dest and move_file(fid, dest):
                        st.success(f"{msg} — ย้ายไฟล์ไปโฟลเดอร์ POSTED แล้ว")
                    else:
                        st.warning(f"{msg} — แต่ย้ายไฟล์ไม่สำเร็จ")
                    # The listing just changed; a stale cache would keep showing
                    # a file that is no longer in the queue.
                    _clear_queue_cache()
                    st.rerun()
                else:
                    st.error(msg)
        with c2:
            if st.button("❌ ไม่อนุมัติ", key=f"q_no_{fid}", width="stretch"):
                dest = ensure_subfolder(QUEUE_ROOT_FOLDER_ID, "REJECTED")
                if dest and move_file(fid, dest):
                    st.info("ย้ายไปโฟลเดอร์ REJECTED แล้ว")
                    _clear_queue_cache()
                    st.rerun()
                else:
                    st.error("ย้ายไฟล์ไม่สำเร็จ")


def _render_flow_sync(authed: bool = True) -> None:
    """Pull freshly downloaded Google Flow exports into the right Drive folders."""
    if not FLOW_SYNC_AVAILABLE:
        return

    with st.expander("⬇️ ซิงก์ไฟล์จาก Google Flow", expanded=not authed):
        st.caption(
            "Flow ไม่มี API ให้ดึงไฟล์ออกโดยตรง — ให้กดดาวน์โหลดจาก Flow ตามปกติ "
            "แล้วระบบจะหยิบไฟล์ใหม่ในโฟลเดอร์นี้ไปเข้า Drive ให้เอง"
        )
        st.link_button("🎬 ไปดาวน์โหลดจาก Google Flow", FLOW_PROJECT_URL,
                       width="stretch")

        local_root = flow_sync.default_local_root()
        if local_root:
            st.success(f"⚡ โหมดย้ายไฟล์ในเครื่อง — `{local_root}` "
                       "(เร็วกว่า ไม่กินโควตา API และ Drive ซิงก์ขึ้นคลาวด์ให้เอง)")
        else:
            st.caption("โหมดอัปโหลดผ่าน Drive API — ถ้าติดตั้ง Google Drive for Desktop "
                       "ระบบจะเปลี่ยนไปย้ายไฟล์ในเครื่องให้อัตโนมัติ (เร็วกว่ามาก)")
        default_dir = str(flow_sync.default_watch_dir())
        watch = st.text_input("โฟลเดอร์ที่ไฟล์ดาวน์โหลดลง", value=default_dir,
                              key="flow_watch_dir")
        c1, c2 = st.columns(2)
        with c1:
            hours = st.selectbox(
                "ดูเฉพาะไฟล์ใหม่ภายใน", options=[6, 24, 72, 0], index=1,
                format_func=lambda h: "ทั้งหมด" if h == 0 else f"{h} ชั่วโมง",
                key="flow_watch_hours",
            )
        with c2:
            st.caption("ไฟล์ที่ซิงก์แล้วจะถูกย้ายไปโฟลเดอร์ย่อย `_synced` "
                       "เพื่อไม่ให้อัปซ้ำ")

        pending = flow_sync.find_new_files(Path(watch), hours) if watch else []
        overrides: dict[str, str] = {}
        if pending:
            st.info(f"เจอไฟล์ใหม่ {len(pending)} ไฟล์ — เลือกปลายทางของแต่ละไฟล์")
            st.caption("Flow ตั้งชื่อไฟล์โดยไม่บอกแพลตฟอร์ม จึงต้องเลือกเอง "
                       "(หรือตั้งชื่อไฟล์ให้มี `ig` / `fb` / `tiktok` / `yt` แล้วเลือก อัตโนมัติ)")
            dest_options = ["auto", "facebook", "instagram", "tiktok", "youtube",
                            "line_oa", "skip"]
            for p in pending[:20]:
                kind = flow_sync.classify(p)
                guessed = flow_sync.guess_platform(p.name)
                fc, dc = st.columns([2, 1])
                with fc:
                    st.markdown(f"{'🖼️' if kind == 'image' else '🎬'} `{p.name[:52]}`")
                with dc:
                    overrides[p.name] = st.selectbox(
                        "ปลายทาง",
                        options=dest_options,
                        index=dest_options.index(guessed) if guessed in dest_options else 0,
                        format_func=lambda v: {
                            "auto": "🔎 อัตโนมัติ",
                            "skip": "⏭️ ข้ามไฟล์นี้",
                        }.get(v, PLATFORM_THAI_NAMES.get(v, v)),
                        key=f"flow_dest_{p.name}",
                        label_visibility="collapsed",
                    )
            # "auto" means "no override" as far as the sync layer is concerned.
            overrides = {k: ("" if v == "auto" else v) for k, v in overrides.items()}
        else:
            st.caption("ยังไม่เจอไฟล์ใหม่ในโฟลเดอร์นี้")

        # Moving into the Drive-for-Desktop mirror needs no API access at all.
        can_sync = authed or local_root is not None
        if not can_sync:
            st.caption("🔐 ต้อง authorize Google Drive ก่อนถึงจะซิงก์ได้ (ปุ่มอยู่ด้านล่าง)")

        if st.button("⬇️ ซิงก์เข้า Drive", type="primary",
                     disabled=not pending or not can_sync, width="stretch"):
            prog = st.progress(0.0, text="เริ่มซิงก์...")

            def _tick(i: int, total: int, name: str) -> None:
                prog.progress((i - 1) / max(total, 1), text=f"{i}/{total} — {name}")

            results = flow_sync.sync_folder(watch, QUEUE_ROOT_FOLDER_ID,
                                            max_age_hours=hours, on_progress=_tick,
                                            overrides=overrides, local_root=local_root)
            prog.progress(1.0, text="เสร็จแล้ว")
            ok = sum(1 for r in results if r["ok"])
            (st.success if ok == len(results) else st.warning)(
                f"ซิงก์สำเร็จ {ok}/{len(results)} ไฟล์")
            for r in results:
                st.markdown(f"{'✅' if r['ok'] else '❌'} **{r['name']}** — "
                            f"{r['folder'] if r['ok'] else r['error']}")
            _clear_queue_cache()   # newly filed files must show up straight away
            st.rerun()

        st.divider()
        st.markdown("**⚡ ทำให้อัตโนมัติเต็มรูปแบบ**")
        st.caption("1️⃣ รัน watcher ค้างไว้ — ไฟล์ลงปุ๊บจัดเข้าโฟลเดอร์ทันที ไม่ต้องกดปุ่มนี้อีก")
        st.code(f'{Path.cwd() / ".venv/Scripts/python.exe"} {Path.cwd() / "flow_watch.py"}',
                language="powershell")

        st.caption("2️⃣ กดดาวน์โหลดทุกคลิปใน Flow รวดเดียว — เปิด Flow ใน Chrome → กด F12 → "
                   "แท็บ Console → วางสคริปต์นี้ → Enter")
        helper = Path(__file__).parent / "flow_download_helper.js"
        if helper.exists():
            with st.popover("📋 เปิดสคริปต์เพื่อคัดลอก", width="stretch"):
                st.code(helper.read_text(encoding="utf-8"), language="javascript")
            st.caption("สคริปต์ทำงานบนหน้าที่คุณเปิดเอง หน่วง 3-5 วิต่อไฟล์ "
                       "และจำกัด 15 ไฟล์ต่อรอบ")

        st.caption("ทางเลือก: ตั้งเวลาแทน watcher (ทุก 5 นาที)")
        st.code(
            'schtasks /create /tn "FlowSync" /tr '
            f'"{Path.cwd() / ".venv/Scripts/python.exe"} {Path.cwd() / "flow_sync.py"}" '
            '/sc minute /mo 5',
            language="powershell",
        )


def render_queue_page(line_token: str = "", fb_token: str = "",
                      fb_page_id: str = "", ig_business_id: str = "") -> None:
    st.title("📁 คิวอนุมัติ")
    st.caption("อ่านไฟล์จาก Google Drive (รวมงานที่สร้างใน Google Flow) → ตรวจ → อนุมัติ → โพสต์")

    lk1, lk2 = st.columns(2)
    with lk1:
        st.link_button("🎬 เปิด Google Flow", FLOW_PROJECT_URL, width="stretch")
    with lk2:
        st.link_button("📁 เปิดโฟลเดอร์ Drive", DRIVE_FOLDER_URL, width="stretch")

    if not GDRIVE_AVAILABLE:
        st.error("ไม่พบ google_drive.py")
        return
    authed = not needs_auth()
    # Show the sync panel even before authorization so the folder and schedule can
    # be set up first; only the upload itself needs Drive access.
    _render_flow_sync(authed)

    if not authed:
        st.warning("ยังไม่ได้ authorize Google Drive")
        if st.button("🔐 Authorize Google Drive", type="primary"):
            with st.spinner("กำลังเปิด browser..."):
                run_first_time_auth()
            st.rerun()
        return

    folders = _cached_child_folders(QUEUE_ROOT_FOLDER_ID)
    if not folders:
        st.warning(
            "มองไม่เห็นโฟลเดอร์ย่อยเลย — น่าจะเป็นเพราะ **OAuth scope เดิม** "
            "(`drive.file` เห็นเฉพาะไฟล์ที่แอปสร้างเอง)"
        )
        st.markdown(
            "**วิธีแก้:** ลบไฟล์ `token.json` ในโฟลเดอร์โปรเจกต์ แล้วกด Authorize ใหม่ "
            "เพื่อให้สิทธิ์แบบเต็ม (`drive`)"
        )
        return

    skip = {"POSTED", "REJECTED"}
    review = {n: i for n, i in folders.items() if n.upper() not in skip}
    st.caption(f"เจอ {len(review)} โฟลเดอร์: " + " · ".join(sorted(review)))

    pick = st.multiselect("เลือกโฟลเดอร์ที่จะตรวจ", options=sorted(review),
                          default=sorted(review))

    # Newest first by default: the usual reason to open this page is to review
    # something just generated. Oldest first is for working down a backlog.
    sort_label = st.radio(
        "เรียงลำดับ", ["🆕 ใหม่สุดก่อน", "⏳ เก่าสุดก่อน (ค้างนานสุด)"],
        horizontal=True, label_visibility="collapsed", key="queue_sort",
    )
    oldest_first = sort_label.startswith("⏳")
    if st.button("🔄 โหลดใหม่"):
        # Drop cached previews and collapse every folder back to one page.
        for k in list(st.session_state):
            if k.startswith(("q_data_", "queue_shown_")):
                del st.session_state[k]
        _clear_queue_cache()
        st.rerun()

    total = 0
    for folder_name in pick:
        files = _cached_files(review[folder_name], oldest_first)
        if not files:
            continue
        platform = _platform_from_folder(folder_name)
        st.divider()
        # Icon only — the folder name already says which platform it is, so the
        # full label would read "🔵 Facebook Facebook VDO". Taken from the Thai
        # label rather than content_studio so the queue works even if that
        # module fails to import.
        icon = PLATFORM_THAI_NAMES.get(platform, "📂").split()[0]

        # Render a page at a time. Streamlit reruns the whole script on every
        # click, so drawing a hundred files means every approve costs a full
        # redraw of all of them.
        shown_key = f"queue_shown_{folder_name}"
        shown = min(st.session_state.get(shown_key, QUEUE_PAGE_SIZE), len(files))

        st.subheader(f"{icon} {folder_name} ({len(files)})")
        if len(files) > shown:
            order = "เก่าสุดก่อน" if oldest_first else "ใหม่สุดก่อน"
            st.caption(f"แสดง {shown} จาก {len(files)} ไฟล์ · เรียง{order}")
        if not platform:
            st.caption("⚠️ เดาแพลตฟอร์มจากชื่อโฟลเดอร์ไม่ได้ — อนุมัติแล้วจะโพสต์ไม่ได้")

        for f in files[:shown]:
            total += 1
            _render_queue_file(folder_name, platform, f,
                               line_token, fb_token, fb_page_id, ig_business_id)

        remaining = len(files) - shown
        if remaining > 0:
            more = min(QUEUE_PAGE_SIZE, remaining)
            if st.button(f"⬇️ ดูเพิ่มอีก {more} ไฟล์ (เหลือ {remaining})",
                         key=f"queue_more_{folder_name}", width="stretch"):
                st.session_state[shown_key] = shown + QUEUE_PAGE_SIZE
                st.rerun()

    if total == 0:
        st.success("🎉 ไม่มีงานค้างรออนุมัติ")


# ── Canva (Connect API) ──────────────────────────────────────────────────────────

def _canva_token() -> str:
    """Current Canva access token, refreshed if it's about to expire."""
    tok = st.session_state.get("canva_token")
    if not tok:
        return ""
    if canva_client.token_expired(tok) and tok.get("refresh_token"):
        cid, secret, _ = canva_client.get_credentials()
        new, _msg = canva_client.refresh_token(cid, secret, tok["refresh_token"])
        if new:
            st.session_state["canva_token"] = new
            return new.get("access_token", "")
    return tok.get("access_token", "")


def _render_canva_connect() -> None:
    """Manual OAuth: show the authorize link, take the redirected URL back."""
    cid, secret, redirect_uri = canva_client.get_credentials()
    if not cid or not secret:
        st.warning("ยังไม่ได้ตั้งค่า Canva app")
        st.markdown(
            "**วิธีตั้งค่า** — สร้าง integration ที่ "
            "[canva.com/developers](https://www.canva.com/developers/) แล้วใส่ค่าใน "
            "`.streamlit/secrets.toml`:"
        )
        st.code(
            '[canva]\n'
            'client_id = "ใส่ Client ID"\n'
            'client_secret = "ใส่ Client Secret"\n'
            f'redirect_uri = "{redirect_uri}"',
            language="toml",
        )
        st.caption(f"อย่าลืมตั้ง Redirect URL ใน Canva ให้ตรงกับ `{redirect_uri}`")
        return

    if "canva_pkce" not in st.session_state:
        st.session_state["canva_pkce"] = canva_client.make_pkce()
    verifier, challenge = st.session_state["canva_pkce"]
    auth_url = canva_client.build_auth_url(cid, redirect_uri, challenge)

    st.markdown(f"**1.** [🔗 กดที่นี่เพื่ออนุญาตให้แอปเข้าถึง Canva]({auth_url})")
    st.caption("**2.** อนุญาตแล้ว Canva จะพาไปหน้าที่ URL มี `?code=...` — copy URL นั้นทั้งอัน")
    pasted = st.text_input("**3.** วาง URL ที่ถูก redirect มาที่นี่", key="canva_redirect_url")
    if st.button("เชื่อมต่อ Canva", type="primary", disabled=not pasted):
        code = canva_client.extract_code(pasted)
        if not code:
            st.error("ไม่พบ `code=` ใน URL — ตรวจสอบว่า copy มาครบทั้ง URL")
            return
        with st.spinner("กำลังเชื่อมต่อ..."):
            tok, msg = canva_client.exchange_code(cid, secret, code, verifier, redirect_uri)
        if tok:
            st.session_state["canva_token"] = tok
            st.session_state.pop("canva_pkce", None)
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def _render_canva_autofill(token: str, caps: dict) -> None:
    """Brand template → autofill → export. Enterprise-only."""
    if not caps.get("brand_templates"):
        st.warning(
            "⚠️ บัญชี Canva นี้ใช้ **Autofill / Brand Template ไม่ได้** — "
            "Canva กำหนดให้ต้องเป็นแพลน **Enterprise** เท่านั้น"
        )
        if caps.get("note"):
            st.caption(caps["note"])
        st.markdown(
            "**ทางเลือกที่ใช้ได้เลยตอนนี้:** ส่งรูปที่ AI สร้างขึ้นไปเก็บใน Canva "
            "แล้วเปิดแต่งต่อเองในเว็บ (ดูหัวข้อด้านล่าง)"
        )
        return

    templates, err = canva_client.list_brand_templates(token)
    if err:
        st.error(err)
        return
    if not templates:
        st.info("ยังไม่มี Brand Template ในบัญชีนี้ — สร้างในเว็บ Canva ก่อน")
        return

    tmap = {t["title"]: t["id"] for t in templates}
    picked = st.selectbox("เลือก Brand Template", options=list(tmap.keys()))
    tid = tmap[picked]

    fields, derr = canva_client.get_template_dataset(token, tid)
    if derr:
        st.error(derr)
        return
    if not fields:
        st.info("เทมเพลตนี้ไม่มีช่องที่เติมข้อมูลได้")
        return

    st.caption(f"เทมเพลตนี้มี {len(fields)} ช่อง")
    values: dict = {}
    for fname, meta in fields.items():
        ftype = (meta or {}).get("type", "text")
        if ftype == "image":
            st.caption(f"🖼️ `{fname}` — ช่องรูป (ใช้รูปที่สร้างจากแชท)")
            img = st.session_state.get("canva_pending_image")
            if img:
                st.image(img, width=120)
                values[fname] = "__PENDING_IMAGE__"
            else:
                st.caption("ยังไม่มีรูป — สร้างรูปในหน้า Copilot แล้วกด 'ส่งไป Canva'")
        else:
            values[fname] = st.text_input(f"📝 {fname}", key=f"canva_f_{fname}")

    title = st.text_input("ชื่อดีไซน์", value=f"LEMED {dt.datetime.now():%d/%m %H:%M}")

    if st.button("🎨 สร้างดีไซน์จากเทมเพลต", type="primary", width="stretch"):
        with st.spinner("กำลังอัปโหลดรูป / สร้างดีไซน์..."):
            # Any image field needs a Canva asset id, so upload first.
            img = st.session_state.get("canva_pending_image")
            for k, v in list(values.items()):
                if v == "__PENDING_IMAGE__":
                    if not img:
                        values.pop(k)
                        continue
                    asset_id, amsg = canva_client.upload_asset(
                        token, img, f"lemed_{dt.datetime.now():%Y%m%d_%H%M%S}.png")
                    if not asset_id:
                        st.error(amsg)
                        return
                    values[k] = asset_id

            data = canva_client.build_autofill_data(fields, values)
            design, msg = canva_client.autofill(token, tid, data, title)

        if not design:
            st.error(msg)
            return
        st.success(msg)
        url = (design.get("urls") or {}).get("edit_url") or design.get("url", "")
        if url:
            st.markdown(f"[🔗 เปิดดีไซน์ใน Canva]({url})")

        design_id = design.get("id", "")
        if design_id:
            with st.spinner("กำลัง export เป็นรูป..."):
                urls, emsg = canva_client.export_design(token, design_id, "png")
            if urls:
                st.success(emsg)
                for i, u in enumerate(urls, 1):
                    data_bytes = canva_client.download(u)
                    if data_bytes:
                        st.image(data_bytes, caption=f"หน้า {i}", width="stretch")
                        st.download_button(
                            f"📥 ดาวน์โหลดหน้า {i}", data=data_bytes,
                            file_name=f"canva_{design_id}_{i}.png", mime="image/png",
                            key=f"canva_dl_{design_id}_{i}", width="stretch")
            else:
                st.warning(emsg)


def render_canva_page() -> None:
    st.title("🎨 Canva")
    st.caption("เชื่อม Canva Connect API — เติมข้อมูลลง Brand Template แล้ว export เป็นโปสเตอร์/carousel")

    if not CANVA_AVAILABLE:
        st.error("ไม่พบ canva_client.py — ตรวจสอบไฟล์ในโฟลเดอร์โปรเจกต์")
        return

    token = _canva_token()
    if not token:
        _render_canva_connect()
        return

    with st.spinner("กำลังเช็คสิทธิ์บัญชี..."):
        caps = st.session_state.get("canva_caps") or canva_client.capabilities(token)
        st.session_state["canva_caps"] = caps

    if not caps.get("connected"):
        st.error(caps.get("note") or "token ใช้ไม่ได้")
        if st.button("🔌 เชื่อมต่อใหม่"):
            for k in ("canva_token", "canva_caps", "canva_pkce"):
                st.session_state.pop(k, None)
            st.rerun()
        return

    head, btn = st.columns([3, 1])
    with head:
        badge = "✅ Enterprise (ใช้ Autofill ได้)" if caps.get("brand_templates") \
            else "⚠️ ไม่ใช่ Enterprise (Autofill ใช้ไม่ได้)"
        st.success(f"เชื่อม Canva แล้ว — {badge}")
    with btn:
        if st.button("ตัดการเชื่อมต่อ", width="stretch"):
            for k in ("canva_token", "canva_caps", "canva_pkce"):
                st.session_state.pop(k, None)
            st.rerun()

    st.divider()
    st.subheader("🖼️ สร้างจาก Brand Template")
    _render_canva_autofill(token, caps)

    st.divider()
    st.subheader("📤 ส่งรูปเข้าคลัง Canva")
    st.caption("ใช้ได้ทุกแพลน — อัปรูปที่ AI สร้างเข้า Canva แล้วเปิดแต่งต่อในเว็บ")
    img = st.session_state.get("canva_pending_image")
    if img:
        st.image(img, width=180, caption="รูปที่รอส่ง (จากหน้า Copilot)")
        if st.button("📤 อัปโหลดเข้า Canva", width="stretch"):
            with st.spinner("กำลังอัปโหลด..."):
                asset_id, msg = canva_client.upload_asset(
                    token, img, f"lemed_{dt.datetime.now():%Y%m%d_%H%M%S}.png")
            if asset_id:
                st.success(f"{msg} — เปิด Canva แล้วหาในแท็บ Uploads ได้เลย")
                st.markdown("[🔗 เปิด Canva](https://www.canva.com/)")
            else:
                st.error(msg)
    else:
        st.info("ยังไม่มีรูป — ไปหน้า 🗨️ แชท AI สร้างรูปแล้วกด **ส่งไป Canva**")


# ── Brain Storm (Business Model Canvas) ──────────────────────────────────────────

def _send_idea_to_copilot(prompt: str) -> None:
    """Hand an idea to the Chat Copilot and jump to that page."""
    st.session_state["copilot_pending"] = prompt
    st.session_state["shop_menu"] = "🗨️ แชท AI"


def render_brainstorm_page(ai_mode: str, api_key: str) -> None:
    st.title("🧠 Brain Storm")
    st.caption("อธิบายธุรกิจ → ร่าง Business Model Canvas → ได้ไอเดียคอนเทนต์ ส่งเข้า Copilot ได้เลย")

    if not BRAINSTORM_AVAILABLE:
        st.error("ไม่พบ brainstorm.py — ตรวจสอบไฟล์ในโฟลเดอร์โปรเจกต์")
        return

    _key, _provider, _label = _resolve_ai(ai_mode, api_key)
    st.caption(_label)
    _mandala_badge()
    brand_ctx = brainstorm.load_brand_context()

    desc = st.text_area(
        "ธุรกิจของคุณ",
        value=st.session_state.get("bs_desc", brainstorm.DEFAULT_BUSINESS),
        height=100,
        key="bs_desc",
        help="ยิ่งอธิบายละเอียด (สินค้า/กลุ่มเป้าหมาย/จุดขาย) ผลลัพธ์ยิ่งตรง",
    )

    gen_col, clr_col = st.columns([3, 1])
    with gen_col:
        if st.button("🧠 ร่าง Business Model Canvas", type="primary", width="stretch"):
            with st.spinner("กำลังร่าง BMC..."):
                st.session_state["bs_bmc"] = brainstorm.generate_bmc(
                    desc, _key, brand_ctx, _provider)
            st.session_state.pop("bs_ideas", None)
            st.rerun()
    with clr_col:
        if "bs_bmc" in st.session_state and st.button("🗑️ ล้าง", width="stretch"):
            st.session_state.pop("bs_bmc", None)
            st.session_state.pop("bs_ideas", None)
            st.rerun()

    bmc = st.session_state.get("bs_bmc")
    if not bmc:
        st.info("💡 กรอกข้อมูลธุรกิจแล้วกดปุ่มด้านบน เพื่อร่าง BMC 9 ช่อง")
        return

    st.divider()
    st.subheader("📋 Business Model Canvas")
    st.caption("แก้ไขได้ทุกช่อง — ไอเดียคอนเทนต์จะอิงจากที่แก้ล่าสุด")

    cols = st.columns(3)
    for i, (bkey, label, question) in enumerate(brainstorm.BMC_BLOCKS):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{label}**")
                st.caption(question)
                bmc[bkey] = st.text_area(
                    label, value=bmc.get(bkey, ""), height=110,
                    key=f"bs_block_{bkey}", label_visibility="collapsed",
                )
    st.session_state["bs_bmc"] = bmc

    st.divider()
    st.subheader("💡 ไอเดียคอนเทนต์")

    n_ideas = st.slider("จำนวนไอเดีย", 2, 6, 4, key="bs_n")
    if st.button("✨ เสนอไอเดียจาก BMC", width="stretch"):
        with st.spinner("กำลังคิดไอเดีย..."):
            st.session_state["bs_ideas"] = brainstorm.generate_ideas(
                bmc, desc, _key, n_ideas, brand_ctx, _provider)
        st.rerun()

    ideas = st.session_state.get("bs_ideas")
    if not ideas:
        st.info("กดปุ่มด้านบนเพื่อให้ AI เสนอไอเดียคอนเทนต์จาก BMC")
        return

    for idx, idea in enumerate(ideas):
        with st.container(border=True):
            st.markdown(f"**{idea['title']}**")
            if idea.get("rationale"):
                st.caption(idea["rationale"])
            plats = " · ".join(
                f"{PLATFORMS[p]['icon']} {PLATFORMS[p]['name']}"
                for p in idea["platforms"] if p in PLATFORMS
            )
            st.markdown(f"<span style='font-size:12.5px;opacity:.75'>{plats} — โทน {idea['tone']}</span>",
                        unsafe_allow_html=True)
            st.code(idea["prompt"], language=None)
            st.button(
                "🗨️ ส่งเข้า Copilot เพื่อร่างคอนเทนต์",
                key=f"bs_send_{idx}",
                width="stretch",
                on_click=_send_idea_to_copilot,
                args=(idea["prompt"],),
            )


# ── Chat Copilot ─────────────────────────────────────────────────────────────────

def _copilot_examples() -> list[str]:
    """Everyday phrasing, not marketing vocabulary.

    Examples double as instructions here — someone unsure what to type copies
    the shape of these. "Flash sale / โทนพรีเมียม" taught the wrong lesson: that
    you need the jargon to be understood.
    """
    return [
        "อยากได้คลิปลง TikTok",
        "ทำโปรลดราคาหน่อย",
        "โพสต์ให้คนที่เป็นสิวง่าย",
        "ขอบคุณลูกค้าเก่า",
    ]


def _copilot_send_to_queue(pid: str, content: str, brief: dict) -> None:
    """Write a pending draft into its per-platform Drive folder.

    Drive is the queue — the ✋ คิวอนุมัติ page reads straight from those folders,
    so there is no second list to keep in sync here.
    """
    if not GDRIVE_AVAILABLE or needs_auth():
        st.warning("ยังไม่ได้ต่อ Google Drive — ไปที่หน้า ✋ คิวอนุมัติ เพื่อ authorize ก่อน")
        return

    # Copilot drafts are captions/scripts. TikTok & YouTube live in VDO folders;
    # the rest go to their Post folder.
    is_video = pid in ("tiktok", "youtube")
    target_folder, routed = QUEUE_ROOT_FOLDER_ID, False
    try:
        from google_drive import resolve_platform_folder
        sub = resolve_platform_folder(QUEUE_ROOT_FOLDER_ID, pid, is_video)
        if sub:
            target_folder, routed = sub, True
    except Exception:  # noqa: BLE001 — routing is a nicety; the root still works
        pass

    fname = f"PENDING_{pid}_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    link = upload_text(content, fname, target_folder)
    if not link:
        st.error("ส่งเข้าคิวไม่สำเร็จ — ลองใหม่อีกครั้ง")
        return

    where = PLATFORM_THAI_NAMES.get(pid, pid) if routed else "โฟลเดอร์รวม"
    st.success(f"ส่งเข้าคิว → {where} แล้ว · ไปตรวจที่หน้า **✋ คิวอนุมัติ**")
    st.markdown(f"[🔗 เปิดไฟล์ใน Drive]({link})")


def _angle_picker(mi: int, scene: str, medium: str, label: str) -> str:
    """Let the user pick how the scene is told, for one medium.

    The list is medium-specific: an angle only appears where it has material, so
    "3 เหตุผล" is offered for a clip and a carousel but not for a single frame.
    """
    if not SCENES_AVAILABLE:
        return ""
    options = scene_presets.angles_for(scene, medium)
    chosen = st.radio(label, options=options,
                      format_func=scene_presets.angle_label, horizontal=True,
                      key=f"copilot_angle_{medium}_{mi}")
    st.caption(f"🎯 {scene_presets.angle_goal(chosen)}")
    return chosen


def _render_copilot_image(mi: int, brief: dict, scene: str,
                          gemini_key: str) -> bytes | None:
    """Image block: show the prompt, and let Gemini actually render it.

    Returns the generated image bytes (if any) so posting can attach them.
    """
    img_key = f"copilot_img_{mi}"
    with st.expander("🖼️ ภาพประกอบ — Master Prompt", expanded=bool(st.session_state.get(img_key))):
        angle = _angle_picker(mi, scene, "image", "🖼️ แบบของภาพ — เลือกได้หลายแบบในหมวดเดียวกัน")
        image_prompt = content_copilot.build_master_image_prompt(brief, scene, angle)
        st.caption("📋 คัดลอกไปวางใน Google Flow / Midjourney ได้เลย (กดไอคอนคัดลอกมุมขวาบน)")
        st.code(image_prompt, language=None)
        st.link_button("🎬 เปิด Google Flow แล้ววาง prompt นี้", FLOW_PROJECT_URL,
                       width="stretch")

        if gemini_key:
            if st.button("✨ สร้างรูปด้วย Gemini", key=f"copilot_genimg_{mi}",
                         width="stretch"):
                import ai_provider
                with st.spinner("กำลังสร้างรูป... (10-30 วินาที)"):
                    img_bytes, msg = ai_provider.generate_image(image_prompt, gemini_key)
                if img_bytes:
                    st.session_state[img_key] = img_bytes
                    st.toast(msg, icon="✅")
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.caption("💡 ใส่ **Gemini API key** ในแถบซ้าย แล้วจะสร้างรูปได้จากในแชทเลย")

        img = st.session_state.get(img_key)
        if img:
            st.image(img, caption="ภาพที่สร้างด้วย Gemini", width="stretch")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.download_button("📥 ดาวน์โหลด", data=img,
                                   file_name=f"lemed_{mi}.png", mime="image/png",
                                   key=f"copilot_dlimg_{mi}", width="stretch")
            with c2:
                if CANVA_AVAILABLE and st.button("🎨 ส่งไป Canva",
                                                 key=f"copilot_canva_{mi}",
                                                 width="stretch"):
                    st.session_state["canva_pending_image"] = img
                    st.session_state["shop_menu"] = "🎨 Canva"
                    st.rerun()
            with c3:
                if st.button("🗑️ ลบรูป", key=f"copilot_rmimg_{mi}", width="stretch"):
                    del st.session_state[img_key]
                    st.rerun()
        return img
    return None


def _render_copilot_video(mi: int, brief: dict, scene: str, aspect: str,
                          gemini_key: str) -> bytes | None:
    """Video block: prompt, cost estimate, generate with Veo, preview in chat."""
    import ai_provider

    vid_key = f"copilot_vid_{mi}"
    with st.expander("🎬 วิดีโอ — Master Prompt", expanded=bool(st.session_state.get(vid_key))):
        # The scene fixes where the clip is shot; the angle picks how it is told,
        # so the same scene yields several genuinely different videos.
        angle = _angle_picker(mi, scene, "video",
                              "🎞️ แนวการเล่าเรื่อง — เลือกได้หลายแบบในหมวดเดียวกัน")
        if SCENES_AVAILABLE and not scene_presets.has_people(scene):
            st.caption("📦 หมวดนี้ไม่มีคนในภาพ แนวที่ต้องมีตัวแสดง (รีวิว, สาธิต, "
                       "ก่อน-หลัง) จึงไม่ขึ้นให้เลือก")

        st.caption(f"📋 คัดลอกไปวางใน Google Flow ได้เลย · สัดส่วน {aspect} · "
                   "10 วินาที · Hook → Decision → CTA · เสียงพากย์ไทย")
        st.code(content_copilot.build_master_video_prompt(brief, scene, 10, angle),
                language=None)
        st.link_button("🎬 เปิด Google Flow แล้ววาง prompt นี้", FLOW_PROJECT_URL,
                       width="stretch")

        if gemini_key:
            st.info("ℹ️ Veo สร้างได้สูงสุด **8 วินาที** ต่อคลิป — ตัว Master Prompt ด้านบน "
                    "เป็นเวอร์ชัน 10 วินาทีสำหรับ Google Flow (ต่อคลิปได้)")
            c1, c2 = st.columns(2)
            with c1:
                tier = st.selectbox(
                    "คุณภาพ", options=["fast", "standard"],
                    format_func=lambda t: {"fast": "⚡ Fast (ถูกกว่า)",
                                           "standard": "💎 Standard (คมกว่า)"}[t],
                    key=f"copilot_vtier_{mi}",
                )
            with c2:
                secs = st.selectbox("ความยาว", options=[4, 6, 8], index=2,
                                    format_func=lambda s: f"{s} วินาที",
                                    key=f"copilot_vsec_{mi}")

            cost = ai_provider.estimate_video_cost(secs, tier)
            st.warning(f"💰 คลิปนี้มีค่าใช้จ่ายประมาณ **${cost:.2f}** "
                       f"({secs} วิ · {tier}) — คิดเงินเฉพาะตอนสร้างสำเร็จ")

            if st.button("🎬 สร้างวิดีโอด้วย Veo", key=f"copilot_genvid_{mi}",
                         width="stretch"):
                status = st.empty()
                with st.spinner("กำลังสร้างวิดีโอ... (ปกติ 1-3 นาที อย่าปิดหน้านี้)"):
                    vid, msg = ai_provider.generate_video(
                        content_copilot.build_master_video_prompt(brief, scene, secs, angle),
                        gemini_key, tier=tier, seconds=secs,
                        aspect_ratio=aspect, on_progress=status.info,
                    )
                status.empty()
                if vid:
                    st.session_state[vid_key] = vid
                    st.toast(msg, icon="✅")
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.caption("💡 ใส่ **Gemini API key** ในแถบซ้าย แล้วจะสร้างวิดีโอได้จากในแชท")

        vid = st.session_state.get(vid_key)
        if vid:
            st.video(vid)
            st.caption(f"ขนาดไฟล์ {len(vid)/1024/1024:.1f} MB")
            d1, d2 = st.columns(2)
            with d1:
                st.download_button("📥 ดาวน์โหลดวิดีโอ", data=vid,
                                   file_name=f"lemed_{mi}.mp4", mime="video/mp4",
                                   key=f"copilot_dlvid_{mi}", width="stretch")
            with d2:
                if st.button("🗑️ ลบวิดีโอ", key=f"copilot_rmvid_{mi}",
                             width="stretch"):
                    del st.session_state[vid_key]
                    st.rerun()
        return vid
    return None


def _render_copilot_carousel(mi: int, brief: dict, scene: str, gemini_key: str) -> None:
    """Poster carousel: per-slide Thai copy + master prompt, optional batch render."""
    key_all = f"copilot_car_{mi}"

    with st.expander("🖼️ โปสเตอร์ Carousel (5 สไลด์) — Master Prompt"):
        angle = _angle_picker(mi, scene, "carousel",
                              "📑 โครงเรื่องของชุดสไลด์ — เลือกได้หลายแบบในหมวดเดียวกัน")
        slides = content_copilot.build_carousel(brief, scene, 5, angle)
        # Name the arc from the slides themselves, so a different angle does not
        # keep advertising the default Hook → ปัญหา → ทางออก shape.
        st.caption("เล่าเรื่องต่อกันเป็นชุด: "
                   + " → ".join(s["label"].split(" ", 1)[-1] for s in slides)
                   + " · สัดส่วน 4:5")

        if gemini_key:
            if st.button(f"✨ สร้างรูปทั้ง {len(slides)} สไลด์ด้วย Gemini",
                         key=f"copilot_genall_{mi}", width="stretch"):
                import ai_provider
                imgs, prog = {}, st.progress(0.0, text="เริ่มสร้าง...")
                for idx, s in enumerate(slides):
                    prog.progress(idx / len(slides),
                                  text=f"สไลด์ {s['n']}/{len(slides)} — {s['label']}")
                    img, msg = ai_provider.generate_image(s["prompt"], gemini_key)
                    if img:
                        imgs[s["n"]] = img
                    else:
                        st.warning(f"สไลด์ {s['n']}: {msg}")
                prog.progress(1.0, text="เสร็จแล้ว")
                st.session_state[key_all] = imgs
                st.rerun()
        else:
            st.caption("💡 ใส่ Gemini API key เพื่อสร้างรูปทุกสไลด์รวดเดียว")

        # Tabs, not a popover per slide. Each prompt is 32 lines, which rendered a
        # ~500px floating panel anchored to a button already near the bottom of an
        # open expander — it opened below the fold, moved with the page as you
        # scrolled after it, and left its own close target off screen. Tabs put the
        # same content in the page flow, where there is nothing to chase or close.
        made = st.session_state.get(key_all, {})
        for tab, s in zip(st.tabs([f"{s['n']}. {s['label']}" for s in slides]), slides):
            with tab:
                st.caption(s["purpose"])
                st.markdown(f"> **{s['headline_th']}**  \n> {s['sub_th']}")
                img = made.get(s["n"])
                if img:
                    st.image(img, width="stretch")
                    st.download_button(
                        f"📥 ดาวน์โหลดสไลด์ {s['n']}", data=img,
                        file_name=f"carousel_{mi}_{s['n']}.png", mime="image/png",
                        key=f"copilot_cardl_{mi}_{s['n']}", width="stretch")
                st.code(s["prompt"], language=None)
                st.link_button("🎬 เปิด Google Flow แล้ววาง prompt นี้",
                               FLOW_PROJECT_URL, width="stretch")


def _render_copilot_draft(mi: int, brief: dict, package: dict,
                          line_token: str, fb_token: str, fb_page_id: str,
                          ig_business_id: str, gemini_key: str = "") -> None:
    """Render one assistant draft: summary + editable content + approve/queue."""
    campaign_label = CAMPAIGN_TYPES.get(brief.get("campaign", ""), {}).get(
        "label", brief.get("campaign", "")
    )
    summary = brief.get("summary") or content_copilot.describe(brief)
    st.markdown(f"ร่างให้แล้วค่ะ ✨ — **{campaign_label}**")
    if summary:
        st.caption(summary)

    plats = [p for p in brief.get("platforms", []) if p in package and p in PLATFORMS]
    if not plats:
        st.warning("ยังไม่มีแพลตฟอร์มที่ร่างได้ — ลองพิมพ์ระบุแพลตฟอร์มเพิ่มดูนะ (เช่น IG, LINE)")
        return

    # Scene picker — one choice drives both the image and video master prompts so
    # a campaign's stills and clip stay visually consistent.
    scene = scene_presets.DEFAULT_SCENE
    if SCENES_AVAILABLE:
        # Order by how well each angle fits this brand's own material, so the
        # most relevant scenes are the ones read first.
        scores = _scene_scores()
        choices = scene_presets.scene_choices()
        if scores:
            choices = sorted(choices, key=lambda k: (-scores[k], scene_presets.label_for(k)))
            default_index = 0
        else:
            default_index = (choices.index(scene_presets.DEFAULT_SCENE)
                             if scene_presets.DEFAULT_SCENE in choices else 0)

        def _scene_label(k: str) -> str:
            n = scores.get(k, 0)
            stars = f"{'★' * n}{'·' * (5 - n)} " if n else ""
            return f"{stars}{scene_presets.label_for(k)}"

        sc_col, sc_info = st.columns([2, 1])
        with sc_col:
            scene = st.selectbox(
                "🎯 หมวด / ฉากของภาพและวิดีโอ",
                options=choices,
                index=default_index,
                format_func=_scene_label,
                key=f"copilot_scene_{mi}",
            )
        with sc_info:
            st.caption(scene_presets.group_for(scene))
            if scene_presets.has_people(scene):
                st.caption("👤 มีคนในภาพ")

        goal = scene_presets.goal_for(scene)
        if goal:
            st.info(f"**เป้าหมายของหมวดนี้:** {goal}")
        if scores.get(scene):
            st.caption(
                f"{'★' * scores[scene]}{'·' * (5 - scores[scene])} "
                "ความเข้ากับแบรนด์ — วัดจากที่บริบทและคอนเทนต์เดิมใน Mandala AI "
                "พูดถึงมุมนี้บ่อยแค่ไหน (ไม่ใช่การทำนายยอด engagement)"
            )

    img_bytes = _render_copilot_image(mi, brief, scene, gemini_key)

    _render_copilot_carousel(mi, brief, scene, gemini_key)

    vid_bytes = _render_copilot_video(
        mi, brief, scene, content_copilot.video_aspect_for(brief), gemini_key)

    if img_bytes or vid_bytes:
        attached = " + ".join(x for x in [
            "รูป" if img_bytes else "", "วิดีโอ" if vid_bytes else ""] if x)
        st.caption(f"✅ {attached} จะถูกแนบไปกับโพสต์อัตโนมัติ")

    tabs = st.tabs([f"{PLATFORMS[p]['icon']} {PLATFORMS[p]['name']}" for p in plats])
    for tab, pid in zip(tabs, plats):
        with tab:
            edited = st.text_area(
                "คอนเทนต์",
                value=package.get(pid, ""),
                height=180,
                key=f"copilot_text_{mi}_{pid}",
                label_visibility="collapsed",
            )
            act1, act2 = st.columns(2)
            with act1:
                if st.button("✅ อนุมัติ + โพสต์", key=f"copilot_post_{mi}_{pid}",
                             type="primary", width="stretch"):
                    _do_post(pid, edited, line_token, fb_token, fb_page_id,
                             ig_business_id=ig_business_id,
                             image_bytes=img_bytes,
                             image_name=f"lemed_{mi}.png",
                             video_bytes=vid_bytes,
                             video_name=f"lemed_{mi}.mp4")
            with act2:
                if st.button("📁 ส่งเข้าคิว (Drive)", key=f"copilot_queue_{mi}_{pid}",
                             width="stretch"):
                    _copilot_send_to_queue(pid, edited, brief)

    if st.button("🚀 อนุมัติ + โพสต์ทั้งหมด", key=f"copilot_postall_{mi}",
                 width="stretch"):
        for pid in plats:
            content_i = st.session_state.get(f"copilot_text_{mi}_{pid}") or package.get(pid, "")
            _do_post(pid, content_i, line_token, fb_token, fb_page_id,
                     ig_business_id=ig_business_id, quiet=True,
                     image_bytes=img_bytes, image_name=f"lemed_{mi}.png",
                     video_bytes=vid_bytes, video_name=f"lemed_{mi}.mp4")
        st.success("ส่งคำสั่งโพสต์ครบทุกแพลตฟอร์มแล้ว — ดูผลได้ที่ toast มุมขวาบน")


def render_copilot_page(ai_mode: str, api_key: str, line_token: str = "",
                        fb_token: str = "", fb_page_id: str = "",
                        ig_business_id: str = "") -> None:
    st.title("🗨️ แชท AI")
    st.caption("พิมพ์บอกว่าอยากได้คอนเทนต์อะไร — AI คิดแคปชัน ภาพ และคลิปให้")

    # Someone opening this for the first time should not have to guess what
    # happens after they type. Three steps, stated once, at the top.
    st.markdown(
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin:-4px 0 14px">'
        '<span style="background:rgba(45,212,191,.12);border:1px solid rgba(45,212,191,.35);'
        'border-radius:999px;padding:5px 13px;font-size:13px">1️⃣ พิมพ์บอกสิ่งที่อยากได้</span>'
        '<span style="background:rgba(45,212,191,.12);border:1px solid rgba(45,212,191,.35);'
        'border-radius:999px;padding:5px 13px;font-size:13px">2️⃣ AI ร่างแคปชัน + prompt ภาพ/คลิป</span>'
        '<span style="background:rgba(45,212,191,.12);border:1px solid rgba(45,212,191,.35);'
        'border-radius:999px;padding:5px 13px;font-size:13px">3️⃣ กดอนุมัติ แล้วโพสต์</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not COPILOT_AVAILABLE:
        st.error("ไม่พบ content_copilot.py — ตรวจสอบไฟล์ในโฟลเดอร์โปรเจกต์")
        return

    _key, _provider, _label = _resolve_ai(ai_mode, api_key)
    can_image = _provider == "gemini"

    head_l, head_r = st.columns([3, 1])
    with head_r:
        st.caption(_label + (" · สร้างรูปได้" if can_image else ""))
    _mandala_badge()
    with st.expander("⚙️ ตั้งค่าแบรนด์เริ่มต้น (ไม่บังคับ)"):
        st.text_input("ชื่อแบรนด์", value="LEMED", key="copilot_brand")
        # Show what the brief locks the catalogue to, so a request naming
        # something else doesn't look like it was silently ignored.
        known = content_copilot.product_from_context(content_copilot.load_brand_context())
        if known:
            st.success(f"🔒 สินค้าของแบรนด์: **{known}** — คอนเทนต์จะอ้างถึงสินค้านี้เสมอ "
                       "(อ่านจากบริบทแบรนด์ ไม่ใช่เดาจากคำที่พิมพ์)")
        st.selectbox(
            "ประเภทธุรกิจ",
            options=["auto", "product", "fnb"],
            format_func=lambda v: {
                "auto": "🔎 ตรวจอัตโนมัติจากคำสั่ง + บริบทแบรนด์",
                "product": "🧴 สินค้า / สกินแคร์ / ความงาม",
                "fnb": "🍜 ร้านอาหาร / คาเฟ่",
            }[v],
            key="copilot_vertical",
            help="กำหนดโทนคอนเทนต์ — ตั้งไว้ถ้าคำสั่งสั้นจนระบบเดาผิด",
        )

    msgs = st.session_state.setdefault("copilot_msgs", [])

    if not msgs:
        with st.chat_message("assistant", avatar="🧴"):
            st.markdown(
                "สวัสดีค่ะ! อยากได้คอนเทนต์อะไรดีคะ 😊\n\n"
                "พิมพ์บอกแบบพูดคุยได้เลย ไม่ต้องรู้ศัพท์เทคนิค เช่น "
                "*“อยากได้คลิปลง TikTok”* หรือ *“ทำโปรลดราคาหน่อย”*\n\n"
                "**หรือกดตัวอย่างด้านล่างนี้ได้เลย** 👇"
            )
            ex_cols = st.columns(2)
            for i, ex in enumerate(_copilot_examples()):
                with ex_cols[i % 2]:
                    if st.button(ex, key=f"copilot_ex_{i}", width="stretch"):
                        st.session_state["copilot_pending"] = ex
                        st.rerun()

    for mi, m in enumerate(msgs):
        if m["role"] == "user":
            with st.chat_message("user"):
                st.markdown(m["text"])
        else:
            with st.chat_message("assistant", avatar="🧴"):
                if m.get("error"):
                    st.error(f"ร่างไม่สำเร็จ: {m['error']}")
                else:
                    _render_copilot_draft(mi, m["brief"], m["package"],
                                          line_token, fb_token, fb_page_id, ig_business_id,
                                          gemini_key=_key if can_image else "")

    pending = st.session_state.pop("copilot_pending", None)
    typed = st.chat_input("พิมพ์บอกสิ่งที่อยากได้…")
    if typed:
        pending = typed

    if pending:
        msgs.append({"role": "user", "text": pending})
        with st.spinner("กำลังร่างให้..."):
            try:
                brief, package = content_copilot.generate(
                    pending, _key, st.session_state.get("copilot_brand", "LEMED"),
                    provider=_provider,
                    vertical=st.session_state.get("copilot_vertical", "auto"),
                )
                msgs.append({"role": "assistant", "brief": brief, "package": package})
            except Exception as e:  # noqa: BLE001 — surface any failure in-chat
                msgs.append({"role": "assistant", "error": str(e)})
        st.rerun()

    if msgs and st.button("🗑️ เริ่มแชทใหม่", key="copilot_clear"):
        st.session_state["copilot_msgs"] = []
        st.rerun()


# ── AI Chat Inbox ───────────────────────────────────────────────────────────────

def render_ai_inbox_page(ai_mode: str, api_key: str, fb_token: str = "",
                         fb_page_id: str = "", line_token: str = "") -> None:
    st.title("💬 AI Chat Inbox")
    st.caption("อ่านแชทลูกค้าจาก Facebook Messenger / Instagram DM แล้วให้ AI ช่วยตอบ")

    if not CHAT_INBOX_AVAILABLE:
        st.error("ไม่พบ chat_inbox.py")
        return

    with st.expander("📖 ต้องเปิดสิทธิ์อะไรเพิ่ม (ครั้งแรกครั้งเดียว)"):
        st.markdown("""
##### Facebook Messenger / Instagram DM

**1.** เปิด [Graph API Explorer](https://developers.facebook.com/tools/explorer)

**2.** เพิ่ม permissions:
- `pages_messaging` (อ่าน+ตอบแชท Messenger)
- `instagram_manage_messages` (อ่าน+ตอบ IG DM)

**3.** เลือก "ผู้ใช้หรือเพจ" เป็นเพจของคุณ → กด `Generate Access Token`

**4.** Copy token ใหม่มาวางในช่อง Facebook Page Token (แถบซ้าย)

---

##### LINE OA

LINE ไม่ให้ดึงแชทย้อนหลังผ่าน API — ต้องใช้ **webhook bot**
ดูวิธีตั้งค่าที่หัวข้อ 💚 LINE Auto-Reply Bot ด้านล่างสุด
""")

    # ── Shop profile (AI knowledge) ────────────────────────────────────────────
    st.subheader("🏪 ข้อมูลร้าน (สมองของ AI)")
    prof = st.session_state.setdefault("shop_profile", dict(DEFAULT_PROFILE))
    c1, c2 = st.columns(2)
    with c1:
        prof["shop_name"] = st.text_input("ชื่อร้าน", prof["shop_name"])
        prof["hours"] = st.text_input("เวลาเปิด-ปิด", prof["hours"])
        prof["address"] = st.text_input("ที่อยู่ / การเดินทาง", prof["address"])
    with c2:
        prof["menu"] = st.text_input("เมนูแนะนำ + ราคา", prof["menu"])
        prof["promo"] = st.text_input("โปรโมชันตอนนี้", prof["promo"])
        prof["booking"] = st.text_input("นโยบายจองโต๊ะ", prof["booking"])

    _ai_key = api_key.strip() if (ai_mode == "Claude API" and api_key.strip()) else ""
    st.caption(f"โหมด AI: {'🤖 Claude API (ฉลาด เข้าใจบริบท)' if _ai_key else '⚡ Rule-based (ตอบตามคีย์เวิร์ด — ใส่ Claude API key เพื่ออัปเกรด)'}")

    st.divider()

    # ── Inbox ──────────────────────────────────────────────────────────────────
    plat = st.radio("แพลตฟอร์ม", ["🔵 Facebook Messenger", "🟣 Instagram DM"], horizontal=True)
    platform_key = "messenger" if "Facebook" in plat else "instagram"

    if not fb_token or not fb_page_id:
        st.warning("ใส่ Facebook Page Token + Page ID ในแถบซ้ายก่อน")
        return

    if st.button("🔄 ดึงแชทล่าสุด", type="primary"):
        with st.spinner("กำลังดึงแชท..."):
            convs, msg = fetch_conversations(fb_token, fb_page_id, platform=platform_key)
        if convs is None:
            st.error(msg)
            st.info("ถ้าเจอ error เรื่อง permission — เปิด expander ด้านบนแล้วทำตามขั้นตอนเพิ่มสิทธิ์")
            return
        st.session_state["inbox_convs"] = convs

    convs = st.session_state.get("inbox_convs", [])
    if not convs:
        st.info("กด '🔄 ดึงแชทล่าสุด' เพื่อเริ่ม")
    else:
        waiting = [cv for cv in convs if cv["messages"] and cv["messages"][-1]["from_customer"]]
        st.caption(f"พบ {len(convs)} บทสนทนา — 🔴 รอตอบ {len(waiting)} แชท")

        # ── Auto-reply batch ───────────────────────────────────────────────────
        replied: set = st.session_state.setdefault("auto_replied_ids", set())
        pending = [cv for cv in waiting if cv["messages"][-1]["id"] not in replied]
        if pending:
            if st.button(f"⚡ ให้ AI ตอบ {len(pending)} แชทที่รอ — อัตโนมัติทั้งหมด",
                         type="primary", width="stretch"):
                prog = st.progress(0.0)
                done = 0
                for j, cv in enumerate(pending):
                    reply = generate_ai_reply(cv["messages"], prof, _ai_key)
                    ok, m = send_message(fb_token, fb_page_id, cv["customer_id"], reply)
                    if ok:
                        replied.add(cv["messages"][-1]["id"])
                        done += 1
                    prog.progress((j + 1) / len(pending),
                                  text=f"{cv['customer_name']}: {'✅' if ok else '❌ ' + m}")
                st.success(f"🤖 AI ตอบไปแล้ว {done}/{len(pending)} แชท")

        # ── Conversation list ──────────────────────────────────────────────────
        for i, cv in enumerate(convs):
            is_waiting = cv["messages"] and cv["messages"][-1]["from_customer"]
            badge = "🔴 รอตอบ" if is_waiting else "🟢 ตอบแล้ว"
            with st.expander(f"{badge} — {cv['customer_name']} ({cv['updated'][:16]})",
                             expanded=bool(is_waiting and i < 2)):
                for m in cv["messages"]:
                    if not m["text"]:
                        continue
                    who = "🧑 ลูกค้า" if m["from_customer"] else "🏪 ร้าน"
                    st.markdown(f"**{who}:** {m['text']}")
                st.divider()
                draft_key = f"draft_{cv['conversation_id']}"
                if st.button("🤖 ให้ AI ร่างคำตอบ", key=f"ai_{i}"):
                    with st.spinner("AI กำลังคิด..."):
                        st.session_state[draft_key] = generate_ai_reply(cv["messages"], prof, _ai_key)
                reply_text = st.text_area("คำตอบ", value=st.session_state.get(draft_key, ""),
                                          key=f"txt_{i}", height=100)
                if st.button("📨 ส่งตอบ", key=f"send_{i}", type="primary"):
                    ok, m = send_message(fb_token, fb_page_id, cv["customer_id"], reply_text)
                    (st.success if ok else st.error)(m)

    # ── LINE bot guide ─────────────────────────────────────────────────────────
    st.divider()
    with st.expander("💚 LINE OA Auto-Reply Bot — วิธีตั้งค่า"):
        st.markdown("""
LINE ตอบอัตโนมัติต้องใช้ webhook bot (ไฟล์ `line_ai_bot.py` ในโปรเจกต์นี้ พร้อมใช้แล้ว)

**รันบนเครื่องตัวเอง:**
```bash
pip install fastapi uvicorn
export LINE_CHANNEL_SECRET="จาก LINE Developers → Basic settings"
export LINE_CHANNEL_ACCESS_TOKEN="token ตัวเดียวกับที่ใช้โพสต์"
export ANTHROPIC_API_KEY="sk-ant-..."   # ไม่ใส่ = rule-based
uvicorn line_ai_bot:app --port 8001
```

**เปิด tunnel ให้ LINE เรียกถึง:**
```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8001
```

**ตั้งค่าใน [LINE Developers Console](https://developers.line.biz/console/):**
1. Messaging API → Webhook URL = `https://<tunnel-url>/webhook`
2. เปิด **Use webhook**
3. ปิด **Auto-reply messages** (ของ LINE เดิม) เพื่อให้ bot ตอบแทน

ทดสอบ: ทักแชทหา OA → AI ตอบกลับทันที 🤖
""")


# ── Sidebar ─────────────────────────────────────────────────────────────────────

with st.sidebar:
    _txt_logo = "#F9FAFB" if _theme == "dark" else "#111827"
    _txt_ver  = "#374151" if _theme == "dark" else "#9CA3AF"
    st.markdown(f"""
<div style="padding:0.75rem 0 1.5rem 0;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:5px;">
    <div style="width:34px;height:34px;background:linear-gradient(135deg,#B45309,#F59E0B);border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;box-shadow:0 4px 14px rgba(245,158,11,0.28);">📊</div>
    <div>
      <div style="font-weight:800;font-size:17px;color:{_txt_logo};letter-spacing:0.02em;line-height:1.2;">REVENUE <span style="color:#F59E0B;">AI</span></div>
    </div>
  </div>
  <div style="font-size:10px;color:{_txt_ver};font-weight:600;letter-spacing:0.12em;text-transform:uppercase;padding-left:44px;">Smart Business Suite</div>
</div>
""", unsafe_allow_html=True)

    # ── Mode switch — MUST be the first sidebar widget. The theme toggle below
    #    calls st.rerun(), which aborts the run before any widget under it is
    #    instantiated; if the keyed mode radio hasn't rendered yet, Streamlit
    #    drops `app_mode` and the app falls back to shop mode. Rendering it
    #    first keeps the selected mode sticky across theme changes. ───────────
    mode = st.radio(
        "โหมดการใช้งาน",
        [MODE_SHOP, MODE_AFFILIATE],
        label_visibility="collapsed",
        key="app_mode",
    )
    st.divider()

    # ── Theme toggle — use on_click callbacks, NOT `if st.button(): st.rerun()`.
    #    A mid-run st.rerun() aborts before the menu widgets below are rendered,
    #    so Streamlit drops their keyed state and the app jumps back to the first
    #    page/mode. A callback sets the theme before the natural rerun, keeping
    #    the current mode + page sticky across theme changes. ──────────────────
    def _set_theme(t: str) -> None:
        st.session_state["theme"] = t

    tc1, tc2 = st.columns(2)
    with tc1:
        st.button(
            "🌙 Dark" if _theme == "light" else "✓ Dark",
            width="stretch",
            type="secondary" if _theme == "light" else "primary",
            on_click=_set_theme, args=("dark",),
        )
    with tc2:
        st.button(
            "✓ Light" if _theme == "light" else "☀️ Light",
            width="stretch",
            type="primary" if _theme == "light" else "secondary",
            on_click=_set_theme, args=("light",),
        )

    st.divider()

    if mode == MODE_AFFILIATE:
        page = st.radio(
            "เมนูแอฟฟิลิเอต",
            affiliate_ui.PAGES if AFFILIATE_AVAILABLE else ["📈 ภาพรวม"],
            label_visibility="collapsed",
            key="aff_menu",
        )
        st.divider()
        if AFFILIATE_AVAILABLE:
            affiliate_ui.sidebar_controls()
    else:
        # Customers open this to do one thing: chat, and get something to post.
        # Ten equal-weight menu items made that choice look like ten choices, and
        # the app opened on a dashboard of sample sales data that has nothing to
        # do with it. The daily path is now the only thing on screen by default.
        DAILY_PAGES = ["🗨️ แชท AI", "✋ คิวอนุมัติ"]
        MORE_PAGES = [
            "🧠 Brain Storm", "🎨 Canva", "📣 Content Studio", "💬 AI Inbox",
            "📊 Dashboard", "📁 Upload Data", "🔌 Connect POS", "🧮 ROI Calculator",
        ]
        show_all = st.toggle("🧰 เครื่องมือทั้งหมด", value=False,
                             help="เปิดเพื่อใช้เครื่องมือขั้นสูง — งานประจำวันใช้แค่ 2 เมนูบน")
        page = st.radio(
            "เมนู",
            DAILY_PAGES + (MORE_PAGES if show_all else []),
            label_visibility="collapsed",
            key="shop_menu",
        )

    demo_profile = "General Business"
    lv_token = ""
    lv_days = 30

    if page == "📊 Dashboard":
        st.divider()
        st.markdown("**Demo Profile**")
        demo_profile = st.radio(
            "demo",
            ["General Business", "ร้านหมูกระทะ", "ร้านเย็นตาโฟ (ข้อมูลจริง)"],
            label_visibility="collapsed",
        )
    elif page == "🔌 Connect POS":
        st.divider()
        st.markdown("**Loyverse POS**")
        lv_token = st.text_input("API Token", type="password", placeholder="ใส่ token จาก Loyverse Back Office")
        lv_days = st.slider("ดึงข้อมูลย้อนหลัง (วัน)", 7, 90, 30)

    # Defaults so affiliate mode never references undefined shop variables
    ai_mode = "Local Smart"
    api_key = ""
    line_token = fb_token = fb_page_id = ig_business_id = ""

    if mode == MODE_SHOP:
        st.divider()
        st.markdown("**🔗 ทางลัด**")
        st.link_button("🎬 เปิด Google Flow", FLOW_PROJECT_URL, width="stretch")
        st.link_button("📁 เปิดโฟลเดอร์ Drive", DRIVE_FOLDER_URL, width="stretch")

        st.divider()
        st.markdown("**⚙️ Settings**")

        ai_mode = st.radio(
            "AI Insights Mode",
            ["Local Smart", "Gemini API", "Claude API"],
            help="Local Smart ใช้ rule-based logic ทำงานได้ทันที | "
                 "Gemini สร้างรูปได้ด้วย | Claude เน้นคุณภาพงานเขียน",
        )

        api_key = ""
        if ai_mode == "Gemini API":
            api_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")
            if api_key:
                st.success("พร้อมใช้ Gemini — สร้างข้อความ + รูปได้")
            else:
                st.caption("ขอฟรีที่ [aistudio.google.com/apikey](https://aistudio.google.com/apikey)")
        elif ai_mode == "Claude API":
            if not ANTHROPIC_AVAILABLE:
                st.warning("ติดตั้ง anthropic ก่อน:\n`pip install anthropic`")
            api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
            if api_key:
                st.success("พร้อมใช้ Claude API")

        st.divider()
        st.markdown("**📱 Platform Tokens**")
        st.caption("ใส่ token เพื่อโพสต์จริง")

        # ── LINE OA ──────────────────────────────────────────────────────────────
        line_token = st.text_input(
            "LINE OA Token",
            type="password",
            placeholder="Channel Access Token",
            help="จาก LINE Developers → Messaging API → Channel Access Token",
        )
        if line_token:
            st.success("LINE OA พร้อมโพสต์")

        with st.expander("📖 วิธีขอ LINE OA Token"):
            st.markdown("""
##### ขั้นตอน

**1.** เปิดเว็บ [developers.line.biz](https://developers.line.biz)

**2.** Login ด้วย LINE account

**3.** กดปุ่ม `Create a new provider` (ทำครั้งแรกครั้งเดียว)

**4.** กดปุ่ม `Create a new channel`

**5.** เลือกประเภท `Messaging API`

**6.** กรอกข้อมูล Channel ให้ครบ แล้วกด Create

**7.** เปิด tab `Messaging API`

**8.** เลื่อนลงล่างสุดหา `Channel access token`

**9.** กดปุ่ม `Issue` เพื่อสร้าง token

**10.** Copy token มาวางในช่อง LINE OA Token ด้านบน

---

⚠️ ต้องมี LINE Official Account ก่อน

สมัครฟรีที่ [account.line.biz](https://account.line.biz)
""")

        # ── Facebook ─────────────────────────────────────────────────────────────
        fb_token = st.text_input(
            "Facebook Page Token",
            type="password",
            placeholder="Page Access Token",
            help="จาก Meta Developer → Graph API → Page Token",
        )
        fb_page_id = ""
        ig_business_id = ""
        if fb_token:
            fb_page_id = st.text_input("Facebook Page ID", placeholder="เช่น 123456789")
            if fb_page_id:
                st.success("Facebook พร้อมโพสต์")
            ig_business_id = st.text_input(
                "Instagram Business Account ID",
                placeholder="เช่น 17841...",
                help="ID ของ IG Business Account ที่ผูกกับ Facebook Page (ใช้ FB Token เดียวกัน)",
            )
            if ig_business_id:
                st.success("Instagram พร้อมโพสต์")

        with st.expander("📖 วิธีหา IG Business ID"):
            st.markdown("""
##### ขั้นตอน (ใช้ FB Token เดิม)

**1.** ต้องเชื่อม Instagram กับ Facebook Page ก่อน

**2.** เปิด [Graph API Explorer](https://developers.facebook.com/tools/explorer)

**3.** Method: `GET`

**4.** URL: `{PAGE_ID}?fields=instagram_business_account` (แทน PAGE_ID ด้วย Facebook Page ID)

**5.** กด **ส่ง**

**6.** Response จะมี:
```
"instagram_business_account": {
  "id": "17841xxxxxxxxx"   ← copy เลขนี้
}
```

**7.** วางในช่อง Instagram Business Account ID

---

⚠️ Instagram ต้องเป็น Business/Creator Account
""")

        # ── TikTok ───────────────────────────────────────────────────────────────
        if TIKTOK_AVAILABLE:
            st.text_input(
                "TikTok Access Token",
                type="password",
                placeholder="act....",
                key="tiktok_token",
                help="ต้องมี scope video.publish — token อายุสั้น (~24 ชม.)",
            )
            if st.session_state.get("tiktok_token"):
                st.selectbox(
                    "การมองเห็นโพสต์ TikTok",
                    options=list(tiktok_poster.PRIVACY_LEVELS.keys()),
                    format_func=lambda v: tiktok_poster.PRIVACY_LEVELS[v],
                    key="tiktok_privacy",
                )
                if st.button("ทดสอบ TikTok", width="stretch"):
                    info, m = tiktok_poster.creator_info(st.session_state["tiktok_token"])
                    (st.success if info else st.error)(m)
                    if info and info.get("creator_nickname"):
                        st.caption(f"บัญชี: {info['creator_nickname']}")
            with st.expander("⚠️ ข้อจำกัด TikTok API"):
                st.markdown(tiktok_poster.describe_limits())
                st.caption("ขอ token ที่ [developers.tiktok.com](https://developers.tiktok.com/)")

        with st.expander("📖 วิธีขอ Facebook Page Token"):
            st.markdown("""
##### ขั้นตอน

**1.** เปิดเว็บ [developers.facebook.com](https://developers.facebook.com)

**2.** Login ด้วย Facebook account

**3.** ที่เมนูบน คลิก `My Apps`

**4.** กดปุ่ม `Create App`

**5.** เลือกประเภท `Business` แล้วกรอกชื่อ app

**6.** ไปที่เมนู `Tools` แล้วเลือก `Graph API Explorer`

**7.** ที่แถบขวา เลือก App ที่เพิ่งสร้าง

**8.** คลิก `Generate Access Token`

**9.** เลือก Facebook Page ที่ต้องการโพสต์

**10.** ติ๊ก permissions ทั้ง 2 ตัว:
- `pages_manage_posts`
- `pages_read_engagement`

**11.** กดปุ่ม `Generate Token` แล้ว Copy token

---

##### วิธีหา Page ID

**1.** เปิด Facebook Page ของคุณ

**2.** คลิกที่แถบ `About`

**3.** เลื่อนลงล่างสุด จะเห็น `Page ID`

---

⚠️ ต้องเป็น Admin ของ Facebook Page
""")

        st.divider()
        if st.button("🔌 เช็คการเชื่อมต่อทั้งหมด", width="stretch"):
            from platform_poster import test_line_token, test_facebook_token, test_instagram_account
            with st.spinner("กำลังเช็ค..."):
                if line_token:
                    ok, m = test_line_token(line_token)
                    (st.success if ok else st.error)(m)
                else:
                    st.caption("➖ LINE OA: ยังไม่ใส่ token")
                if fb_token and fb_page_id:
                    ok, m = test_facebook_token(fb_token, fb_page_id)
                    (st.success if ok else st.error)(m)
                else:
                    st.caption("➖ Facebook: ยังไม่ใส่ token/Page ID")
                if fb_token and ig_business_id:
                    ok, m = test_instagram_account(ig_business_id, fb_token)
                    (st.success if ok else st.error)(m)
                else:
                    st.caption("➖ Instagram: ยังไม่ใส่ IG ID")
                if GDRIVE_AVAILABLE and not needs_auth():
                    st.success("Google Drive + YouTube: พร้อม")
                else:
                    st.error("Google Drive: ยังไม่ได้ authorize")

        st.divider()
        st.caption("Built with Streamlit + Claude AI")


# ── Affiliate mode routing ───────────────────────────────────────────────────────

if mode == MODE_AFFILIATE:
    if AFFILIATE_AVAILABLE:
        affiliate_ui.render(page)
    else:
        st.error("โหลดโมดูลแอฟฟิลิเอตไม่ได้ (affiliate_ui.py) — ตรวจสอบไฟล์")
    st.stop()


# ── Page routing (shop owner mode) ───────────────────────────────────────────────

if page == "📁 Upload Data":
    render_csv_upload_page(ai_mode, api_key)
    st.stop()

if page == "🔌 Connect POS":
    render_connect_pos_page(lv_token, lv_days, ai_mode, api_key)
    st.stop()

if page == "🧠 Brain Storm":
    render_brainstorm_page(ai_mode, api_key)
    st.stop()

if page == "🗨️ แชท AI":
    render_copilot_page(ai_mode, api_key, line_token=line_token, fb_token=fb_token, fb_page_id=fb_page_id, ig_business_id=ig_business_id)
    st.stop()

if page == "🎨 Canva":
    render_canva_page()
    st.stop()

if page == "✋ คิวอนุมัติ":
    render_queue_page(line_token=line_token, fb_token=fb_token,
                      fb_page_id=fb_page_id, ig_business_id=ig_business_id)
    st.stop()

if page == "📣 Content Studio":
    render_content_studio_page(ai_mode, api_key, line_token=line_token, fb_token=fb_token, fb_page_id=fb_page_id, ig_business_id=ig_business_id)
    st.stop()

if page == "💬 AI Inbox":
    render_ai_inbox_page(ai_mode, api_key, fb_token=fb_token, fb_page_id=fb_page_id, line_token=line_token)
    st.stop()

if page == "🧮 ROI Calculator":
    render_roi_calculator()
    st.stop()

# ── Dashboard ───────────────────────────────────────────────────────────────────

st.title("REVENUE AI")
st.caption("Data → Insight → Action | สำหรับร้านอาหาร / คาเฟ่ / บาร์ / ยิม")

if demo_profile == "ร้านเย็นตาโฟ (ข้อมูลจริง)":
    st.info("กำลังแสดงข้อมูลจริงของลูกค้าร้านเย็นตาโฟจากไฟล์ Excel")
    render_yentafo_dashboard(load_yentafo_aggregates(YENTAFO_DIR))
    st.stop()
elif demo_profile == "ร้านหมูกระทะ":
    df = generate_mookrata_data()
    st.info("กำลังแสดงข้อมูลจำลองร้านหมูกระทะ")
else:
    df = load_data()

# Date + branch filter
min_date = df["order_time"].min().date()
max_date = df["order_time"].max().date()
left, right = st.columns([2, 1])
with left:
    selected_dates = st.date_input(
        "ช่วงข้อมูล",
        value=(max_date - dt.timedelta(days=30), max_date),
        min_value=min_date, max_value=max_date,
    )
with right:
    branch_filter = st.multiselect(
        "เลือกสาขา",
        options=sorted(df["branch"].unique()),
        default=sorted(df["branch"].unique()),
    )

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date, end_date = max_date - dt.timedelta(days=30), max_date

filtered = df[
    (df["order_time"].dt.date >= start_date) &
    (df["order_time"].dt.date <= end_date) &
    (df["branch"].isin(branch_filter))
].copy()

if filtered.empty:
    st.warning("ไม่พบข้อมูลในช่วงที่เลือก")
    st.stop()

# KPI row
sales = filtered["net_sales"].sum()
margin = filtered["margin"].sum()
aov = filtered["net_sales"].mean()
repeat_rate = (filtered["customer_segment"] != "new").mean() if "customer_segment" in filtered.columns else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Revenue", f"฿{sales:,.0f}")
k2.metric("Margin", f"฿{margin:,.0f}")
k3.metric("AOV", f"฿{aov:,.0f}")
k4.metric("Repeat Rate", f"{repeat_rate:.1%}")

forecast_df = get_sales_forecast(filtered)
if not forecast_df.empty:
    next_7d = forecast_df[forecast_df["type"] == "Forecast"]["net_sales"].sum()
    st.info(f"💡 **AI Forecast:** คาดการณ์ยอดขาย 7 วันข้างหน้า: **฿{next_7d:,.0f}**")

if "service_type" in filtered.columns:
    buffet_share = (filtered["service_type"] == "buffet").mean()
    st.caption(f"Service Mix — Buffet: {buffet_share:.1%} | À la carte: {1 - buffet_share:.1%}")

# 4 tabs
tab1, tab2, tab3, tab4 = st.tabs(["Executive Dashboard", "Customer Intelligence", "Real-time Marketing", "Branch & Staff"])

with tab1:
    daily = (
        filtered.assign(order_date=filtered["order_time"].dt.date)
        .groupby("order_date", as_index=False)["net_sales"].sum()
    )
    
    # Sales Forecast
    st.subheader("ยอดขายและการพยากรณ์ (Sales Forecast)")
    forecast_df = get_sales_forecast(filtered)
    if not forecast_df.empty:
        fig = px.line(
            forecast_df, x="date", y="net_sales", color="type",
            line_dash="type", markers=True,
            title="Actual Sales vs 7-Day Forecast",
            color_discrete_map={"Actual": "#3B82F6", "Forecast": "#F59E0B"}
        )
        _chart(fig)
    else:
        _chart(px.line(daily, x="order_date", y="net_sales", title="ยอดขายรายวัน", markers=True))

    top_items = (
        filtered.groupby("item", as_index=False)["margin"].sum()
        .sort_values("margin", ascending=False).head(5)
    ) if "item" in filtered.columns else pd.DataFrame()
    if not top_items.empty:
        _chart(px.bar(top_items, x="item", y="margin", title="Top 5 Items by Margin"))

    if "service_type" in filtered.columns:
        mix = filtered.groupby("service_type", as_index=False)["net_sales"].sum()
        _chart(px.bar(mix, x="service_type", y="net_sales", title="ยอดขายตามประเภทบริการ"))

with tab2:
    # Compute RFM for the filtered dataset
    rfm_data = compute_rfm(filtered)
    if not rfm_data.empty:
        filtered = label_transactions(filtered, rfm_data)
    _render_rfm_tab(filtered, rfm_data)

    st.divider()
    st.subheader(f"AI Insights ({ai_mode})")
    with st.spinner("กำลังวิเคราะห์..."):
        for insight in get_ai_insights(filtered, ai_mode, api_key):
            st.success(insight)

with tab3:
    hourly_df = (
        filtered.assign(order_hour=filtered["order_time"].dt.hour)
        .groupby("order_hour", as_index=False)["net_sales"].sum()
    )
    _chart(px.area(hourly_df, x="order_hour", y="net_sales", title="Opportunity by Hour"))

    st.subheader("Recommended Campaign & Content")
    for line in content_suggestions(filtered):
        st.info(line)

with tab4:
    by_branch = filtered.groupby("branch", as_index=False).agg(
        revenue=("net_sales", "sum"),
        margin=("margin", "sum"),
        transactions=("order_id", "count"),
    )
    st.dataframe(by_branch)

    if "staff" in filtered.columns:
        by_staff = (
            filtered.groupby("staff", as_index=False).agg(
                revenue=("net_sales", "sum"),
                margin=("margin", "sum"),
                transactions=("order_id", "count"),
            ).sort_values("revenue", ascending=False)
        )
        st.dataframe(by_staff)

st.divider()
dl_col, info_col = st.columns([1, 2])
with dl_col:
    st.download_button(
        label="📥 Download Report (.xlsx)",
        data=generate_excel_report(filtered),
        file_name=f"ai_revenue_{dt.datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
with info_col:
    st.caption("รายงานรวม 7 sheet: KPI Summary, Daily Sales, Top Items, Branch Performance, Customer Segments, Hourly Revenue, AI Insights")

