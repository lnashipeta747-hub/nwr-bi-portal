"""
config.py
---------
Central configuration for the NWR BI Portal.

Design note (why this matters for the panel):
Nothing secret is hard-coded here. Every sensitive value (database
credentials, the CiMSO API key, the Flask secret key) is read from an
environment variable. In production these live in a `.env` file that is
NEVER committed to GitHub (see .gitignore). This is the "Environment
Variable" pattern described in the study guide's glossary.

Database note:
The brief and study guide specify PostgreSQL for production. This project
is written entirely against SQLAlchemy, so the *only* thing that changes
when you move from a laptop demo to a real Postgres server is the
DATABASE_URL environment variable below — none of the application code
(models, queries, routes) needs to change. For the hackathon demo/dev
environment we default to SQLite so anyone can clone the repo and run it
in 30 seconds with zero external services. See README.md -> "Switching to
PostgreSQL" for the one-line change needed for Phase 2.
"""

import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Core Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-CHANGE-ME")

    # --- Database ---
    # Production (Phase 2) example:
    #   DATABASE_URL=postgresql://nwr_user:password@localhost:5432/nwr_bi
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'instance', 'nwr_bi.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Sessions ---
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # In production behind HTTPS/TLS this MUST be True (see Slide 5, L3).
    SESSION_COOKIE_SECURE = os.environ.get("FORCE_SECURE_COOKIES", "false").lower() == "true"

    # --- CiMSO integration (mock in Phase 1, real endpoint in Phase 2) ---
    CIMSO_API_BASE_URL = os.environ.get("CIMSO_API_BASE_URL", "https://mock-cimso.local/api/v1")
    CIMSO_API_KEY = os.environ.get("CIMSO_API_KEY", "")
    CIMSO_SYNC_INTERVAL_MINUTES = int(os.environ.get("CIMSO_SYNC_INTERVAL_MINUTES", "15"))
    # Set to "true" to use the built-in fake CiMSO data generator instead of a
    # real HTTP call. This is what lets the whole portal run end-to-end
    # during the hackathon without live NWR credentials.
    CIMSO_USE_MOCK = os.environ.get("CIMSO_USE_MOCK", "true").lower() == "true"

    # --- Uploads ---
    UPLOAD_FOLDER = os.path.join(basedir, "uploads_incoming")
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB per upload
    ALLOWED_UPLOAD_EXTENSIONS = {"csv", "xlsx", "xls"}

    # --- Scheduler ---
    SCHEDULER_API_ENABLED = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
