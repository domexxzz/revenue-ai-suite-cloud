"""flow_bot.py — drive the Google Flow UI to download generated media.

🛑 สถานะ: ใช้งานไม่ได้ — Google บล็อกการล็อกอินจากเบราว์เซอร์ที่ถูกโปรแกรมควบคุม
    ทดสอบเมื่อ 2026-08-01 ด้วย Chrome จริง (channel="chrome") หน้าล็อกอินขึ้นว่า
    "ลงชื่อเข้าใช้ให้คุณไม่ได้ — เบราว์เซอร์หรือแอปนี้อาจไม่ปลอดภัย"
    คือระบบตรวจจับ automation ของ Google ปฏิเสธตั้งแต่ประตูแรก

    มีเทคนิคหลบ (stealth plugin, ดูดคุกกี้จากโปรไฟล์จริง, ต่อ CDP เข้าเบราว์เซอร์
    ที่ล็อกอินไว้) แต่ทั้งหมดคือการหลบระบบตรวจจับบอทที่ Google ตั้งใจวางไว้
    **จงใจไม่ทำ** — บัญชีนี้ผูกกับ Drive/YouTube/Gmail ทั้งหมด

    ✅ วิธีที่ใช้จริง: ตั้ง Chrome ให้ดาวน์โหลดลง G:\\My Drive\\Lemed\\ (Drive for
    Desktop) แล้วกดดาวน์โหลดใน Flow เอง — ไฟล์ขึ้น Drive ทันที จากนั้น flow_sync.py
    จัดเข้าโฟลเดอร์ย่อยให้ ต่างจากบอทแค่คลิกเดียวต่อคลิปที่เลือกจะเอา

    เก็บไฟล์นี้ไว้เผื่อ Flow เปิด public API ในอนาคต — โครงเดินหน้าต่อได้ทันที

⚠️  ความเสี่ยงเดิม (ถ้าจะรื้อมาใช้)
    Google Flow ไม่มี public API บอทนี้จึงทำงานโดย "กดปุ่มแทนคน" บนหน้าเว็บจริง
    ด้วย session ที่คุณล็อกอินเอง ซึ่ง **มักผิด ToS ของ Google** และบัญชีนี้ผูกกับ
    Drive / YouTube / Gmail ทั้งหมด — ถ้าโดนระงับคือเสียทั้งบัญชี
    จึงตั้งค่าให้ทำงาน human-scale (หน่วงต่อไฟล์ + เพดานต่อรอบ) **อย่าถอดตัวจำกัดออก**
    ถ้ายอมรับความเสี่ยงไม่ได้ ให้ใช้วิธีกดดาวน์โหลดเองแล้วให้ flow_sync.py จัดไฟล์แทน

วิธีใช้
    py flow_bot.py --login     # ครั้งแรก: เปิดเบราว์เซอร์ให้ล็อกอิน Google เอง
    py flow_bot.py             # รันจริง: ไล่ดาวน์โหลดสื่อที่ยังไม่เคยโหลด
    py flow_bot.py --dry-run   # ดูว่าจะโหลดกี่ชิ้น โดยไม่กดอะไร

บอทเซฟไฟล์ลง G:\\My Drive\\Lemed\\... โดยตรง (Drive for Desktop ซิงก์ขึ้นคลาวด์ให้เอง)
สิ่งที่โหลดแล้วถูกจำไว้ใน flow_bot_state.json จึงไม่โหลดซ้ำ

หมายเหตุ: บอทไม่เคยกรอกรหัสผ่านแทนคุณ — โหมด --login เปิดหน้าต่างให้คุณล็อกอินเอง
แล้วเก็บ session ไว้ในโปรไฟล์เบราว์เซอร์ของบอท
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
PROFILE_DIR = BASE_DIR / ".flow_profile"          # session ของบอท (ห้าม commit)
STATE_FILE = BASE_DIR / "flow_bot_state.json"     # จำสิ่งที่โหลดแล้ว

DEFAULT_PROJECT_URL = os.getenv(
    "FLOW_PROJECT_URL",
    "https://labs.google/fx/th/tools/flow/project/c9bfbfd9-88ea-4c56-b6b5-7711df26d9b8",
)
DEFAULT_DEST = Path(os.getenv("FLOW_BOT_DEST", r"G:\My Drive\Lemed"))

# ── ตัวจำกัดแบบ human-scale — อย่าถอดออก ────────────────────────────────────────
MIN_DELAY_SEC = float(os.getenv("FLOW_BOT_MIN_DELAY", "5"))
MAX_DELAY_SEC = float(os.getenv("FLOW_BOT_MAX_DELAY", "9"))
MAX_PER_RUN = int(os.getenv("FLOW_BOT_MAX_PER_RUN", "10"))

# ข้อความบนเมนู/ปุ่ม — Flow เป็น Labs ปรับ UI บ่อย ถ้าพังให้แก้ตรงนี้ก่อน
MENU_BUTTON_HINTS = ["more_vert", "ตัวเลือก", "More options", "เพิ่มเติม"]
DOWNLOAD_ITEM_HINTS = ["ดาวน์โหลด", "Download"]

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v"}


def _sleep_human(label: str = "") -> None:
    """หน่วงแบบคน — กันยิงถี่จนถูกตรวจจับ"""
    wait = random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC)
    if label:
        print(f"      …รอ {wait:.1f} วิ {label}")
    time.sleep(wait)


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"downloaded": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def dest_for(filename: str, dest_root: Path) -> Path:
    """เลือกโฟลเดอร์ปลายทางจากชนิดไฟล์ (ปรับเองได้ในแอปทีหลัง)"""
    ext = Path(filename).suffix.lower()
    sub = "TikTok VDO" if ext in VIDEO_EXTS else "รูปภาพ"
    target = dest_root / sub
    target.mkdir(parents=True, exist_ok=True)
    return target / filename


def _launch(pw, headless: bool):
    """เปิดเบราว์เซอร์ด้วยโปรไฟล์ถาวร เพื่อคง session ที่ผู้ใช้ล็อกอินไว้

    ใช้ Chrome ที่ติดตั้งในเครื่องก่อน เพราะ Windows Smart App Control บล็อก
    Chromium ที่ Playwright โหลดมาเอง (เจอ `spawn UNKNOWN`) ส่วน Chrome ของ Google
    มีลายเซ็นถูกต้องจึงผ่าน — และยังเหมือนเบราว์เซอร์ที่คนใช้จริงมากกว่าด้วย
    """
    PROFILE_DIR.mkdir(exist_ok=True)
    common = dict(
        user_data_dir=str(PROFILE_DIR),
        headless=headless,
        accept_downloads=True,
        viewport={"width": 1500, "height": 950},
        locale="th-TH",
    )
    try:
        return pw.chromium.launch_persistent_context(channel="chrome", **common)
    except Exception as e:
        print(f"! เปิด Chrome ไม่ได้ ({str(e)[:60]}) — ลอง Chromium ของ Playwright แทน")
        return pw.chromium.launch_persistent_context(**common)


def cmd_login(project_url: str) -> None:
    """เปิดหน้าต่างให้ผู้ใช้ล็อกอิน Google ด้วยตัวเอง แล้วเก็บ session ไว้"""
    from playwright.sync_api import sync_playwright

    print("เปิดเบราว์เซอร์ให้ล็อกอิน Google ด้วยตัวคุณเอง")
    print("(บอทไม่กรอกรหัสผ่านให้ — คุณเป็นคนล็อกอินเอง)")
    with sync_playwright() as pw:
        ctx = _launch(pw, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(project_url, wait_until="domcontentloaded", timeout=120_000)
        print("\nล็อกอินให้เรียบร้อยจนเห็นสื่อในโปรเจกต์ แล้วกด Enter ที่หน้าต่างนี้...")
        try:
            input()
        except EOFError:
            print("! รันแบบไม่มี stdin — รอ 120 วินาทีแทน")
            time.sleep(120)
        ctx.close()
    print("เก็บ session แล้ว — รัน `py flow_bot.py` ได้เลย")


def _open_tile_menu(page, tile) -> bool:
    """เปิดเมนู ⋮ ของสื่อชิ้นหนึ่ง คืน True ถ้าเมนูเปิดได้"""
    try:
        tile.scroll_into_view_if_needed(timeout=10_000)
        tile.hover(timeout=10_000)
    except Exception:
        return False

    for hint in MENU_BUTTON_HINTS:
        try:
            btn = tile.locator(f"text={hint}").first
            if btn.count() and btn.is_visible():
                btn.click(timeout=5_000)
                return True
        except Exception:
            continue
    # เผื่อ UI ใช้ปุ่มไอคอนล้วน — ลองปุ่มสุดท้ายในไทล์
    try:
        btns = tile.locator("button")
        n = btns.count()
        if n:
            btns.nth(n - 1).click(timeout=5_000)
            return True
    except Exception:
        pass
    return False


def _click_download(page) -> bool:
    """กดรายการ 'ดาวน์โหลด' ในเมนูที่เปิดอยู่"""
    for hint in DOWNLOAD_ITEM_HINTS:
        try:
            item = page.get_by_text(re.compile(rf"^\s*{re.escape(hint)}\s*$"), exact=False).last
            if item.count() and item.is_visible():
                item.click(timeout=5_000)
                return True
        except Exception:
            continue
    return False


def run(project_url: str, dest_root: Path, dry_run: bool, headless: bool,
        limit: int) -> None:
    from playwright.sync_api import sync_playwright

    state = load_state()
    done = set(state.get("downloaded", []))
    print(f"โปรเจกต์ : {project_url}")
    print(f"ปลายทาง  : {dest_root}")
    print(f"เคยโหลดแล้ว {len(done)} ชิ้น | เพดานรอบนี้ {limit} ชิ้น")
    if not dest_root.exists():
        print(f"! ไม่พบโฟลเดอร์ปลายทาง {dest_root} — เปิด Google Drive for Desktop หรือยัง?")
        return

    with sync_playwright() as pw:
        ctx = _launch(pw, headless=headless)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(project_url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(6_000)

        if "accounts.google.com" in page.url:
            print("! ยังไม่ได้ล็อกอิน — รัน `py flow_bot.py --login` ก่อน")
            ctx.close()
            return

        # ไทล์สื่อ = การ์ดที่มีรูป/วิดีโออยู่ข้างใน
        tiles = page.locator("div").filter(has=page.locator("img, video"))
        total = tiles.count()
        print(f"เจอไทล์สื่อประมาณ {total} ชิ้นบนหน้า")
        if dry_run:
            print("(dry-run) ไม่กดอะไร จบการทำงาน")
            ctx.close()
            return

        saved = 0
        for i in range(total):
            if saved >= limit:
                print(f"ถึงเพดาน {limit} ชิ้นแล้ว — หยุดเพื่อความปลอดภัยของบัญชี")
                break
            tile = tiles.nth(i)
            try:
                if not tile.is_visible():
                    continue
            except Exception:
                continue

            print(f"  [{i+1}/{total}] เปิดเมนู…")
            if not _open_tile_menu(page, tile):
                continue

            try:
                with page.expect_download(timeout=120_000) as dl_info:
                    if not _click_download(page):
                        page.keyboard.press("Escape")
                        continue
                download = dl_info.value
            except Exception as e:
                print(f"      ! ไม่ได้ไฟล์: {str(e)[:70]}")
                page.keyboard.press("Escape")
                _sleep_human()
                continue

            name = download.suggested_filename
            if name in done:
                print(f"      ข้าม (โหลดแล้ว): {name[:45]}")
                _sleep_human()
                continue

            target = dest_for(name, dest_root)
            try:
                download.save_as(str(target))
            except Exception as e:
                print(f"      ! เซฟไม่สำเร็จ: {str(e)[:70]}")
                _sleep_human()
                continue

            done.add(name)
            state["downloaded"] = sorted(done)
            save_state(state)
            saved += 1
            print(f"      ✓ {name[:45]} → {target.parent.name}")
            _sleep_human("(human-scale)")

        ctx.close()

    print(f"\nเสร็จ: โหลดใหม่ {saved} ชิ้น | รวมสะสม {len(done)} ชิ้น")
    print("Drive for Desktop จะซิงก์ขึ้นคลาวด์ให้เอง")


def main() -> None:
    ap = argparse.ArgumentParser(description="ดาวน์โหลดสื่อจาก Google Flow ลง Drive")
    ap.add_argument("--login", action="store_true", help="ล็อกอิน Google ครั้งแรก")
    ap.add_argument("--dry-run", action="store_true", help="นับจำนวนโดยไม่กดดาวน์โหลด")
    ap.add_argument("--headless", action="store_true", help="ซ่อนหน้าต่าง (ไม่แนะนำ)")
    ap.add_argument("--url", default=DEFAULT_PROJECT_URL, help="URL โปรเจกต์ Flow")
    ap.add_argument("--dest", default=str(DEFAULT_DEST), help="โฟลเดอร์ Drive ปลายทาง")
    ap.add_argument("--limit", type=int, default=MAX_PER_RUN, help="เพดานต่อรอบ")
    args = ap.parse_args()

    if args.limit > 25:
        print("! เพดานต่อรอบสูงเกินไป — ปรับลงเหลือ 25 เพื่อลดความเสี่ยงบัญชี")
        args.limit = 25

    if args.login:
        cmd_login(args.url)
        return
    run(args.url, Path(args.dest), args.dry_run, args.headless, args.limit)


if __name__ == "__main__":
    main()
