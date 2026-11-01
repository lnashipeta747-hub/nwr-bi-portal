"""
app/api/scheduler.py
----------------------
"Flask will call these addresses automatically every 15 minutes using a
tool called APScheduler." (Slide 4)

run_cimso_sync() is the single function called both by the scheduled job
and by the manual "Sync Now" button in app/api/routes.py, so behaviour is
identical whether the sync is automatic or demo-triggered.
"""

from datetime import datetime

from flask import current_app

from app.extensions import db, scheduler
from app.api.cimso_client import fetch_bookings
from app.models import StagingBooking, CimsoSyncLog
from app.upload.validators import validate_and_promote_staging_row


def run_cimso_sync():
    """Fetches raw bookings from CiMSO (mock or real), stages each one,
    validates, promotes passing rows to FactBooking, and writes a
    CimsoSyncLog entry. Must be called inside an app context."""
    rows_fetched = 0
    rows_passed = 0
    rows_failed = 0
    error_message = None

    try:
        raw_records = fetch_bookings()
        rows_fetched = len(raw_records)

        for record in raw_records:
            staging_row = StagingBooking(
                source="CIMSO_API",
                source_reference=record.get("booking_id"),
                resort_name_raw=record.get("resort_name", ""),
                room_type_raw=record.get("room_type", ""),
                booking_date_raw=record.get("booking_date", ""),
                checkin_date_raw=record.get("checkin_date", ""),
                checkout_date_raw=record.get("checkout_date", ""),
                nights_raw=str(record.get("nights", "")),
                revenue_raw=str(record.get("revenue", "")),
                guest_count_raw=str(record.get("guest_count", "")),
            )
            db.session.add(staging_row)
            db.session.flush()

            passed = validate_and_promote_staging_row(staging_row)
            rows_passed += int(passed)
            rows_failed += int(not passed)

        db.session.commit()
        status = "SUCCESS"
    except Exception as exc:  # noqa: BLE001 - logged below, never crashes the scheduler
        db.session.rollback()
        status = "FAILED"
        error_message = str(exc)

    log_entry = CimsoSyncLog(
        run_at=datetime.utcnow(),
        rows_fetched=rows_fetched,
        rows_passed=rows_passed,
        rows_failed=rows_failed,
        status=status,
        error_message=error_message,
    )
    db.session.add(log_entry)
    db.session.commit()

    return {
        "rows_fetched": rows_fetched,
        "rows_passed": rows_passed,
        "rows_failed": rows_failed,
        "status": status,
    }


def init_scheduler(app):
    """Registers the recurring CiMSO sync job. Called once from the app
    factory. Guarded so it only starts one scheduler even with Flask's
    debug-mode reloader (which otherwise imports the app twice)."""
    if scheduler.running:
        return

    interval = app.config.get("CIMSO_SYNC_INTERVAL_MINUTES", 15)

    def job():
        with app.app_context():
            run_cimso_sync()

    scheduler.add_job(
        func=job,
        trigger="interval",
        minutes=interval,
        id="cimso_sync_job",
        replace_existing=True,
    )
    scheduler.start()
