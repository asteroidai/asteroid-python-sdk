import datetime
import unittest
import uuid
from http import HTTPStatus
from typing import List
from unittest.mock import MagicMock, ANY, patch

import httpx
import openai.resources.chat
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
from asteroid_sdk.wrappers.openai import CompletionsWrapper, asteroid_init
from tests.acceptance.init_asteroid import InitAsteroidForTestsConfig, init_asteroid_for_tests
from tests.helper.api.mock_api import make_created_response, make_created_response_with_id, make_response, \
    make_ok_response
from tests.helper.tools.get_weather import get_weather_tool_object_dict


class TestOpenAi(unittest.TestCase):
    def setUp(self):
        self.mock_asteroid_client = MagicMock(Client)
        self.api_logger = APILogger(self.mock_asteroid_client)
        self.supervision_runner = SupervisionRunner(self.mock_asteroid_client, self.api_logger)

        self.chat_supervision_manager = AsteroidChatSupervisionManager(
            self.mock_asteroid_client,
            self.api_logger,
            self.supervision_runner
        )

        self.run_id = uuid.uuid4()
        self.mock_completions = MagicMock(openai.resources.chat.Completions)
        self.openai_wrapper = CompletionsWrapper(
            self.mock_completions,
            self.chat_supervision_manager,
            self.run_id,
            ExecutionMode.SUPERVISION
        )

    def test_no_supervisors_are_run_with_no_tool_calls_in_llm_response(self):
        # Define test data
        first_chat_id = uuid.uuid4()
        first_choice_id = uuid.uuid4()

        # Mock API methods
        expected_response = self.create_chat_completion_with_message("Hello, nice to meet you")
        self.mock_completions.create.return_value = expected_response
        self.mock_asteroid_client.get_httpx_client.return_value.request.return_value = httpx.Response(
            status_code=HTTPStatus.OK,
            headers={},
            json={
                'chat_id': str(first_chat_id),
                'choice_ids': [
                    {'choice_id': str(first_choice_id), 'message_id': str(first_chat_id), 'tool_call_ids': []}
                ]
            }
        )

        messages = [{"role": "user", "content": "Hello"}]
        model = "test-model"
        # When
        response = self.openai_wrapper.create(messages=messages, model=model, parallel_tool_calls=False)

        # Then
        self.assertEqual(expected_response, response, "The response should be the same as the one returned by the API")
        self.mock_asteroid_client.get_httpx_client.return_value.request.assert_called_with(
            method=ANY,
            url=f"/run/{self.run_id}/chat",
            json=ANY,
            headers=ANY
        )

    @patch('asteroid_sdk.registration.helper.APIClientFactory.get_client')
    def test_original_response_is_returned_with_supervision_is_successful(self, mock_get_client):
        # Mocking API client from the point it's called in registration
        mock_get_client.return_value = self.mock_asteroid_client

        project_id=uuid.uuid4()
        task_id=uuid.uuid4()
        run_id=uuid.uuid4()
        tool_id=uuid.uuid4()
        supervisor_id=uuid.uuid4()
        chain_id_1=uuid.uuid4()

        config = InitAsteroidForTestsConfig(
            project_id,
            task_id,
            run_id,
            tool_id,
            supervisor_id,
            chain_id_1,
            {
                "execution_mode": ExecutionMode.SUPERVISION,
                "allow_tool_modifications": True,
                "rejection_policy": RejectionPolicy.RESAMPLE_WITH_FEEDBACK,
                "n_resamples": 3,
                "multi_supervisor_resolution": MultiSupervisorResolution.ALL_MUST_APPROVE,
                "remove_feedback_from_context": True,
            }
        )

        init_asteroid_for_tests(self.mock_asteroid_client, config)

        # THIS IS KEY- maybe we should instantiate the wrapper after we've run the init?
        self.openai_wrapper.run_id = run_id

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

        first_chat_id = uuid.uuid4()
        first_choice_id = uuid.uuid4()
        first_message_id = uuid.uuid4()
        first_tool_call_id = uuid.uuid4()

        # asteroid_sdk.api.asteroid_chat_supervision_manager.AsteroidChatSupervisionManager.handle_language_model_interaction
        # src/asteroid_sdk/api/asteroid_chat_supervision_manager.py:73
        send_chats_response = make_ok_response(
            ChatIds(
                chat_id=first_chat_id,
                choice_ids=[ChoiceIds(
                    choice_id=str(first_choice_id),
                    message_id=str(first_message_id),
                    tool_call_ids=[
                        ToolCallIds(
                            tool_call_id=str(first_tool_call_id),
                            tool_id=str(tool_id),
                        )
                    ]
                )]
            ).to_dict()
        )

        # asteroid_sdk.registration.helper.get_supervisor_chains_for_tool
        # src/asteroid_sdk/registration/helper.py:370
        get_tool_supervisor_chains_response = make_ok_response(
            [
                SupervisorChain(
                    chain_id=chain_id_1,
                    supervisors=[Supervisor(
                        name="test_supervisor",
                        id=supervisor_id,
                        type=SupervisorType.CLIENT_SUPERVISOR,
                        description="test description",
                        created_at=datetime.datetime.now(),
                        code="def test_supervisor(tool_call): return True",
                        attributes=SupervisorAttributes.from_dict({})
                    )],
                ).to_dict()
            ]
        )

        # asteroid_sdk.api.supervision_runner.SupervisionRunner.get_tool
        # src/asteroid_sdk/api/supervision_runner.py:193
        get_tool_response = make_ok_response(
            Tool(
                run_id=run_id,
                name="get_weather",
                description="Get the weather in a city",
                code="def get_weather(location: str, unit: str): return f'The weather in {location} is {unit}.",
                id=tool_id,
                ignored_attributes=[],
                attributes=ToolAttributes().from_dict({'location': "<class 'str'>", 'unit': "<class 'str'>"})
            ).to_dict()
        )

        review_id = uuid.uuid4()
        # asteroid_sdk.registration.helper.send_supervision_request
        # src/asteroid_sdk/registration/helper.py:394
        send_supervision_request_response = make_created_response_with_id(review_id)

        supervision_result_id = uuid.uuid4()
        # asteroid_sdk.registration.helper.send_supervision_result
        # src/asteroid_sdk/registration/helper.py:453
        send_supervision_result__response = make_created_response_with_id(supervision_result_id)

        # Setup mock calls to asteroid API for during supervision
        self.mock_asteroid_client.get_httpx_client.return_value.request.side_effect = [
            send_chats_response,
            get_tool_supervisor_chains_response,
            get_tool_response,
            send_supervision_request_response,
            send_supervision_result__response
        ]

        response = self.openai_wrapper.create(messages=messages, model=model, parallel_tool_calls=False)

        # Then
        self.assertEqual(response, desired_completion_message, "The response should be the same as the one returned by the API")

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
