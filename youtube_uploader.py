"""YouTube video uploader using existing Google OAuth token."""
from __future__ import annotations

import io
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def _build_youtube_service():
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    import json

    SCOPES = [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/youtube.upload",
    ]
    TOKEN_PATH = Path(__file__).parent / "token.json"

    creds = None

    # Try Streamlit secrets first
    try:
        import streamlit as st
        token_json = st.secrets.get("google_drive", {}).get("token_json", "")
        if token_json:
            creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    except Exception:
        pass

    if creds is None and TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if TOKEN_PATH.exists():
                TOKEN_PATH.write_text(creds.to_json())
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
