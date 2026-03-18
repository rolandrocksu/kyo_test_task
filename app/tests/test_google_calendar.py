import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from sqlalchemy.orm import Session
from app.models.google_token import GoogleToken
from app.services.google_calendar_service import get_google_calendar_events

def test_get_google_calendar_events_no_token(db_session):
    """Test that it returns an empty list if no token exists for the employee."""
    events = get_google_calendar_events(db_session, "nonexistent@example.com", date(2026, 3, 17), date(2026, 3, 18))
    assert events == []

@patch("app.services.google_calendar_service.build")
@patch("app.services.google_calendar_service.Credentials")
def test_get_google_calendar_events_success(mock_creds, mock_build, db_session):
    """Test successful fetching of events with a mock Google API."""
    # Setup mock token in DB
    token = GoogleToken(
        employee_email="test@example.com",
        access_token="fake_access",
        refresh_token="fake_refresh",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="fake_id",
        client_secret="fake_secret",
        scopes="https://www.googleapis.com/auth/calendar.readonly"
    )
    db_session.add(token)
    db_session.commit()

    # Mock the Google Calendar API response
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_service.events().list().execute.return_value = {
        "items": [
            {
                "summary": "Real Meeting",
                "start": {"dateTime": "2026-03-17T10:00:00Z"},
                "end": {"dateTime": "2026-03-17T10:30:00Z"},
            }
        ]
    }

    events = get_google_calendar_events(db_session, "test@example.com", date(2026, 3, 17), date(2026, 3, 18))
    
    assert len(events) == 1
    assert events[0]["summary"] == "Real Meeting"
    assert events[0]["start"] == "2026-03-17 10:00"
