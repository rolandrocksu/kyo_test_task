from typing import Any, Dict, List, Optional
from datetime import date
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import os

class LeaveRequestSchema(BaseModel):
    leave_type: Optional[str] = Field(
        None, 
        description="Type of leave (pto, vacation, sick, unpaid, other)",
        enum=["pto", "vacation", "sick", "unpaid", "other", None]
    )
    start_date: Optional[str] = Field(None, description="Start date in ISO 8601 format (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date in ISO 8601 format (YYYY-MM-DD)")
    department: Optional[str] = Field(None, description="Employee department")

class LangChainAIClient:
    def __init__(self, model: str = None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.llm = ChatOpenAI(model=self.model, temperature=0)
        self.structured_llm = self.llm.with_structured_output(LeaveRequestSchema)

    def extract_leave_request(self, email_subject: str, email_body: str, history: List[str] = None) -> Dict[str, Any]:
        system_prompt = """
You are an assistant that extracts structured leave requests from employee messages.

Rules:
- Extract leave_type, start_date, end_date, and department.
- Convert relative dates like "next Monday" or "tomorrow" to ISO 8601 (YYYY-MM-DD).
- Only extract information present in the message. If missing or ambiguous, return null.
- Do not invent leave_type; if not mentioned, return null.
- Use previous conversation context if provided to fill in missing details.
""".strip()

        history_context = ""
        if history:
            history_context = "\nPrevious email history (oldest first):\n" + "\n---\n".join(history) + "\n---\n"

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "Today is {today}.\n{history}\nCurrent Email subject:\n{subject}\n\nCurrent Email body:\n{body}")
        ])

        chain = prompt | self.structured_llm
        
        result = chain.invoke({
            "today": date.today().isoformat(),
            "history": history_context,
            "subject": email_subject,
            "body": email_body
        })
        
        return result.model_dump()

langchain_ai_client = LangChainAIClient()
