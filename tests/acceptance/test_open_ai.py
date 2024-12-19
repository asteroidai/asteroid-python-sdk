import unittest
from typing import List
from unittest.mock import MagicMock, patch

import openai.resources.chat
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_tool_call import Function

from asteroid_sdk.supervision.config import ExecutionMode
from asteroid_sdk.supervision.helpers.openai_helper import OpenAiSupervisionHelper
from asteroid_sdk.wrappers.openai import CompletionsWrapper
from tests.acceptance.abstract_acceptance_test import AbstractAcceptanceTest


class TestOpenAi(AbstractAcceptanceTest):
    def setUp(self):
        self.setUpGlobal(OpenAiSupervisionHelper())
        self.mock_completions = MagicMock(openai.resources.chat.Completions)
        self.openai_wrapper = CompletionsWrapper(
            self.mock_completions,
            self.chat_supervision_manager,
            self.run_id,
            ExecutionMode.SUPERVISION
        )

    @patch('asteroid_sdk.registration.helper.APIClientFactory.get_client')
    def test_original_response_is_returned_with_supervision_is_successful(self, mock_get_client):
        self.original_response_when_supervision_successful(mock_get_client)
        # THIS IS KEY- maybe we should instantiate the wrapper after we've run the init?
        self.openai_wrapper.run_id = self.run_id

        messages = [{"role": "user", "content": "Get me the weather in London"}]
        model = "test-model"

        # Mock call to LM
        desired_completion_message = self.create_chat_completion_with_tool_calls(
            [
                ChatCompletionMessageToolCall(
                    id="random_id",
                    type="function",
                    function=Function(
                        name="get_weather",
                        arguments='{"location": "London", "unit": "C"}'
                    )
                )
            ]
        )
        self.mock_completions.create.return_value = desired_completion_message

        response = self.openai_wrapper.create(messages=messages, model=model, parallel_tool_calls=False)

        # Then
        self.assertEqual(response, desired_completion_message,
                         "The response should be the same as the one returned by the API")

    @patch('asteroid_sdk.registration.helper.APIClientFactory.get_client')
    def test_resamples_and_then_works(self, mock_get_client):
        self.resamples_then_works_globals(mock_get_client)
        # Mock call to LM
        # Note- the allow: true param is what the supervisor is after to approve
        desired_completion_message = self.create_chat_completion_with_tool_calls(
            [
                ChatCompletionMessageToolCall(
                    id="random_id",
                    type="function",
                    function=Function(
                        name="google_search",
                        arguments='{"query_string": "is BTC going to the moon", "allow": false}'
                    )
                )
            ]
        )
        resampled_completion_message = self.create_chat_completion_with_tool_calls(
            [
                ChatCompletionMessageToolCall(
                    id="random_id",
                    type="function",
                    function=Function(
                        name="google_search",
                        arguments='{"query_string": "is BTC going to the moon", "allow": true}'
                    )
                )
            ]
        )
        self.mock_completions.create.side_effect = [
            desired_completion_message,
            resampled_completion_message
        ]
        # THIS IS KEY- maybe we should instantiate the wrapper after we've run the init?
        self.openai_wrapper.run_id = self.run_id

        messages = [{"role": "user", "content": "Search the internet for 'is BTC going to the moon'"}]
        model = "test-model"
        response = self.openai_wrapper.create(messages=messages, model=model, parallel_tool_calls=False)

        # Then
        self.assertEqual(response, resampled_completion_message,
                         "The response should be the same as the one returned by the API")

    def create_chat_completion_with_message(self, content: str) -> ChatCompletion:
        choice = Choice(
            message=ChatCompletionMessage(
                content=content,
                role="assistant"
            ),
            finish_reason="stop",
            index=0,
        )
        return ChatCompletion(
            id="test_id",
            created=0,
            model="test-model",
            object="chat.completion",
            choices=[choice]  # Ensure the choice is passed as a dictionary
        )

    def create_chat_completion_with_tool_calls(self, tool_calls: List[ChatCompletionMessageToolCall]) -> ChatCompletion:
        choice = Choice(
            message=ChatCompletionMessage(
                content="test response",
                role="assistant",
                tool_calls=tool_calls
            ),
            finish_reason="tool_calls",
            index=0,
        )

        return ChatCompletion(
            id="test_id",
            created=0,
            model="test-model",
            object="chat.completion",
            choices=[choice]
        )


if __name__ == '__main__':
    unittest.main()
