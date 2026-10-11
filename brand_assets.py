"""brand_assets.py — รูปสินค้าจริงของแบรนด์ ที่ใช้เป็น reference ตอนสร้างคลิป

คลิปที่หลุดแบรนด์มักหลุดตั้งแต่ต้นทาง: ผู้ใช้พิมพ์ prompt เอง ไม่ได้แนบรูปสินค้าจริง
Google Flow จึงวาดสบู่ในจินตนาการขึ้นมาแทน โมดูลนี้เก็บรูปของจริงไว้ใน repo เพื่อให้
ทั้งหน้าเว็บ (โชว์ให้เลือก) และบอทในเครื่อง (แนบเข้า Flow) อ้างรูปเดียวกันด้วย "ชื่อไฟล์"

ชื่อไฟล์คือสัญญาเดียวที่ผูกสองฝั่งเข้าด้วยกัน — task JSON เก็บแค่ asset_name
ฝั่งบอทค่อย resolve เป็น path จริงในเครื่องตัวเอง
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets" / "lemed"

_VALID_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# โฟลเดอร์ Assets ของเว็บมีรูปสบู่สมุนไพรเปลือกมังคุด (คนละแบรนด์ กล่องเขียว-ส้ม) ปนอยู่
# ชื่อขึ้นต้น th-11134207 ถ้าหลุดเข้ามาเป็น reference ให้ Google Flow คลิปจะออกมาเป็น
# สบู่ก้อนสีน้ำตาล เพราะโมเดลเชื่อรูปมากกว่าข้อความ — กันไว้ตรงนี้เผื่อมีใครก๊อปกลับเข้ามา
_NOT_LEMED_PREFIXES = ("th-11134207",)


def list_assets() -> list[Path]:
    """รูปแบรนด์ทั้งหมด เรียงชื่อคงที่ เพื่อให้ลำดับไม่สลับทุกครั้งที่รีเฟรช"""
    if not ASSETS_DIR.exists():
        return []
    return sorted(
        p for p in ASSETS_DIR.iterdir()
        if p.suffix.lower() in _VALID_EXTS and p.is_file()
        and not p.name.lower().startswith(_NOT_LEMED_PREFIXES)
    )


def resolve(asset_name: str) -> Path | None:
    """ชื่อไฟล์ → path จริง คืน None ถ้าไม่มี

    กัน path traversal ด้วยการเทียบกับรายการที่รู้จักเท่านั้น ไม่ต่อ string เข้า path ตรง ๆ
    เพราะชื่อนี้เดินทางมาจาก task JSON ซึ่งถือเป็นข้อมูลภายนอก
    """
    if not asset_name:
        return None
    for p in list_assets():
        if p.name == asset_name:
            return p
    return None


def sample(count: int = 8, seed: str = "") -> list[Path]:
    """เลือกรูปมาโชว์ในตัวเลือก จำนวน count รูป

    ใช้ hash ของ seed แทน random เพื่อให้คลิปเดียวกันเห็นชุดรูปเดิมทุกครั้งที่ rerun
    (Streamlit rerun ทั้งหน้าเมื่อกดปุ่ม — ถ้าสุ่มสดรูปจะกระโดดจนกดเลือกไม่ทัน)
    """
    items = list_assets()
    if not items:
        return []
    if not seed:
        return items[:count]
    offset = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16) % len(items)
    rotated = items[offset:] + items[:offset]
    return rotated[:count]
