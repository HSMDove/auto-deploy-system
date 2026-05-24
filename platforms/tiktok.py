"""
tiktok.py — TikTok Content Posting API v2 publisher.
Docs: https://developers.tiktok.com/doc/content-posting-api-get-started-overview
"""
import os
import time
import logging
import urllib.parse
import secrets
import hashlib
import base64
from typing import Optional, List, Dict, Any, Tuple

import requests

from platforms.base import BasePublisher, PublishResult
from core.config import get_secret, set_secret
from core.database import upsert_account, get_accounts

logger = logging.getLogger(__name__)

TIKTOK_AUTH_BASE = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_VIDEO_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_PUBLISH_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
TIKTOK_USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"

REDIRECT_URI = "https://hsmdove.github.io/auto-deploy-system/callback/tiktok"
SCOPES = "video.publish,user.info.basic"


def _generate_pkce() -> Tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    code_verifier = secrets.token_urlsafe(43)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return code_verifier, code_challenge


class TikTokPublisher(BasePublisher):
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    # ── OAuth ────────────────────────────────────────────────────────────────

    def get_auth_url(self) -> Tuple[str, str]:
        """Build the TikTok OAuth authorization URL with PKCE.
        Returns (auth_url, code_verifier) — store code_verifier for token exchange.
        """
        state = secrets.token_urlsafe(16)
        code_verifier, code_challenge = _generate_pkce()
        params = {
            "client_key": self.client_id,
            "scope": SCOPES,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        url = TIKTOK_AUTH_BASE + "?" + urllib.parse.urlencode(params)
        logger.info("TikTok auth URL generated (PKCE)")
        return url, code_verifier

    def handle_callback(self, code: str, account_name: str, code_verifier: str = "") -> bool:
        """Exchange authorization code for access/refresh tokens."""
        try:
            payload = {
                "client_key": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
            }
            if code_verifier:
                payload["code_verifier"] = code_verifier

            resp = requests.post(TIKTOK_TOKEN_URL, data=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "data" not in data:
                logger.error("TikTok token exchange failed: %s", data)
                return False

            token_data = data["data"]
            access_token = token_data.get("access_token")
            open_id = token_data.get("open_id", "")
            refresh_token = token_data.get("refresh_token", "")

            if not access_token:
                return False

            # Store tokens
            account_id = f"tiktok_{open_id or account_name}"
            set_secret(f"tiktok_access_token_{account_id}", access_token)
            if refresh_token:
                set_secret(f"tiktok_refresh_token_{account_id}", refresh_token)

            # Fetch display name
            display_name = self._get_user_display_name(access_token, open_id)

            upsert_account({
                "id": account_id,
                "platform": "tiktok",
                "display_name": display_name or account_name,
                "account_id": open_id,
            })
            logger.info("TikTok account %s connected", account_id)
            return True

        except Exception as e:
            logger.error("TikTok handle_callback error: %s", e)
            return False

    def _get_user_display_name(self, access_token: str, open_id: str) -> str:
        try:
            resp = requests.get(
                TIKTOK_USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "display_name,avatar_url", "open_id": open_id},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("user", {}).get("display_name", "")
        except Exception:
            return ""

    def _get_access_token(self, account_id: str) -> Optional[str]:
        return get_secret(f"tiktok_access_token_{account_id}")

    # ── Publishing ───────────────────────────────────────────────────────────

    def publish_video(
        self,
        video_path: str,
        cover_path: Optional[str],
        caption: str,
        account_id: str,
    ) -> PublishResult:
        access_token = self._get_access_token(account_id)
        if not access_token:
            return PublishResult(success=False, error_msg="No access token for account")

        # Decide strategy: PULL_FROM_URL if video_path is URL, else FILE_UPLOAD
        if video_path.startswith("http"):
            return self._publish_video_pull(access_token, video_path, caption, cover_path)
        else:
            return self._publish_video_upload(access_token, video_path, caption, cover_path)

    def _publish_video_upload(
        self, access_token: str, video_path: str, caption: str,
        cover_path: Optional[str]
    ) -> PublishResult:
        """FILE_UPLOAD flow: init → chunk upload → poll status."""
        try:
            if not os.path.exists(video_path):
                return PublishResult(success=False, error_msg=f"Video file not found: {video_path}")

            file_size = os.path.getsize(video_path)

            # Step 1: Init
            init_body: Dict[str, Any] = {
                "post_info": {
                    "title": caption[:150],
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                    "video_cover_timestamp_ms": 1000,
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                    "chunk_size": min(file_size, 10 * 1024 * 1024),  # up to 10 MB chunks
                    "total_chunk_count": max(1, (file_size + 10 * 1024 * 1024 - 1) // (10 * 1024 * 1024)),
                }
            }

            resp = requests.post(
                TIKTOK_VIDEO_INIT_URL,
                json=init_body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                timeout=30,
            )
            resp.raise_for_status()
            init_data = resp.json()

            if init_data.get("error", {}).get("code", "ok") != "ok":
                return PublishResult(
                    success=False,
                    error_msg=f"Init error: {init_data.get('error', {}).get('message')}"
                )

            upload_url = init_data["data"]["upload_url"]
            publish_id = init_data["data"]["publish_id"]

            # Step 2: Upload chunks
            chunk_size = 10 * 1024 * 1024  # 10 MB
            with open(video_path, "rb") as f:
                chunk_idx = 0
                offset = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    end_offset = offset + len(chunk) - 1
                    put_resp = requests.put(
                        upload_url,
                        data=chunk,
                        headers={
                            "Content-Range": f"bytes {offset}-{end_offset}/{file_size}",
                            "Content-Type": "video/mp4",
                            "Content-Length": str(len(chunk)),
                        },
                        timeout=120,
                    )
                    if put_resp.status_code not in (200, 201, 206):
                        return PublishResult(
                            success=False,
                            error_msg=f"Chunk {chunk_idx} upload failed: {put_resp.status_code}"
                        )
                    offset += len(chunk)
                    chunk_idx += 1

            # Step 3: Poll status
            return self._poll_publish_status(access_token, publish_id)

        except Exception as e:
            logger.error("TikTok upload error: %s", e)
            return PublishResult(success=False, error_msg=str(e))

    def _publish_video_pull(
        self, access_token: str, video_url: str, caption: str,
        cover_url: Optional[str]
    ) -> PublishResult:
        """PULL_FROM_URL flow."""
        try:
            body: Dict[str, Any] = {
                "post_info": {
                    "title": caption[:150],
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": video_url,
                }
            }
            if cover_url:
                body["post_info"]["cover_url"] = cover_url

            resp = requests.post(
                TIKTOK_VIDEO_INIT_URL,
                json=body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("error", {}).get("code", "ok") != "ok":
                return PublishResult(
                    success=False,
                    error_msg=f"Pull init error: {data.get('error', {}).get('message')}"
                )

            publish_id = data["data"]["publish_id"]
            return self._poll_publish_status(access_token, publish_id)

        except Exception as e:
            return PublishResult(success=False, error_msg=str(e))

    def _poll_publish_status(self, access_token: str, publish_id: str) -> PublishResult:
        """Poll publish status until done or failed (max 2 minutes)."""
        max_polls = 24  # 24 * 5s = 2 min
        for _ in range(max_polls):
            try:
                resp = requests.post(
                    TIKTOK_PUBLISH_STATUS_URL,
                    json={"publish_id": publish_id},
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json; charset=UTF-8",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                status = data.get("data", {}).get("status", "")

                if status == "PUBLISH_COMPLETE":
                    post_id = data.get("data", {}).get("publicaly_available_post_id", [None])[0]
                    return PublishResult(success=True, platform_post_id=str(post_id))
                elif status in ("FAILED", "PUBLISH_FAILED"):
                    fail_reason = data.get("data", {}).get("fail_reason", "Unknown")
                    return PublishResult(success=False, error_msg=f"TikTok publish failed: {fail_reason}")
                # Still processing: SENDING_TO_USER_INBOX, DOWNLOAD_TIMEOUT, etc.
                time.sleep(5)

            except Exception as e:
                return PublishResult(success=False, error_msg=str(e))

        return PublishResult(success=False, error_msg="Publish status poll timeout")

    def publish_photo(self, photo_paths: List[str], caption: str, account_id: str) -> PublishResult:
        return PublishResult(success=False, error_msg="TikTok photo posts not supported via this API")

    def publish_tweet(self, text: str, media_path: Optional[str], account_id: str) -> PublishResult:
        return PublishResult(success=False, error_msg="TikTok does not support tweet-type posts")

    def get_connected_accounts(self) -> List[Dict[str, Any]]:
        return get_accounts("tiktok")
