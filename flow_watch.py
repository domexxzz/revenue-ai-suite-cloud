"""flow_watch.py — เฝ้าโฟลเดอร์ดาวน์โหลด แล้วจัดไฟล์เข้าโฟลเดอร์แพลตฟอร์มทันที

รันค้างไว้ตัวเดียว: พอไฟล์จาก Google Flow ดาวน์โหลดลงมา ระบบจะรอจนเขียนไฟล์เสร็จ
แล้วย้ายเข้า Facebook VDO / TikTok VDO / รูปภาพ ให้เอง ภายในไม่กี่วินาที
ไม่ต้องกดปุ่มซิงก์ในแอป และไม่ต้องรอ Task Scheduler

    py flow_watch.py                 # เฝ้าโฟลเดอร์ดาวน์โหลดของ Chrome
    py flow_watch.py --dir "G:\\My Drive\\Lemed"
    py flow_watch.py --interval 3    # เช็คทุก 3 วินาที

หยุดด้วย Ctrl+C

ทำไมต้องรอไฟล์นิ่งก่อน: ตอนเบราว์เซอร์กำลังเขียนไฟล์ ขนาดจะยังเพิ่มขึ้นเรื่อย ๆ
ถ้าย้ายตอนนั้นจะได้ไฟล์ที่ยังไม่ครบ — จึงต้องเห็นขนาดเท่าเดิมติดกันก่อนถึงจะแตะ
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import flow_sync

STABLE_CHECKS = 2          # ต้องเห็นขนาดเท่าเดิมกี่ครั้งติดกัน
DEFAULT_INTERVAL = 5.0


def _size_of(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def wait_until_stable(path: Path, interval: float) -> bool:
    """รอจนไฟล์เขียนเสร็จ (ขนาดคงที่ติดกันหลายรอบ)"""
    last = _size_of(path)
    if last is None:
        return False
    steady = 0
    while steady < STABLE_CHECKS:
        time.sleep(interval)
        now = _size_of(path)
        if now is None:
            return False          # ไฟล์หายไประหว่างทาง
        if now == last and now > 0:
            steady += 1
        else:
            steady = 0
        last = now
    return True


def watch(watch_dir: Path, interval: float, local_root: Path | None,
          drive_root: str) -> None:
    seen: set[str] = set()
    print(f"เฝ้าโฟลเดอร์: {watch_dir}")
    if local_root:
        print(f"โหมด        : ย้ายไฟล์ในเครื่อง → {local_root}")
    else:
        print("โหมด        : อัปโหลดผ่าน Drive API")
    print(f"เช็คทุก {interval:g} วินาที · หยุดด้วย Ctrl+C\n")

    while True:
        try:
            # ดูเฉพาะไฟล์ใหม่ ๆ เพื่อไม่ไปกวาดของเก่าทั้งโฟลเดอร์
            files = flow_sync.find_new_files(watch_dir, max_age_hours=24)
        except Exception as e:  # noqa: BLE001 — watcher ต้องไม่ตายเพราะ error ชั่วคราว
            print(f"! อ่านโฟลเดอร์ไม่ได้: {e}")
            time.sleep(interval)
            continue

        for path in files:
            key = f"{path.name}:{_size_of(path)}"
            if key in seen:
                continue

            print(f"เจอไฟล์ใหม่: {path.name[:52]}")
            if not wait_until_stable(path, interval):
                print("   ข้าม (ไฟล์หายหรือยังเขียนไม่เสร็จ)")
                continue

            try:
                record = flow_sync.sync_file(path, drive_root, local_root=local_root)
            except Exception as e:  # noqa: BLE001
                print(f"   ! จัดไฟล์ไม่สำเร็จ: {e}")
                seen.add(key)
                continue

            if record["ok"]:
                print(f"   ✓ → {record['folder']}")
            else:
                print(f"   ✗ {record['error']}")
                seen.add(key)      # อย่าวนลองไฟล์เดิมไม่สิ้นสุด

        time.sleep(interval)


def main() -> None:
    ap = argparse.ArgumentParser(description="เฝ้าโฟลเดอร์แล้วจัดไฟล์เข้า Drive ทันที")
    ap.add_argument("--dir", default=None, help="โฟลเดอร์ที่จะเฝ้า")
    ap.add_argument("--interval", type=float, default=DEFAULT_INTERVAL,
                    help="เช็คทุกกี่วินาที")
    ap.add_argument("--no-local", action="store_true",
                    help="บังคับอัปผ่าน API แทนการย้ายไฟล์")
    args = ap.parse_args()

    watch_dir = Path(args.dir) if args.dir else flow_sync.default_watch_dir()
    if not watch_dir.is_dir():
        print(f"! ไม่พบโฟลเดอร์ {watch_dir}")
        return

    local_root = None if args.no_local else flow_sync.default_local_root()
    if local_root is None and args.no_local is False:
        from google_drive import needs_auth
        if needs_auth():
            print("! ไม่พบ Drive for Desktop และยังไม่ได้ authorize Drive API")
            return

    try:
        watch(watch_dir, max(1.0, args.interval), local_root, flow_sync._queue_root())
    except KeyboardInterrupt:
        print("\nหยุดแล้ว")


if __name__ == "__main__":
    main()
