"""
scheduler.py — APScheduler background scheduler.
Checks every 5 minutes for scheduled tasks that are due and publishes them.
"""
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_scheduler = None


def _publish_due_tasks():
    """Called every 5 minutes by the scheduler."""
    from core.database import get_scheduled_due_tasks, update_task_status
    from core.config import get_secret

    tasks = get_scheduled_due_tasks()
    if not tasks:
        return

    logger.info("Scheduler: found %d due tasks", len(tasks))

    for task in tasks:
        try:
            _run_task(task)
        except Exception as e:
            logger.error("Scheduler: task %s failed: %s", task["id"], e)
            update_task_status(task["id"], "failed", str(e))


def _run_task(task: dict):
    """Download media and publish to all configured platforms."""
    from core.database import update_task_status, add_post_history
    from core.drive_client import download_file, cleanup_tmp_file
    from core.config import get_secret
    import core.notion_client as nc

    task_id = task["id"]
    platforms = task.get("platforms", [])
    content_type = task.get("content_type", "video")
    caption = task.get("caption", "")

    update_task_status(task_id, "publishing")

    # Update Notion status to publishing
    notion_token = get_secret("notion_token")
    if notion_token:
        try:
            nc.update_task_status(task_id, nc.STATUS_PUBLISHING, notion_token)
        except Exception:
            pass

    # Download media files
    video_path = None
    cover_path = None
    tmp_files = []

    if task.get("video_url"):
        ok, path = download_file(task["video_url"])
        if ok:
            video_path = path
            tmp_files.append(path)
        else:
            logger.warning("Could not download video for task %s: %s", task_id, path)

    if task.get("cover_url"):
        ok, path = download_file(task["cover_url"])
        if ok:
            cover_path = path
            tmp_files.append(path)

    # Default platforms to TikTok if none specified (for users without a platforms column)
    if not platforms:
        platforms = ["tiktok"]
        logger.info("Task %s has no platforms — defaulting to TikTok", task_id)

    # Publish to each platform
    attempted = False
    any_success = False
    errors = []
    skipped = []  # platforms skipped (not configured or no accounts)

    for platform in platforms:
        publisher = _get_publisher(platform)
        if publisher is None:
            skipped.append(f"{platform} (بيانات API ناقصة)")
            logger.info("Platform %s not configured, skipping", platform)
            continue

        accounts = publisher.get_connected_accounts()
        if not accounts:
            skipped.append(f"{platform} (لا يوجد حساب مربوط)")
            logger.info("No accounts for %s, skipping", platform)
            continue

        for account in accounts:
            account_id = account.get("id", "")
            attempted = True
            try:
                if content_type == "video" and video_path:
                    result = publisher.publish_video(video_path, cover_path, caption, account_id)
                elif content_type == "photo" and video_path:
                    result = publisher.publish_photo([video_path], caption, account_id)
                elif content_type == "tweet":
                    result = publisher.publish_tweet(caption, video_path, account_id)
                else:
                    result = publisher.publish_video(video_path or "", cover_path, caption, account_id)

                add_post_history(
                    task_id=task_id,
                    platform=platform,
                    status="success" if result.success else "failed",
                    platform_post_id=result.platform_post_id,
                    error_msg=result.error_msg,
                )

                if result.success:
                    any_success = True
                else:
                    errors.append(f"{platform}: {result.error_msg}")

            except Exception as e:
                logger.error("Platform %s publish error: %s", platform, e)
                add_post_history(task_id=task_id, platform=platform, status="failed", error_msg=str(e))
                errors.append(f"{platform}: {str(e)}")

    # Cleanup temp files
    for f in tmp_files:
        cleanup_tmp_file(f)

    # Final status — be honest about what happened
    if not attempted:
        # Nothing was even tried — don't mark as "done"
        reason = "لم يتم النشر: " + (", ".join(skipped) if skipped else "لا توجد منصات أو حسابات مربوطة")
        update_task_status(task_id, "failed", reason)
        if notion_token:
            try:
                nc.update_task_status(task_id, nc.STATUS_FAILED, notion_token)
            except Exception:
                pass
    elif any_success:
        update_task_status(task_id, "done")
        if notion_token:
            try:
                nc.update_task_status(task_id, nc.STATUS_DONE, notion_token)
            except Exception:
                pass
    else:
        error_summary = "; ".join(errors[:3]) if errors else "فشل النشر بدون رسالة خطأ"
        update_task_status(task_id, "failed", error_summary)
        if notion_token:
            try:
                nc.update_task_status(task_id, nc.STATUS_FAILED, notion_token)
            except Exception:
                pass


def _get_publisher(platform: str):
    """Return the publisher instance for a platform, or None if not configured."""
    from core.config import get_secret

    try:
        if platform == "tiktok":
            cid = get_secret("tiktok_client_id")
            csecret = get_secret("tiktok_client_secret")
            if not cid or not csecret:
                return None
            from platforms.tiktok import TikTokPublisher
            return TikTokPublisher(cid, csecret)

        elif platform == "youtube":
            cid = get_secret("youtube_client_id")
            csecret = get_secret("youtube_client_secret")
            if not cid or not csecret:
                return None
            from platforms.youtube import YouTubePublisher
            return YouTubePublisher(cid, csecret)

        elif platform == "instagram":
            from platforms.instagram import InstagramPublisher
            return InstagramPublisher()

        elif platform == "x":
            bearer = get_secret("twitter_bearer_token")
            cid = get_secret("twitter_client_id")
            csecret = get_secret("twitter_client_secret")
            if not bearer and not cid:
                return None
            from platforms.twitter import TwitterPublisher
            return TwitterPublisher(bearer or "", cid or "", csecret or "")

    except Exception as e:
        logger.error("Failed to instantiate publisher for %s: %s", platform, e)

    return None


def start_scheduler():
    """Start the APScheduler background scheduler."""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.info("Scheduler already running")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        _scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60}
        )
        _scheduler.add_job(
            _publish_due_tasks,
            trigger=IntervalTrigger(minutes=5),
            id="publish_due_tasks",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info("Scheduler started — checking every 5 minutes")
    except Exception as e:
        logger.error("Failed to start scheduler: %s", e)


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error("Error stopping scheduler: %s", e)
    _scheduler = None


def schedule_task(task_id: str, run_at: datetime) -> bool:
    """
    Update a task's status to 'scheduled' with the given datetime.
    The background job will pick it up automatically.
    """
    from core.database import update_task_status, upsert_task, get_task
    task = get_task(task_id)
    if not task:
        return False

    task["scheduled_at"] = run_at.isoformat()
    task["status"] = "scheduled"
    upsert_task(task)
    logger.info("Task %s scheduled for %s", task_id, run_at.isoformat())
    return True


def run_task_now(task_id: str) -> bool:
    """
    Immediately run a single task (bypassing the scheduler interval).
    Returns True if the task was found and execution started.
    """
    from core.database import get_task
    task = get_task(task_id)
    if not task:
        logger.error("Task %s not found", task_id)
        return False

    try:
        _run_task(task)
        return True
    except Exception as e:
        logger.error("run_task_now error for %s: %s", task_id, e)
        return False


def is_running() -> bool:
    return _scheduler is not None and _scheduler.running
