"""
app/auth/routes.py
--------------------
Screen 1 from the study guide's wireframes: Login.

Data flow (matches Slide 3 exactly):
  1. Browser sends username + password (+ role, for the demo dropdown) to Flask
  2. Flask-Login / this route checks the `users` table in the database
  3. If correct: read the user's role, start a session, redirect to their dashboard
  4. If wrong: show an error and log the failed attempt with the IP address
"""

from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, LoginAttempt

auth_bp = Blueprint("auth", __name__, template_folder="../templates")


def _client_ip():
    # Respects a reverse proxy's X-Forwarded-For if present (common in
    # production deployments), otherwise falls back to the direct remote address.
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() if forwarded else request.remote_addr


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        success = user is not None and user.check_password(password) and user.is_active_flag

        # Audit every attempt, successful or not (Slide 3 + Slide 5, L1).
        attempt = LoginAttempt(
            username_attempted=username,
            ip_address=_client_ip(),
            success=success,
        )
        db.session.add(attempt)
        db.session.commit()

        if success:
            login_user(user)
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            flash(f"Welcome back, {user.username} ({user.role.name}).", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.home"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
