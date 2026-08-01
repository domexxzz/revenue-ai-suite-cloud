"""flow_fetch.py — โหลดคลิปจากลิงก์ที่คัดลอกมาจากหน้า Google Flow

ทำไมต้องมีไฟล์นี้
    ไฟล์จริงของ Flow อยู่ที่ flow-content.google ส่วนหน้าเว็บอยู่ที่ labs.google
    คนละ origin กัน เบราว์เซอร์จึงไม่ยอมให้สคริปต์ในหน้าอ่านไฟล์มาเซฟเอง
    (แอตทริบิวต์ download ถูกเมิน กลายเป็นเปิดวิดีโอแทน)

    แต่ลิงก์ที่ CDN ส่งมามีลายเซ็นอยู่ในตัว — Expires + Signature — ใช้ได้โดยไม่ต้อง
    มีคุกกี้หรือล็อกอิน ฝั่ง Python จึงโหลดได้ตรง ๆ ไม่ติดข้อจำกัดของเบราว์เซอร์เลย

    บุ๊กมาร์กเล็ตในหน้า Flow เก็บลิงก์พวกนี้ให้แล้ววางในกล่องคัดลอก จากนั้นเอามาวาง
    ในแอป ไฟล์จะถูกโหลดลง G:\\My Drive\\Lemed แล้ว flow_watch จัดเข้าโฟลเดอร์ต่อเอง

ใช้จากบรรทัดคำสั่งก็ได้
    py flow_fetch.py "https://flow-content.google/video/..." "https://..."
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

import flow_sync

# ลิงก์ CDN มีลายเซ็นและวันหมดอายุติดมา ปกติหมดอายุในไม่กี่ชั่วโมง
TIMEOUT_SEC = 120
CHUNK = 1 << 16


@dataclass(frozen=True)
class FetchResult:
    """ผลของการโหลดหนึ่งลิงก์ — เก็บเหตุผลไว้ด้วยเวลาไม่สำเร็จ"""
    url: str
    ok: bool
    path: Path | None = None
    bytes: int = 0
    error: str = ""


def parse_urls(text: str) -> list[str]:
    """ดึงลิงก์ออกจากข้อความที่วางมา — รับได้ทั้งบรรทัดละอันและปนกันมั่ว ๆ"""
    found = re.findall(r"https?://\S+", text or "")
    seen: list[str] = []
    for u in found:
        u = u.rstrip('",\'')
        if u not in seen:
            seen.append(u)
    return seen


def name_for(url: str, index: int) -> str:
    """ตั้งชื่อไฟล์จาก id ในลิงก์

    ลิงก์ของ Flow เป็น /video/<uuid> ซึ่งไม่มีนามสกุล และคลิปทุกอันมี path
    หน้าตาเหมือนกัน ถ้าตั้งชื่อจาก path จะได้ชื่อซ้ำกันหมด จึงใช้ uuid แทน
    """
    parsed = urlparse(url)
    last = Path(parsed.path).name or ""
    if re.search(r"\.\w{2,5}$", last):
        return last
    # id อยู่ได้สองที่: ท้าย path ของลิงก์ที่ CDN เซ็นมา (/video/<uuid>) หรือ
    # ?name=<uuid> ของลิงก์ redirect — เอาจาก query ก่อน เพราะ path ของ redirect
    # เป็น media.getMediaUrlRedirect เหมือนกันทุกคลิป ตั้งชื่อจากมันจะซ้ำกันหมด
    qs = parse_qs(parsed.query).get("name", [""])[0]
    ident = (qs or last)[:8]
    return f"flow_{ident or index}.mp4"


def fetch_one(url: str, dest_dir: Path, index: int = 1) -> FetchResult:
    """โหลดลิงก์เดียวลงโฟลเดอร์ปลายทาง"""
    try:
        with requests.get(url, stream=True, timeout=TIMEOUT_SEC) as r:
            if r.status_code != 200:
                return FetchResult(url, False,
                                   error=f"HTTP {r.status_code} — ลิงก์อาจหมดอายุแล้ว")
            dest_dir.mkdir(parents=True, exist_ok=True)
            # เขียนเป็นไฟล์ .part ก่อน แล้วค่อยเปลี่ยนชื่อ — watcher เฝ้าโฟลเดอร์นี้อยู่
            # ถ้าเห็นไฟล์ครึ่ง ๆ กลาง ๆ มันจะคว้าไปทั้งที่ยังเขียนไม่เสร็จ
            target = flow_sync._unique_path(dest_dir / name_for(url, index))
            part = target.with_suffix(target.suffix + ".part")
            size = 0
            with open(part, "wb") as fh:
                for chunk in r.iter_content(CHUNK):
                    if chunk:
                        fh.write(chunk)
                        size += len(chunk)
            part.rename(target)
            return FetchResult(url, True, path=target, bytes=size)
    except Exception as e:  # noqa: BLE001 — เครือข่ายพังได้หลายแบบ รายงานไปตามจริง
        return FetchResult(url, False, error=str(e)[:120])


def fetch_all(text_or_urls: str | list[str], dest_dir: Path | None = None,
              on_progress=None) -> list[FetchResult]:
    """โหลดทุกลิงก์ที่ให้มา ลงโฟลเดอร์ที่ watcher เฝ้าอยู่"""
    urls = (parse_urls(text_or_urls) if isinstance(text_or_urls, str)
            else list(text_or_urls))
    dest = Path(dest_dir) if dest_dir else Path(flow_sync.default_watch_dir())
    out: list[FetchResult] = []
    for i, u in enumerate(urls, 1):
        if on_progress:
            on_progress(i, len(urls), u)
        out.append(fetch_one(u, dest, i))
    return out


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("วางลิงก์ต่อท้ายคำสั่ง หรือ pipe ข้อความเข้ามาก็ได้")
        text = sys.stdin.read()
    else:
        text = " ".join(args)

    results = fetch_all(text)
    if not results:
        print("ไม่เจอลิงก์ในข้อความที่ให้มา")
        return
    ok = [r for r in results if r.ok]
    for r in results:
        if r.ok:
            print(f"  ✅ {r.path.name}  {r.bytes / 1048576:.1f} MB")
        else:
            print(f"  ❌ {r.url[:60]}… — {r.error}")
    print(f"\nโหลดสำเร็จ {len(ok)}/{len(results)} ไฟล์")


if __name__ == "__main__":
    main()
