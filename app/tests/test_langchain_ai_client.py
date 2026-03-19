"""
Unit tests for LangChainAIClient.run_agent

The module-level singleton `langchain_ai_client = LangChainAIClient()` at the
bottom of ai_client.py instantiates ChatOpenAI at import time.  We must
pre-stub the relevant modules in sys.modules *before* the first import so that
no real OpenAI client is ever constructed.
"""
import sys
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Pre-stub heavy dependencies before any app module is imported
# ---------------------------------------------------------------------------
_mock_chat_openai = MagicMock()

for _mod, _mock in [
    ("langchain_openai", MagicMock(ChatOpenAI=_mock_chat_openai)),
    ("langchain.agents", MagicMock(
        AgentExecutor=MagicMock(),
        create_openai_tools_agent=MagicMock(),
    )),
    ("google", MagicMock()),
    ("google.oauth2", MagicMock()),
    ("google.oauth2.credentials", MagicMock()),
    ("google.auth", MagicMock()),
    ("google.auth.transport", MagicMock()),
    ("google.auth.transport.requests", MagicMock()),
    ("googleapiclient", MagicMock()),
    ("googleapiclient.discovery", MagicMock()),
]:
    sys.modules.setdefault(_mod, _mock)

# Now it's safe to import — ChatOpenAI() will hit our MagicMock
from app.services.langchain_workflow.ai_client import LangChainAIClient  # noqa: E402


class TestLangChainAIClient(unittest.TestCase):

    def setUp(self):
        self.client = LangChainAIClient(model="test-model")

    # ------------------------------------------------------------------
    # run_agent — happy path
    # ------------------------------------------------------------------

    @patch("app.services.langchain_workflow.ai_client.AgentExecutor")
    @patch("app.services.langchain_workflow.ai_client.create_openai_tools_agent")
    @patch("app.services.langchain_workflow.ai_client.build_tools")
    def test_run_agent_returns_agent_output(
        self, mock_build_tools, mock_create_agent, mock_executor_cls
    ):
        """Executor returning {"output": "reply"} → that string is returned."""
        mock_build_tools.return_value = []
        mock_create_agent.return_value = MagicMock()

        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {"output": "I have submitted your leave request."}
        mock_executor_cls.return_value = mock_executor

        result = self.client.run_agent(
            employee_email="alice@example.com",
            email_subject="PTO request",
            email_body="I need Monday off.",
        )

        self.assertEqual(result, "I have submitted your leave request.")
        mock_executor.invoke.assert_called_once()

    # ------------------------------------------------------------------
    # run_agent — missing output key
    # ------------------------------------------------------------------

    @patch("app.services.langchain_workflow.ai_client.AgentExecutor")
    @patch("app.services.langchain_workflow.ai_client.create_openai_tools_agent")
    @patch("app.services.langchain_workflow.ai_client.build_tools")
    def test_run_agent_missing_output_key_returns_fallback(
        self, mock_build_tools, mock_create_agent, mock_executor_cls
    ):
        """If executor returns dict without 'output', fallback message is returned."""
        mock_build_tools.return_value = []
        mock_create_agent.return_value = MagicMock()

        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {}  # no "output" key
        mock_executor_cls.return_value = mock_executor

        result = self.client.run_agent(
            employee_email="alice@example.com",
            email_subject="PTO request",
            email_body="I need Monday off.",
        )

        self.assertIn("unable to process", result.lower())

    # ------------------------------------------------------------------
    # run_agent — history formatting
    # ------------------------------------------------------------------

    @patch("app.services.langchain_workflow.ai_client.AgentExecutor")
    @patch("app.services.langchain_workflow.ai_client.create_openai_tools_agent")
    @patch("app.services.langchain_workflow.ai_client.build_tools")
    def test_run_agent_history_included_in_invoke(
        self, mock_build_tools, mock_create_agent, mock_executor_cls
    ):
        """History list should be formatted and passed to executor.invoke."""
        mock_build_tools.return_value = []
        mock_create_agent.return_value = MagicMock()

        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {"output": "ok"}
        mock_executor_cls.return_value = mock_executor

        history = ["First email body", "Second email body"]
        self.client.run_agent(
            employee_email="alice@example.com",
            email_subject="Follow-up",
            email_body="Any update?",
            history=history,
        )

        call_payload = mock_executor.invoke.call_args[0][0]
        self.assertIn("First email body", call_payload["history"])
        self.assertIn("Second email body", call_payload["history"])

    # ------------------------------------------------------------------
    # run_agent — no history
    # ------------------------------------------------------------------

    @patch("app.services.langchain_workflow.ai_client.AgentExecutor")
    @patch("app.services.langchain_workflow.ai_client.create_openai_tools_agent")
    @patch("app.services.langchain_workflow.ai_client.build_tools")
    def test_run_agent_no_history_passes_empty_string(
        self, mock_build_tools, mock_create_agent, mock_executor_cls
    ):
        """With no history, the history key in the invoke payload is ''."""
        mock_build_tools.return_value = []
        mock_create_agent.return_value = MagicMock()

        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {"output": "ok"}
        mock_executor_cls.return_value = mock_executor

        self.client.run_agent(
            employee_email="alice@example.com",
            email_subject="New request",
            email_body="I need a day off.",
        )

        call_payload = mock_executor.invoke.call_args[0][0]
        self.assertEqual(call_payload["history"], "")

    @patch("app.services.langchain_workflow.ai_client.AgentExecutor")
    @patch("app.services.langchain_workflow.ai_client.create_openai_tools_agent")
    @patch("app.services.langchain_workflow.ai_client.build_tools")
    def test_run_agent_passes_verbose_today_format(
        self, mock_build_tools, mock_create_agent, mock_executor_cls
    ):
        """The 'today' value passed to executor.invoke should include the day of the week."""
        mock_build_tools.return_value = []
        mock_create_agent.return_value = MagicMock()

        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {"output": "ok"}
        mock_executor_cls.return_value = mock_executor

        self.client.run_agent(
            employee_email="alice@example.com",
            email_subject="New request",
            email_body="I need a day off.",
        )

        call_payload = mock_executor.invoke.call_args[0][0]
        today_val = call_payload["today"]
        # Expected format: "Thursday, 2026-03-19"
        self.assertRegex(today_val, r"\w+, \d{4}-\d{2}-\d{2}")

    # ------------------------------------------------------------------
    # extract_leave_request — deprecated guard
    # ------------------------------------------------------------------

    def test_extract_leave_request_raises_not_implemented(self):
        """The deprecated method must raise NotImplementedError."""
        with self.assertRaises(NotImplementedError):
            self.client.extract_leave_request("Subject", "Body")


if __name__ == "__main__":
    unittest.main()
