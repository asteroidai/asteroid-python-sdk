import unittest
from unittest.mock import MagicMock
from asteroid_sdk.wrappers.openai import ChatCompletionWrapper, AsteroidChatSupervisionManager

class TestChatCompletionWrapper(unittest.TestCase):
    def setUp(self):
        # Mock the APIClient
        self.mock_client = MagicMock()
        self.logger = AsteroidChatSupervisionManager(api_key="dummy_key")
        self.logger.client = self.mock_client

        # Mock the create function
        self.mock_create_fn = MagicMock(return_value={"response": "test response"})

        # Initialize the wrapper
        self.wrapper = ChatCompletionWrapper(self.mock_create_fn, self.logger)

    def test_create_logs_request_and_response(self):
        # Define test data
        messages = [{"role": "user", "content": "Hello"}]
        model = "test-model"

        # Call the create method
        response = self.wrapper.create(messages=messages, model=model)

        # Check if the request was logged
        self.mock_client.post.assert_any_call("/requests", json={
            "messages": messages,
            "model": model,
            "parameters": {}
        })

        # Check if the response was logged
        self.mock_client.post.assert_any_call("/responses", json={"response": "test response"})

        # Check if the response is returned correctly
        self.assertEqual(response, {"response": "test response"})

if __name__ == '__main__':
    unittest.main()
