"""
drive_client.py — Download media files from Google Drive or direct URLs.
"""
import os
import re
import logging
import urllib.parse
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

TMP_DIR = os.path.expanduser("~/.techvoice-publisher/tmp")


def _ensure_tmp_dir() -> str:
    os.makedirs(TMP_DIR, exist_ok=True)
    return TMP_DIR


def _extract_drive_file_id(url: str) -> Optional[str]:
    """
    Extract the Google Drive file ID from various URL formats:
    - https://drive.google.com/file/d/{ID}/view
    - https://drive.google.com/open?id={ID}
    - https://drive.google.com/uc?id={ID}
    - Just a raw file ID (no slashes, no protocol)
    """
    # Pattern 1: /file/d/{ID}/
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)

    # Pattern 2: ?id={ID} or &id={ID}
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if "id" in qs:
        return qs["id"][0]

    # Pattern 3: raw ID (no slashes, looks like a Drive ID)
    if re.match(r"^[a-zA-Z0-9_-]{25,}$", url):
        return url

    return None


def _is_drive_url(url: str) -> bool:
    return "drive.google.com" in url or "docs.google.com" in url


def _is_local_path(url: str) -> bool:
    return url.startswith("/") or url.startswith("~") or os.path.exists(os.path.expanduser(url))


def download_file(url_or_id: str, dest_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Download a file from Google Drive, a direct URL, or use a local path.

    Args:
        url_or_id: Google Drive share URL, direct HTTP URL, local path, or Drive file ID.
        dest_path: Destination file path. If None, a temp path is auto-generated.

    Returns:
        (success: bool, file_path: str)
    """
    _ensure_tmp_dir()

    # Handle local paths
    if _is_local_path(url_or_id):
        local = os.path.expanduser(url_or_id)
        if os.path.exists(local):
            return True, local
        return False, f"Local file not found: {local}"

    # Auto-generate dest_path if not provided
    if not dest_path:
        filename = _guess_filename(url_or_id)
        dest_path = os.path.join(TMP_DIR, filename)

    # Google Drive
    if _is_drive_url(url_or_id):
        return _download_from_drive(url_or_id, dest_path)

    # Raw Drive file ID
    file_id = _extract_drive_file_id(url_or_id)
    if file_id and not url_or_id.startswith("http"):
        return _download_from_drive(f"https://drive.google.com/uc?id={file_id}", dest_path)

    # Direct HTTP/HTTPS URL
    return _download_direct(url_or_id, dest_path)


def _download_from_drive(url: str, dest_path: str) -> Tuple[bool, str]:
    """Download using gdown."""
    try:
        import gdown  # type: ignore

        file_id = _extract_drive_file_id(url)
        if file_id:
            download_url = f"https://drive.google.com/uc?id={file_id}"
        else:
            download_url = url

        result = gdown.download(download_url, dest_path, quiet=False, fuzzy=True)
        if result and os.path.exists(dest_path):
            logger.info("Downloaded Drive file to %s", dest_path)
            return True, dest_path
        return False, f"gdown returned no output for URL: {url}"

    except ImportError:
        return False, "gdown is not installed. Run: pip install gdown"
    except Exception as e:
        logger.error("Drive download error: %s", e)
        return False, str(e)


def _download_direct(url: str, dest_path: str) -> Tuple[bool, str]:
    """Download from a direct HTTP/HTTPS URL using requests with streaming."""
    try:
        import requests

        logger.info("Downloading directly from %s", url)
        with requests.get(url, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        if os.path.exists(dest_path):
            size_mb = os.path.getsize(dest_path) / (1024 * 1024)
            logger.info("Downloaded %.1f MB to %s", size_mb, dest_path)
            return True, dest_path

        return False, "Download completed but file not found"

    except Exception as e:
        logger.error("Direct download error: %s", e)
        return False, str(e)


def _guess_filename(url: str) -> str:
    """Guess a filename from URL, fallback to timestamp-based name."""
    import hashlib
    import time

    try:
        parsed = urllib.parse.urlparse(url)
        basename = os.path.basename(parsed.path)
        if basename and "." in basename:
            return basename
    except Exception:
        pass

    ts = int(time.time())
    short = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"media_{ts}_{short}"


def cleanup_tmp_file(file_path: str) -> None:
    """Delete a temp file if it lives inside TMP_DIR."""
    if file_path and file_path.startswith(TMP_DIR):
        try:
            os.remove(file_path)
            logger.debug("Cleaned up temp file: %s", file_path)
        except OSError as e:
            logger.warning("Could not delete temp file %s: %s", file_path, e)


def cleanup_tmp_dir() -> int:
    """Delete all files in TMP_DIR. Returns count of deleted files."""
    count = 0
    if not os.path.exists(TMP_DIR):
        return 0
    for fname in os.listdir(TMP_DIR):
        fpath = os.path.join(TMP_DIR, fname)
        if os.path.isfile(fpath):
            try:
                os.remove(fpath)
                count += 1
            except OSError:
                pass
    return count
