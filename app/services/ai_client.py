import json
import os
from datetime import date
from typing import Any, Dict

from openai import OpenAI


class AIClient:
    def __init__(self, model: str = None):
        # OPENAI_API_KEY is read from the environment by the SDK.
        self.client = OpenAI()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5")

    def extract_leave_request(self, email_subject: str, email_body: str) -> Dict[str, Any]:
        """
        Call OpenAI to extract structured leave-request data.

        Uses the Responses/Chat API with JSON mode so we always get a JSON object back.
        """
        system_prompt = """
You are an assistant that extracts structured leave requests from employee messages.

Rules:
- Extract leave_type, start_date, end_date, and department.
- Convert relative dates like "next Monday" or "tomorrow" to ISO 8601 (YYYY-MM-DD).
- Only extract information present in the message. If missing or ambiguous, return null.
- Do not invent leave_type; if not mentioned, return null.
- Always follow the JSON schema strictly.
""".strip()

        user_prompt = f"""
Today is {date.today().isoformat()}.
Email subject:
{email_subject}

Email body:
{email_body}
""".strip()

        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "leave_request",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "leave_type": {
                                "type": ["string", "null"],
                                "enum": ["pto", "vacation", "sick", "unpaid", "other", None]
                            },
                            "start_date": {
                                "type": ["string", "null"]
                            },
                            "end_date": {
                                "type": ["string", "null"]
                            },
                            "department": {
                                "type": ["string", "null"]
                            }
                        },
                        "required": [
                            "leave_type",
                            "start_date",
                            "end_date",
                            "department",
                        ],
                        "additionalProperties": False
                    }
                }
            },
        )

        content = response.output_text

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON returned by model: {content}") from e


ai_client = AIClient()

