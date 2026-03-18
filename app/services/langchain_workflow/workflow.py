"""
Langchain agent workflow entry point.

Instead of a rigid extraction + template pipeline, this hands the entire
email to the agent which can call tools, ask for clarification, or answer
questions — and returns a plain-text reply to send back to the employee.
"""
from __future__ import annotations

from typing import Optional

from app.services.langchain_workflow.ai_client import langchain_ai_client
from app.services.email_service import email_service


def handle_email(
    *,
    employee_email: str,
    email_subject: str,
    email_body: str,
    history: list[str],
    mailhog_id: Optional[str] = None,
) -> None:
    """
    Pass the employee's email through the LangChain agent and send its
    response back as an email reply.
    """
    reply = langchain_ai_client.run_agent(
        employee_email=employee_email,
        email_subject=email_subject,
        email_body=email_body,
        history=history,
    )

    email_service.send_reply(employee_email, reply)
    print(f"[langchain_workflow] Agent reply sent to {employee_email}: {reply[:120]}...")
