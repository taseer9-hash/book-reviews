"""Uploads the finished video to YouTube using the Data API v3.

Auth uses a pre-generated OAuth refresh token (see README: "YouTube auth
setup") so the pipeline can run unattended in GitHub Actions — no browser
login step happens at runtime.
"""
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.config import Secrets

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_credentials() -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=Secrets.YOUTUBE_REFRESH_TOKEN,
        client_id=Secrets.YOUTUBE_CLIENT_ID,
        client_secret=Secrets.YOUTUBE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def upload_video(video_path: str, title: str, description: str, cfg: dict) -> str:
    """Uploads the video and returns the resulting YouTube video ID."""
    creds = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    yt_cfg = cfg["youtube"]
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": yt_cfg["default_tags"],
            "categoryId": yt_cfg["category_id"],
        },
        "status": {
            "privacyStatus": yt_cfg["privacy_status"],
            "selfDeclaredMadeForKids": yt_cfg["made_for_kids"],
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[youtube] upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"[youtube] uploaded: https://youtube.com/watch?v={video_id}")
    return video_id
