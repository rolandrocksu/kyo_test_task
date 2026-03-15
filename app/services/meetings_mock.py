import datetime as dt
import random
from typing import List, Dict


FAKE_MEETING_TITLES = [
    "Weekly Sync",
    "1:1 with Manager",
    "Project Standup",
    "Client Check-in",
    "Design Review",
    "Planning Session",
]


def get_mock_meetings_for_employee(
    employee_email: str,
    start_date: dt.date,
    end_date: dt.date,
) -> List[Dict]:
    """
    Mock function that randomly returns 0–3 fake meetings
    overlapping the given date range.
    """
    random.seed(hash((employee_email, start_date, end_date)))

    count = random.randint(0, 3)
    meetings: List[Dict] = []

    for _ in range(count):
        day_offset = random.randint(0, max((end_date - start_date).days, 0))
        day = start_date + dt.timedelta(days=day_offset)
        start_hour = random.choice([9, 10, 11, 14, 15, 16])

        start_dt = dt.datetime.combine(day, dt.time(hour=start_hour))
        end_dt = start_dt + dt.timedelta(minutes=30)

        meetings.append(
            {
                "summary": random.choice(FAKE_MEETING_TITLES),
                "start": start_dt.strftime("%Y-%m-%d %H:%M"),
                "end": end_dt.strftime("%Y-%m-%d %H:%M"),
                "attendees": [employee_email],
            }
        )

    return meetings

