"""
app/models/dimension.py
------------------------
Dimension tables. In a star schema, dimension tables hold the descriptive,
slowly-changing context (which resort, which room type, which calendar
date) that fact rows point to via foreign keys. This keeps fact tables
lean (numbers + foreign keys only) and avoids repeating text like resort
names on every single row.
"""

from app.extensions import db


class DimResort(db.Model):
    __tablename__ = "dim_resort"

    id = db.Column(db.Integer, primary_key=True)
    resort_name = db.Column(db.String(120), unique=True, nullable=False)
    region = db.Column(db.String(120))
    total_rooms = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<DimResort {self.resort_name}>"


class DimRoomType(db.Model):
    __tablename__ = "dim_room_type"

    id = db.Column(db.Integer, primary_key=True)
    room_type_name = db.Column(db.String(80), unique=True, nullable=False)
    base_rate = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    def __repr__(self):
        return f"<DimRoomType {self.room_type_name}>"


class DimDate(db.Model):
    """
    A classic BI 'date dimension' — one row per calendar day, pre-computed
    so queries can group by month/quarter/weekday without doing date math
    in every single SQL query.
    """
    __tablename__ = "dim_date"

    date_key = db.Column(db.Date, primary_key=True)  # e.g. 2026-07-14
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    month_name = db.Column(db.String(20), nullable=False)
    day = db.Column(db.Integer, nullable=False)
    weekday_name = db.Column(db.String(20), nullable=False)
    is_weekend = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<DimDate {self.date_key}>"
