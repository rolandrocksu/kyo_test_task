"""
Unit tests for app.services.langchain_workflow.agent_tools.build_tools

All DB and external-service calls (including Google APIs) are patched so
tests run with no real Postgres, LangChain, or Google Calendar connection.
"""
import sys
import datetime as dt
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out google packages before any app imports pull them in
# ---------------------------------------------------------------------------
for _mod in [
    "google",
    "google.oauth2",
    "google.oauth2.credentials",
    "google.auth",
    "google.auth.transport",
    "google.auth.transport.requests",
    "googleapiclient",
    "googleapiclient.discovery",
]:
    sys.modules.setdefault(_mod, MagicMock())

from app.services.langchain_workflow.agent_tools import build_tools  # noqa: E402


EMPLOYEE = "test@example.com"


def _get_tool(name: str):
    """Return the named tool from build_tools."""
    tools = build_tools(EMPLOYEE)
    for t in tools:
        if t.name == name:
            return t
    raise KeyError(f"Tool '{name}' not found in {[t.name for t in tools]}")


# ---------------------------------------------------------------------------
# list_leave_requests
# ---------------------------------------------------------------------------

class TestListLeaveRequests(unittest.TestCase):

    @patch("app.services.langchain_workflow.agent_tools.SessionLocal")
    def test_empty_returns_no_requests_message(self, mock_session_cls):
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_session_cls.return_value = db

        tool = _get_tool("list_leave_requests")
        result = tool.invoke({})

        self.assertIn("No leave requests found", result)
        db.close.assert_called_once()

    @patch("app.services.langchain_workflow.agent_tools.SessionLocal")
    def test_with_data_returns_formatted_list(self, mock_session_cls):
        db = MagicMock()

        lr = MagicMock()
        lr.status.value = "PENDING"
        lr.leave_type = "vacation"
        lr.start_date = dt.date(2026, 4, 1)
        lr.end_date = dt.date(2026, 4, 5)

        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [lr]
        mock_session_cls.return_value = db

        tool = _get_tool("list_leave_requests")
        result = tool.invoke({})

        self.assertIn("PENDING", result)
        self.assertIn("vacation", result)
        self.assertIn("2026-04-01", result)
        self.assertIn("2026-04-05", result)
        db.close.assert_called_once()


# ---------------------------------------------------------------------------
# submit_leave_request
# ---------------------------------------------------------------------------

class TestSubmitLeaveRequest(unittest.TestCase):

    def test_invalid_leave_type_returns_error(self):
        tool = _get_tool("submit_leave_request")
        result = tool.invoke({
            "leave_type": "holiday",
            "start_date": "2026-04-01",
            "end_date": "2026-04-05",
        })
        self.assertIn("Invalid leave_type", result)
        self.assertIn("holiday", result)

    def test_invalid_start_date_returns_error(self):
        tool = _get_tool("submit_leave_request")
        result = tool.invoke({
            "leave_type": "pto",
            "start_date": "not-a-date",
            "end_date": "2026-04-05",
        })
        self.assertIn("Invalid start_date", result)

    @patch("app.services.langchain_workflow.agent_tools.SessionLocal")
    @patch("app.services.langchain_workflow.agent_tools.LeaveRequest")
    def test_success_returns_confirmation(self, mock_lr_cls, mock_session_cls):
        db = MagicMock()
        mock_session_cls.return_value = db

        lr_instance = MagicMock()
        lr_instance.id = 42
        mock_lr_cls.return_value = lr_instance

        # Patch the late import of email_service inside the tool
        with patch.dict(sys.modules, {
            "app.services.email_service": MagicMock(email_service=MagicMock()),
        }):
            tool = _get_tool("submit_leave_request")
            result = tool.invoke({
                "leave_type": "pto",
                "start_date": "2026-04-01",
                "end_date": "2026-04-03",
                "department": "engineering",
            })

        self.assertIn("submitted successfully", result)
        self.assertIn("pto", result.lower())
        db.commit.assert_called_once()
        db.close.assert_called_once()


# ---------------------------------------------------------------------------
# check_calendar
# ---------------------------------------------------------------------------

class TestCheckCalendar(unittest.TestCase):

    def test_bad_dates_returns_error(self):
        tool = _get_tool("check_calendar")
        result = tool.invoke({"start_date": "bad", "end_date": "also-bad"})
        self.assertIn("Invalid date format", result)

    @patch("app.services.langchain_workflow.agent_tools.get_meetings_for_employee")
    def test_no_meetings_returns_no_meetings_message(self, mock_get):
        mock_get.return_value = []

        tool = _get_tool("check_calendar")
        result = tool.invoke({"start_date": "2026-04-01", "end_date": "2026-04-07"})

        self.assertIn("No meetings found", result)
        mock_get.assert_called_once_with(EMPLOYEE, dt.date(2026, 4, 1), dt.date(2026, 4, 7))

    @patch("app.services.langchain_workflow.agent_tools.get_meetings_for_employee")
    def test_with_meetings_returns_formatted_list(self, mock_get):
        mock_get.return_value = [
            {"summary": "Standup", "start": "2026-04-01 09:00", "end": "2026-04-01 09:15"},
            {"summary": "Planning", "start": "2026-04-02 14:00", "end": "2026-04-02 15:00"},
        ]

        tool = _get_tool("check_calendar")
        result = tool.invoke({"start_date": "2026-04-01", "end_date": "2026-04-07"})

        self.assertIn("Standup", result)
        self.assertIn("Planning", result)


# ---------------------------------------------------------------------------
# recommend_best_days_off
# ---------------------------------------------------------------------------

class TestRecommendBestDaysOff(unittest.TestCase):

    @patch("app.services.langchain_workflow.agent_tools.get_meetings_for_employee")
    def test_free_days_returned(self, mock_get):
        mock_get.return_value = []  # no meetings → lots of free days

        tool = _get_tool("recommend_best_days_off")
        result = tool.invoke({"look_ahead_days": 14})

        self.assertIn("good days to take off", result)

    @patch("app.services.langchain_workflow.agent_tools.get_meetings_for_employee")
    def test_small_window_all_busy_returns_busy_message(self, mock_get):
        # Fill every day in a 5-day window with meetings
        today = dt.date.today()
        busy = []
        d = today
        for _ in range(7):
            d += dt.timedelta(days=1)
            busy.append({
                "summary": "Meeting",
                "start": d.isoformat() + " 09:00",
                "end": d.isoformat() + " 10:00",
            })
        mock_get.return_value = busy

        tool = _get_tool("recommend_best_days_off")
        result = tool.invoke({"look_ahead_days": 5})

        # Within a 5-day window fully covered by meetings, expect the "quite busy" message
        self.assertIn("quite busy", result)


if __name__ == "__main__":
    unittest.main()
