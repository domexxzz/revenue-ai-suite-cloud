"""YouTube video uploader using existing Google OAuth token."""
from __future__ import annotations

import io
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


# Google refuses an OAuth request that mixes YouTube and Drive scopes, so YouTube
# gets its own consent round and its own token file rather than sharing Drive's.
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_TOKEN_PATH = Path(__file__).parent / "youtube_token.json"
OAUTH_PATH = Path(__file__).parent / "oauth_credentials.json"


def needs_auth() -> bool:
    """True when YouTube still needs its own authorization."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    import json

    try:
        import streamlit as st
        token_json = st.secrets.get("youtube", {}).get("token_json", "")
        if token_json:
            creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
            if creds.valid:
                return False
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                return False
    except Exception:
        pass

    if not YOUTUBE_TOKEN_PATH.exists():
        return True
    try:
        creds = Credentials.from_authorized_user_file(str(YOUTUBE_TOKEN_PATH), SCOPES)
        if creds.valid:
            return False
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            YOUTUBE_TOKEN_PATH.write_text(creds.to_json())
            return False
    except Exception:
        pass
    return True


def run_first_time_auth() -> str:
    """Run the YouTube-only OAuth flow and save its token."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    YOUTUBE_TOKEN_PATH.write_text(creds.to_json())
    return "auth_complete"


def _build_youtube_service():
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    import json

    creds = None

    # Streamlit secrets first (cloud deployment), then the local token file.
    try:
        import streamlit as st
        token_json = st.secrets.get("youtube", {}).get("token_json", "")
        if token_json:
            creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    except Exception:
        pass

    if creds is None and YOUTUBE_TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(YOUTUBE_TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            YOUTUBE_TOKEN_PATH.write_text(creds.to_json())
        else:
            return None

    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_video(
    video_bytes: bytes,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    privacy: str = "public",  # "public" | "private" | "unlisted"
    category_id: str = "22",  # 22 = People & Blogs
) -> tuple[bool, str]:
    """Upload a video to YouTube. Returns (ok, message_or_url)."""
    try:
        from googleapiclient.http import MediaIoBaseUpload

        service = _build_youtube_service()
        if service is None:
            return False, "ยังไม่ได้ authorize YouTube (re-auth Google)"

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaIoBaseUpload(
            io.BytesIO(video_bytes),
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024,
        )

        request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()

        video_id = response.get("id")
        if video_id:
            return True, f"https://www.youtube.com/watch?v={video_id}"
        return False, "Upload เสร็จแต่ไม่ได้ video ID"

    except Exception as e:
        logger.error("YouTube upload failed: %s", e)
        return False, f"Error: {e}"
