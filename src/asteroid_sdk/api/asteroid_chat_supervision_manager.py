from typing import Any, Dict, List, Optional, Callable
from uuid import UUID
import asyncio

from anthropic.types import Message
from openai.types.chat.chat_completion import ChatCompletion

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.supervision.config import get_supervision_config
from asteroid_sdk.api.supervision_runner import SupervisionRunner
from asteroid_sdk.registration.helper import generate_fake_message_tool_call
from asteroid_sdk.supervision.helpers.model_provider_helper import ModelProviderHelper, Provider
from asteroid_sdk.supervision.model.tool_call import ToolCall
from asteroid_sdk.api.generated.asteroid_api_client.models import ChatFormat

import logging

class AsteroidLoggingError(Exception):
    """Raised when there's an error logging to Asteroid API."""
    pass


class AsteroidChatSupervisionManager:
    """Handles logging to the Asteroid API, including supervision and resampling."""

    def __init__(
            self,
            client: Client,
            api_logger: APILogger,
            supervision_runner: SupervisionRunner,
            model_provider_helper: ModelProviderHelper
    ):
        """
        Initialize the API logger with the given API key.

        :param api_key: The API key for authenticating with the Sentinel API.
        """
        self.client = client
        self.api_logger = api_logger
        self.supervision_runner = supervision_runner
        self.model_provider_helper = model_provider_helper


    async def log_request(self, request_data: Dict[str, Any], run_id: UUID) -> None:
        """
        Log the request data. Currently a no-op as the Asteroid API doesn't require request data
        to be sent separately; it is sent along with the response in `log_response`.

        :param request_data: The data of the request to log.
        :param run_id: The unique identifier for the run.
        """
        pass  # No action required.

    async def handle_language_model_interaction(
            self,
            response: ChatCompletion|Message, # TODO - Change this to use a generic maybe
            request_kwargs: Dict[str, Any],
            run_id: UUID,
            execution_mode: str,
            completions: Any,
            args: Any,
            message_supervisors: Optional[List[List[Callable]]] = None
    ) -> Optional[ChatCompletion]: # TODO - Change this to use a generic maybe
        """
        Send the raw response data to the Sentinel API, and process tool calls
        through supervision and resampling if necessary.

        :param response: The response from the OpenAI API.
        :param request_kwargs: The request keyword arguments used in the OpenAI API call.
        :param run_id: The unique identifier for the run.
        :param execution_mode: The execution mode for the logging.
        :param completions: The completions object (e.g., the OpenAI.Completions class).
        :param args: Additional arguments for the completions.create call.
        :param message_supervisors: The message supervisors to use for supervision.
        :return: Potentially modified response after supervision and resampling, or None.
        """

        # Get the run by the run_id to retrieve the supervision context
        supervision_config = get_supervision_config()
        run = supervision_config.get_run_by_id(run_id)
        if not run:
            print(f"Run not found for ID: {run_id}")
            return None

        supervision_context = run.supervision_context
        # Update messages on the supervision context
        supervision_context.update_messages(request_kwargs,
                                            provider=self.model_provider_helper.get_provider(),
                                            system_message=request_kwargs.get('system', None))

        response, response_data_tool_calls = self.get_tool_calls_and_modify_response_if_necessary(
            response=response,
            supervision_context=supervision_context,
            message_supervisors=message_supervisors
        )

        # Log the interaction
        # It needs to be after the tool calls are processed in case we switch a chat message to tool call
        create_new_chat_response = self.api_logger.log_llm_interaction(
            response,
            request_kwargs,
            run_id,
        )

        if not response_data_tool_calls:
            return None

        choice_ids = create_new_chat_response.choice_ids

        # Extract execution settings from the supervision configuration
        new_response = await self.supervision_runner.handle_tool_calls_from_llm_response(
            args=args,
            choice_ids=choice_ids,
            completions=completions,
            execution_mode=execution_mode,
            request_kwargs=request_kwargs,
            response=response,
            response_data_tool_calls=response_data_tool_calls,
            run_id=run_id,
            supervision_context=supervision_context,
            message_supervisors=message_supervisors
        )
                                   
        # We need to check if the the new response is our fake message tool call and change it to a normal message
        new_response = self.model_provider_helper.generate_message_from_fake_tool_call(new_response)

        return new_response

    def get_tool_calls_and_modify_response_if_necessary(
            self,
            response: Any,
            supervision_context: Any,
            message_supervisors: Optional[List[List[Callable]]] = None,
    ) -> tuple[Any, Optional[List[ToolCall]]]:
        """
        Process the tool calls from the response data. If no tool calls are found,
        handle accordingly based on the presence of chat supervisors.

        :param response: The original ChatCompletion response from the OpenAI API.
        :param response_data: The response data as a dictionary.
        :param supervision_context: The supervision context associated with the run.
        :param message_supervisors: A list of message supervisor callables.
        :return: A tuple of (modified_response, response_data_tool_calls) or None.
        """
        response_data_tool_calls = self.model_provider_helper.get_tool_call_from_response(response)

        if message_supervisors and not response_data_tool_calls:
            # Use the extracted function to generate fake tool calls
            modified_response, response_data_tool_calls = generate_fake_message_tool_call(
                response=response,
                supervision_context=supervision_context,
                model_provider_helper=self.model_provider_helper,
                message_supervisors=message_supervisors,
            )
            logging.info("No tool calls found in response, but message supervisors provided, executing message supervisors")

            return modified_response, response_data_tool_calls
        else:
            return response, response_data_tool_calls
