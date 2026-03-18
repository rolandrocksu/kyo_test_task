import os
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from app.db import SessionLocal
from app.models.google_token import GoogleToken

router = APIRouter(prefix="/google", tags=["google"])

# This should match your GOOGLE_REDIRECT_URI in .env
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/google/callback")
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/authorize")
def authorize(email: str):
    """
    Initial step: Redirect user to Google for authorization.
    Email is passed as a query param for tracking.
    """
    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    # Use state to pass the email through the OAuth flow
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=email
    )
    
    return RedirectResponse(authorization_url)

@router.get("/callback")
def callback(request: Request, db: Session = Depends(get_db)):
    """
    Second step: Google redirects here with an auth code.
    We exchange it for tokens and store them.
    """
    code = request.query_params.get("code")
    email = request.query_params.get("state") # We passed email as 'state'
    
    if not code or not email:
        raise HTTPException(status_code=400, detail="Authorization failed: missing code or state.")

    client_config = {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Save or update tokens in DB
    token_record = db.query(GoogleToken).filter(GoogleToken.employee_email == email).first()
    if not token_record:
        token_record = GoogleToken(employee_email=email)
        
    token_record.access_token = creds.token
    token_record.refresh_token = creds.refresh_token
    token_record.token_uri = creds.token_uri
    token_record.client_id = creds.client_id
    token_record.client_secret = creds.client_secret
    token_record.scopes = ",".join(creds.scopes)
    
    db.add(token_record)
    db.commit()

    return {"message": f"Successfully linked Google Calendar for {email}!"}
