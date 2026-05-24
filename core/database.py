"""
database.py — SQLite database layer for tasks, post_history, and accounts.
DB lives at ~/.techvoice-publisher/data.db
"""
import sqlite3
import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

DB_DIR = os.path.expanduser("~/.techvoice-publisher")
DB_PATH = os.path.join(DB_DIR, "data.db")


def _get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT,
                status TEXT DEFAULT 'pending',
                video_url TEXT,
                cover_url TEXT,
                caption TEXT,
                platforms TEXT,
                scheduled_at TEXT,
                content_type TEXT DEFAULT 'video',
                error_msg TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS post_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                platform TEXT,
                status TEXT,
                platform_post_id TEXT,
                error_msg TEXT,
                posted_at TEXT
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                platform TEXT,
                display_name TEXT,
                account_id TEXT,
                is_active INTEGER DEFAULT 1,
                added_at TEXT
            );
        """)
        conn.commit()
        logger.info("Database initialized at %s", DB_PATH)
    finally:
        conn.close()


# ─── Tasks ────────────────────────────────────────────────────────────────────

def upsert_task(task: Dict[str, Any]) -> None:
    """Insert or update a task row."""
    conn = _get_connection()
    try:
        now = datetime.utcnow().isoformat()
        platforms = task.get("platforms")
        if isinstance(platforms, list):
            platforms = json.dumps(platforms, ensure_ascii=False)

        conn.execute("""
            INSERT INTO tasks (id, name, status, video_url, cover_url, caption,
                               platforms, scheduled_at, content_type, error_msg,
                               created_at, updated_at)
            VALUES (:id, :name, :status, :video_url, :cover_url, :caption,
                    :platforms, :scheduled_at, :content_type, :error_msg,
                    COALESCE(:created_at, :now), :now)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                status=excluded.status,
                video_url=excluded.video_url,
                cover_url=excluded.cover_url,
                caption=excluded.caption,
                platforms=excluded.platforms,
                scheduled_at=excluded.scheduled_at,
                content_type=excluded.content_type,
                error_msg=excluded.error_msg,
                updated_at=excluded.updated_at
        """, {
            "id": task["id"],
            "name": task.get("name", ""),
            "status": task.get("status", "pending"),
            "video_url": task.get("video_url"),
            "cover_url": task.get("cover_url"),
            "caption": task.get("caption"),
            "platforms": platforms,
            "scheduled_at": task.get("scheduled_at"),
            "content_type": task.get("content_type", "video"),
            "error_msg": task.get("error_msg"),
            "created_at": task.get("created_at"),
            "now": now,
        })
        conn.commit()
    finally:
        conn.close()


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _task_row_to_dict(row) if row else None
    finally:
        conn.close()


def get_all_tasks(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = _get_connection()
    try:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY scheduled_at ASC, created_at DESC",
                (status_filter,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY scheduled_at ASC, created_at DESC"
            ).fetchall()
        return [_task_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_scheduled_due_tasks() -> List[Dict[str, Any]]:
    """Return tasks that are scheduled and whose scheduled_at <= now."""
    now = datetime.utcnow().isoformat()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = 'scheduled' AND scheduled_at <= ?",
            (now,)
        ).fetchall()
        return [_task_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def update_task_status(task_id: str, status: str, error_msg: Optional[str] = None) -> None:
    now = datetime.utcnow().isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE tasks SET status = ?, error_msg = ?, updated_at = ? WHERE id = ?",
            (status, error_msg, now, task_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_task(task_id: str) -> None:
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
    finally:
        conn.close()


def _task_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    if d.get("platforms") and isinstance(d["platforms"], str):
        try:
            d["platforms"] = json.loads(d["platforms"])
        except (json.JSONDecodeError, TypeError):
            d["platforms"] = []
    return d


# ─── Post History ─────────────────────────────────────────────────────────────

def add_post_history(task_id: str, platform: str, status: str,
                     platform_post_id: Optional[str] = None,
                     error_msg: Optional[str] = None) -> None:
    now = datetime.utcnow().isoformat()
    conn = _get_connection()
    try:
        conn.execute("""
            INSERT INTO post_history (task_id, platform, status, platform_post_id, error_msg, posted_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (task_id, platform, status, platform_post_id, error_msg, now))
        conn.commit()
    finally:
        conn.close()


def get_post_history(task_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    conn = _get_connection()
    try:
        if task_id:
            rows = conn.execute(
                "SELECT * FROM post_history WHERE task_id = ? ORDER BY posted_at DESC LIMIT ?",
                (task_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM post_history ORDER BY posted_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ─── Accounts ─────────────────────────────────────────────────────────────────

def upsert_account(account: Dict[str, Any]) -> None:
    now = datetime.utcnow().isoformat()
    conn = _get_connection()
    try:
        conn.execute("""
            INSERT INTO accounts (id, platform, display_name, account_id, is_active, added_at)
            VALUES (:id, :platform, :display_name, :account_id, :is_active, :added_at)
            ON CONFLICT(id) DO UPDATE SET
                display_name=excluded.display_name,
                account_id=excluded.account_id,
                is_active=excluded.is_active
        """, {
            "id": account["id"],
            "platform": account["platform"],
            "display_name": account.get("display_name", ""),
            "account_id": account.get("account_id", ""),
            "is_active": account.get("is_active", 1),
            "added_at": account.get("added_at", now),
        })
        conn.commit()
    finally:
        conn.close()


def get_accounts(platform: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = _get_connection()
    try:
        if platform:
            rows = conn.execute(
                "SELECT * FROM accounts WHERE platform = ? AND is_active = 1 ORDER BY added_at",
                (platform,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM accounts WHERE is_active = 1 ORDER BY platform, added_at"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_account(account_id: str) -> None:
    conn = _get_connection()
    try:
        conn.execute("UPDATE accounts SET is_active = 0 WHERE id = ?", (account_id,))
        conn.commit()
    finally:
        conn.close()
