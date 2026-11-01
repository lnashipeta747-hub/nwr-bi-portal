"""
app/dashboard/routes.py
--------------------------
Screens 2 and 3 from the study guide's wireframes: Dashboard Home and the
Finance / Reservations / Operations detail views.

CRITICAL DESIGN POINT (this is the line the study guide tells you to say
out loud to the panel): role filtering happens INSIDE the SQL query, via
the `_resort_filter()` helper below — not by hiding buttons in the
template. An EXCO or Manager user's query simply never fetches rows
outside their permitted scope from PostgreSQL/SQLite in the first place.
"""

import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from flask import Blueprint, render_template, Response, request
from flask_login import login_required, current_user
from sqlalchemy import func

from app.extensions import db
from app.auth.decorators import role_required
from app.models import FactBooking, DimResort, DimRoomType, DimDate
from app.models.user import ROLE_ADMIN, ROLE_MANAGER, ROLE_EXCO

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates")


def _resort_filter(query):
    """
    Applies the role-based row filter to a FactBooking query.
    - Admin & EXCO: see every resort (EXCO still only sees *aggregated*
      figures in the templates, but at the SQL layer this is where the
      access decision is actually enforced).
    - Manager: restricted to their assigned resort_scope, if one is set.
    This is the single choke point every dashboard query passes through,
    so there is exactly one place to audit for correctness.
    """
    if current_user.has_role(ROLE_MANAGER) and current_user.resort_scope:
        query = query.join(DimResort).filter(DimResort.resort_name == current_user.resort_scope)
    return query


def _kpis_for_period(start_date: date, end_date: date):
    base = _resort_filter(FactBooking.query.filter(
        FactBooking.checkin_date >= start_date,
        FactBooking.checkin_date <= end_date,
    ))

    total_revenue = base.with_entities(func.coalesce(func.sum(FactBooking.revenue), 0)).scalar()
    total_bookings = base.with_entities(func.count(FactBooking.id)).scalar()
    total_room_nights_sold = base.with_entities(func.coalesce(func.sum(FactBooking.nights), 0)).scalar()

    # Available room-nights = total rooms (in scope) x number of days in period.
    resort_query = DimResort.query
    if current_user.has_role(ROLE_MANAGER) and current_user.resort_scope:
        resort_query = resort_query.filter(DimResort.resort_name == current_user.resort_scope)
    total_rooms = resort_query.with_entities(func.coalesce(func.sum(DimResort.total_rooms), 0)).scalar() or 1
    days_in_period = max((end_date - start_date).days + 1, 1)
    available_room_nights = total_rooms * days_in_period

    occupancy_pct = min(100.0, (float(total_room_nights_sold) / available_room_nights) * 100) if available_room_nights else 0
    revpar = (float(total_revenue) / available_room_nights) if available_room_nights else 0

    return {
        "occupancy_pct": round(occupancy_pct, 1),
        "revenue": float(total_revenue),
        "bookings": int(total_bookings),
        "revpar": round(revpar, 2),
    }


def _revenue_trend(days: int = 30):
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    rows = (
        _resort_filter(
            FactBooking.query.filter(
                FactBooking.checkin_date >= start_date,
                FactBooking.checkin_date <= end_date,
            )
        )
        .with_entities(FactBooking.checkin_date, func.sum(FactBooking.revenue))
        .group_by(FactBooking.checkin_date)
        .order_by(FactBooking.checkin_date)
        .all()
    )
    by_date = {d: float(rev) for d, rev in rows}

    labels, values = [], []
    cursor = start_date
    while cursor <= end_date:
        labels.append(cursor.strftime("%d %b"))
        values.append(round(by_date.get(cursor, 0.0), 2))
        cursor += timedelta(days=1)
    return labels, values


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def home():
    end_date = date.today()
    start_date = end_date - timedelta(days=29)

    kpis = _kpis_for_period(start_date, end_date)
    labels, values = _revenue_trend(30)

    return render_template(
        "dashboard.html",
        kpis=kpis,
        chart_labels=labels,
        chart_values=values,
    )


@dashboard_bp.route("/finance")
@login_required
@role_required(ROLE_ADMIN, ROLE_MANAGER)
def finance():
    """Drill-down: revenue by resort, then by room type within each resort."""
    rows = (
        _resort_filter(FactBooking.query)
        .join(DimResort).join(DimRoomType)
        .with_entities(
            DimResort.resort_name,
            DimRoomType.room_type_name,
            func.count(FactBooking.id).label("bookings"),
            func.coalesce(func.sum(FactBooking.revenue), 0).label("revenue"),
        )
        .group_by(DimResort.resort_name, DimRoomType.room_type_name)
        .order_by(DimResort.resort_name, DimRoomType.room_type_name)
        .all()
    )
    return render_template("finance.html", rows=rows)


@dashboard_bp.route("/reservations")
@login_required
@role_required(ROLE_ADMIN, ROLE_MANAGER)
def reservations():
    """A booking-level list — the closest thing to a 'calendar' view in
    Phase 1. Sorted by check-in date, most recent first."""
    bookings = (
        _resort_filter(FactBooking.query)
        .join(DimResort).join(DimRoomType)
        .order_by(FactBooking.checkin_date.desc())
        .limit(200)
        .all()
    )
    return render_template("reservations.html", bookings=bookings)


@dashboard_bp.route("/operations")
@login_required
@role_required(ROLE_ADMIN, ROLE_MANAGER)
def operations():
    """Occupancy by resort for the current month."""
    end_date = date.today()
    start_date = end_date.replace(day=1)
    days_in_period = max((end_date - start_date).days + 1, 1)

    resort_query = DimResort.query
    if current_user.has_role(ROLE_MANAGER) and current_user.resort_scope:
        resort_query = resort_query.filter(DimResort.resort_name == current_user.resort_scope)
    resorts = resort_query.all()

    rows = []
    for resort in resorts:
        nights_sold = (
            FactBooking.query.filter(
                FactBooking.resort_id == resort.id,
                FactBooking.checkin_date >= start_date,
                FactBooking.checkin_date <= end_date,
            )
            .with_entities(func.coalesce(func.sum(FactBooking.nights), 0))
            .scalar()
        )
        available = resort.total_rooms * days_in_period
        occ = min(100.0, (float(nights_sold) / available) * 100) if available else 0
        rows.append({"resort_name": resort.resort_name, "occupancy_pct": round(occ, 1),
                      "total_rooms": resort.total_rooms, "nights_sold": int(nights_sold)})

    return render_template("operations.html", rows=rows)


@dashboard_bp.route("/export/<view_name>")
@login_required
@role_required(ROLE_ADMIN, ROLE_MANAGER)
def export_csv(view_name):
    """One-click CSV export (Slide 5 UX section: 'Every table has an
    Export button'). Applies the exact same role filter as the on-screen
    view, so an export can never leak more than the screen shows."""
    output = io.StringIO()
    writer = csv.writer(output)

    if view_name == "finance":
        writer.writerow(["Resort", "Room Type", "Bookings", "Revenue (N$)"])
        rows = (
            _resort_filter(FactBooking.query)
            .join(DimResort).join(DimRoomType)
            .with_entities(
                DimResort.resort_name, DimRoomType.room_type_name,
                func.count(FactBooking.id), func.coalesce(func.sum(FactBooking.revenue), 0),
            )
            .group_by(DimResort.resort_name, DimRoomType.room_type_name)
            .all()
        )
        for r in rows:
            writer.writerow(r)

    elif view_name == "reservations":
        writer.writerow(["Resort", "Room Type", "Check-in", "Check-out", "Nights", "Guests", "Revenue (N$)"])
        bookings = (
            _resort_filter(FactBooking.query)
            .join(DimResort).join(DimRoomType)
            .order_by(FactBooking.checkin_date.desc())
            .all()
        )
        for b in bookings:
            writer.writerow([
                b.resort.resort_name, b.room_type.room_type_name,
                b.checkin_date, b.checkout_date, b.nights, b.guest_count, b.revenue,
            ])
    else:
        return Response("Unknown export view.", status=404)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={view_name}_export.csv"},
    )
