"""
Wrapper for the OpenAI client to intercept requests and responses.
"""

import json
from typing import Any, Callable, List, Optional, Dict
from uuid import UUID
from openai import OpenAIError

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.supervision_runner import SupervisionRunner
from asteroid_sdk.api.asteroid_chat_supervision_manager import AsteroidChatSupervisionManager, AsteroidLoggingError
from asteroid_sdk.settings import settings
from asteroid_sdk.registration.helper import create_run, register_project, register_task, register_tools_and_supervisors
from asteroid_sdk.supervision.config import ExecutionMode
import asyncio

class CompletionsWrapper:
    """Wraps chat completions with logging capabilities"""
    def __init__(
        self,
        completions: Any,
        chat_supervision_manager: AsteroidChatSupervisionManager,
        run_id: UUID,
        execution_mode: str = "supervision"
    ):
        self._completions = completions
        self.chat_supervision_manager = chat_supervision_manager
        self.run_id = run_id
        self.execution_mode = execution_mode

    def create(self, *args, chat_supervisors: Optional[List[Callable]] = None, **kwargs) -> Any:
        # If parallel tool calls not set to false (or doesn't exist, defaulting to true), then raise an error.
        # Parallel tool calls do not work at the moment due to conflicts when trying to 'resample'
        if kwargs.get("parallel_tool_calls", True):
            raise ValueError("Parallel tool calls are not supported, Please turn them off by setting 'parallel_tool_calls=False' in your request.")

        if self.execution_mode == ExecutionMode.MONITORING:
            # Run in async mode
            return asyncio.run(self.create_async(*args, chat_supervisors=chat_supervisors, **kwargs))
        elif self.execution_mode == ExecutionMode.SUPERVISION:
            # Run in sync mode
            return self.create_sync(*args, chat_supervisors=chat_supervisors, **kwargs)
        else:
            raise ValueError(f"Invalid execution mode: {self.execution_mode}")

    def create_sync(self, *args, chat_supervisors: Optional[List[Callable]] = None, **kwargs) -> Any:
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
                    response, request_kwargs=kwargs, run_id=self.run_id,
                    execution_mode=self.execution_mode, completions=self._completions, args=args
                )
                if new_response is not None:
                    print(f"New response: {new_response}")
                    return new_response
            except Exception as e:
                print(f"Warning: Failed to log response: {str(e)}")

            return response

        except OpenAIError as e:
            try:
                raise e
            except AsteroidLoggingError:
                raise e

    async def create_async(self, *args, chat_supervisors: Optional[List[Callable]] = None, **kwargs) -> Any:
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
            asyncio.create_task(self.async_log_response(response, kwargs, args, chat_supervisors))

            # Return the response immediately
            return response

        except OpenAIError as e:
            try:
                raise e
            except AsteroidLoggingError:
                raise e

    async def async_log_response(self, response, kwargs, args, chat_supervisors):
        try:
            await asyncio.to_thread(
                self.chat_supervision_manager.handle_language_model_interaction, response, request_kwargs=kwargs, run_id=self.run_id,
                execution_mode=self.execution_mode, completions=self._completions, args=args, chat_supervisors=chat_supervisors
            )
        except Exception as e:
            print(f"Warning: Failed to log response: {str(e)}")


def asteroid_openai_client(
    openai_client: Any,
    run_id: UUID,
    execution_mode: str = "supervision"
) -> Any:
    """
    Wraps an OpenAI client instance with logging capabilities and registers supervisors.
    """
    if not openai_client:
        raise ValueError("Client is required")

    if not hasattr(openai_client, 'chat'):
        raise ValueError("Invalid OpenAI client: missing chat attribute")

    try:

        # TODO - Clean up where this is instantiated
        client = Client(base_url=settings.api_url)
        api_logger = APILogger(client)
        supervision_runner = SupervisionRunner(client, api_logger)
        supervision_manager = AsteroidChatSupervisionManager(client, api_logger, supervision_runner)
        openai_client.chat.completions = CompletionsWrapper(
            openai_client.chat.completions,
            supervision_manager,
            run_id,
            execution_mode
        )
        return openai_client
    except Exception as e:
        raise RuntimeError(f"Failed to wrap OpenAI client: {str(e)}") from e

def asteroid_init(
    project_name: str = "My Project",
    task_name: str = "My Agent",
    run_name: str = "My Run",
    tools: Optional[List[Callable]] = None,
    execution_settings: Dict[str, Any] = {}
) -> UUID:
    """
    Initializes supervision for a project, task, and run.
    """

    project_id = register_project(project_name)
    print(f"Registered new project '{project_name}' with ID: {project_id}")
    task_id = register_task(project_id, task_name)
    print(f"Registered new task '{task_name}' with ID: {task_id}")
    run_id = create_run(project_id, task_id, run_name)
    print(f"Registered new run with ID: {run_id}")

    register_tools_and_supervisors(run_id, tools, execution_settings)

    return run_id

def asteroid_end(run_id: UUID) -> None:
    """
    Stops supervision for a run.
    """
    pass
