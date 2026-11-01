"""
app/models/user.py
-------------------
Users and Roles — the foundation of Authentication (proving who you are)
and Authorisation / RBAC (deciding what you can see), as described on
Slide 3 and Slide 5 of the study guide.
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db

# Fixed set of roles for Phase 1. Kept as a Python constant (not just DB rows)
# so decorators like @role_required("EXCO") can reference it safely.
ROLE_ADMIN = "Admin"
ROLE_MANAGER = "Manager"
ROLE_EXCO = "EXCO"
ALL_ROLES = [ROLE_ADMIN, ROLE_MANAGER, ROLE_EXCO]


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

    users = db.relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    role = db.relationship("Role", back_populates="users")

    # Which resort/department a Manager is scoped to (None = all, used by EXCO/Admin)
    resort_scope = db.Column(db.String(100), nullable=True)

    is_active_flag = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, raw_password: str) -> None:
        # Werkzeug's default method is pbkdf2:sha256, which — like bcrypt —
        # is a one-way, salted hash. Either satisfies the "hash, never
        # store plaintext" requirement in the study guide's Security slide.
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_active(self):
        return self.is_active_flag

    def has_role(self, *role_names) -> bool:
        return self.role.name in role_names

    def __repr__(self):
        return f"<User {self.username} ({self.role.name if self.role else 'no role'})>"


class LoginAttempt(db.Model):
    """
    Audit trail for authentication events (Slide 3: 'shows an error and logs
    the failed attempt with the IP address'; Slide 5, L1).
    """
    __tablename__ = "login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    username_attempted = db.Column(db.String(80), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"<LoginAttempt {self.username_attempted} {status} @ {self.timestamp}>"
