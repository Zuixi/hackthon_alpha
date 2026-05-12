"""Background scheduler for multi-platform hot topics.

Uses NewsNow aggregation for all platforms (including Zhihu) with
configurable Zhihu-native fallback, and cleans up data older than 5 days.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from app.config import settings
from app.database import SessionLocal
from app.models.hot_topic import HotTopic
from app.services.zhihu import zhihu_service
from app.services.newsnow_fetcher import fetch_all_platforms, PLATFORM_NAMES

logger = logging.getLogger(__name__)

FETCH_INTERVAL_SECONDS = 30 * 60
DATA_RETENTION_DAYS = 5
ZHIHU_SOURCE_MODES = {"newsnow_first", "newsnow_only", "native_only"}


async def fetch_zhihu_to_db(batch_id: str, now: datetime) -> int:
    """Fetch hot list from Zhihu native API and persist.
    Returns the number of items saved.
    """
    if not settings.ZHIHU_DEV_TOKEN:
        logger.info("ZHIHU_ACCESS_SECRET not configured, skipping Zhihu fetch")
        return 0

    raw = await zhihu_service.get_hot_list(limit=30)
    code = raw.get("Code", -1)
    if code != 0:
        raise RuntimeError(f"Zhihu API error code={code}: {raw.get('Message', '')}")

    items = raw.get("Data", {}).get("Items", [])
    if not items:
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
                platform="zhihu",
                source="zhihu_api",
                fetch_batch=batch_id,
                fetched_at=now,
            )
            db.add(topic)
            saved += 1
        db.commit()
        logger.info("Zhihu: saved %d topics (batch=%s)", saved, batch_id)
        return saved
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def fetch_newsnow_to_db(
    batch_id: str,
    now: datetime,
    exclude_platforms: set[str] | None = None,
) -> tuple[int, dict[str, int]]:
    """Fetch hot topics from all NewsNow platforms and persist.
    Returns tuple of (total items saved, per-platform saved counts).
    """
    platform_results = await fetch_all_platforms(exclude_platform_keys=exclude_platforms)
    if not platform_results:
        return 0, {}

    db = SessionLocal()
    try:
        total_saved = 0
        platform_counts: dict[str, int] = {}
        for platform_key, items in platform_results.items():
            saved = 0
            for item in items:
                title = item.get("title", "")
                if not title:
                    continue
                topic = HotTopic(
                    question_id="",
                    title=title,
                    url=item.get("url", ""),
                    thumbnail_url="",
                    excerpt="",
                    hot_score=0,
                    answer_count=0,
                    follower_count=0,
                    detail="",
                    platform=platform_key,
                    source="newsnow",
                    fetch_batch=batch_id,
                    fetched_at=now,
                )
                db.add(topic)
                saved += 1
            total_saved += saved
            platform_counts[platform_key] = saved
            logger.info("NewsNow [%s]: saved %d topics", platform_key, saved)

        db.commit()
        logger.info("NewsNow total: saved %d topics (batch=%s)", total_saved, batch_id)
        return total_saved, platform_counts
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def cleanup_old_data() -> int:
    """Delete hot topics older than DATA_RETENTION_DAYS."""
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
    """Long-running loop: fetch NewsNow -> optional Zhihu fallback -> clean -> sleep."""
    zhihu_mode = (settings.HOT_ZHIHU_SOURCE_MODE or "newsnow_first").strip().lower()
    if zhihu_mode not in ZHIHU_SOURCE_MODES:
        logger.warning(
            "Invalid HOT_ZHIHU_SOURCE_MODE=%s, fallback to newsnow_first",
            settings.HOT_ZHIHU_SOURCE_MODE,
        )
        zhihu_mode = "newsnow_first"

    logger.info(
        "Multi-platform scheduler started (interval=%ds, retention=%dd, platforms=%d, zhihu_mode=%s)",
        FETCH_INTERVAL_SECONDS, DATA_RETENTION_DAYS, len(PLATFORM_NAMES), zhihu_mode,
    )

    await asyncio.sleep(5)

    while True:
        batch_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        now = datetime.now(timezone.utc)

        # Phase 1: NewsNow multi-platform
        newsnow_counts: dict[str, int] = {}
        try:
            exclude_platforms = {"zhihu"} if zhihu_mode == "native_only" else None
            newsnow_count, newsnow_counts = await fetch_newsnow_to_db(
                batch_id=batch_id,
                now=now,
                exclude_platforms=exclude_platforms,
            )
            logger.info("Scheduler: NewsNow fetched %d topics total", newsnow_count)
        except Exception as e:
            logger.error("Scheduler: NewsNow fetch failed: %s", e)

        # Phase 2: Zhihu native API fallback / forced mode
        should_fetch_native = False
        if zhihu_mode == "native_only":
            should_fetch_native = True
        elif zhihu_mode == "newsnow_first":
            should_fetch_native = newsnow_counts.get("zhihu", 0) == 0

        if should_fetch_native:
            try:
                zhihu_count = await fetch_zhihu_to_db(batch_id, now)
                logger.info("Scheduler: Zhihu native fetched %d topics", zhihu_count)
            except Exception as e:
                logger.error("Scheduler: Zhihu native fetch failed: %s", e)
        else:
            logger.info("Scheduler: Zhihu native fetch skipped (mode=%s)", zhihu_mode)

        # Phase 3: Cleanup
        try:
            cleanup_old_data()
        except Exception as e:
            logger.error("Scheduler: cleanup failed: %s", e)

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
