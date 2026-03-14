"""
FastAPI application — Amsterdam Padel Availability Tracker

Endpoints:
  GET  /venues                         — list tracked venues
  GET  /availability?date=YYYY-MM-DD   — availability for all venues on a date
  GET  /availability/{venue_id}?date=  — availability for a single venue
  POST /alerts                         — subscribe to a slot alert
  GET  /health                         — health check
"""

import logging
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import init_db, get_latest_snapshot, add_alert
from playtomic import AMSTERDAM_VENUES, get_all_availability, get_availability, playtomic_booking_url
from scheduler import create_scheduler, poll

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Run an initial poll immediately so the first request has data.
    await poll()
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Amsterdam Padel Tracker",
    description="Track real-time padel court availability in Amsterdam.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AlertRequest(BaseModel):
    contact: str          # Telegram chat_id or email address
    channel: str          # "telegram" | "email"
    venue_id: str
    date: str             # YYYY-MM-DD
    time_from: str        # "HH:MM"
    time_to: str          # "HH:MM"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/venues")
def list_venues():
    return [
        {**v, "booking_url": playtomic_booking_url(v["id"])}
        for v in AMSTERDAM_VENUES
    ]


@app.get("/availability")
async def availability_all(
    date: str = Query(default=None, description="YYYY-MM-DD — defaults to today")
):
    target = _parse_date(date)
    # Try cache first; fall back to live fetch.
    results = []
    for venue in AMSTERDAM_VENUES:
        slots = get_latest_snapshot(venue["id"], target.isoformat())
        if slots is None:
            try:
                slots = await get_availability(venue["id"], target)
            except Exception as e:
                logger.warning("Live fetch failed for %s: %s", venue["name"], e)
                slots = []
        results.append({
            "venue_id": venue["id"],
            "venue_name": venue["name"],
            "booking_url": playtomic_booking_url(venue["id"]),
            "date": target.isoformat(),
            "slots": slots,
        })
    return results


@app.get("/availability/{venue_id}")
async def availability_venue(
    venue_id: str,
    date: str = Query(default=None, description="YYYY-MM-DD — defaults to today"),
):
    target = _parse_date(date)
    venue = next((v for v in AMSTERDAM_VENUES if v["id"] == venue_id), None)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    slots = get_latest_snapshot(venue_id, target.isoformat())
    if slots is None:
        try:
            slots = await get_availability(venue_id, target)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Playtomic fetch failed: {e}")

    return {
        "venue_id": venue_id,
        "venue_name": venue["name"],
        "booking_url": playtomic_booking_url(venue_id),
        "date": target.isoformat(),
        "slots": slots,
    }


@app.post("/alerts", status_code=201)
def create_alert(req: AlertRequest):
    venue = next((v for v in AMSTERDAM_VENUES if v["id"] == req.venue_id), None)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    alert_id = add_alert(
        contact=req.contact,
        channel=req.channel,
        venue_id=req.venue_id,
        venue_name=venue["name"],
        date=req.date,
        time_from=req.time_from,
        time_to=req.time_to,
    )
    return {"alert_id": alert_id, "message": "Alert registered. You will be notified when the slot opens."}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(date_str: str | None) -> date:
    if date_str is None:
        return date.today()
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
