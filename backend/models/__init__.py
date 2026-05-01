# backend/models/__init__.py
"""
Centralized model registry for Flask-Migrate
Import all models here to ensure they're discovered
"""

# Base models and utilities
from backend.models.models import (
    db,
    CalendarYear,
    CalendarMonth,
    CalendarDay,
    Locations,
    Users,
    Roles,
    Subjects,

)

# Import models from other modules


