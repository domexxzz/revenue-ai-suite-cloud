"""Flow → Drive sync: file the clips and stills you export from Google Flow.

Google Flow has no public API, so nothing can reach into a Flow project and pull
assets out. What it does have is a download button — so this watches wherever
those downloads land, works out what each file is, and uploads it into the right
Drive subfolder (Facebook Post, TikTok VDO, รูปภาพ, …).

Two ways to run it:

  • from the app — the queue page has a "ซิงก์จาก Flow" button
  • on a schedule — `py flow_sync.py` picks up anything new, so Windows Task
    Scheduler can run it every few minutes:

        schtasks /create /tn "FlowSync" /tr "D:\\ai-revenue\\.venv\\Scripts\\python.exe D:\\ai-revenue\\flow_sync.py" /sc minute /mo 5

Processed files move into a `_synced` subfolder so nothing uploads twice.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v"}

MIME_BY_EXT = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".mp4": "video/mp4", ".mov": "video/quicktime",
    ".webm": "video/webm", ".m4v": "video/x-m4v",
}

DONE_DIRNAME = "_synced"

# Filename fragments → platform. Name a Flow export "ig_serum_hook.mp4" and it
# files itself; anything unrecognised falls back to the generic folders.
_PLATFORM_HINTS = [
    (("facebook", "_fb", "fb_", "fb-"), "facebook"),
    (("instagram", "instragram", "_ig", "ig_", "ig-", "reel"), "instagram"),
    (("tiktok", "tik_tok", "_tt", "tt_"), "tiktok"),
    (("youtube", "_yt", "yt_", "shorts"), "youtube"),
    (("line",), "line_oa"),
]

# Where a file goes when no platform is named in the filename.
FALLBACK_IMAGE_FOLDER = "รูปภาพ"
FALLBACK_VIDEO_FOLDER = "TikTok VDO"


def default_watch_dir() -> Path:
    """Where Flow downloads usually land."""
    env = os.getenv("FLOW_WATCH_DIR", "").strip()
    if env:
        return Path(env)
    return Path.home() / "Downloads"


def classify(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return "other"


def guess_platform(filename: str) -> str:
    low = filename.lower()
    for fragments, key in _PLATFORM_HINTS:
        if any(f in low for f in fragments):
            return key
    return ""


def find_new_files(watch_dir: Path, max_age_hours: int = 0) -> list[Path]:
    """Media files sitting in watch_dir that haven't been synced yet.

    max_age_hours > 0 limits the sweep to recent files, which matters the first
    time it runs against a Downloads folder with years of history in it.
    """
    if not watch_dir.is_dir():
        return []
    import time

    cutoff = time.time() - max_age_hours * 3600 if max_age_hours else 0
    out: list[Path] = []
    for p in watch_dir.iterdir():
        if not p.is_file() or p.parent.name == DONE_DIRNAME:
            continue
        if classify(p) == "other":
            continue
        try:
            if cutoff and p.stat().st_mtime < cutoff:
                continue
            # Skip files still being written by the browser.
            if p.suffix.lower() in (".crdownload", ".part", ".tmp"):
                continue
        except OSError:
            continue
        out.append(p)
    return sorted(out, key=lambda p: p.stat().st_mtime)


# ── Drive for Desktop (local move) ──────────────────────────────────────────────
# When the queue folders are already mirrored on disk by Drive for Desktop, moving
# a file is strictly better than uploading it: a 100 MB clip lands instantly, the
# API quota goes untouched, and Drive syncs it up on its own.

def default_local_root() -> Path | None:
    """Local folder mirroring the Drive queue root, if Drive for Desktop has it."""
    env = os.getenv("FLOW_LOCAL_ROOT", "").strip()
    candidates = [Path(env)] if env else []
    candidates += [
        Path(r"G:\My Drive\Lemed"),
        Path.home() / "Google Drive" / "My Drive" / "Lemed",
    ]
    for p in candidates:
        try:
            if p.is_dir():
                return p
        except OSError:
            continue
    return None


def local_subfolders(local_root: Path) -> list[str]:
    try:
        return [p.name for p in local_root.iterdir() if p.is_dir()]
    except OSError:
        return []


def resolve_local_target(local_root: Path, path: Path,
                         platform_override: str = "") -> tuple[Path, str]:
    """Local destination for a file. Returns (target_dir, label)."""
    from google_drive import match_platform_folder_name

    kind = classify(path)
    platform = platform_override or guess_platform(path.name)
    names = local_subfolders(local_root)

    if platform:
        match = match_platform_folder_name(names, platform, is_video=(kind == "video"))
        if match:
            return local_root / match, f"{match} (ในเครื่อง)"

    wanted = FALLBACK_IMAGE_FOLDER if kind == "image" else FALLBACK_VIDEO_FOLDER
    for name in names:
        if name.strip().lower() == wanted.strip().lower():
            return local_root / name, f"{name} (ในเครื่อง)"
    return local_root, "โฟลเดอร์หลัก (ในเครื่อง)"


def _unique_path(target: Path) -> Path:
    """Avoid clobbering a file that is already there."""
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    for n in range(2, 100):
        candidate = target.with_name(f"{stem} ({n}){suffix}")
        if not candidate.exists():
            return candidate
    return target.with_name(f"{stem} ({os.getpid()}){suffix}")


def move_into_drive(path: Path, local_root: Path,
                    platform_override: str = "") -> dict:
    """Move a file into its Drive-for-Desktop folder. Drive syncs it from there."""
    record = {"name": path.name, "ok": False, "folder": "", "link": "",
              "error": "", "mode": "local"}
    target_dir, label = resolve_local_target(local_root, path, platform_override)
    record["folder"] = label
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = _unique_path(target_dir / path.name)
        shutil.move(str(path), str(dest))
        record["ok"] = True
        record["link"] = str(dest)
    except OSError as e:
        record["error"] = f"ย้ายไฟล์ไม่สำเร็จ: {e}"
    return record


def resolve_target(drive_root: str, path: Path, platform_override: str = "") -> tuple[str, str]:
    """Pick the Drive folder for a file. Returns (folder_id, folder_label).

    Flow names its exports things like "Product_photography_by_LEMED_2026….jpeg",
    with no hint of where the file should go — so an explicit override matters
    more here than the filename guess does.
    """
    from google_drive import resolve_platform_folder, list_child_folders

    kind = classify(path)
    platform = platform_override or guess_platform(path.name)

    if platform:
        fid = resolve_platform_folder(drive_root, platform, is_video=(kind == "video"))
        if fid:
            return fid, f"{platform} ({kind})"

    folders = list_child_folders(drive_root)
    wanted = FALLBACK_IMAGE_FOLDER if kind == "image" else FALLBACK_VIDEO_FOLDER
    for name, fid in folders.items():
        if name.strip().lower() == wanted.strip().lower():
            return fid, name
    # Last resort: the root itself, so a file is never silently dropped.
    return drive_root, "โฟลเดอร์หลัก"


def sync_file(path: Path, drive_root: str, move_done: bool = True,
              platform_override: str = "", local_root: Path | None = None) -> dict:
    """File one export into Drive.

    Prefers moving the file into the Drive-for-Desktop mirror when one is
    available; falls back to uploading through the API otherwise.
    """
    from google_drive import upload_file

    if local_root is not None:
        return move_into_drive(path, local_root, platform_override)

    record = {"name": path.name, "ok": False, "folder": "", "link": "",
              "error": "", "mode": "upload"}
    try:
        data = path.read_bytes()
    except OSError as e:
        record["error"] = f"อ่านไฟล์ไม่ได้: {e}"
        return record

    folder_id, label = resolve_target(drive_root, path, platform_override)
    record["folder"] = label
    mime = MIME_BY_EXT.get(path.suffix.lower(), "application/octet-stream")

    link = upload_file(data, path.name, folder_id, mime_type=mime)
    if not link:
        record["error"] = "อัปโหลดขึ้น Drive ไม่สำเร็จ"
        return record

    record["ok"] = True
    record["link"] = link

    if move_done:
        done_dir = path.parent / DONE_DIRNAME
        try:
            done_dir.mkdir(exist_ok=True)
            shutil.move(str(path), str(done_dir / path.name))
        except OSError as e:
            # The upload already succeeded; failing to tidy up is not fatal, but
            # say so or the next run will upload the same file again.
            record["error"] = f"อัปโหลดสำเร็จ แต่ย้ายไฟล์ไม่ได้: {e}"
    return record


def sync_folder(watch_dir: Path | str, drive_root: str,
                max_age_hours: int = 0, move_done: bool = True,
                limit: int = 50, on_progress=None,
                overrides: dict[str, str] | None = None,
                local_root: Path | None = None,
                prefer_local: bool = True) -> list[dict]:
    """Sync every new media file in watch_dir. Returns one record per file.

    `overrides` maps a filename to a platform key, letting the caller route files
    whose names carry no hint. A filename mapped to "skip" is left alone.

    With a Drive-for-Desktop mirror present, files are moved there instead of
    uploaded — set prefer_local=False to force the API path.
    """
    watch_dir = Path(watch_dir)
    overrides = overrides or {}
    if prefer_local and local_root is None:
        local_root = default_local_root()
    files = find_new_files(watch_dir, max_age_hours)[:limit]
    results: list[dict] = []
    for i, path in enumerate(files, 1):
        choice = overrides.get(path.name, "")
        if choice == "skip":
            continue
        if on_progress:
            try:
                on_progress(i, len(files), path.name)
            except Exception:  # noqa: BLE001
                pass
        results.append(sync_file(path, drive_root, move_done, choice, local_root))
    return results


def _queue_root() -> str:
    """Drive folder that holds the per-platform subfolders."""
    env = os.getenv("QUEUE_ROOT_FOLDER_ID", "").strip()
    if env:
        return env
    try:
        import streamlit as st
        cfg = st.secrets.get("google_drive", {}).get("queue_root_id", "")
        if cfg:
            return cfg
    except Exception:  # noqa: BLE001
        pass
    return "12sVv5PEq9KNk7JlPq0sKVUAfqvIf8Nzb"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    watch = default_watch_dir()
    root = _queue_root()
    local = default_local_root()
    print(f"เฝ้าโฟลเดอร์: {watch}")

    if local:
        print(f"โหมด        : ย้ายไฟล์ในเครื่อง → {local} (Drive ซิงก์ให้เอง)")
    else:
        print("โหมด        : อัปโหลดผ่าน Drive API")
        from google_drive import needs_auth
        if needs_auth():
            print("! ยังไม่ได้ authorize Google Drive — เปิดแอปแล้วกด Authorize ก่อน")
            return

    results = sync_folder(watch, root, local_root=local)
    if not results:
        print("ไม่มีไฟล์ใหม่")
        return
    ok = sum(1 for r in results if r["ok"])
    for r in results:
        mark = "✓" if r["ok"] else "✗"
        detail = r["folder"] if r["ok"] else r["error"]
        print(f"  {mark} {r['name']} → {detail}")
    print(f"เสร็จ: {ok}/{len(results)} ไฟล์")


if __name__ == "__main__":
    main()
