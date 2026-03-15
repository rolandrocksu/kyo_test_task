import os
import smtplib
from email.message import EmailMessage
from typing import List, Dict, Any, Optional

import requests
from jinja2 import Environment, FileSystemLoader

from app.services.meetings_service import get_meetings_for_employee

# Template configuration
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "email")


class EmailService:
    def __init__(self):
        # When running under Docker Compose, the MailHog host is "mailhog".
        # When running everything locally without Docker, it's "localhost".
        self.smtp_host = os.getenv("SMTP_HOST", "mailhog")
        self.smtp_port = int(os.getenv("SMTP_PORT", "1025"))

        self.mailhog_host = os.getenv("MAILHOG_HOST", "mailhog")
        self.mailhog_port = int(os.getenv("MAILHOG_PORT", "8025"))
        self.mailhog_api_base = f"http://{self.mailhog_host}:{self.mailhog_port}/api/v2"

        self.manager_email = os.getenv("MANAGER_EMAIL", "manager@test.com")
        self.approval_base_url = os.getenv("APPROVAL_BASE_URL", "http://localhost:3000")

        self.jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

    def _send_email(self, to: str, subject: str, text: str, html: Optional[str] = None) -> None:
        """Internal helper to send an email via SMTP."""
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = "hr@test.com"
        msg["To"] = to
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            smtp.send_message(msg)

    def _render_and_send(
        self, to: str, template_folder: str, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Internal helper to render templates and send email."""
        ctx = context or {}
        subject_tpl = self.jinja_env.get_template(f"{template_folder}/subject.txt")
        plain_tpl = self.jinja_env.get_template(f"{template_folder}/body.txt")
        html_tpl = self.jinja_env.get_template(f"{template_folder}/body.html")

        subject = subject_tpl.render(ctx).strip()
        plain = plain_tpl.render(ctx)
        html = html_tpl.render(ctx)

        self._send_email(to, subject, plain, html)

    def send_reply(self, to: str, text: str) -> None:
        self._send_email(to, "Leave Request Update", text)

    def send_manager_approval_email(self, leave_request: Any) -> None:
        """
        Send an HTML email to the manager with Approve/Decline buttons.
        """
        approve_link = f"{self.approval_base_url}/requests/{leave_request.id}/approve"
        reject_link = f"{self.approval_base_url}/requests/{leave_request.id}/reject"

        meetings = get_meetings_for_employee(
            employee_email=leave_request.employee_email,
            start_date=leave_request.start_date,
            end_date=leave_request.end_date,
        )

        context = {
            "leave_request": leave_request,
            "employee_email": leave_request.employee_email,
            "leave_type": leave_request.leave_type,
            "start_date": leave_request.start_date,
            "end_date": leave_request.end_date,
            "meetings": meetings,
            "approve_link": approve_link,
            "reject_link": reject_link,
        }

        to_addr = getattr(leave_request, "manager_email", None) or self.manager_email
        self._render_and_send(to_addr, "leave_request_approval", context)

    def send_clarification_email(self, employee_email: str) -> None:
        """
        Send an email to the employee asking for clarification on their leave request.
        """
        self._render_and_send(employee_email, "leave_request_clarification")

    def send_date_clarification_email(self, employee_email: str) -> None:
        """
        Send an email specifically asking for dates if other info is known.
        """
        self._render_and_send(employee_email, "leave_request_date_clarification")

    def send_approved_email(self, leave_request: Any) -> None:
        """
        Send an email to the employee notifying them their request was approved.
        """
        context = {
            "leave_type": leave_request.leave_type,
            "start_date": leave_request.start_date,
            "end_date": leave_request.end_date,
        }
        self._render_and_send(
            leave_request.employee_email, "leave_request_approved", context
        )

    def send_rejected_email(self, leave_request: Any) -> None:
        """
        Send an email to the employee notifying them their request was rejected.
        """
        context = {
            "leave_type": leave_request.leave_type,
            "start_date": leave_request.start_date,
            "end_date": leave_request.end_date,
        }
        self._render_and_send(
            leave_request.employee_email, "leave_request_rejected", context
        )

    def fetch_mailhog_messages(self) -> Dict[str, Any]:
        """Fetch all messages from MailHog."""
        resp = requests.get(f"{self.mailhog_api_base}/messages", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_email_history(self, employee_email: str, limit: int = 5) -> List[str]:
        """
        Fetch the last few emails from/to this employee to provide context.
        Returns a list of email bodies.
        """
        try:
            payload = self.fetch_mailhog_messages()
            items = payload.get("items", [])
            history = []
            employee_email_lower = employee_email.lower()
            
            for msg in items:
                basic = self.extract_email_payload(msg)
                # Check if email is from or to the employee
                # (to_addr is not easily available in basic extract but we can check headers)
                headers = msg.get("Content", {}).get("Headers", {})
                to_headers = headers.get("To") or []
                is_to_employee = any(employee_email_lower in t.lower() for t in to_headers)
                
                if basic["from"].lower() == employee_email_lower or is_to_employee:
                    history.append(f"From: {basic['from']}\nSubject: {basic['subject']}\n\n{basic['body']}")
                
                if len(history) >= limit:
                    break
            
            # Return reversed so it's oldest first for the LLM prompt
            return list(reversed(history))
        except Exception:
            return []

    def extract_email_payload(self, message: Dict[str, Any]) -> Dict[str, str]:
        """
        Normalize a MailHog message into from/subject/body.
        """
        from_addr = message.get("From", {}).get("Mailbox", "") + "@" + message.get(
            "From", {}
        ).get("Domain", "")
        subject = ""
        body = ""

        headers: List[Dict[str, Any]] = message.get("Content", {}).get("Headers", {})
        if isinstance(headers, dict):
            subject_list = headers.get("Subject") or []
            if subject_list:
                subject = subject_list[0]

        mime_body = message.get("Content", {}).get("Body", "")
        if isinstance(mime_body, str):
            body = mime_body

        return {
            "from": from_addr or "unknown@test.com",
            "subject": subject,
            "body": body,
        }


# Singleton instance for module-level usage
email_service = EmailService()

