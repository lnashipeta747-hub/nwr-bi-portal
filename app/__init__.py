"""
app/__init__.py
-----------------
The application factory (create_app). Using a factory instead of a bare
module-level `app = Flask(__name__)` is what makes this "production-ready"
in the sense the study guide means on Slide 6: it lets you spin up
different configurations (development vs production, or a throwaway
instance for automated tests) from the same codebase.
"""

import os
from flask import Flask, render_template
from flask_login import current_user

from config import config_by_name
from app.extensions import db, login_manager


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    os.makedirs(app.instance_path, exist_ok=True)

    # --- Extensions ---
    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Blueprints ---
    from app.auth import auth_bp
    from app.dashboard import dashboard_bp
    from app.api import api_bp
    from app.upload import upload_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(upload_bp)

    # --- Error handlers (401/403 map onto the RBAC decorator, Slide 5 L2) ---
    @app.errorhandler(401)
    def unauthorized(_e):
        return render_template("error.html", code=401,
                                message="Please log in to view this page."), 401

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403,
                                message="Your role does not have access to this page."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="Page not found."), 404

    # --- Scheduler (Slide 4: APScheduler runs the CiMSO sync every 15 min) ---
    if not app.config.get("TESTING"):
        from app.api.scheduler import init_scheduler
        init_scheduler(app)

    @app.context_processor
    def inject_globals():
        return {"current_user": current_user}

    return app
