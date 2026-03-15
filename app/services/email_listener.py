import time
from typing import Set

import os
from app.services.email_service import email_service

WORKFLOW_TYPE = os.getenv("WORKFLOW_TYPE", "default").lower()

if WORKFLOW_TYPE == "langchain":
    from app.services.langchain_workflow.ai_client import langchain_ai_client as ai_client
    from app.services.langchain_workflow.workflow import process_leave_request
else:
    from app.services.default_workflow.ai_client import ai_client
    from app.services.default_workflow.workflow import process_leave_request


from app.db import SessionLocal, init_db
from app.models.leave_request import LeaveRequest


def _load_processed_ids() -> Set[str]:
    session = SessionLocal()
    try:
        rows = session.query(LeaveRequest.mailhog_id).filter(
            LeaveRequest.mailhog_id.isnot(None)
        )
        return {r[0] for r in rows}
    finally:
        session.close()


def poll_loop() -> None:
    """
    Simple polling loop that:
    - Reads messages from MailHog
    - Skips ones we've already processed
    - Sends each new email through AI + workflow
    """
    init_db()
    processed_ids = _load_processed_ids()

    print("Email listener started. Polling MailHog every", POLL_INTERVAL_SECONDS, "s")

    while True:
        try:
            payload = email_service.fetch_mailhog_messages()
            items = payload.get("items", [])
            for msg in items:
                msg_id = msg.get("ID")
                if not msg_id or msg_id in processed_ids:
                    continue

                basic = email_service.extract_email_payload(msg)

                # Avoid feedback loops: ignore our own outbound notifications.
                from_addr = (basic.get("from") or "").lower()
                subject = (basic.get("subject") or "").lower()
                if from_addr == "hr@test.com" or subject.startswith("leave request update"):
                    processed_ids.add(msg_id)
                    continue

                print(f"New email from {basic['from']} with subject: {basic['subject']}")

                # Fetch history for context
                history = email_service.get_email_history(basic["from"])

                parsed = ai_client.extract_leave_request(
                    email_subject=basic["subject"],
                    email_body=basic["body"],
                    history=history,
                )
                print("Intent detected: leave_request")
                print("Parsed payload:", parsed)

                process_leave_request(
                    parsed,
                    employee_email=basic["from"],
                    raw_subject=basic["subject"],
                    raw_body=basic["body"],
                    conversation_id=None,
                    mailhog_id=msg_id,
                )

                processed_ids.add(msg_id)

        except Exception as exc:  # pragma: no cover - simple demo logging
            print("Error in poll loop:", exc)

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    poll_loop()

