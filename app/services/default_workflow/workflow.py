from datetime import date
from typing import Any, Dict, Optional
import os

from app.db import SessionLocal
from app.models.leave_request import LeaveRequest, LeaveStatus
from app.services.email_service import email_service


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _resolve_manager_email(department: Optional[str]) -> str:
    """
    Map department -> manager email, with env overrides.
    """
    dept_key = (department or "general").strip().lower()

    default_manager = os.getenv("DEFAULT_MANAGER_EMAIL", "manager@test.com")

    department_managers = {
        "engineering": os.getenv("ENG_MANAGER_EMAIL", "eng_manager@test.com"),
        "sales": os.getenv("SALES_MANAGER_EMAIL", "sales_manager@test.com"),
        "hr": os.getenv("HR_MANAGER_EMAIL", "hr_manager@test.com"),
        "finance": os.getenv("FIN_MANAGER_EMAIL", "finance_manager@test.com"),
        "general": default_manager,
    }

    return department_managers.get(dept_key, default_manager)


def process_leave_request(
    parsed: Dict[str, Any],
    *,
    employee_email: str,
    raw_subject: str,
    raw_body: str,
    conversation_id: Optional[str],
    mailhog_id: Optional[str],
) -> None:
    """
    Simple workflow:
    - If key fields are missing, send clarification mail to employee.
    - Else, create a leave request record and ask manager to approve/decline.
    """
    session = SessionLocal()
    try:
        leave_type = parsed.get("leave_type")
        start_date_str = parsed.get("start_date")
        end_date_str = parsed.get("end_date")
        department = parsed.get("department")

        start_date = _parse_date(start_date_str)
        end_date = _parse_date(end_date_str)

        # Logic: need clarification if key field is missing from AI extraction
        if not leave_type:
            email_service.send_clarification_email(employee_email)
            return
        
        if not start_date_str or not start_date:
            email_service.send_date_clarification_email(employee_email)
            return

        manager_email = _resolve_manager_email(department)

        # Create leave request record.
        lr = LeaveRequest(
            employee_email=employee_email,
            department=department,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date or start_date,
            status=LeaveStatus.PENDING,
            manager_email=manager_email,
            conversation_id=conversation_id,
            raw_subject=raw_subject,
            raw_body=raw_body,
            mailhog_id=mailhog_id,
        )
        session.add(lr)
        session.commit()
        session.refresh(lr)

        # Notify manager with approval links instead of directly confirming to employee.
        email_service.send_manager_approval_email(lr)
    finally:
        session.close()

