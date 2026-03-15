import json
import unittest
from unittest.mock import MagicMock, patch
from app.services.ai_client import AIClient

class TestAIClient(unittest.TestCase):
    def setUp(self):
        with patch("app.services.ai_client.OpenAI"):
            self.ai_client = AIClient(model="test-model")

    def test_extract_leave_request_success(self):
        # Mock beta.chat.completions.parse response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"leave_type": "vacation", "start_date": "2024-01-01", "end_date": "2024-01-02", "department": "engineering"}'
        mock_response.choices = [mock_choice]
        self.ai_client.client.beta.chat.completions.parse.return_value = mock_response

        result = self.ai_client.extract_leave_request("Subject", "Body")

        self.assertEqual(result, {
            "leave_type": "vacation",
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "department": "engineering"
        })
        self.ai_client.client.beta.chat.completions.parse.assert_called_once()

    def test_extract_leave_request_with_history(self):
        # Mock beta.chat.completions.parse response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"leave_type": "pto", "start_date": "2024-03-20", "end_date": "2024-03-22", "department": "sales"}'
        mock_response.choices = [mock_choice]
        self.ai_client.client.beta.chat.completions.parse.return_value = mock_response

        history = ["From: user@test.com\nSubject: pto\n\nI want to take PTO"]
        result = self.ai_client.extract_leave_request("dates", "from next Wednesday to Friday", history=history)

        self.assertEqual(result["leave_type"], "pto")
        self.assertEqual(result["start_date"], "2024-03-20")
        
        # Verify history was in the prompt
        args, kwargs = self.ai_client.client.beta.chat.completions.parse.call_args
        user_msg = kwargs['messages'][1]['content']
        self.assertIn("Previous email history", user_msg)
        self.assertIn("I want to take PTO", user_msg)

    def test_extract_leave_request_json_error(self):
        # Mock beta.chat.completions.parse with invalid JSON
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = 'Invalid JSON'
        mock_response.choices = [mock_choice]
        self.ai_client.client.beta.chat.completions.parse.return_value = mock_response

        with self.assertRaises(ValueError):
            self.ai_client.extract_leave_request("Subject", "Body")

if __name__ == "__main__":
    unittest.main()
