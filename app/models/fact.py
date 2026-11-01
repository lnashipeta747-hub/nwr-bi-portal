"""
app/models/fact.py
--------------------
Fact tables — "where clean, validated data lives permanently" (Slide 2).
These are lean: mostly foreign keys into the dimension tables plus the
actual measurable numbers (revenue, nights, guests). All dashboard KPIs
(Occupancy, Revenue, Bookings, RevPAR) are calculated by querying these
tables, never the staging tables.
"""

from datetime import datetime
from app.extensions import db


class FactBooking(db.Model):
    __tablename__ = "fact_bookings"

    id = db.Column(db.Integer, primary_key=True)

    resort_id = db.Column(db.Integer, db.ForeignKey("dim_resort.id"), nullable=False)
    room_type_id = db.Column(db.Integer, db.ForeignKey("dim_room_type.id"), nullable=False)
    booking_date_key = db.Column(db.Date, db.ForeignKey("dim_date.date_key"), nullable=False)
    checkin_date = db.Column(db.Date, nullable=False)
    checkout_date = db.Column(db.Date, nullable=False)

    nights = db.Column(db.Integer, nullable=False)
    guest_count = db.Column(db.Integer, nullable=False, default=1)
    revenue = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    source = db.Column(db.String(20), nullable=False)  # CIMSO_API / MANUAL_UPLOAD
    staging_record_id = db.Column(db.Integer, db.ForeignKey("staging_bookings.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    resort = db.relationship("DimResort")
    room_type = db.relationship("DimRoomType")

    def __repr__(self):
        return f"<FactBooking id={self.id} resort_id={self.resort_id} revenue={self.revenue}>"
