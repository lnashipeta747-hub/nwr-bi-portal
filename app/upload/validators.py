"""
app/upload/validators.py
--------------------------
Shared ETL logic: Extract, Transform, Load (see glossary).

Both data-entry paths described in the study guide funnel through here:
  - the CiMSO API sync (app/api/routes.py), and
  - manual CSV/Excel uploads (app/upload/routes.py)

Both write raw rows into StagingBooking first, then this module
validates/cleans each row and — only if it passes — promotes it into
FactBooking, creating/reusing the matching DimResort, DimRoomType, and
DimDate rows as needed. Rows that fail validation stay in staging with
a human-readable validation_error and are never deleted, so nothing is
silently lost and everything can be traced (Slide 4: "Nothing enters the
[fact tables] without being checked").
"""

from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from app.extensions import db
from app.models import StagingBooking, FactBooking, DimResort, DimRoomType, DimDate


REQUIRED_FIELDS = [
    "resort_name", "room_type", "booking_date",
    "checkin_date", "checkout_date", "nights", "revenue", "guest_count",
]

# Handles the "'Booking Date' and 'booking_date' become the same field"
# normalisation problem called out on Slide 4.
COLUMN_ALIASES = {
    "resort": "resort_name",
    "resort name": "resort_name",
    "lodge": "resort_name",
    "room type": "room_type",
    "roomtype": "room_type",
    "booking date": "booking_date",
    "check-in": "checkin_date",
    "check in": "checkin_date",
    "check-in date": "checkin_date",
    "check-out": "checkout_date",
    "check out": "checkout_date",
    "check-out date": "checkout_date",
    "no of nights": "nights",
    "number of nights": "nights",
    "amount": "revenue",
    "total revenue": "revenue",
    "guests": "guest_count",
    "no of guests": "guest_count",
    "pax": "guest_count",
}


def normalize_columns(raw_columns):
    """Maps messy real-world spreadsheet headers onto our canonical field
    names. Case/space/punctuation-insensitive."""
    normalized = {}
    for col in raw_columns:
        key = str(col).strip().lower().replace("_", " ")
        canonical = COLUMN_ALIASES.get(key, str(col).strip().lower().replace(" ", "_"))
        normalized[col] = canonical
    return normalized


def _parse_date(value):
    if value is None or str(value).strip() == "":
        return None
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        cleaned = str(value).replace(",", "").replace("N$", "").strip()
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _parse_int(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def get_or_create_dim_resort(resort_name: str) -> DimResort:
    resort = DimResort.query.filter_by(resort_name=resort_name).first()
    if resort is None:
        resort = DimResort(resort_name=resort_name, region="Unknown", total_rooms=50)
        db.session.add(resort)
        db.session.flush()
    return resort


def get_or_create_dim_room_type(room_type_name: str) -> DimRoomType:
    room_type = DimRoomType.query.filter_by(room_type_name=room_type_name).first()
    if room_type is None:
        room_type = DimRoomType(room_type_name=room_type_name, base_rate=0)
        db.session.add(room_type)
        db.session.flush()
    return room_type


def get_or_create_dim_date(d: date) -> DimDate:
    dim = DimDate.query.get(d)
    if dim is None:
        dim = DimDate(
            date_key=d,
            year=d.year,
            month=d.month,
            month_name=d.strftime("%B"),
            day=d.day,
            weekday_name=d.strftime("%A"),
            is_weekend=d.weekday() >= 5,
        )
        db.session.add(dim)
        db.session.flush()
    return dim


def validate_and_promote_staging_row(staging_row: StagingBooking) -> bool:
    """
    Validates one StagingBooking row. On success: creates/reuses dimension
    rows, inserts a FactBooking, marks the staging row PASSED + promoted.
    On failure: marks the staging row FAILED with a specific reason and
    leaves it in staging for review. Returns True/False for pass/fail.
    """
    errors = []

    resort_name = (staging_row.resort_name_raw or "").strip()
    room_type_name = (staging_row.room_type_raw or "").strip()
    checkin = _parse_date(staging_row.checkin_date_raw)
    checkout = _parse_date(staging_row.checkout_date_raw)
    booking_date = _parse_date(staging_row.booking_date_raw) or checkin
    nights = _parse_int(staging_row.nights_raw)
    revenue = _parse_decimal(staging_row.revenue_raw)
    guests = _parse_int(staging_row.guest_count_raw) or 1

    if not resort_name:
        errors.append("missing resort_name")
    if not room_type_name:
        errors.append("missing room_type")
    if checkin is None:
        errors.append("invalid/missing checkin_date")
    if checkout is None:
        errors.append("invalid/missing checkout_date")
    if nights is None or nights <= 0:
        errors.append("invalid/missing nights")
    if revenue is None or revenue < 0:
        errors.append("invalid/missing revenue")
    if checkin and checkout and checkout <= checkin:
        errors.append("checkout_date must be after checkin_date")

    if errors:
        staging_row.validation_status = "FAILED"
        staging_row.validation_error = "; ".join(errors)
        staging_row.promoted_to_fact = False
        return False

    resort = get_or_create_dim_resort(resort_name)
    room_type = get_or_create_dim_room_type(room_type_name)
    dim_date = get_or_create_dim_date(booking_date)

    fact = FactBooking(
        resort_id=resort.id,
        room_type_id=room_type.id,
        booking_date_key=dim_date.date_key,
        checkin_date=checkin,
        checkout_date=checkout,
        nights=nights,
        guest_count=guests,
        revenue=revenue,
        source=staging_row.source,
        staging_record_id=staging_row.id,
    )
    db.session.add(fact)

    staging_row.validation_status = "PASSED"
    staging_row.validation_error = None
    staging_row.promoted_to_fact = True
    return True
