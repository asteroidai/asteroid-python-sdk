import datetime
import unittest
import uuid
from abc import ABC
from unittest.mock import MagicMock

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.asteroid_chat_supervision_manager import AsteroidChatSupervisionManager
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.generated.asteroid_api_client.models import Tool, ToolAttributes, ChatIds, ChoiceIds, ToolCallIds, \
    SupervisorChain, Supervisor, SupervisorType, SupervisorAttributes
from asteroid_sdk.api.supervision_runner import SupervisionRunner
from asteroid_sdk.supervision.config import ExecutionMode, RejectionPolicy, MultiSupervisorResolution
from asteroid_sdk.supervision.helpers.model_provider_helper import ModelProviderHelper
from tests.acceptance.init_asteroid import InitAsteroidForTestsConfig, init_asteroid_for_tests
from tests.helper.api.mock_api import make_created_response_with_id, make_ok_response, make_created_response
from tests.helper.tools.get_weather import get_weather_tool_object_dict
from tests.helper.tools.google_search import get_google_search_tool_object_dict


class AbstractAcceptanceTest(ABC, unittest.TestCase):
    def setUpGlobal(self, helper: ModelProviderHelper):
        self.mock_asteroid_client = MagicMock(Client)
        self.api_logger = APILogger(self.mock_asteroid_client, helper)
        self.model_provider_helper = helper
        self.supervision_runner = SupervisionRunner(
            self.mock_asteroid_client,
            self.api_logger,
            self.model_provider_helper
        )

        self.chat_supervision_manager = AsteroidChatSupervisionManager(
            self.mock_asteroid_client,
            self.api_logger,
            self.supervision_runner,
            self.model_provider_helper
        )

        self.run_id = uuid.uuid4()

    def resamples_then_works_globals(self, mock_get_client):
        """
        Sets up the global mocks for the resamples_then_works test
        """
        mock_get_client.return_value = self.mock_asteroid_client

        project_id = uuid.uuid4()
        task_id = uuid.uuid4()
        weather_tool_and_supervisor_id = uuid.uuid4()
        search_tool_and_supervisor_id = uuid.uuid4()

        config = InitAsteroidForTestsConfig(
            project_id,
            task_id,
            self.run_id,
            {
                "execution_mode": ExecutionMode.SUPERVISION,
                "allow_tool_modifications": True,
                "rejection_policy": RejectionPolicy.RESAMPLE_WITH_FEEDBACK,
                "n_resamples": 3,
                "multi_supervisor_resolution": MultiSupervisorResolution.ALL_MUST_APPROVE,
                "remove_feedback_from_context": True,
            },
            # NO IDEA WHY but order matters here
            [get_weather_tool_object_dict(self.run_id, weather_tool_and_supervisor_id),
             get_google_search_tool_object_dict(self.run_id, search_tool_and_supervisor_id)]
        )

        init_asteroid_for_tests(self.mock_asteroid_client, config)

        first_chat_id = uuid.uuid4()
        first_choice_id = uuid.uuid4()
        first_message_id = uuid.uuid4()
        first_tool_call_id = uuid.uuid4()

        # asteroid_sdk.api.asteroid_chat_supervision_manager.AsteroidChatSupervisionManager.handle_language_model_interaction
        # src/asteroid_sdk/api/asteroid_chat_supervision_manager.py:73
        send_chats_response = make_created_response(
            ChatIds(
                chat_id=first_chat_id,
                choice_ids=[ChoiceIds(
                    choice_id=str(first_choice_id),
                    message_id=str(first_message_id),
                    tool_call_ids=[
                        ToolCallIds(
                            tool_call_id=str(first_tool_call_id),
                            tool_id=str(search_tool_and_supervisor_id),
                        )
                    ]
                )]
            ).to_dict()
        )

        # asteroid_sdk.registration.helper.get_supervisor_chains_for_tool
        # src/asteroid_sdk/registration/helper.py:370
        # None of the data in here is particularly relevant to the test (bar ids)- using a Faker would probably be better
        get_tool_supervisor_chains_response = make_ok_response(
            [
                SupervisorChain(
                    chain_id=search_tool_and_supervisor_id,
                    supervisors=[Supervisor(
                        name="test_supervisor",
                        id=search_tool_and_supervisor_id,
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
                run_id=self.run_id,
                name="google_search",
                description="Search for a query string",
                code="def google_search(query_string: str): return f'Searched {query_string}.",
                id=search_tool_and_supervisor_id,
                ignored_attributes=[],
                attributes=ToolAttributes().from_dict({'query_string': "<class 'str'>"})
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
            send_supervision_result__response,

            send_chats_response,
            get_tool_supervisor_chains_response,
            get_tool_response,
            send_supervision_request_response,
            send_supervision_result__response,
        ]

    def original_response_when_supervision_successful(self, mock_get_client):
        # Mocking API client from the point it's called in registration
        mock_get_client.return_value = self.mock_asteroid_client

        project_id = uuid.uuid4()
        task_id = uuid.uuid4()
        weather_tool_and_supervisor_id = uuid.uuid4()
        search_tool_and_supervisor_id = uuid.uuid4()

        config = InitAsteroidForTestsConfig(
            project_id,
            task_id,
            self.run_id,
            {
                "execution_mode": ExecutionMode.SUPERVISION,
                "allow_tool_modifications": True,
                "rejection_policy": RejectionPolicy.RESAMPLE_WITH_FEEDBACK,
                "n_resamples": 3,
                "multi_supervisor_resolution": MultiSupervisorResolution.ALL_MUST_APPROVE,
                "remove_feedback_from_context": True,
            },
            # NO IDEA WHY but order matters here
            [get_weather_tool_object_dict(self.run_id, weather_tool_and_supervisor_id),
             get_google_search_tool_object_dict(self.run_id, search_tool_and_supervisor_id)]
        )

        init_asteroid_for_tests(self.mock_asteroid_client, config)

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
                            tool_id=str(weather_tool_and_supervisor_id),
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
                    chain_id=weather_tool_and_supervisor_id,
                    supervisors=[Supervisor(
                        name="test_supervisor",
                        id=weather_tool_and_supervisor_id,
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
                run_id=self.run_id,
                name="get_weather",
                description="Get the weather in a city",
                code="def get_weather(location: str, unit: str): return f'The weather in {location} is {unit}.",
                id=weather_tool_and_supervisor_id,
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
