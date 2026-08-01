"""flow_bookmarklet.py — ห่อ flow_download_helper.js ให้เป็นบุ๊กมาร์กกดปุ่มเดียว

สคริปต์ตัวเดิมต้องเปิด F12 → Console → วางทั้งไฟล์ ทุกครั้งที่อยากโหลดคลิป
บุ๊กมาร์กเล็ตทำสิ่งเดียวกันแต่ลากเก็บไว้บนแถบบุ๊กมาร์กครั้งเดียว แล้วกดปุ่มเดียว

    py flow_bookmarklet.py            # พิมพ์ javascript: URI ออกมา
    py flow_bookmarklet.py --html     # เขียนหน้าเว็บที่มีลิงก์ให้ลากเก็บ

ทำงานในเบราว์เซอร์ปกติของคุณที่ล็อกอินอยู่แล้ว — ไม่มีเบราว์เซอร์อัตโนมัติ ไม่มีการ
กรอกรหัสผ่านแทนคุณ และไม่ไปยุ่งกับระบบตรวจจับใด ๆ ของ Google เท่ากับกดปุ่มดาวน์โหลด
เองทีละอัน เพียงแต่ไม่ต้องนั่งกด

⚠️ ตัวจำกัดอยู่ในสคริปต์ต้นทาง (หน่วง 3-5 วิต่อไฟล์ · สูงสุด 15 ไฟล์ต่อรอบ) — การโหลด
   เป็นชุดอาจขัด ToS ของ Flow อยู่ดี อย่าถอดตัวจำกัดออก
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import quote

BASE_DIR = Path(__file__).parent
HTML_OUT = BASE_DIR / "flow_bookmarklet.html"

# ตัวโหลดคือของหลัก ตัวตรวจมีไว้ตอนที่ Flow เปลี่ยนชื่อปุ่มแล้วตัวโหลดหาไม่เจอ
SOURCES = {
    "download": BASE_DIR / "flow_download_helper.js",
    "inspect": BASE_DIR / "flow_inspect_helper.js",
}
HELPER = SOURCES["download"]


def _strip_comments(src: str) -> str:
    """Drop comments and blank lines, keeping anything inside a string literal.

    A plain regex would eat the "//" in a URL and the "*" in a CSS box-shadow, so
    this walks the source and tracks whether it is inside a quote, a template
    literal, or a regex-looking slash before deciding a "//" starts a comment.
    """
    out: list[str] = []
    i, n = 0, len(src)
    quote_ch = ""
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""

        if quote_ch:
            out.append(c)
            if c == "\\":                      # escaped char — copy the pair
                if i + 1 < n:
                    out.append(nxt)
                    i += 1
            elif c == quote_ch:
                quote_ch = ""
            i += 1
            continue

        if c in "\"'`":
            quote_ch = c
            out.append(c)
            i += 1
            continue

        if c == "/" and nxt == "/":
            while i < n and src[i] != "\n":
                i += 1
            continue
        if c == "/" and nxt == "*":
            i += 2
            while i + 1 < n and not (src[i] == "*" and src[i + 1] == "/"):
                i += 1
            i += 2
            continue

        out.append(c)
        i += 1

    text = "".join(out)
    # Collapse the whitespace a bookmarklet has no use for. Line breaks go last so
    # a statement that relied on automatic semicolon insertion keeps its newline
    # until the very end, when every line already ends in ; { } or ,.
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def build(kind: str = "download") -> str:
    """The whole helper as one javascript: URI, ready to be a bookmark."""
    src = SOURCES.get(kind)
    if src is None:
        raise ValueError(f"ไม่รู้จัก kind={kind!r} — มีแค่ {sorted(SOURCES)}")
    if not src.exists():
        raise FileNotFoundError(f"ไม่เจอ {src}")
    body = _strip_comments(src.read_text(encoding="utf-8"))
    # void(0) so the page is not replaced by the expression's return value —
    # without it the browser navigates away to whatever the script evaluated to.
    return "javascript:" + quote(f"(function(){{{body}}})();void 0;", safe="")


def write_html(path: Path = HTML_OUT) -> Path:
    """A tiny page holding the draggable link, since a bookmark cannot be typed."""
    uri = build()
    page = f"""<!doctype html>
<meta charset="utf-8">
<title>ลากไปเก็บบนแถบบุ๊กมาร์ก</title>
<style>
 body {{ font: 16px/1.7 system-ui, "Segoe UI", sans-serif; max-width: 40rem;
        margin: 3rem auto; padding: 0 1.5rem; color: #111827; background: #F8F7F4; }}
 a.bm {{ display: inline-block; background: #F59E0B; color: #111827; font-weight: 700;
        padding: .7rem 1.4rem; border-radius: 10px; text-decoration: none;
        box-shadow: 0 2px 8px rgba(0,0,0,.15); cursor: grab; }}
 ol {{ padding-left: 1.3rem; }} li {{ margin: .5rem 0; }}
 code {{ background: #fff; padding: .1rem .4rem; border-radius: 5px; }}
 .warn {{ background: #FEF3C7; border-left: 4px solid #F59E0B;
         padding: .8rem 1rem; border-radius: 6px; }}
</style>
<h1>⬇️ Flow → Drive</h1>
<ol>
  <li>เปิดแถบบุ๊กมาร์กก่อน — <code>Ctrl+Shift+B</code></li>
  <li><b>ลาก</b>ปุ่มส้มนี้ขึ้นไปวางบนแถบบุ๊กมาร์ก (ลากนะ อย่ากด)</li>
  <li>เปิดโปรเจกต์ใน Google Flow แล้วกดบุ๊กมาร์กนั้น</li>
</ol>
<p><a class="bm" href="{uri}">⬇️ โหลดคลิปจาก Flow</a>
   <a class="bm" style="background:#E5E7EB" href="{build("inspect")}">🔎 ตรวจปุ่มในหน้า Flow</a></p>
<p>ปุ่มสีเทาใช้ตอนตัวโหลดขึ้นว่า “หาปุ่ม ⋮ ไม่เจอ” — มันอ่านอย่างเดียว
ไม่กดอะไร แล้วให้ข้อความที่คัดลอกส่งมาได้เลย</p>
<p class="warn">ตั้งโฟลเดอร์ดาวน์โหลดของ Chrome เป็น
<code>G:\\My Drive\\Lemed</code> และปิด “ถามที่จัดเก็บทุกครั้ง” ก่อน
แล้ว <code>flow_watch.py</code> จะจัดไฟล์เข้าโฟลเดอร์แพลตฟอร์มให้เอง</p>
<p>หน่วง 3-5 วินาทีต่อไฟล์ สูงสุด 15 ไฟล์ต่อรอบ กดซ้ำได้ถ้ายังเหลือ</p>
"""
    path.write_text(page, encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description="สร้างบุ๊กมาร์กเล็ตกดโหลดคลิปจาก Flow")
    ap.add_argument("--html", action="store_true",
                    help="เขียนหน้าเว็บที่มีลิงก์ให้ลากเก็บ")
    ap.add_argument("--kind", choices=sorted(SOURCES), default="download",
                    help="download = ตัวโหลด · inspect = ตัวตรวจปุ่ม")
    args = ap.parse_args()

    if args.html:
        print("เขียนแล้ว:", write_html())
    else:
        uri = build(args.kind)
        print(uri)
        print(f"\n({len(uri):,} ตัวอักษร · {args.kind})")


if __name__ == "__main__":
    main()
