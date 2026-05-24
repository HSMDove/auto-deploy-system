"""
instagram.py — Meta Graph API publisher for Instagram.
Uses the Content Publishing API (Reels + Photo).
Docs: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
"""
import os
import time
import logging
from typing import Optional, List, Dict, Any

import requests

from platforms.base import BasePublisher, PublishResult
from core.config import get_secret, set_secret
from core.database import upsert_account, get_accounts

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
IG_AUTH_URL = "https://api.instagram.com/oauth/authorize"
IG_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
IG_LONG_TOKEN_URL = "https://graph.instagram.com/access_token"
REDIRECT_URI = "http://localhost:8501/callback/instagram"
SCOPES = "instagram_basic,instagram_content_publish,pages_read_engagement"


class InstagramPublisher(BasePublisher):
    # ── OAuth ────────────────────────────────────────────────────────────────

    def _get_app_credentials(self):
        app_id = get_secret("instagram_app_id") or get_secret("tiktok_client_id")  # reuse if same Meta app
        app_secret = get_secret("instagram_app_secret") or get_secret("tiktok_client_secret")
        return app_id, app_secret

    def get_auth_url(self) -> str:
        import urllib.parse, secrets
        app_id, _ = self._get_app_credentials()
        if not app_id:
            return ""
        state = secrets.token_urlsafe(16)
        params = {
            "client_id": app_id,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "response_type": "code",
            "state": state,
        }
        return IG_AUTH_URL + "?" + urllib.parse.urlencode(params)

    def handle_callback(self, code: str, account_name: str) -> bool:
        app_id, app_secret = self._get_app_credentials()
        if not app_id or not app_secret:
            logger.error("Instagram app_id or app_secret not configured")
            return False
        try:
            # Step 1: Get short-lived token
            resp = requests.post(IG_TOKEN_URL, data={
                "client_id": app_id,
                "client_secret": app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
                "code": code,
            }, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            short_token = data.get("access_token")
            ig_user_id = str(data.get("user_id", ""))

            # Step 2: Exchange for long-lived token
            long_resp = requests.get(IG_LONG_TOKEN_URL, params={
                "grant_type": "ig_exchange_token",
                "client_secret": app_secret,
                "access_token": short_token,
            }, timeout=30)
            long_resp.raise_for_status()
            long_data = long_resp.json()
            long_token = long_data.get("access_token", short_token)

            account_id = f"instagram_{ig_user_id or account_name}"
            set_secret(f"instagram_access_token_{account_id}", long_token)

            # Get username
            username = self._get_username(long_token, ig_user_id)

            upsert_account({
                "id": account_id,
                "platform": "instagram",
                "display_name": username or account_name,
                "account_id": ig_user_id,
            })
            logger.info("Instagram account %s connected", account_id)
            return True

        except Exception as e:
            logger.error("Instagram handle_callback error: %s", e)
            return False

    def _get_token(self, account_id: str) -> Optional[str]:
        return get_secret(f"instagram_access_token_{account_id}")

    def _get_username(self, token: str, ig_user_id: str) -> str:
        try:
            resp = requests.get(
                f"{GRAPH_API_BASE}/{ig_user_id}",
                params={"fields": "username", "access_token": token},
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("username", "")
        except Exception:
            return ""

    def _get_ig_user_id(self, account_id: str, token: str) -> Optional[str]:
        """Get the IG User ID from the accounts DB."""
        accounts = get_accounts("instagram")
        for acc in accounts:
            if acc["id"] == account_id:
                return acc.get("account_id")
        return None

    # ── Publishing ───────────────────────────────────────────────────────────

    def publish_video(
        self,
        video_path: str,
        cover_path: Optional[str],
        caption: str,
        account_id: str,
    ) -> PublishResult:
        token = self._get_token(account_id)
        if not token:
            return PublishResult(success=False, error_msg="No access token for Instagram account")

        ig_user_id = self._get_ig_user_id(account_id, token)
        if not ig_user_id:
            return PublishResult(success=False, error_msg="Instagram user ID not found")

        try:
            # Instagram Reels require a publicly accessible video URL.
            # If we have a local file we cannot upload it directly via the Graph API —
            # the caller should pass the video URL from Notion/Drive instead.
            if not video_path.startswith("http"):
                return PublishResult(
                    success=False,
                    error_msg="Instagram Reels require a public video URL. Local file upload not supported."
                )

            # Step 1: Create media container
            container_params: Dict[str, Any] = {
                "media_type": "REELS",
                "video_url": video_path,
                "caption": caption,
                "access_token": token,
                "share_to_feed": True,
            }
            if cover_path and cover_path.startswith("http"):
                container_params["cover_url"] = cover_path

            resp = requests.post(
                f"{GRAPH_API_BASE}/{ig_user_id}/media",
                data=container_params,
                timeout=60,
            )
            resp.raise_for_status()
            container_id = resp.json().get("id")
            if not container_id:
                return PublishResult(success=False, error_msg="No container ID returned")

            # Step 2: Poll container status
            container_ready = self._wait_for_container(token, container_id)
            if not container_ready:
                return PublishResult(success=False, error_msg="Container processing timed out")

            # Step 3: Publish
            pub_resp = requests.post(
                f"{GRAPH_API_BASE}/{ig_user_id}/media_publish",
                data={"creation_id": container_id, "access_token": token},
                timeout=30,
            )
            pub_resp.raise_for_status()
            post_id = pub_resp.json().get("id", "")

            logger.info("Instagram Reel published: %s", post_id)
            return PublishResult(success=True, platform_post_id=post_id)

        except Exception as e:
            logger.error("Instagram publish_video error: %s", e)
            return PublishResult(success=False, error_msg=str(e))

    def publish_photo(self, photo_paths: List[str], caption: str, account_id: str) -> PublishResult:
        token = self._get_token(account_id)
        if not token:
            return PublishResult(success=False, error_msg="No access token for Instagram account")

        ig_user_id = self._get_ig_user_id(account_id, token)
        if not ig_user_id:
            return PublishResult(success=False, error_msg="Instagram user ID not found")

        if not photo_paths:
            return PublishResult(success=False, error_msg="No photos provided")

        try:
            # Single photo
            if len(photo_paths) == 1:
                photo_url = photo_paths[0]
                if not photo_url.startswith("http"):
                    return PublishResult(
                        success=False,
                        error_msg="Instagram requires public URLs for photos"
                    )

                resp = requests.post(
                    f"{GRAPH_API_BASE}/{ig_user_id}/media",
                    data={
                        "image_url": photo_url,
                        "caption": caption,
                        "access_token": token,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                container_id = resp.json().get("id")

                pub_resp = requests.post(
                    f"{GRAPH_API_BASE}/{ig_user_id}/media_publish",
                    data={"creation_id": container_id, "access_token": token},
                    timeout=30,
                )
                pub_resp.raise_for_status()
                post_id = pub_resp.json().get("id", "")
                return PublishResult(success=True, platform_post_id=post_id)

            # Carousel (multiple photos)
            child_ids = []
            for photo_url in photo_paths[:10]:  # max 10
                if not photo_url.startswith("http"):
                    continue
                r = requests.post(
                    f"{GRAPH_API_BASE}/{ig_user_id}/media",
                    data={
                        "image_url": photo_url,
                        "is_carousel_item": True,
                        "access_token": token,
                    },
                    timeout=30,
                )
                r.raise_for_status()
                child_ids.append(r.json().get("id"))

            if not child_ids:
                return PublishResult(success=False, error_msg="No valid photo URLs for carousel")

            carousel_resp = requests.post(
                f"{GRAPH_API_BASE}/{ig_user_id}/media",
                data={
                    "media_type": "CAROUSEL",
                    "children": ",".join(child_ids),
                    "caption": caption,
                    "access_token": token,
                },
                timeout=30,
            )
            carousel_resp.raise_for_status()
            carousel_id = carousel_resp.json().get("id")

            pub_resp = requests.post(
                f"{GRAPH_API_BASE}/{ig_user_id}/media_publish",
                data={"creation_id": carousel_id, "access_token": token},
                timeout=30,
            )
            pub_resp.raise_for_status()
            return PublishResult(success=True, platform_post_id=pub_resp.json().get("id", ""))

        except Exception as e:
            logger.error("Instagram publish_photo error: %s", e)
            return PublishResult(success=False, error_msg=str(e))

    def _wait_for_container(self, token: str, container_id: str, max_wait: int = 120) -> bool:
        """Poll container status until FINISHED or timeout."""
        deadline = time.time() + max_wait
        while time.time() < deadline:
            try:
                resp = requests.get(
                    f"{GRAPH_API_BASE}/{container_id}",
                    params={"fields": "status_code", "access_token": token},
                    timeout=15,
                )
                resp.raise_for_status()
                status = resp.json().get("status_code", "")
                if status == "FINISHED":
                    return True
                if status in ("ERROR", "EXPIRED"):
                    return False
                time.sleep(5)
            except Exception:
                time.sleep(5)
        return False

    def publish_tweet(self, text: str, media_path: Optional[str], account_id: str) -> PublishResult:
        return PublishResult(success=False, error_msg="Instagram does not support tweet-type posts")

    def get_connected_accounts(self) -> List[Dict[str, Any]]:
        return get_accounts("instagram")
