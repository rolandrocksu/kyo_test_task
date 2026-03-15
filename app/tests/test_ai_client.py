import json
import unittest
from unittest.mock import MagicMock, patch
from app.services.ai_client import AIClient

class TestAIClient(unittest.TestCase):
    def setUp(self):
        with patch("app.services.ai_client.OpenAI"):
            self.ai_client = AIClient(model="test-model")

    def test_extract_leave_request_success(self):
        # Mock responses API response
        mock_response = MagicMock()
        mock_response.output_text = '{"leave_type": "vacation", "start_date": "2024-01-01", "end_date": "2024-01-02", "department": "engineering"}'
        self.ai_client.client.responses.create.return_value = mock_response

        result = self.ai_client.extract_leave_request("Subject", "Body")

        self.assertEqual(result, {
            "leave_type": "vacation",
            "start_date": "2024-01-01",
            "end_date": "2024-01-02",
            "department": "engineering"
        })
        self.ai_client.client.responses.create.assert_called_once()

    def test_extract_leave_request_json_error(self):
        # Mock responses API with invalid JSON
        mock_response = MagicMock()
        mock_response.output_text = 'Invalid JSON'
        self.ai_client.client.responses.create.return_value = mock_response

        with self.assertRaises(ValueError):
            self.ai_client.extract_leave_request("Subject", "Body")

if __name__ == "__main__":
    unittest.main()
