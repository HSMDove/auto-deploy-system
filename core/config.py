"""
config.py — Secure secret management using macOS Keychain via keyring,
with .env file fallback.
"""
import os
import logging
from typing import Optional

try:
    import keyring
    import keyring.errors
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/.techvoice-publisher/.env"))
except ImportError:
    pass

logger = logging.getLogger(__name__)

SERVICE_NAME = "techvoice-publisher"

# All known secret keys
SECRET_KEYS = [
    "notion_token",
    "notion_database_id",
    "tiktok_client_id",
    "tiktok_client_secret",
    "youtube_client_id",
    "youtube_client_secret",
    "twitter_bearer_token",
    "twitter_client_id",
    "twitter_client_secret",
]


def get_secret(key: str) -> Optional[str]:
    """
    Retrieve a secret. Checks keyring first, then environment variables,
    then the .env file at ~/.techvoice-publisher/.env.
    """
    # 1. Try keyring (macOS Keychain)
    if KEYRING_AVAILABLE:
        try:
            value = keyring.get_password(SERVICE_NAME, key)
            if value:
                return value
        except keyring.errors.KeyringError as e:
            logger.warning(f"Keyring read error for '{key}': {e}")

    # 2. Fallback to environment variable
    env_key = key.upper()
    value = os.environ.get(env_key)
    if value:
        return value

    # 3. Fallback to .env file directly
    env_path = os.path.expanduser("~/.techvoice-publisher/.env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    if k.strip().upper() == env_key:
                        return v.strip()
        except OSError as e:
            logger.warning(f".env read error: {e}")

    return None


def set_secret(key: str, value: str) -> bool:
    """
    Store a secret. Tries keyring first, falls back to .env file.
    Returns True on success.
    """
    if KEYRING_AVAILABLE:
        try:
            keyring.set_password(SERVICE_NAME, key, value)
            return True
        except keyring.errors.KeyringError as e:
            logger.warning(f"Keyring write error for '{key}': {e}")

    # Fallback: write to .env file
    return _write_to_env_file(key, value)


def delete_secret(key: str) -> bool:
    """
    Delete a secret from keyring and .env file.
    Returns True if deleted from at least one location.
    """
    deleted = False

    if KEYRING_AVAILABLE:
        try:
            keyring.delete_password(SERVICE_NAME, key)
            deleted = True
        except keyring.errors.PasswordDeleteError:
            pass
        except keyring.errors.KeyringError as e:
            logger.warning(f"Keyring delete error for '{key}': {e}")

    # Also remove from .env file if present
    if _delete_from_env_file(key):
        deleted = True

    return deleted


def is_configured() -> bool:
    """
    Returns True if the minimum required configuration is present:
    notion_token and notion_database_id.
    """
    return bool(get_secret("notion_token") and get_secret("notion_database_id"))


def _write_to_env_file(key: str, value: str) -> bool:
    """Write or update a key=value line in ~/.techvoice-publisher/.env."""
    env_dir = os.path.expanduser("~/.techvoice-publisher")
    env_path = os.path.join(env_dir, ".env")
    os.makedirs(env_dir, exist_ok=True)

    lines = []
    found = False
    env_key = key.upper()

    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            lines = []

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        k, _, _ = stripped.partition("=")
        if k.strip().upper() == env_key:
            new_lines.append(f"{env_key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{env_key}={value}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    except OSError as e:
        logger.error(f"Failed to write .env file: {e}")
        return False


def _delete_from_env_file(key: str) -> bool:
    """Remove a key from ~/.techvoice-publisher/.env. Returns True if removed."""
    env_path = os.path.expanduser("~/.techvoice-publisher/.env")
    if not os.path.exists(env_path):
        return False

    env_key = key.upper()
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        removed = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") or "=" not in stripped:
                new_lines.append(line)
                continue
            k, _, _ = stripped.partition("=")
            if k.strip().upper() == env_key:
                removed = True
            else:
                new_lines.append(line)

        if removed:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

        return removed
    except OSError as e:
        logger.error(f"Failed to update .env file: {e}")
        return False
