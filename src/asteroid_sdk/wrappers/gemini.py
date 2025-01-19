"""
Wrapper for the Anthropic client to intercept requests and responses.
"""

import asyncio
import threading
from copy import deepcopy
from typing import Any, Callable, List, Optional
from uuid import UUID
import logging

from anthropic import Anthropic, AnthropicError
from google.generativeai import GenerativeModel, ChatSession

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.asteroid_chat_supervision_manager import AsteroidChatSupervisionManager, AsteroidLoggingError
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.supervision_runner import SupervisionRunner
from asteroid_sdk.settings import settings
from asteroid_sdk.supervision.config import ExecutionMode, RejectionPolicy, get_supervision_config
from asteroid_sdk.supervision.helpers.anthropic_helper import AnthropicSupervisionHelper
import traceback

from asteroid_sdk.supervision.helpers.gemini_helper import GeminiHelper


class GeminiGenerateContentWrapper:
    """Wraps chat completions with logging capabilities"""

    def __init__(
            self,
            gemini_model: GenerativeModel, #TODO - rename this var
            chat_supervision_manager: AsteroidChatSupervisionManager,
            run_id: UUID,
            execution_mode: str = "supervision"
    ):
        self._gemini_model = gemini_model
        self.chat_supervision_manager = chat_supervision_manager
        self.run_id = run_id
        self.execution_mode = execution_mode

    def generate_content(self, *args, message_supervisors: Optional[List[List[Callable]]] = None, **kwargs) -> Any:
        # TODO - Check if there's any other config that we need to sort out here
        # if kwargs.get("tool_choice", {}) and not kwargs["tool_choice"].get("disable_parallel_tool_use", False):
        #     logging.warning("Parallel tool calls are not supported, setting disable_parallel_tool_use=True")
        #     kwargs["tool_choice"]["disable_parallel_tool_use"] = True

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
            response = self._gemini_model.generate_content(*args, **kwargs)

            # SYNC LOGGING + SUPERVISION
            try:
                new_response = self.chat_supervision_manager.handle_language_model_interaction(
                    response,
                    request_kwargs=kwargs,
                    run_id=self.run_id,
                    execution_mode=self.execution_mode,
                    completions=self._gemini_model,
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
        try:
            self.chat_supervision_manager.log_request(kwargs, self.run_id)
        except AsteroidLoggingError as e:
            print(f"Warning: Failed to log request: {str(e)}")

        response = self._gemini_model.create(*args, **kwargs)

        try:
            # Make API call
            thread = threading.Thread(
                target=self.chat_supervision_manager.handle_language_model_interaction,
                kwargs={
                    "response": response, "request_kwargs": kwargs, "run_id": self.run_id,
                    "execution_mode": self.execution_mode, "completions": self._gemini_model, "args": args,
                    "message_supervisors": message_supervisors
                }
            )

            thread.start()
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
                execution_mode=self.execution_mode, completions=self._gemini_model, args=args,
                message_supervisors=message_supervisors
            )
        except Exception as e:
            print(f"Warning: Failed to log response: {str(e)}")
            traceback.print_exc()

def asteroid_gemini_wrap_model_generate_content(
        model: GenerativeModel,
        run_id: UUID,
        execution_mode: str = "supervision",
        rejection_policy: RejectionPolicy = RejectionPolicy.NO_RESAMPLE
) -> GenerativeModel:
    """
    Wraps an Anthropic client instance with logging capabilities and registers supervisors.
    """
    # TODO - Uncomment these
    if rejection_policy != RejectionPolicy.NO_RESAMPLE:
        raise ValueError("Unable to resample with Gemini yet! This feature is coming!")


    supervision_config = get_supervision_config()

    # Retrieve the run from the supervision configuration
    run = supervision_config.get_run_by_id(run_id)
    if run is None:
        raise Exception(f"Run with ID {run_id} not found in supervision config.")
    supervision_context = run.supervision_context

    try:
        # TODO - Clean up where this is instantiated
        client = Client(base_url=settings.api_url, headers={"X-Asteroid-Api-Key": f"{settings.api_key}"})
        supervision_manager = _create_supervision_manager(client)
        original_model = deepcopy(model)
        wrapper = GeminiGenerateContentWrapper(
            original_model,
            supervision_manager,
            run_id,
            execution_mode
        )
        model.generate_content = wrapper.generate_content
        return model
    except Exception as e:
        raise RuntimeError(f"Failed to wrap Anthropic client: {str(e)}") from e


def _create_supervision_manager(client):
    model_provider_helper = GeminiHelper()
    api_logger = APILogger(client, model_provider_helper)
    supervision_runner = SupervisionRunner(client, api_logger, model_provider_helper)
    supervision_manager = AsteroidChatSupervisionManager(client, api_logger, supervision_runner, model_provider_helper)
    return supervision_manager
