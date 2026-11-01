"""
app/upload/routes.py
----------------------
Slide 2, Step 6 / Slide 4 "CSV / Excel Uploads (Unstructured Data)".

Handles the manual file upload path: staff submit a spreadsheet, pandas
reads and standardises it, every row lands in StagingBooking, validation
runs, passing rows are promoted to FactBooking, and the whole event is
recorded in UploadAuditLog for accountability.

Only Admin and Manager roles can upload (EXCO is read-only in this design).
"""

import os
from datetime import datetime

import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.auth.decorators import role_required
from app.models import StagingBooking, UploadAuditLog
from app.upload.validators import normalize_columns, validate_and_promote_staging_row
from app.models.user import ROLE_ADMIN, ROLE_MANAGER

upload_bp = Blueprint("upload", __name__, template_folder="../templates")


def _allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]


def _read_spreadsheet(filepath: str) -> pd.DataFrame:
    if filepath.lower().endswith(".csv"):
        return pd.read_csv(filepath, dtype=str, keep_default_na=False)
    return pd.read_excel(filepath, dtype=str)


@upload_bp.route("/upload", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_MANAGER)
def upload_file():
    if request.method == "POST":
        file = request.files.get("file")

        if not file or file.filename == "":
            flash("Please choose a CSV or Excel file to upload.", "warning")
            return redirect(url_for("upload.upload_file"))

        if not _allowed_file(file.filename):
            flash("Unsupported file type. Please upload a .csv, .xlsx, or .xls file.", "danger")
            return redirect(url_for("upload.upload_file"))

        filename = secure_filename(file.filename)
        stamped_name = f"{datetime.utcnow():%Y%m%d%H%M%S}_{filename}"
        os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], stamped_name)
        file.save(filepath)

        try:
            df = _read_spreadsheet(filepath)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user, then logged
            flash(f"Could not read the file: {exc}", "danger")
            return redirect(url_for("upload.upload_file"))

        column_map = normalize_columns(df.columns)
        df = df.rename(columns=column_map)

        rows_total = len(df)
        rows_passed = 0
        rows_failed = 0

        for _, row in df.iterrows():
            staging_row = StagingBooking(
                source="MANUAL_UPLOAD",
                source_reference=filename,
                resort_name_raw=row.get("resort_name", ""),
                room_type_raw=row.get("room_type", ""),
                booking_date_raw=row.get("booking_date", ""),
                checkin_date_raw=row.get("checkin_date", ""),
                checkout_date_raw=row.get("checkout_date", ""),
                nights_raw=row.get("nights", ""),
                revenue_raw=row.get("revenue", ""),
                guest_count_raw=row.get("guest_count", ""),
            )
            db.session.add(staging_row)
            db.session.flush()  # assigns staging_row.id before validation

            passed = validate_and_promote_staging_row(staging_row)
            rows_passed += int(passed)
            rows_failed += int(not passed)

        audit = UploadAuditLog(
            uploaded_by_user_id=current_user.id,
            original_filename=filename,
            rows_total=rows_total,
            rows_passed=rows_passed,
            rows_failed=rows_failed,
            notes="Uploaded via web portal.",
        )
        db.session.add(audit)
        db.session.commit()

        flash(
            f"Upload complete: {rows_passed} of {rows_total} rows passed validation "
            f"and were added to the dashboard. {rows_failed} row(s) failed and are "
            f"available for review below.",
            "success" if rows_failed == 0 else "warning",
        )
        return redirect(url_for("upload.upload_file"))

    recent_uploads = (
        UploadAuditLog.query.order_by(UploadAuditLog.uploaded_at.desc()).limit(15).all()
    )
    failed_rows = (
        StagingBooking.query.filter_by(validation_status="FAILED")
        .order_by(StagingBooking.ingested_at.desc())
        .limit(30)
        .all()
    )
    return render_template("upload.html", recent_uploads=recent_uploads, failed_rows=failed_rows)
