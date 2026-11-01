"""
extensions.py
-------------
Flask extension instances live here, separate from the app factory in
app/__init__.py. This avoids circular imports: models.py can `from
app.extensions import db` without needing to import the app factory itself.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
login_manager = LoginManager()
scheduler = BackgroundScheduler()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access the BI Portal."
login_manager.login_message_category = "warning"
