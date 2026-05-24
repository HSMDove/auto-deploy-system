"""
base.py — Abstract base class for all platform publishers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class PublishResult:
    success: bool
    platform_post_id: Optional[str] = None
    error_msg: Optional[str] = None


class BasePublisher(ABC):
    """Abstract publisher — all platform implementations must subclass this."""

    @abstractmethod
    def publish_video(
        self,
        video_path: str,
        cover_path: Optional[str],
        caption: str,
        account_id: str,
    ) -> PublishResult:
        """Upload and publish a video."""
        ...

    @abstractmethod
    def publish_photo(
        self,
        photo_paths: List[str],
        caption: str,
        account_id: str,
    ) -> PublishResult:
        """Publish one or more photos."""
        ...

    @abstractmethod
    def publish_tweet(
        self,
        text: str,
        media_path: Optional[str],
        account_id: str,
    ) -> PublishResult:
        """Post a tweet / X post, optionally with media."""
        ...

    @abstractmethod
    def get_auth_url(self) -> str:
        """Return the OAuth authorization URL for the user to open in their browser."""
        ...

    @abstractmethod
    def handle_callback(self, code: str, account_name: str) -> bool:
        """
        Exchange the OAuth authorization code for tokens and persist them.
        Returns True on success.
        """
        ...

    @abstractmethod
    def get_connected_accounts(self) -> List[Dict[str, Any]]:
        """Return a list of connected account dicts from the local DB."""
        ...
