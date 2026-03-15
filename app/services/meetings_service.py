import datetime as dt
from typing import List, Dict

from . import __init__  # silence linter about empty package; no-op
from .meetings_mock import get_mock_meetings_for_employee


def get_meetings_for_employee(
    employee_email: str,
    start_date: dt.date,
    end_date: dt.date,
) -> List[Dict]:
    """
    Service hook for fetching meetings for an employee over a date range.

    For now this returns mocked data, but you can later replace the body
    with a real Google Calendar integration without touching callers.
    """

    return get_mock_meetings_for_employee(
        employee_email=employee_email,
        start_date=start_date,
        end_date=end_date,
    )

