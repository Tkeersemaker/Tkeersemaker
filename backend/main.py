"""
FastAPI application — Amsterdam Padel Availability Tracker

Endpoints:
  GET  /venues                         — list tracked venues
  GET  /availability?date=YYYY-MM-DD   — availability for all venues on a date
  GET  /availability/{venue_id}?date=  — availability for a single venue
  POST /alerts                         — subscribe to a slot alert
  GET  /health                         — health check
"""

import asyncio
import logging
import re
from contextlib import asynccontextmanager
from datetime import date as date_type
from enum import Enum

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator, model_validator

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
    allow_origins=["*"],  # Restrict to your domain in production
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Channel(str, Enum):
    telegram = "telegram"
    email = "email"


class AlertRequest(BaseModel):
    contact: str
    channel: Channel
    venue_id: str
    date: str    # YYYY-MM-DD
    time_from: str  # HH:MM
    time_to: str    # HH:MM

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            target = date_type.fromisoformat(v)
        except ValueError:
            raise ValueError("Invalid date — use YYYY-MM-DD")
        if target < date_type.today():
            raise ValueError("Date cannot be in the past")
        return v

    @field_validator("time_from", "time_to")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("Time must be in HH:MM format")
        return v

    @model_validator(mode="after")
    def validate_time_range(self) -> "AlertRequest":
        if self.time_from >= self.time_to:
            raise ValueError("time_to must be after time_from")
        return self

    @field_validator("contact")
    @classmethod
    def validate_contact(cls, v: str, info) -> str:
        channel = info.data.get("channel")
        if channel == Channel.telegram and not v.lstrip("-").isdigit():
            raise ValueError("Telegram contact must be a numeric chat ID")
        if channel == Channel.email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email address")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(date_str: str | None) -> date_type:
    if date_str is None:
        return date_type.today()
    try:
        return date_type.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")


def _get_venue(venue_id: str) -> dict:
    venue = next((v for v in AMSTERDAM_VENUES if v["id"] == venue_id), None)
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue


async def _venue_availability(venue: dict, target: date_type) -> dict:
    slots = get_latest_snapshot(venue["id"], target.isoformat())
    if slots is None:
        try:
            slots = await get_availability(venue["id"], target)
        except Exception as e:
            logger.warning("Live fetch failed for %s: %s", venue["name"], e)
            slots = []
    return {
        "venue_id": venue["id"],
        "venue_name": venue["name"],
        "booking_url": playtomic_booking_url(venue["id"]),
        "date": target.isoformat(),
        "slots": slots,
    }


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
    date_str: str = Query(default=None, alias="date", description="YYYY-MM-DD — defaults to today")
):
    target = _parse_date(date_str)
    return list(await asyncio.gather(*[_venue_availability(v, target) for v in AMSTERDAM_VENUES]))


@app.get("/availability/{venue_id}")
async def availability_venue(
    venue_id: str,
    date_str: str = Query(default=None, alias="date", description="YYYY-MM-DD — defaults to today"),
):
    target = _parse_date(date_str)
    venue = _get_venue(venue_id)
    return await _venue_availability(venue, target)


@app.post("/alerts", status_code=201)
def create_alert(req: AlertRequest):
    venue = _get_venue(req.venue_id)
    alert_id = add_alert(
        contact=req.contact,
        channel=req.channel.value,
        venue_id=req.venue_id,
        venue_name=venue["name"],
        date=req.date,
        time_from=req.time_from,
        time_to=req.time_to,
    )
    return {"alert_id": alert_id, "message": "Alert registered. You will be notified when the slot opens."}
