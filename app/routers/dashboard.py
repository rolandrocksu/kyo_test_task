from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.leave_request import LeaveRequest, LeaveStatus
from app.services.email_service import email_service
from app.services.meetings_service import get_meetings_for_employee


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_class=HTMLResponse)
def read_root(request: Request) -> HTMLResponse:
    db = SessionLocal()
    try:
        rows = db.query(LeaveRequest).order_by(LeaveRequest.id.desc()).all()
    finally:
        db.close()

    rows_data = []
    for r in rows:
        # Status badge
        status_color = {
            "PENDING": "#facc15",
            "APPROVED": "#16a34a",
            "REJECTED": "#dc2626"
        }.get(r.status.value.upper(), "#9ca3af")

        # Meetings
        meetings = []
        if r.employee_email and r.start_date and r.end_date:
            meetings = get_meetings_for_employee(
                employee_email=r.employee_email,
                start_date=r.start_date,
                end_date=r.end_date,
            )
        
        rows_data.append({
            "id": r.id,
            "employee_email": r.employee_email,
            "department": r.department,
            "leave_type": r.leave_type,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "status": r.status.value,
            "status_color": status_color,
            "manager_email": r.manager_email,
            "approved_by": r.approved_by,
            "meetings": meetings,
            "meetings_summary": f"{len(meetings)} meeting(s)" if meetings else "",
            "show_actions": r.status == LeaveStatus.PENDING
        })

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "rows": rows_data}
    )


@router.get("/requests/{request_id}/approve")
def approve_request(request: Request, request_id: int):
    db = SessionLocal()
    try:
        lr = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
        if not lr:
            return templates.TemplateResponse(
                "status_message.html",
                {"request": request, "message": "Request not found", "auto_close": True}
            )

        if lr.status != LeaveStatus.PENDING:
            return templates.TemplateResponse(
                "status_message.html",
                {
                    "request": request,
                    "message": "This leave request has already been approved or rejected.",
                    "auto_close": True
                }
            )

        lr.status = LeaveStatus.APPROVED
        lr.approved_by = lr.manager_email or "manager@test.com"
        db.add(lr)
        db.commit()

        email_service.send_approved_email(lr)
    finally:
        db.close()

    return templates.TemplateResponse(
        "status_message.html",
        {
            "request": request,
            "message": "If the tab does not close automatically, you can close it manually.",
            "auto_close": False
        }
    )


@router.get("/requests/{request_id}/reject")
def reject_request(request: Request, request_id: int):
    db = SessionLocal()
    try:
        lr = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
        if not lr:
            return templates.TemplateResponse(
                "status_message.html",
                {"request": request, "message": "Request not found", "auto_close": True}
            )

        if lr.status != LeaveStatus.PENDING:
            return templates.TemplateResponse(
                "status_message.html",
                {
                    "request": request,
                    "message": "This leave request has already been approved or rejected.",
                    "auto_close": True
                }
            )

        lr.status = LeaveStatus.REJECTED
        lr.approved_by = lr.manager_email or "manager@test.com"
        db.add(lr)
        db.commit()

        email_service.send_rejected_email(lr)
    finally:
        db.close()

    return templates.TemplateResponse(
        "status_message.html",
        {
            "request": request,
            "message": "If the tab does not close automatically, you can close it manually.",
            "auto_close": False
        }
    )

