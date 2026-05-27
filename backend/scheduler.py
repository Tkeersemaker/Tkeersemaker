"""
Background scheduler.

Polls Playtomic every 5 minutes for all Amsterdam venues (today + next 6 days),
saves snapshots to SQLite, and fires any pending alerts.
"""

import asyncio
import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from playtomic import get_all_availability
from db import save_snapshot, cleanup_old_snapshots
from alerts import check_and_fire_alerts

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 300  # 5 minutes
DAYS_AHEAD = 6


async def poll() -> None:
    logger.info("Polling Playtomic availability...")
    targets = [date.today() + timedelta(days=offset) for offset in range(DAYS_AHEAD + 1)]

    # Fetch all days concurrently.
    all_results = await asyncio.gather(*[get_all_availability(target) for target in targets])

    for results in all_results:
        for r in results:
            if "error" in r:
                logger.warning("Error fetching %s on %s: %s", r["venue_name"], r["date"], r["error"])
            elif r["slots"]:
                save_snapshot(r["venue_id"], r["venue_name"], r["date"], r["slots"])

    await check_and_fire_alerts()
    cleanup_old_snapshots(hours_back=24)
    logger.info("Poll complete.")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(poll, "interval", seconds=POLL_INTERVAL_SECONDS, id="poll_availability")
    return scheduler
