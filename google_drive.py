"""Google Drive uploader using OAuth2 Desktop App credentials."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
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
