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

    def extract_leave_request(self, email_subject: str, email_body: str, history: list[str] = None) -> Dict[str, Any]:
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
- Use previous conversation context if provided to fill in missing details.
- Always follow the JSON schema strictly.
""".strip()

        history_context = ""
        if history:
            history_context = "\nPrevious email history (oldest first):\n" + "\n---\n".join(history) + "\n---\n"

        user_prompt = f"""
Today is {date.today().isoformat()}.
{history_context}
Current Email subject:
{email_subject}

Current Email body:
{email_body}
""".strip()

        response = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
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

        content = response.choices[0].message.content

        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Invalid JSON returned by model: {content}") from e


ai_client = AIClient()

