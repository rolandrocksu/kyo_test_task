import datetime as dt
from typing import List, Dict
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session
from app.models.google_token import GoogleToken

def get_google_calendar_events(
    db: Session,
    employee_email: str,
    start_date: dt.date,
    end_date: dt.date,
) -> List[Dict]:
    """
    Fetch events from Google Calendar for a specific employee.
    Refreshes the token if necessary.
    """
    token_record = db.query(GoogleToken).filter(GoogleToken.employee_email == employee_email).first()
    if not token_record:
        return []

    creds = Credentials(
        token=token_record.access_token,
        refresh_token=token_record.refresh_token,
        token_uri=token_record.token_uri,
        client_id=token_record.client_id,
        client_secret=token_record.client_secret,
        scopes=token_record.scopes.split(','),
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Update the stored token
        token_record.access_token = creds.token
        db.add(token_record)
        db.commit()

    service = build('calendar', 'v3', credentials=creds)

    # Convert dates to RFC3339 format
    time_min = dt.datetime.combine(start_date, dt.time.min).isoformat() + 'Z'
    time_max = dt.datetime.combine(end_date, dt.time.max).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    formatted_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        # Simple parsing/formatting to match existing mock format
        # existing format: "2026-03-17 09:00"
        try:
            start_dt = dt.datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = dt.datetime.fromisoformat(end.replace('Z', '+00:00'))
            start_str = start_dt.strftime("%Y-%m-%d %H:%M")
            end_str = end_dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            # Fallback for all-day events or different formats
            start_str = start
            end_str = end

        formatted_events.append({
            "summary": event.get('summary', 'No Title'),
            "start": start_str,
            "end": end_str,
            "attendees": [employee_email], # Simplification for now
        })

    return formatted_events
