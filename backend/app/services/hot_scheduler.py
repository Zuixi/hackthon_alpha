"""Background scheduler that fetches Zhihu hot list every 30 minutes
and cleans up data older than 5 days."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from app.config import settings
from app.database import SessionLocal
from app.models.hot_topic import HotTopic
from app.services.zhihu import zhihu_service

logger = logging.getLogger(__name__)

FETCH_INTERVAL_SECONDS = 30 * 60  # 30 minutes
DATA_RETENTION_DAYS = 5


async def fetch_hot_list_to_db() -> int:
    """Fetch hot list from Zhihu API and persist to database.
    Returns the number of items saved.
    """
    batch_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    now = datetime.now(timezone.utc)

    raw = await zhihu_service.get_hot_list(limit=30)

    code = raw.get("Code", -1)
    if code != 0:
        raise RuntimeError(f"Zhihu hot_list API returned error code={code}: {raw.get('Message', '')}")

    data = raw.get("Data", {})
    items = data.get("Items", [])

    if not items:
        logger.info("Hot list API returned 0 items, skipping save")
        return 0

    db = SessionLocal()
    try:
        saved = 0
        for item in items:
            title = item.get("Title", "")
            url = item.get("Url", "")
            if not title:
                continue

            topic = HotTopic(
                question_id=_extract_question_id(url),
                title=title,
                url=url,
                thumbnail_url=item.get("ThumbnailUrl", ""),
                excerpt=item.get("Summary", ""),
                hot_score=0,
                answer_count=0,
                follower_count=0,
                detail="",
                fetch_batch=batch_id,
                fetched_at=now,
            )
            db.add(topic)
            saved += 1

        db.commit()
        logger.info("Saved %d hot topics (batch=%s)", saved, batch_id)
        return saved
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def cleanup_old_data() -> int:
    """Delete hot topics older than DATA_RETENTION_DAYS. Returns count deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=DATA_RETENTION_DAYS)
    db = SessionLocal()
    try:
        count = db.query(HotTopic).filter(HotTopic.fetched_at < cutoff).delete()
        db.commit()
        if count > 0:
            logger.info("Cleaned up %d hot topics older than %s", count, cutoff.isoformat())
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def hot_list_scheduler_loop():
    """Long-running loop: fetch → clean → sleep 30min → repeat."""
    logger.info("Hot list scheduler started (interval=%ds, retention=%dd)",
                FETCH_INTERVAL_SECONDS, DATA_RETENTION_DAYS)

    await asyncio.sleep(5)

    while True:
        if not settings.ZHIHU_DEV_TOKEN:
            logger.warning("ZHIHU_ACCESS_SECRET not configured, skipping hot list fetch")
        else:
            try:
                count = await fetch_hot_list_to_db()
                logger.info("Scheduler fetched %d hot topics", count)
            except Exception as e:
                logger.error("Scheduler fetch failed: %s", e)

        try:
            cleanup_old_data()
        except Exception as e:
            logger.error("Scheduler cleanup failed: %s", e)

        await asyncio.sleep(FETCH_INTERVAL_SECONDS)


def _extract_question_id(url: str) -> str:
    """Try to extract question ID from zhihu URL."""
    if "/question/" in url:
        parts = url.split("/question/")
        if len(parts) > 1:
            return parts[1].split("/")[0].split("?")[0]
    if "/p/" in url:
        parts = url.split("/p/")
        if len(parts) > 1:
            return "p_" + parts[1].split("/")[0].split("?")[0]
    return ""
