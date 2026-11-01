"""
app/models/staging.py
-----------------------
Staging tables — the "temporary holding area" described in the study guide
(Slide 2, Step 2 and Slide 4). Nothing coming in from CiMSO or a manual
CSV/Excel upload is trusted immediately. It lands here first in as
close to raw form as possible, gets validated, and only rows that pass
validation are promoted into the fact tables. Rows that fail stay here
with an error reason attached, so nothing is silently dropped.
"""

from datetime import datetime
from app.extensions import db


class StagingBooking(db.Model):
    """
    Raw booking rows before validation, regardless of whether they came
    from the CiMSO API sync or a manual CSV/Excel upload.
    """
    __tablename__ = "staging_bookings"

    id = db.Column(db.Integer, primary_key=True)

    source = db.Column(db.String(20), nullable=False)  # "CIMSO_API" or "MANUAL_UPLOAD"
    source_reference = db.Column(db.String(120))  # e.g. CiMSO booking ID or uploaded filename

    resort_name_raw = db.Column(db.String(120))
    room_type_raw = db.Column(db.String(80))
    booking_date_raw = db.Column(db.String(50))   # kept as string until parsed/validated
    checkin_date_raw = db.Column(db.String(50))
    checkout_date_raw = db.Column(db.String(50))
    nights_raw = db.Column(db.String(20))
    revenue_raw = db.Column(db.String(30))
    guest_count_raw = db.Column(db.String(20))

    ingested_at = db.Column(db.DateTime, default=datetime.utcnow)

    validation_status = db.Column(db.String(20), default="PENDING")  # PENDING / PASSED / FAILED
    validation_error = db.Column(db.Text, nullable=True)
    promoted_to_fact = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<StagingBooking id={self.id} source={self.source} status={self.validation_status}>"


class UploadAuditLog(db.Model):
    """
    Accountability trail for every manual file upload (Slide 4:
    'Every upload is recorded: who uploaded it, when, how many rows it
    had, and the reason any rows were rejected.')
    """
    __tablename__ = "upload_audit_log"

    id = db.Column(db.Integer, primary_key=True)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    rows_total = db.Column(db.Integer, default=0)
    rows_passed = db.Column(db.Integer, default=0)
    rows_failed = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, nullable=True)

    uploaded_by = db.relationship("User")

    def __repr__(self):
        return f"<UploadAuditLog {self.original_filename} by user {self.uploaded_by_user_id}>"


class CimsoSyncLog(db.Model):
    """
    Audit trail for each automated CiMSO API pull (APScheduler job).
    Mirrors the manual upload audit log so both data-entry paths are
    equally traceable.
    """
    __tablename__ = "cimso_sync_log"

    id = db.Column(db.Integer, primary_key=True)
    run_at = db.Column(db.DateTime, default=datetime.utcnow)
    rows_fetched = db.Column(db.Integer, default=0)
    rows_passed = db.Column(db.Integer, default=0)
    rows_failed = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="SUCCESS")  # SUCCESS / FAILED
    error_message = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<CimsoSyncLog {self.run_at} status={self.status}>"
