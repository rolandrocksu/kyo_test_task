"""
Langchain-based AI client that runs a tool-calling agent.

The agent receives the employee's email in its system context so it can
use the bound tools (calendar checks, leave submission, recommendations)
without needing to know how to call the underlying APIs directly.
"""
from __future__ import annotations

import os
from datetime import date
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_openai_tools_agent

from app.services.langchain_workflow.agent_tools import build_tools


SYSTEM_PROMPT = """\
You are Kyo, an AI HR assistant that helps employees manage their leave requests.

Today is {today}. You are helping: {employee_email}.

You have access to tools that let you:
- Check the employee's calendar for upcoming meetings.
- List all their current leave requests.
- Submit a new leave request on their behalf.
- Recommend the best days off based on their schedule.

Guidelines:
- Always be friendly, concise, and professional.
- Before submitting a leave request, confirm you have the leave type, start and end dates.
  If any are missing or unclear, ask for clarification in your reply — do NOT call submit_leave_request.
- When asked about the best time to take a day off, use recommend_best_days_off.
- When you submit a request, confirm back with the details (type, dates, and that it's pending manager approval).
- For anything unrelated to leave management, politely state that you can only help with leave requests.
- Respond in a clear, plain-text format suitable for an email reply. Do NOT use markdown.
""".strip()


class LangChainAIClient:
    def __init__(self, model: str = None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.llm = ChatOpenAI(model=self.model, temperature=0)

    def run_agent(
        self,
        employee_email: str,
        email_subject: str,
        email_body: str,
        history: List[str] = None,
    ) -> str:
        """
        Run the agent for a given employee email interaction.
        Returns the agent's final text response to send back to the employee.
        """
        tools = build_tools(employee_email)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "{history}Current email subject: {subject}\n\nEmail body:\n{body}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(self.llm, tools, prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=8)

        history_text = ""
        if history:
            history_text = (
                "Previous email conversation (oldest first):\n"
                + "\n---\n".join(history)
                + "\n---\n\n"
            )

        result = executor.invoke({
            "today": date.today().isoformat(),
            "employee_email": employee_email,
            "history": history_text,
            "subject": email_subject,
            "body": email_body,
        })

        return result.get("output", "Sorry, I was unable to process your request.")

    # ------------------------------------------------------------------
    # Kept for backward-compatibility with tests / default_workflow references
    # ------------------------------------------------------------------
    def extract_leave_request(self, email_subject: str, email_body: str, history: List[str] = None):
        """Deprecated: use run_agent instead."""
        raise NotImplementedError(
            "extract_leave_request is not used in the agent workflow. Use run_agent()."
        )


langchain_ai_client = LangChainAIClient()
