"""
Importing every model module here ensures they are all registered on
db.metadata by the time db.create_all() runs in run.py / seed_data.py.
"""

from app.models.user import User, Role, LoginAttempt, ROLE_ADMIN, ROLE_MANAGER, ROLE_EXCO, ALL_ROLES  # noqa
from app.models.dimension import DimResort, DimRoomType, DimDate  # noqa
from app.models.staging import StagingBooking, UploadAuditLog, CimsoSyncLog  # noqa
from app.models.fact import FactBooking  # noqa
