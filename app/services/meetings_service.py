import datetime as dt
from typing import List, Dict

from . import __init__  # silence linter about empty package; no-op
from .meetings_mock import get_mock_meetings_for_employee
from .google_calendar_service import get_google_calendar_events
from app.db import SessionLocal


def get_meetings_for_employee(
    employee_email: str,
    start_date: dt.date,
    end_date: dt.date,
) -> List[Dict]:
    """
    Service hook for fetching meetings for an employee over a date range.

    Tries to fetch real Google Calendar events first, falls back to mock data.
    """
    db = SessionLocal()
    try:
        real_meetings = get_google_calendar_events(
            db=db,
            employee_email=employee_email,
            start_date=start_date,
            end_date=end_date,
        )
        if real_meetings:
            return real_meetings
    finally:
        db.close()

    return get_mock_meetings_for_employee(
        employee_email=employee_email,
        start_date=start_date,
        end_date=end_date,
    )
