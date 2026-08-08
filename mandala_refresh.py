"""mandala_refresh.py — trigger mandala-bot refresh from inside the suite.

Lets the Streamlit app pull fresh Facebook page insights (and, on demand,
regenerate content) without the owner opening a separate terminal in
mandala-bot. Runs mandala-bot's own scripts as a subprocess so its .env /
credentials stay in mandala-bot, never in the suite.

Read the brand artifacts with `mandala_client`; use THIS module only when you
want to actively refresh them.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import mandala_client


def _bot_dir() -> Path:
    base = mandala_client.find_mandala_dir()
    if base is None:
        raise RuntimeError("ไม่พบ mandala-bot (ตั้ง env MANDALA_BOT_DIR หรือวางไว้ที่ D:\\LEMED\\mandala-bot)")
    return base


def _python(bot_dir: Path) -> str:
    """เลือก interpreter ที่มี requests/python-dotenv ครบ (venv ของ bot → py → ปัจจุบัน)."""
    venv_py = bot_dir / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        return str(venv_py)
    for cand in ("py", "python"):
        if shutil.which(cand):
            return cand
    return sys.executable


def _run(script: str, timeout: int) -> dict:
    bot_dir = _bot_dir()
    if not (bot_dir / script).exists():
        return {"ok": False, "stdout": "", "stderr": f"ไม่พบ {script} ใน {bot_dir}"}
    try:
        proc = subprocess.run(
            [_python(bot_dir), script],
            cwd=str(bot_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": f"หมดเวลา ({timeout}s)"}
    return {
        "ok": proc.returncode == 0,
        "stdout": (proc.stdout or "")[-3000:],
        "stderr": (proc.stderr or "")[-1500:],
    }


def refresh_fb_insights(timeout: int = 120) -> dict:
    """ดึงโพสต์+engagement จากเพจ FB → อัปเดต context.txt ของ mandala-bot (เร็ว ~5-15s)."""
    return _run("fb_insights.py", timeout)


def refresh_content(timeout: int = 900) -> dict:
    """สั่ง mandala-bot สร้างคอนเทนต์ชุดใหม่ (ช้า หลายนาที — ใช้เมื่อจำเป็น)."""
    return _run("mandala_bot.py", timeout)


def refresh_all(content_timeout: int = 900) -> dict:
    """ดึงข้อมูลเพจก่อน แล้วสร้างคอนเทนต์ใหม่ (ใช้กับ scheduler)."""
    fb = refresh_fb_insights()
    content = refresh_content(content_timeout) if fb["ok"] else {"ok": False, "stderr": "ข้าม (fb_insights พลาด)"}
    return {"fb": fb, "content": content, "ok": fb["ok"] and content["ok"]}


if __name__ == "__main__":
    # ใช้กับ scheduler: py mandala_refresh.py  → รีเฟรชข้อมูลเพจ + คอนเทนต์
    import json

    print(json.dumps(refresh_all(), ensure_ascii=False, indent=2))
