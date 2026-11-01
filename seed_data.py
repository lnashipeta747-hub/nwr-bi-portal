"""
seed_data.py
-------------
Run once after cloning the repo:

    python3 seed_data.py

Creates all tables (if they don't already exist), the three roles
(Admin / Manager / EXCO), one demo user per role, the resort/room-type
dimension rows, and then runs one CiMSO mock sync so the dashboard has
real numbers to show the moment you log in — no waiting for the
15-minute scheduler on demo day.

Demo login credentials (change these before any real deployment):
    admin@nwr    / admin123    (Admin)
    manager@nwr  / manager123  (Manager, scoped to Etosha Safari Lodge)
    exco@nwr     / exco123     (EXCO)
"""

from app import create_app
from app.extensions import db
from app.models import Role, User, DimResort, DimRoomType
from app.models.user import ROLE_ADMIN, ROLE_MANAGER, ROLE_EXCO, ALL_ROLES
from app.api.cimso_client import RESORTS, ROOM_TYPES
from app.api.scheduler import run_cimso_sync


def seed():
    app = create_app("development")
    with app.app_context():
        db.create_all()

        # --- Roles ---
        for role_name in ALL_ROLES:
            if not Role.query.filter_by(name=role_name).first():
                db.session.add(Role(name=role_name, description=f"{role_name} role"))
        db.session.commit()

        # --- Dimension seed data (so resort/room-type lookups aren't empty) ---
        for resort_name, region, total_rooms in RESORTS:
            if not DimResort.query.filter_by(resort_name=resort_name).first():
                db.session.add(DimResort(resort_name=resort_name, region=region, total_rooms=total_rooms))
        for room_type_name, base_rate in ROOM_TYPES:
            if not DimRoomType.query.filter_by(room_type_name=room_type_name).first():
                db.session.add(DimRoomType(room_type_name=room_type_name, base_rate=base_rate))
        db.session.commit()

        # --- Demo users ---
        admin_role = Role.query.filter_by(name=ROLE_ADMIN).first()
        manager_role = Role.query.filter_by(name=ROLE_MANAGER).first()
        exco_role = Role.query.filter_by(name=ROLE_EXCO).first()

        demo_users = [
            ("admin@nwr", "admin123", admin_role, None),
            ("manager@nwr", "manager123", manager_role, "Etosha Safari Lodge"),
            ("exco@nwr", "exco123", exco_role, None),
        ]
        for username, password, role, scope in demo_users:
            if not User.query.filter_by(username=username).first():
                user = User(username=username, email=username, role=role, resort_scope=scope)
                user.set_password(password)
                db.session.add(user)
        db.session.commit()

        print("✔ Roles, resorts, room types, and demo users seeded.")

        # --- Populate some historical bookings via the mock CiMSO pipeline ---
        # Run a few sync cycles pretending to be a few different days, so
        # the 30-day revenue trend chart isn't empty on first login.
        from datetime import datetime, timedelta
        import app.api.cimso_client as cimso_client

        original_fetch = cimso_client.fetch_bookings

        for days_ago in range(29, -1, -3):
            since = datetime.utcnow() - timedelta(days=days_ago)
            cimso_client.fetch_bookings = lambda s=since, m=15: cimso_client._fetch_from_mock(s, m)
            run_cimso_sync()

        cimso_client.fetch_bookings = original_fetch

        print("✔ Seeded historical CiMSO booking data across the last 30 days.")
        print("\nDemo login credentials:")
        for username, password, role, _ in demo_users:
            print(f"  {username} / {password}  ->  {role.name}")


if __name__ == "__main__":
    seed()
