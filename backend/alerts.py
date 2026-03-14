"""
Notification engine.

On every poll cycle, compare new availability snapshots against pending alert
subscriptions. If a slot that was previously booked is now free, fire an alert.
"""

import os
import logging
from datetime import datetime

import httpx

from db import get_pending_alerts, mark_alert_triggered, get_latest_snapshot

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def send_telegram(chat_id: str, text: str) -> None:
    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping notification")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})


def slot_matches_window(slot: dict, time_from: str, time_to: str) -> bool:
    """Check if a slot's start time falls within [time_from, time_to]."""
    try:
        slot_time = slot["start"][11:16]  # "HH:MM" from ISO datetime
        return time_from <= slot_time < time_to
    except (KeyError, TypeError):
        return False


async def check_and_fire_alerts() -> None:
    """Check all pending alerts against latest snapshots and fire if a slot opened up."""
    alerts = get_pending_alerts()
    if not alerts:
        return

    for alert in alerts:
        slots = get_latest_snapshot(alert["venue_id"], alert["date"])
        if not slots:
            continue

        matching = [s for s in slots if slot_matches_window(s, alert["time_from"], alert["time_to"])]
        if not matching:
            continue

        # A matching available slot was found — fire the alert.
        slot = matching[0]
        slot_time = slot["start"][11:16]
        message = (
            f"*Padel court available!* \n\n"
            f"Venue: *{alert['venue_name']}*\n"
            f"Date: {alert['date']}\n"
            f"Time: {slot_time}\n"
            f"Duration: {slot.get('duration', '?')} min\n\n"
            f"Book now on Playtomic \u2192 https://playtomic.io"
        )

        if alert["channel"] == "telegram":
            try:
                await send_telegram(alert["contact"], message)
                mark_alert_triggered(alert["id"])
                logger.info("Alert %s fired for %s on %s", alert["id"], alert["venue_name"], alert["date"])
            except Exception as e:
                logger.error("Failed to send Telegram alert %s: %s", alert["id"], e)
