"""
Playtomic API client.

The /v1/availability endpoint is publicly accessible (no auth required).
Reference: https://mattrighetti.com/2025/03/03/reverse-engineering-playtomic
"""

import asyncio
import httpx
from datetime import date

BASE_URL = "https://api.playtomic.io"
PLAYTOMIC_TIMEOUT = 15

# Amsterdam padel venues on Playtomic.
# tenant_id values can be found by inspecting XHR requests on playtomic.io
# while searching for padel courts in Amsterdam.
AMSTERDAM_VENUES: list[dict] = [
    {"id": "9b5e0cad-4f0a-47ed-b793-c01c2a6b2d3e", "name": "XNRGY Club"},
    {"id": "1a2b3c4d-0000-0000-0000-000000000001", "name": "Plaza Padel Amsterdam"},
    {"id": "1a2b3c4d-0000-0000-0000-000000000002", "name": "Padel NEXT"},
    {"id": "1a2b3c4d-0000-0000-0000-000000000003", "name": "B. Amsterdam Padel"},
    {"id": "1a2b3c4d-0000-0000-0000-000000000004", "name": "Padeldam"},
    {"id": "1a2b3c4d-0000-0000-0000-000000000005", "name": "The Padellers"},
    {"id": "1a2b3c4d-0000-0000-0000-000000000006", "name": "Peakz Sloterdijk"},
]

# NOTE: The placeholder IDs above must be replaced with real Playtomic tenant IDs.
# To find them: open playtomic.io → search Amsterdam padel → open DevTools Network tab
# → look for requests to /v1/tenants?sport_id=PADEL&... → copy the "tenant_id" values.


def _build_availability_params(tenant_id: str, target_date: date) -> dict:
    return {
        "user_id": "-1",
        "tenant_id": tenant_id,
        "sport_id": "PADEL",
        "start_min": f"{target_date.isoformat()}T00:00:00",
        "start_max": f"{target_date.isoformat()}T23:59:00",
    }


async def get_venues() -> list[dict]:
    """Search Playtomic for padel venues in Amsterdam."""
    params = {
        "sport_id": "PADEL",
        "playtomic_status": "ACTIVE",
        "with_properties": "true",
        "location": "52.3676,4.9041",  # Amsterdam center lat/lon
        "radius": 20000,               # 20 km radius in metres
        "size": 50,
    }
    async with httpx.AsyncClient(timeout=PLAYTOMIC_TIMEOUT) as client:
        r = await client.get(f"{BASE_URL}/v1/tenants", params=params)
        r.raise_for_status()
        return r.json()


async def get_availability(tenant_id: str, target_date: date | None = None) -> list[dict]:
    """
    Fetch available court slots for a venue on a given date.

    Returns a list of slot objects:
      {
        "resource_id": str,   # court id
        "name": str,          # court name
        "start": str,         # ISO datetime
        "duration": int,      # minutes
        "price": float,
        "currency": str,
      }
    """
    if target_date is None:
        target_date = date.today()

    params = _build_availability_params(tenant_id, target_date)
    async with httpx.AsyncClient(timeout=PLAYTOMIC_TIMEOUT) as client:
        r = await client.get(f"{BASE_URL}/v1/availability", params=params)
        r.raise_for_status()
        return r.json()


async def get_all_availability(target_date: date | None = None) -> list[dict]:
    """Fetch availability for all tracked Amsterdam venues concurrently."""
    if target_date is None:
        target_date = date.today()

    async def fetch_one(client: httpx.AsyncClient, venue: dict) -> dict:
        params = _build_availability_params(venue["id"], target_date)
        try:
            r = await client.get(f"{BASE_URL}/v1/availability", params=params)
            r.raise_for_status()
            return {
                "venue_id": venue["id"],
                "venue_name": venue["name"],
                "date": target_date.isoformat(),
                "slots": r.json(),
            }
        except Exception as e:
            return {
                "venue_id": venue["id"],
                "venue_name": venue["name"],
                "date": target_date.isoformat(),
                "slots": [],
                "error": str(e),
            }

    async with httpx.AsyncClient(timeout=PLAYTOMIC_TIMEOUT) as client:
        return list(await asyncio.gather(*[fetch_one(client, v) for v in AMSTERDAM_VENUES]))


def playtomic_booking_url(tenant_id: str) -> str:
    """Return the Playtomic booking deep-link for a venue."""
    return f"https://playtomic.io/booking/{tenant_id}"
