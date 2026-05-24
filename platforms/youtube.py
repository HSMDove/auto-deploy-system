"""
youtube.py — YouTube Data API v3 publisher via google-auth-oauthlib.
"""
import os
import json
import logging
import secrets
from typing import Optional, List, Dict, Any

from platforms.base import BasePublisher, PublishResult
from core.config import get_secret, set_secret
from core.database import upsert_account, get_accounts

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
REDIRECT_URI = "http://localhost:8501/callback/youtube"

# Where to store OAuth2 client secrets temporarily for the flow
_CLIENT_SECRETS_TEMPLATE = {
    "installed": {
        "client_id": "",
        "client_secret": "",
        "redirect_uris": [REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


class YouTubePublisher(BasePublisher):
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    # ── OAuth ────────────────────────────────────────────────────────────────

    def _build_flow(self):
        from google_auth_oauthlib.flow import Flow

        client_config = json.loads(json.dumps(_CLIENT_SECRETS_TEMPLATE))
        client_config["installed"]["client_id"] = self.client_id
        client_config["installed"]["client_secret"] = self.client_secret

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        return flow

    def get_auth_url(self) -> str:
        flow = self._build_flow()
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url

    def handle_callback(self, code: str, account_name: str) -> bool:
        try:
            flow = self._build_flow()
            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Store tokens as JSON
            token_data = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
            }

            account_id = f"youtube_{account_name}"
            set_secret(f"youtube_tokens_{account_id}", json.dumps(token_data))

            # Get channel info
            display_name, channel_id = self._get_channel_info(credentials)

            upsert_account({
                "id": account_id,
                "platform": "youtube",
                "display_name": display_name or account_name,
                "account_id": channel_id or "",
            })
            logger.info("YouTube account %s connected", account_id)
            return True

        except Exception as e:
            logger.error("YouTube handle_callback error: %s", e)
            return False

    def _get_credentials(self, account_id: str):
        from google.oauth2.credentials import Credentials

        token_json = get_secret(f"youtube_tokens_{account_id}")
        if not token_json:
            return None

        try:
            data = json.loads(token_json)
            creds = Credentials(
                token=data.get("token"),
                refresh_token=data.get("refresh_token"),
                token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=data.get("client_id", self.client_id),
                client_secret=data.get("client_secret", self.client_secret),
                scopes=data.get("scopes", SCOPES),
            )
            # Refresh if expired
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                # Persist refreshed token
                data["token"] = creds.token
                set_secret(f"youtube_tokens_{account_id}", json.dumps(data))
            return creds
        except Exception as e:
            logger.error("Failed to load YouTube credentials: %s", e)
            return None

    def _get_channel_info(self, credentials) -> tuple:
        try:
            from googleapiclient.discovery import build
            service = build("youtube", "v3", credentials=credentials)
            resp = service.channels().list(part="snippet", mine=True).execute()
            items = resp.get("items", [])
            if items:
                snippet = items[0].get("snippet", {})
                return snippet.get("title", ""), items[0].get("id", "")
        except Exception:
            pass
        return "", ""

    # ── Publishing ───────────────────────────────────────────────────────────

    def publish_video(
        self,
        video_path: str,
        cover_path: Optional[str],
        caption: str,
        account_id: str,
    ) -> PublishResult:
        creds = self._get_credentials(account_id)
        if not creds:
            return PublishResult(success=False, error_msg="No credentials for YouTube account")

        if not video_path or not os.path.exists(video_path):
            return PublishResult(success=False, error_msg=f"Video file not found: {video_path}")

        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from googleapiclient.errors import HttpError

            service = build("youtube", "v3", credentials=creds)

            # Split caption: first line = title, rest = description
            lines = caption.strip().split("\n", 1)
            title = lines[0][:100] if lines else "فيديو جديد"
            description = lines[1] if len(lines) > 1 else caption

            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "categoryId": "22",  # People & Blogs
                    "defaultLanguage": "ar",
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            }

            mime_type = "video/mp4"
            if video_path.endswith(".mov"):
                mime_type = "video/quicktime"
            elif video_path.endswith(".avi"):
                mime_type = "video/x-msvideo"

            media = MediaFileUpload(video_path, mimetype=mime_type, resumable=True, chunksize=10 * 1024 * 1024)

            request = service.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info("YouTube upload: %d%%", int(status.progress() * 100))

            video_id = response.get("id", "")

            # Set thumbnail if cover provided
            if cover_path and os.path.exists(cover_path) and video_id:
                try:
                    thumb_media = MediaFileUpload(cover_path, mimetype="image/jpeg")
                    service.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
                except Exception as thumb_err:
                    logger.warning("Failed to set thumbnail: %s", thumb_err)

            logger.info("YouTube video published: %s", video_id)
            return PublishResult(success=True, platform_post_id=video_id)

        except Exception as e:
            logger.error("YouTube publish error: %s", e)
            return PublishResult(success=False, error_msg=str(e))

    def publish_photo(self, photo_paths: List[str], caption: str, account_id: str) -> PublishResult:
        return PublishResult(success=False, error_msg="YouTube does not support photo posts")

    def publish_tweet(self, text: str, media_path: Optional[str], account_id: str) -> PublishResult:
        return PublishResult(success=False, error_msg="YouTube does not support tweet-type posts")

    def get_connected_accounts(self) -> List[Dict[str, Any]]:
        return get_accounts("youtube")
