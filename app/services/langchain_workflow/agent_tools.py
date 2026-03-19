"""
Langchain tools available to the HR leave-request agent.

Each tool receives a pre-bound `employee_email` via StructuredTool + closure
so the agent never has to supply it directly (it cannot be trusted from LLM output).
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Optional

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.leave_request import LeaveRequest, LeaveStatus
from app.services.meetings_service import get_meetings_for_employee


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fmt_date(d: Optional[dt.date]) -> str:
    return d.isoformat() if d else "N/A"


def _resolve_manager_email(department: Optional[str]) -> str:
    dept_key = (department or "general").strip().lower()
    default_manager = os.getenv("DEFAULT_MANAGER_EMAIL", "manager@test.com")
    dept_map = {
        "engineering": os.getenv("ENG_MANAGER_EMAIL", "eng_manager@test.com"),
        "sales": os.getenv("SALES_MANAGER_EMAIL", "sales_manager@test.com"),
        "hr": os.getenv("HR_MANAGER_EMAIL", "hr_manager@test.com"),
        "finance": os.getenv("FIN_MANAGER_EMAIL", "finance_manager@test.com"),
        "general": default_manager,
    }
    return dept_map.get(dept_key, default_manager)


def _parse_date(value: str) -> Optional[dt.date]:
    try:
        return dt.date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Tool factories — return closures bound to employee_email
# ---------------------------------------------------------------------------

def build_tools(employee_email: str):
    """
    Return a list of LangChain tools bound to a specific employee.
    """

    @tool
    def check_calendar(start_date: str, end_date: str) -> str:
        """
        Check the employee's Google Calendar (or mock data) for meetings
        between start_date and end_date (both MUST be absolute date strings in YYYY-MM-DD format).
        If the user uses relative dates (like 'tomorrow' or 'next Monday'), you MUST resolve them
        to absolute dates before calling this tool.
        Returns a summary of scheduled events.
        """
        sd = _parse_date(start_date)
        ed = _parse_date(end_date)
        if not sd or not ed:
            return "Invalid date format. Please use YYYY-MM-DD."
        meetings = get_meetings_for_employee(employee_email, sd, ed)
        if not meetings:
            return f"No meetings found between {start_date} and {end_date}."
        lines = [f"- {m['summary']} ({m['start']} → {m['end']})" for m in meetings]
        return "Meetings during the requested period:\n" + "\n".join(lines)

    @tool
    def list_leave_requests() -> str:
        """
        List all existing leave requests for the employee.
        """
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(LeaveRequest)
                .filter(LeaveRequest.employee_email == employee_email)
                .order_by(LeaveRequest.start_date.desc())
                .limit(10)
                .all()
            )
            if not rows:
                return "No leave requests found."
            lines = [
                f"- [{r.status.value.upper()}] {r.leave_type or 'N/A'}: "
                f"{_fmt_date(r.start_date)} → {_fmt_date(r.end_date)}"
                for r in rows
            ]
            return "Your recent leave requests:\n" + "\n".join(lines)
        finally:
            db.close()

    @tool
    def submit_leave_request(
        leave_type: str,
        start_date: str,
        end_date: str,
        department: Optional[str] = None,
    ) -> str:
        """
        Submit a new leave request for the employee.
        leave_type must be one of: pto, vacation, sick, unpaid, other.
        start_date and end_date MUST be absolute date strings in YYYY-MM-DD format.
        If the user uses relative dates (like 'tomorrow' or 'next week'), you MUST resolve them
        to absolute dates before calling this tool.
        Returns a confirmation message or an error.
        """
        sd = _parse_date(start_date)
        ed = _parse_date(end_date)
        if not sd:
            return "Invalid start_date. Please use YYYY-MM-DD format."
        if not ed:
            ed = sd

        if leave_type not in ("pto", "vacation", "sick", "unpaid", "other"):
            return (
                f"Invalid leave_type '{leave_type}'. "
                "Choose one of: pto, vacation, sick, unpaid, other."
            )

        manager_email = _resolve_manager_email(department)

        db: Session = SessionLocal()
        try:
            lr = LeaveRequest(
                employee_email=employee_email,
                department=department,
                leave_type=leave_type,
                start_date=sd,
                end_date=ed,
                status=LeaveStatus.PENDING,
                manager_email=manager_email,
            )
            db.add(lr)
            db.commit()
            db.refresh(lr)

            # Send manager approval email
            from app.services.email_service import email_service  # late import to avoid circular
            email_service.send_manager_approval_email(lr)

            return (
                f"Leave request submitted successfully (ID #{lr.id}). "
                f"{leave_type.upper()} from {start_date} to {end_date} is now PENDING manager approval."
            )
        except Exception as exc:
            db.rollback()
            return f"Failed to submit leave request: {exc}"
        finally:
            db.close()

    @tool
    def recommend_best_days_off(look_ahead_days: int = 30) -> str:
        """
        Suggest the best upcoming days or windows to take time off based on
        the employee's calendar. Looks at the next look_ahead_days days (default 30).
        Returns days with the fewest meetings.
        """
        today = dt.date.today()
        end = today + dt.timedelta(days=look_ahead_days)

        meetings = get_meetings_for_employee(employee_email, today, end)

        # Build a set of days that have meetings
        busy_days: set[dt.date] = set()
        for m in meetings:
            try:
                day_str = m["start"][:10]
                busy_days.add(dt.date.fromisoformat(day_str))
            except (ValueError, KeyError):
                pass

        # Find free weekdays in the window
        free_days = []
        day = today + dt.timedelta(days=1)  # start from tomorrow
        while day <= end:
            if day.weekday() < 5 and day not in busy_days:  # Mon–Fri, no meetings
                free_days.append(day)
            day += dt.timedelta(days=1)

        if not free_days:
            return (
                f"Your calendar is quite busy over the next {look_ahead_days} days. "
                "Consider planning further ahead."
            )

        # Show at most 5 suggestions, prefer longer consecutive runs
        suggestions = free_days[:10]
        lines = [f"  - {d.strftime('%A, %B %d %Y')}" for d in suggestions[:5]]
        return (
            f"Based on your calendar, here are some good days to take off in the next {look_ahead_days} days:\n"
            + "\n".join(lines)
            + "\n\nThese days have no scheduled meetings."
        )

    return [check_calendar, list_leave_requests, submit_leave_request, recommend_best_days_off]
