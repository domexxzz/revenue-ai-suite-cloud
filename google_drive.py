"""Google Drive uploader using OAuth2 Desktop App credentials."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCOPES = [
    # Full drive access is required to *list* subfolders that the account owner
    # created by hand (e.g. "Facebook Post", "TikTok VDO") so the queue can route
    # each draft into the right folder. `drive.file` alone only sees files the app
    # itself created, so folder discovery would return nothing.
    # NOTE: widening the scope requires the owner to re-authorize once.
    #
    # Drive scopes only. Google rejects a request that mixes YouTube and Drive
    # scopes ("scopes that cannot be requested together"), so YouTube authorises
    # separately into its own token — see youtube_uploader.YOUTUBE_TOKEN_PATH.
    "https://www.googleapis.com/auth/drive",
]
TOKEN_PATH = Path(__file__).parent / "token.json"
OAUTH_PATH = Path(__file__).parent / "oauth_credentials.json"


def _build_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import json

    creds = None

    # Try Streamlit secrets first (for cloud deployment)
    try:
        import streamlit as st
        token_json = st.secrets.get("google_drive", {}).get("token_json", "")
        if token_json:
            creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    except Exception:
        pass

    # Fallback to local token.json
    if creds is None and TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if TOKEN_PATH.exists():
                TOKEN_PATH.write_text(creds.to_json())
        else:
            return None

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def run_first_time_auth() -> str:
    """Run OAuth flow and save token. Returns auth URL if browser can't open."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_PATH.write_text(creds.to_json())
    return "auth_complete"


def needs_auth() -> bool:
    """Check if OAuth token is available (from secrets or local file)."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    import json

    # Try Streamlit secrets first (cloud deployment)
    try:
        import streamlit as st
        token_json = st.secrets.get("google_drive", {}).get("token_json", "")
        if token_json:
            creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
            if creds.valid:
                return False
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                return False
    except Exception:
        pass

    # Fallback to local token.json
    if not TOKEN_PATH.exists():
        return True
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if creds.valid:
            return False
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
            return False
    except Exception:
        pass
    return True


def upload_file(
    file_bytes: bytes,
    filename: str,
    folder_id: str,
    mime_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
) -> Optional[str]:
    """Upload bytes to Google Drive folder. Returns shareable URL or None on error."""
    try:
        from googleapiclient.http import MediaIoBaseUpload

        service = _build_service()
        if service is None:
            return None

        file_metadata = {"name": filename, "parents": [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=False)

        uploaded = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id,webViewLink")
            .execute()
        )

        web_link = uploaded.get("webViewLink", f"https://drive.google.com/file/d/{uploaded['id']}/view")
        return web_link

    except Exception as e:
        logger.error("Google Drive upload failed: %s", e)
        return None


def upload_text(text: str, filename: str, folder_id: str) -> Optional[str]:
    return upload_file(text.encode("utf-8"), filename, folder_id, mime_type="text/plain")


def upload_excel(file_bytes: bytes, filename: str, folder_id: str) -> Optional[str]:
    return upload_file(file_bytes, filename, folder_id,
                       mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def upload_image_public(image_bytes: bytes, filename: str, folder_id: str,
                        mime_type: str = "image/jpeg") -> Optional[str]:
    """Upload image to Drive, make it public, return direct image URL.

    The returned URL is suitable for LINE OA (HTTPS, returns image bytes).
    """
    try:
        import io
        from googleapiclient.http import MediaIoBaseUpload

        service = _build_service()
        if service is None:
            return None

        file_metadata = {"name": filename, "parents": [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=mime_type, resumable=False)

        uploaded = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        file_id = uploaded["id"]

        # Make file readable by anyone with link
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        # Return direct image URL (works for LINE OA / Facebook)
        return f"https://drive.google.com/uc?export=view&id={file_id}"

    except Exception as e:
        logger.error("Google Drive image upload failed: %s", e)
        return None


# ── Folder discovery / routing ──────────────────────────────────────────────────

# Platform → name fragments to look for in a subfolder title. Tolerant of the
# owner's spelling (e.g. "Instragram") and of Post/VDO suffixes.
_PLATFORM_ALIASES = {
    "facebook":  ["facebook", "fb"],
    "instagram": ["instagram", "instragram", "ig"],
    "tiktok":    ["tiktok", "tik tok"],
    "youtube":   ["youtube", "yt"],
    "line_oa":   ["line"],
}


def list_child_folders(parent_id: str) -> dict:
    """Return {folder_name: folder_id} for subfolders of parent_id.

    Requires the full `drive` scope — with only `drive.file` this returns {}
    because the API hides folders the app did not create. Callers should treat
    an empty result as "routing unavailable, fall back to the root folder".
    """
    try:
        service = _build_service()
        if service is None:
            return {}
        query = (
            f"'{parent_id}' in parents "
            "and mimeType='application/vnd.google-apps.folder' "
            "and trashed=false"
        )
        resp = (
            service.files()
            .list(
                q=query,
                fields="files(id,name)",
                pageSize=100,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        return {f["name"]: f["id"] for f in resp.get("files", [])}
    except Exception as e:
        logger.warning("Google Drive list_child_folders failed: %s", e)
        return {}


def list_files_in_folder(folder_id: str, page_size: int = 100) -> list[dict]:
    """Files directly inside a folder, newest first.

    Returns dicts with id, name, mimeType, size, createdTime, webViewLink.
    Folders are excluded — this is for reviewing content, not navigating.
    """
    try:
        service = _build_service()
        if service is None:
            return []
        query = (
            f"'{folder_id}' in parents "
            "and mimeType != 'application/vnd.google-apps.folder' "
            "and trashed=false"
        )
        resp = (
            service.files()
            .list(
                q=query,
                fields="files(id,name,mimeType,size,createdTime,webViewLink)",
                orderBy="createdTime desc",
                pageSize=page_size,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
        return resp.get("files", [])
    except Exception as e:
        logger.warning("Google Drive list_files_in_folder failed: %s", e)
        return []


def download_file(file_id: str) -> Optional[bytes]:
    """Download a Drive file's contents."""
    try:
        service = _build_service()
        if service is None:
            return None
        return service.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
    except Exception as e:
        logger.error("Google Drive download failed: %s", e)
        return None


def ensure_subfolder(parent_id: str, name: str) -> Optional[str]:
    """Return the id of a subfolder by name, creating it if missing."""
    existing = list_child_folders(parent_id)
    if name in existing:
        return existing[name]
    try:
        service = _build_service()
        if service is None:
            return None
        created = (
            service.files()
            .create(
                body={
                    "name": name,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [parent_id],
                },
                fields="id",
                supportsAllDrives=True,
            )
            .execute()
        )
        return created.get("id")
    except Exception as e:
        logger.error("Google Drive ensure_subfolder failed: %s", e)
        return None


def move_file(file_id: str, to_folder_id: str) -> bool:
    """Move a file into another folder (detaching it from its current parents)."""
    try:
        service = _build_service()
        if service is None:
            return False
        meta = service.files().get(
            fileId=file_id, fields="parents", supportsAllDrives=True).execute()
        previous = ",".join(meta.get("parents", []))
        service.files().update(
            fileId=file_id,
            addParents=to_folder_id,
            removeParents=previous,
            fields="id,parents",
            supportsAllDrives=True,
        ).execute()
        return True
    except Exception as e:
        logger.error("Google Drive move_file failed: %s", e)
        return False


def match_platform_folder_name(names, platform_key: str,
                               is_video: bool = False) -> Optional[str]:
    """Pick the folder name that matches a platform + Post/VDO type.

    Works on plain names so the same rule serves both Drive folders and local
    Drive-for-Desktop directories — routing must not drift between the two.
    Matching is case-insensitive and tolerant of spelling (e.g. "Instragram").
    """
    aliases = _PLATFORM_ALIASES.get(platform_key, [platform_key])
    type_keywords = ["vdo", "video"] if is_video else ["post"]

    # 1) best match: platform alias AND the right Post/VDO type
    for name in names:
        low = name.lower()
        if any(a in low for a in aliases) and any(t in low for t in type_keywords):
            return name
    # 2) looser match: platform alias only (any type)
    for name in names:
        if any(a in name.lower() for a in aliases):
            return name
    return None


def resolve_platform_folder(parent_id: str, platform_key: str, is_video: bool = False) -> Optional[str]:
    """Find the Drive subfolder that matches a platform + Post/VDO type.

    Returns the folder id, or None if no match / routing unavailable.
    """
    children = list_child_folders(parent_id)
    if not children:
        return None
    name = match_platform_folder_name(children.keys(), platform_key, is_video)
    return children.get(name) if name else None
