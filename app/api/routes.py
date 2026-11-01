"""
app/api/routes.py
-------------------
The "API/ETL Layer" block from the 5-layer data flow diagram (Slide 3,
Figure 2). In production this sync runs automatically every 15 minutes
via APScheduler (see app/api/scheduler.py). This blueprint additionally
exposes a manual "Sync Now" button/route, which is what you'll actually
click during the live demo so the panel doesn't have to wait 15 minutes
to see data flow in.
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required

from app.auth.decorators import role_required
from app.models.user import ROLE_ADMIN, ROLE_MANAGER
from app.models import CimsoSyncLog
from app.api.scheduler import run_cimso_sync

api_bp = Blueprint("api", __name__, template_folder="../templates")


@api_bp.route("/sync/cimso", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN, ROLE_MANAGER)
def trigger_cimso_sync():
    result = run_cimso_sync()
    flash(
        f"CiMSO sync complete: {result['rows_passed']} of {result['rows_fetched']} "
        f"records passed validation.",
        "success" if result["rows_failed"] == 0 else "warning",
    )
    return redirect(url_for("dashboard.home"))


@api_bp.route("/sync/history")
@login_required
@role_required(ROLE_ADMIN, ROLE_MANAGER)
def sync_history():
    logs = CimsoSyncLog.query.order_by(CimsoSyncLog.run_at.desc()).limit(30).all()
    return render_template("sync_history.html", logs=logs)
