import unittest
from unittest.mock import MagicMock, patch
import sys
from unittest.mock import MagicMock

# Mock langchain dependencies if not installed
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from pydantic import BaseModel, Field
except ImportError:
    mock_langchain = MagicMock()
    sys.modules["langchain_openai"] = mock_langchain
    sys.modules["langchain_core"] = mock_langchain
    sys.modules["langchain_core.prompts"] = mock_langchain
    sys.modules["pydantic"] = mock_langchain
    from unittest.mock import MagicMock as Mock
    ChatOpenAI = Mock
    ChatPromptTemplate = Mock
    BaseModel = Mock
    Field = Mock

from app.services.langchain_workflow.ai_client import LangChainAIClient

class TestLangChainAIClient(unittest.TestCase):
    def setUp(self):
        with patch("app.services.langchain_workflow.ai_client.ChatOpenAI"):
            self.ai_client = LangChainAIClient(model="test-model")

    @patch("app.services.langchain_workflow.ai_client.ChatPromptTemplate")
    def test_extract_leave_request_success(self, mock_prompt):
        # Mock structured LLM output
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "leave_type": "vacation",
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "department": "engineering"
        }
        
        self.ai_client.structured_llm.invoke = MagicMock(return_value=mock_result)

        result = self.ai_client.extract_leave_request("Subject", "Body")

        self.assertEqual(result, {
            "leave_type": "vacation",
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "department": "engineering"
        })
        self.ai_client.structured_llm.invoke.assert_called_once()

if __name__ == "__main__":
    unittest.main()
