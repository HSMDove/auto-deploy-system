"""
twitter.py — X (Twitter) API v2 publisher.
Supports OAuth 2.0 PKCE for user auth + media upload.
"""
import os
import base64
import hashlib
import json
import logging
import secrets
import urllib.parse
from typing import Optional, List, Dict, Any

import requests

from platforms.base import BasePublisher, PublishResult
from core.config import get_secret, set_secret
from core.database import upsert_account, get_accounts

logger = logging.getLogger(__name__)

X_AUTH_BASE = "https://twitter.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
X_TWEETS_URL = "https://api.twitter.com/2/tweets"
X_MEDIA_UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"

REDIRECT_URI = "http://localhost:8501/callback/twitter"
SCOPES = "tweet.write tweet.read users.read offline.access media.write"


class TwitterPublisher(BasePublisher):
    def __init__(self, bearer_token: str, client_id: str, client_secret: str):
        self.bearer_token = bearer_token
        self.client_id = client_id
        self.client_secret = client_secret
        self._pkce_verifiers: Dict[str, str] = {}

    # ── OAuth 2.0 PKCE ───────────────────────────────────────────────────────

    def _generate_pkce_pair(self) -> tuple:
        """Generate code_verifier and code_challenge for PKCE."""
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return verifier, challenge

    def get_auth_url(self) -> str:
        verifier, challenge = self._generate_pkce_pair()
        state = secrets.token_urlsafe(16)
        # Store verifier keyed by state so handle_callback can retrieve it
        self._pkce_verifiers[state] = verifier

        # Persist verifier to keyring for cross-request retrieval
        set_secret(f"twitter_pkce_{state}", verifier)

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return X_AUTH_BASE + "?" + urllib.parse.urlencode(params)

    def handle_callback(self, code: str, account_name: str, state: str = "") -> bool:
        # Retrieve the PKCE verifier
        verifier = self._pkce_verifiers.get(state) or get_secret(f"twitter_pkce_{state}")
        if not verifier:
            logger.error("No PKCE verifier found for state '%s'", state)
            return False

        try:
            auth_str = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()

            resp = requests.post(
                X_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {auth_str}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": REDIRECT_URI,
                    "code_verifier": verifier,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token", "")

            if not access_token:
                logger.error("No access_token in X response: %s", data)
                return False

            account_id = f"x_{account_name}"
            set_secret(f"twitter_access_token_{account_id}", access_token)
            if refresh_token:
                set_secret(f"twitter_refresh_token_{account_id}", refresh_token)

            # Get user info
            user_info = self._get_user_info(access_token)
            display_name = user_info.get("name", account_name)
            x_user_id = user_info.get("id", "")

            upsert_account({
                "id": account_id,
                "platform": "x",
                "display_name": display_name,
                "account_id": x_user_id,
            })
            logger.info("X account %s connected", account_id)
            return True

        except Exception as e:
            logger.error("X handle_callback error: %s", e)
            return False

    def _get_access_token(self, account_id: str) -> Optional[str]:
        token = get_secret(f"twitter_access_token_{account_id}")
        if token:
            return token
        # Fallback: try refreshing
        refresh = get_secret(f"twitter_refresh_token_{account_id}")
        if refresh:
            return self._refresh_token(account_id, refresh)
        return None

    def _refresh_token(self, account_id: str, refresh_token: str) -> Optional[str]:
        try:
            auth_str = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            resp = requests.post(
                X_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {auth_str}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "refresh_token", "refresh_token": refresh_token},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            new_token = data.get("access_token")
            if new_token:
                set_secret(f"twitter_access_token_{account_id}", new_token)
                if data.get("refresh_token"):
                    set_secret(f"twitter_refresh_token_{account_id}", data["refresh_token"])
                return new_token
        except Exception as e:
            logger.error("X token refresh error: %s", e)
        return None

    def _get_user_info(self, access_token: str) -> Dict[str, str]:
        try:
            resp = requests.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("data", {})
        except Exception:
            return {}

    # ── Media Upload (v1.1) ──────────────────────────────────────────────────

    def _upload_media(self, media_path: str, access_token: str) -> Optional[str]:
        """Upload media using chunked INIT/APPEND/FINALIZE flow."""
        if not os.path.exists(media_path):
            return None

        file_size = os.path.getsize(media_path)
        ext = os.path.splitext(media_path)[1].lower()
        mime_map = {
            ".mp4": "video/mp4", ".mov": "video/quicktime",
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "video/mp4")
        media_category = "tweet_video" if mime_type.startswith("video") else "tweet_image"

        headers = {"Authorization": f"Bearer {access_token}"}

        # INIT
        init_resp = requests.post(
            X_MEDIA_UPLOAD_URL,
            headers=headers,
            data={
                "command": "INIT",
                "total_bytes": file_size,
                "media_type": mime_type,
                "media_category": media_category,
            },
            timeout=30,
        )
        if not init_resp.ok:
            logger.error("Media INIT failed: %s", init_resp.text)
            return None

        media_id = str(init_resp.json()["media_id"])

        # APPEND
        segment_index = 0
        chunk_size = 5 * 1024 * 1024  # 5 MB
        with open(media_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                append_resp = requests.post(
                    X_MEDIA_UPLOAD_URL,
                    headers=headers,
                    data={
                        "command": "APPEND",
                        "media_id": media_id,
                        "segment_index": segment_index,
                    },
                    files={"media": chunk},
                    timeout=120,
                )
                if not append_resp.ok:
                    logger.error("Media APPEND failed: %s", append_resp.text)
                    return None
                segment_index += 1

        # FINALIZE
        fin_resp = requests.post(
            X_MEDIA_UPLOAD_URL,
            headers=headers,
            data={"command": "FINALIZE", "media_id": media_id},
            timeout=30,
        )
        if not fin_resp.ok:
            logger.error("Media FINALIZE failed: %s", fin_resp.text)
            return None

        # Poll processing status for video
        if mime_type.startswith("video"):
            import time
            for _ in range(30):
                fin_data = fin_resp.json()
                processing = fin_data.get("processing_info", {})
                state = processing.get("state", "succeeded")
                if state == "succeeded":
                    break
                elif state == "failed":
                    return None
                time.sleep(processing.get("check_after_secs", 5))
                status_resp = requests.get(
                    X_MEDIA_UPLOAD_URL,
                    headers=headers,
                    params={"command": "STATUS", "media_id": media_id},
                    timeout=15,
                )
                if status_resp.ok:
                    fin_resp = status_resp

        return media_id

    # ── Publishing ───────────────────────────────────────────────────────────

    def publish_tweet(self, text: str, media_path: Optional[str], account_id: str) -> PublishResult:
        access_token = self._get_access_token(account_id)
        if not access_token:
            return PublishResult(success=False, error_msg="No access token for X account")

        try:
            payload: Dict[str, Any] = {"text": text[:280]}

            if media_path and os.path.exists(media_path):
                media_id = self._upload_media(media_path, access_token)
                if media_id:
                    payload["media"] = {"media_ids": [media_id]}

            resp = requests.post(
                X_TWEETS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            tweet_id = resp.json().get("data", {}).get("id", "")
            logger.info("X tweet posted: %s", tweet_id)
            return PublishResult(success=True, platform_post_id=tweet_id)

        except Exception as e:
            logger.error("X publish_tweet error: %s", e)
            return PublishResult(success=False, error_msg=str(e))

    def publish_video(
        self, video_path: str, cover_path: Optional[str], caption: str, account_id: str
    ) -> PublishResult:
        return self.publish_tweet(caption, video_path, account_id)

    def publish_photo(self, photo_paths: List[str], caption: str, account_id: str) -> PublishResult:
        access_token = self._get_access_token(account_id)
        if not access_token:
            return PublishResult(success=False, error_msg="No access token for X account")

        try:
            media_ids = []
            for path in photo_paths[:4]:  # max 4 images
                if os.path.exists(path):
                    mid = self._upload_media(path, access_token)
                    if mid:
                        media_ids.append(mid)

            payload: Dict[str, Any] = {"text": caption[:280]}
            if media_ids:
                payload["media"] = {"media_ids": media_ids}

            resp = requests.post(
                X_TWEETS_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            return PublishResult(success=True, platform_post_id=resp.json().get("data", {}).get("id", ""))

        except Exception as e:
            return PublishResult(success=False, error_msg=str(e))

    def get_connected_accounts(self) -> List[Dict[str, Any]]:
        return get_accounts("x")
