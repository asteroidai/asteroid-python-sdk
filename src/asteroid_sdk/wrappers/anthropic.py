"""
Wrapper for the Anthropic client to intercept requests and responses.
"""

import asyncio
from typing import Any, Callable, List, Optional
from uuid import UUID

from anthropic import Anthropic, AnthropicError

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.asteroid_chat_supervision_manager import AsteroidChatSupervisionManager, AsteroidLoggingError
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.supervision_runner import SupervisionRunner
from asteroid_sdk.settings import settings
from asteroid_sdk.supervision.config import ExecutionMode
from asteroid_sdk.supervision.helpers.anthropic_helper import AnthropicSupervisionHelper
import traceback

class CompletionsWrapper:
    """Wraps chat completions with logging capabilities"""

    def __init__(
            self,
            completions: Any, #TODO - Maybe make this generic also?
            chat_supervision_manager: AsteroidChatSupervisionManager,
            run_id: UUID,
            execution_mode: str = "supervision"
    ):
        self._completions = completions
        self.chat_supervision_manager = chat_supervision_manager
        self.run_id = run_id
        self.execution_mode = execution_mode

    def create(self, *args, message_supervisors: Optional[List[List[Callable]]] = None, **kwargs) -> Any:
        # If parallel tool calls not set to false (or doesn't exist, defaulting to true), then raise an error.
        # Parallel tool calls do not work at the moment due to conflicts when trying to 'resample'
        if kwargs.get("tool_choice", False) and kwargs["tool_choice"]["disable_parallel_tool_use"] == False:
            raise ValueError(
                "Parallel tool calls are not supported, Please turn them off by setting 'parallel_tool_calls=False' in your request.")

        if self.execution_mode == ExecutionMode.MONITORING:
            # Run in async mode
            return asyncio.run(self.create_async(*args, message_supervisors=message_supervisors, **kwargs))
        elif self.execution_mode == ExecutionMode.SUPERVISION:
            # Run in sync mode
            return self.create_sync(*args, message_supervisors=message_supervisors, **kwargs)
        else:
            raise ValueError(f"Invalid execution mode: {self.execution_mode}")

    def create_sync(self, *args, message_supervisors: Optional[List[List[Callable]]] = None, **kwargs) -> Any:
        # Log the entire request payload
        try:
            self.chat_supervision_manager.log_request(kwargs, self.run_id)
        except AsteroidLoggingError as e:
            print(f"Warning: Failed to log request: {str(e)}")

        try:
            # Make API call
            response = self._completions.create(*args, **kwargs)

            # SYNC LOGGING + SUPERVISION
            try:
                new_response = self.chat_supervision_manager.handle_language_model_interaction(
                    response,
                    request_kwargs=kwargs,
                    run_id=self.run_id,
                    execution_mode=self.execution_mode,
                    completions=self._completions,
                    args=args,
                    message_supervisors=message_supervisors
                )
                if new_response is not None:
                    print(f"New response: {new_response}")
                    return new_response
            except Exception as e:
                print(f"Warning: Failed to log response: {str(e)}")
                traceback.print_exc()

            return response

        except AnthropicError as e:
            try:
                raise e
            except AsteroidLoggingError:
                raise e

    async def create_async(self, *args, message_supervisors: Optional[List[List[Callable]]] = None, **kwargs) -> Any:
        # Log the entire request payload asynchronously
        try:
            await asyncio.to_thread(self.chat_supervision_manager.log_request, kwargs, self.run_id)
        except AsteroidLoggingError as e:
            print(f"Warning: Failed to log request: {str(e)}")

        try:
            # Make API call synchronously
            response = self._completions.create(*args, **kwargs)

            # ASYNC LOGGING + SUPERVISION
            # Schedule the log_response to run in the background
            asyncio.create_task(self.async_log_response(response, kwargs, args, message_supervisors))

            # Return the response immediately
            return response

        except AnthropicError as e:
            try:
                raise e
            except AsteroidLoggingError:
                raise e

    async def async_log_response(self, response, kwargs, args, message_supervisors):
        try:
            await asyncio.to_thread(
                self.chat_supervision_manager.handle_language_model_interaction, response, request_kwargs=kwargs,
                run_id=self.run_id,
                execution_mode=self.execution_mode, completions=self._completions, args=args,
                message_supervisors=message_supervisors
            )
        except Exception as e:
            print(f"Warning: Failed to log response: {str(e)}")
            traceback.print_exc()


def asteroid_anthropic_client(
        anthropic_client: Anthropic,
        run_id: UUID,
        execution_mode: str = "supervision"
) -> Anthropic:
    """
    Wraps an Anthropic client instance with logging capabilities and registers supervisors.
    """
    if not anthropic_client:
        raise ValueError("Client is required")

    if not hasattr(anthropic_client, 'messages'):
        raise ValueError("Invalid Anthropic client: missing chat attribute")

    try:
        # TODO - Clean up where this is instantiated
        client = Client(base_url=settings.api_url, headers={"X-Asteroid-Api-Key": f"{settings.api_key}"})
        supervision_manager = _create_supervision_manager(client)
        anthropic_client.messages = CompletionsWrapper(
            anthropic_client.messages,
            supervision_manager,
            run_id,
            execution_mode
        )
        return anthropic_client
    except Exception as e:
        raise RuntimeError(f"Failed to wrap Anthropic client: {str(e)}") from e


def _create_supervision_manager(client):
    model_provider_helper = AnthropicSupervisionHelper()
    api_logger = APILogger(client, model_provider_helper)
    supervision_runner = SupervisionRunner(client, api_logger, model_provider_helper)
    supervision_manager = AsteroidChatSupervisionManager(client, api_logger, supervision_runner, model_provider_helper)
    return supervision_manager
