import datetime
import unittest
import uuid
from http import HTTPStatus
from typing import List
from unittest.mock import MagicMock, ANY, patch

import httpx
from anthropic.resources import Messages
from anthropic.types import Message, Usage, TextBlock, ToolUseBlock
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_tool_call import Function

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.asteroid_chat_supervision_manager import AsteroidChatSupervisionManager
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.generated.asteroid_api_client.models import Tool, ToolAttributes, ChatIds, ChoiceIds, ToolCallIds, \
    SupervisorChain, Supervisor, SupervisorType, SupervisorAttributes
from asteroid_sdk.api.supervision_runner import SupervisionRunner
from asteroid_sdk.supervision.config import ExecutionMode, RejectionPolicy, MultiSupervisorResolution
from asteroid_sdk.supervision.helpers.anthropic_helper import AnthropicSupervisionHelper
from asteroid_sdk.wrappers.anthropic import CompletionsWrapper
from tests.acceptance.abstract_acceptance_test import AbstractAcceptanceTest
from tests.acceptance.init_asteroid import InitAsteroidForTestsConfig, init_asteroid_for_tests
from tests.helper.api.mock_api import make_created_response_with_id, make_ok_response
from tests.helper.tools.get_weather import get_weather_tool_object_dict


class TestAnthropic(AbstractAcceptanceTest):
    def setUp(self):
        self.setUpGlobal(AnthropicSupervisionHelper())
        self.mock_messages = MagicMock(Messages)
        self.anthropic_wrapper = CompletionsWrapper(
            self.mock_messages,
            self.chat_supervision_manager,
            self.run_id,
            ExecutionMode.SUPERVISION
        )

    @patch('asteroid_sdk.registration.helper.APIClientFactory.get_client')
    def test_original_response_is_returned_with_supervision_is_successful(self, mock_get_client):
        self.original_response_when_supervision_successful(mock_get_client)

        # THIS IS KEY- maybe we should instantiate the wrapper after we've run the init?
        self.anthropic_wrapper.run_id = self.run_id

        # Mock call to LM
        desired_completion_message = self.create_message_with_tool_calls(
            [
                ToolUseBlock(
                    id="random_id",
                    name="get_weather",
                    input={
                        "location": "London",
                        "unit": "Celsius"
                    },
                    type="tool_use"
                )
            ]
        )
        self.mock_messages.create.return_value = desired_completion_message
        messages = [{"role": "user", "content": "Get me the weather in London"}]
        model = "test-model"
        # When
        response = self.anthropic_wrapper.create(messages=messages, model=model, parallel_tool_calls=False)

        # Then
        self.assertEqual(response, desired_completion_message, "The response should be the same as the one returned by the API")
        # assert the call count on mock messages
        self.assertEqual(self.mock_messages.create.call_count, 1)

    @patch('asteroid_sdk.registration.helper.APIClientFactory.get_client')
    def test_resamples_and_then_works(self, mock_get_client):
        self.resamples_then_works_globals(mock_get_client)
        # Mock call to LM
        # Note- the allow: true param is what the supervisor is after to approve
        desired_completion_message = self.create_message_with_tool_calls(
            [
                ToolUseBlock(
                    id="random_id",
                    name="google_search",
                    input={
                        "query_string": "is BTC going to the moon",
                        "allow": False
                    },
                    type="tool_use"
                )
            ]
        )
        resampled_completion_message = self.create_message_with_tool_calls(
            [
                ToolUseBlock(
                    id="random_id",
                    name="google_search",
                    input={
                        "query_string": "is BTC going to the moon",
                        "allow": True
                    },
                    type="tool_use"
                )
            ]
        )
        self.mock_messages.create.side_effect = [
            desired_completion_message,
            resampled_completion_message
        ]
        # THIS IS KEY- maybe we should instantiate the wrapper after we've run the init?
        self.anthropic_wrapper.run_id = self.run_id

        messages = [{"role": "user", "content": "Search the internet for 'is BTC going to the moon'"}]
        model = "test-model"
        response = self.anthropic_wrapper.create(messages=messages, model=model, parallel_tool_calls=False)

        # Then
        self.assertEqual(response, resampled_completion_message,
                         "The response should be the same as the one returned by the API")

    def create_message_with_text(self, content: str) -> Message:
        text = TextBlock(
            text=content,
            type="text"
        )
        return Message(
            id="test_id",
            content=[text],
            model="test-model",
            role="assistant",
            type="message",
            usage=Usage(
                input_tokens=0,
                output_tokens=0,
            ),
        )

    def create_message_with_tool_calls(self, tool_calls: List[ToolUseBlock]) -> ChatCompletion:
        return Message(
            id="test_id",
            content=tool_calls,
            model="test-model",
            role="assistant",
            type="message",
            usage=Usage(
                input_tokens=0,
                output_tokens=0,
            ),
        )

if __name__ == '__main__':
    unittest.main()
