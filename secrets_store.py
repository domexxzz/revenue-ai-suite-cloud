"""Keeping tokens between runs, on this machine only.

Until now a token lived in Streamlit's session state, which means it survived
exactly as long as the browser tab. Restart the app and every channel had to be
pasted again — and a Facebook Page token is not something anyone retypes from
memory.

This writes them to a file next to the app's own config. Not to
`.streamlit/secrets.toml`, despite that being the obvious home: Streamlit watches
that file and reloads secrets whenever it changes, so an app that writes it on
every edit is poking its own watcher. A sibling file it owns outright avoids
that, and `.gitignore` covers both.

Read order is deliberate: `st.secrets` first, local file second. On Streamlit
Cloud the deploy's secrets must win over anything a previous local run left
behind; locally there are no st.secrets, so the file is all there is.

These are plaintext credentials on disk. That is the same bargain as
`token.json` next door, and the UI says so out loud, but it is worth stating
here too: anyone with the machine has the tokens.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STORE_PATH = Path(__file__).parent / ".streamlit" / "app_secrets.json"

# Only these keys are ever written. A allowlist rather than "whatever the caller
# passed" — session state holds plenty that has no business on disk, including
# uploaded file bytes and whole chat transcripts.
SAVED_KEYS = (
    "set_line_token",
    "set_fb_token",
    "set_fb_page_id",
    "set_ig_business_id",
    "set_fb_app_id",
    "set_fb_app_secret",
    "tiktok_token",
    "set_ai_mode",
    "set_gemini_key",
    "set_claude_key",
    "set_lv_token",
    "copilot_brand",
    "copilot_vertical",
)

SECRET_KEYS = frozenset({
    "set_line_token", "set_fb_token", "set_fb_app_secret", "tiktok_token",
    "set_gemini_key", "set_claude_key", "set_lv_token",
})


def _read_file() -> dict:
    if not STORE_PATH.exists():
        return {}
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:  # noqa: BLE001 — a corrupt store must not block startup
        logger.warning("อ่านไฟล์ค่าที่บันทึกไว้ไม่ได้: %s", e)
        return {}


def _read_st_secrets() -> dict:
    """Whatever the deploy provides under [app_settings]."""
    try:
        import streamlit as st
        block = st.secrets.get("app_settings", {})
        return {k: v for k, v in dict(block).items() if k in SAVED_KEYS}
    except Exception:  # noqa: BLE001 — no secrets.toml is the normal local case
        return {}


def load() -> dict:
    """Saved settings, deploy secrets winning over the local file."""
    merged = {k: v for k, v in _read_file().items() if k in SAVED_KEYS}
    merged.update(_read_st_secrets())
    return {k: v for k, v in merged.items() if v not in (None, "")}


def save(values: dict) -> tuple[bool, str]:
    """Write the allowlisted keys. Returns (ok, message) — never raises."""
    keep = {k: v for k, v in values.items() if k in SAVED_KEYS and v not in (None, "")}
    try:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STORE_PATH.write_text(json.dumps(keep, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        logger.error("บันทึกค่าไม่สำเร็จ: %s", e)
        return False, f"บันทึกไม่สำเร็จ: {e}"
    n_secret = sum(1 for k in keep if k in SECRET_KEYS)
    return True, f"บันทึกแล้ว {len(keep)} ค่า (เป็น token/key {n_secret} ค่า)"


def clear() -> tuple[bool, str]:
    try:
        if STORE_PATH.exists():
            STORE_PATH.unlink()
        return True, "ลบไฟล์ที่บันทึกไว้แล้ว"
    except Exception as e:  # noqa: BLE001
        return False, f"ลบไม่สำเร็จ: {e}"


def describe() -> str:
    """One line about what is on disk, without revealing any of it."""
    data = _read_file()
    if not data:
        return "ยังไม่ได้บันทึกอะไรไว้ในเครื่อง"
    names = ", ".join(sorted(data))
    return f"บันทึกไว้ {len(data)} ค่า: {names}"
