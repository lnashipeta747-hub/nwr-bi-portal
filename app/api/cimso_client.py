"""
app/api/cimso_client.py
-------------------------
CiMSO Innkeeper client.

Phase 1 reality check: NWR has not given the hackathon team live CiMSO
credentials, so this client ships with CIMSO_USE_MOCK=true (see config.py).
In that mode it generates realistic-looking booking data locally instead
of making a real HTTP call, so the *entire* pipeline (API -> staging ->
validation -> fact tables -> dashboard) can be demoed end-to-end today.

Phase 2 switch-over: implement `_fetch_from_real_api()` to call
`{CIMSO_API_BASE_URL}/bookings?since=...` with the CIMSO_API_KEY in an
Authorization header, keep the exact same return shape (a list of dicts),
and flip CIMSO_USE_MOCK to false. Nothing else in the pipeline changes —
this is the same "swap one adapter" design as the database layer.
"""

import random
from datetime import datetime, timedelta

from flask import current_app


RESORTS = [
    ("Etosha Safari Lodge", "Etosha", 60),
    ("Namushasha River Lodge", "Zambezi", 40),
    ("Duwisib Guest Farm", "Hardap", 20),
    ("Swakopmund Rest Camp", "Erongo", 80),
    ("Popa Falls Resort", "Kavango East", 30),
]

ROOM_TYPES = [
    ("Standard Room", 850),
    ("Luxury Chalet", 1650),
    ("Family Unit", 1200),
    ("Camping Pitch", 250),
]


def _fetch_from_mock(since: datetime, max_records: int = 40):
    """Generates plausible-looking raw booking dicts, in the *same shape*
    a real CiMSO REST response would need to arrive in for this pipeline
    to consume it. Intentionally includes a few dirty/invalid rows so the
    validation layer (see app/upload/validators.py) has something real
    to catch — this mirrors real-world CiMSO/CSV data quality issues.
    """
    records = []
    for i in range(max_records):
        resort_name, _, _ = random.choice(RESORTS)
        room_type_name, base_rate = random.choice(ROOM_TYPES)

        checkin = since + timedelta(days=random.randint(0, 30))
        nights = random.randint(1, 6)
        checkout = checkin + timedelta(days=nights)
        guests = random.randint(1, 4)
        revenue = round(base_rate * nights * random.uniform(0.9, 1.15), 2)

        record = {
            "booking_id": f"CIMSO-{since.strftime('%Y%m')}-{i:04d}",
            "resort_name": resort_name,
            "room_type": room_type_name,
            "booking_date": since.strftime("%Y-%m-%d"),
            "checkin_date": checkin.strftime("%Y-%m-%d"),
            "checkout_date": checkout.strftime("%Y-%m-%d"),
            "nights": nights,
            "revenue": revenue,
            "guest_count": guests,
        }

        # Deliberately inject occasional dirty data (~8% of rows) so the
        # staging/validation layer has real failures to demonstrate —
        # this is realistic: CiMSO exports do sometimes have blanks or
        # bad values, which is exactly why a staging table exists.
        if random.random() < 0.08:
            dirty_field = random.choice(["revenue", "nights", "checkin_date"])
            record[dirty_field] = ""  # simulate a missing/blank value

        records.append(record)
    return records


def _fetch_from_real_api(since: datetime, max_records: int = 40):
    """
    Placeholder for Phase 2. Example implementation once NWR issues
    credentials:

        import requests
        resp = requests.get(
            f"{current_app.config['CIMSO_API_BASE_URL']}/bookings",
            params={"since": since.isoformat()},
            headers={"Authorization": f"Bearer {current_app.config['CIMSO_API_KEY']}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["bookings"]
    """
    raise NotImplementedError(
        "Real CiMSO endpoint not wired up yet — set CIMSO_USE_MOCK=true "
        "in .env for the Phase 1 demo, or implement this function for Phase 2."
    )


def fetch_bookings(since: datetime = None, max_records: int = 40):
    """Single entry point the rest of the app calls. Hides whether we're
    talking to the mock generator or the real CiMSO REST API behind one
    function — the API/ETL layer (app/api/routes.py) doesn't need to know
    which."""
    since = since or (datetime.utcnow() - timedelta(days=1))
    use_mock = current_app.config.get("CIMSO_USE_MOCK", True)
    if use_mock:
        return _fetch_from_mock(since, max_records)
    return _fetch_from_real_api(since, max_records)
