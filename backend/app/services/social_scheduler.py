"""Background scheduler for daily follower snapshots (20:00 Asia/Shanghai)."""
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.database import SessionLocal
from app.models.user import User
from app.models.social_follower_snapshot import SocialFollowerSnapshot
from app.services.cache import cache_delete_pattern
from app.services.zhihu import zhihu_service

logger = logging.getLogger(__name__)

SOCIAL_SNAPSHOT_INTERVAL_SECONDS = 10 * 60
SOCIAL_TIMEZONE = ZoneInfo("Asia/Shanghai")
SOCIAL_REFRESH_HOUR = 20


def _should_run_snapshot(now_local: datetime) -> bool:
    return now_local.hour >= SOCIAL_REFRESH_HOUR


async def snapshot_followers_once() -> int:
    now_local = datetime.now(SOCIAL_TIMEZONE)
    if not _should_run_snapshot(now_local):
        return 0

    snapshot_date = now_local.date()
    db = SessionLocal()
    created = 0
    try:
        users = db.query(User).filter(User.zhihu_token.isnot(None), User.zhihu_token != "").all()
        for user in users:
            existing = (
                db.query(SocialFollowerSnapshot)
                .filter(
                    SocialFollowerSnapshot.user_id == user.id,
                    SocialFollowerSnapshot.snapshot_date == snapshot_date,
                )
                .first()
            )
            if existing:
                continue

            try:
                count = await zhihu_service.get_followers_count(user.zhihu_token)
            except Exception as e:
                logger.warning("Follower snapshot failed for user=%s: %s", user.id, e)
                continue

            row = SocialFollowerSnapshot(
                user_id=user.id,
                snapshot_date=snapshot_date,
                follower_count=count,
            )
            db.add(row)
            db.commit()
            created += 1
            cache_delete_pattern(f"social:followers:stats:{user.id}:*")
        return created
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def social_snapshot_scheduler_loop():
    logger.info(
        "Social snapshot scheduler started (interval=%ss, timezone=%s, refresh_hour=%s)",
        SOCIAL_SNAPSHOT_INTERVAL_SECONDS,
        SOCIAL_TIMEZONE.key,
        SOCIAL_REFRESH_HOUR,
    )

    await asyncio.sleep(5)

    while True:
        try:
            created = await snapshot_followers_once()
            if created > 0:
                logger.info("Social snapshot: created %s follower snapshots", created)
        except Exception as e:
            logger.error("Social snapshot scheduler failed: %s", e)

        await asyncio.sleep(SOCIAL_SNAPSHOT_INTERVAL_SECONDS)
