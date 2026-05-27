"""
Notification engine.

On every poll cycle, compare new availability snapshots against the previous
snapshot. Only fire an alert when a slot transitions from booked → free.
"""

import os
import logging

import httpx

from db import get_pending_alerts, mark_alert_triggered, get_latest_snapshot, get_previous_snapshot

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def send_telegram(chat_id: str, text: str) -> None:
    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping notification")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})


def _slot_time(slot: dict) -> str | None:
    """Extract HH:MM from a slot's ISO datetime start field."""
    try:
        return slot["start"][11:16]
    except (KeyError, TypeError, IndexError):
        return None


def _slot_in_window(slot: dict, time_from: str, time_to: str) -> bool:
    t = _slot_time(slot)
    return t is not None and time_from <= t < time_to


async def check_and_fire_alerts() -> None:
    """
    Check all pending alerts against the latest snapshots.
    Only fires when a slot is newly available (wasn't in the previous snapshot).
    """
    alerts = get_pending_alerts()
    if not alerts:
        return

    for alert in alerts:
        current = get_latest_snapshot(alert["venue_id"], alert["date"])
        if not current:
            continue

        previous = get_previous_snapshot(alert["venue_id"], alert["date"]) or []

        # Only consider slots that weren't in the previous snapshot (newly freed).
        previous_ids = {s.get("resource_id") for s in previous}
        newly_free = [s for s in current if s.get("resource_id") not in previous_ids]

        matching = [s for s in newly_free if _slot_in_window(s, alert["time_from"], alert["time_to"])]
        if not matching:
            continue

        slot = matching[0]
        slot_time = _slot_time(slot)
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
