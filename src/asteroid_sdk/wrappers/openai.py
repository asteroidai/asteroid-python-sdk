"""
Wrapper for the OpenAI client to intercept requests and responses.
"""

import asyncio
import logging
import threading
import traceback
import time
import atexit
from typing import Any, Callable, List, Optional
from uuid import UUID

from openai import OpenAIError

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.asteroid_chat_supervision_manager import (
    AsteroidChatSupervisionManager,
    AsteroidLoggingError,
)
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.supervision_runner import SupervisionRunner
from asteroid_sdk.settings import settings
from asteroid_sdk.supervision.config import ExecutionMode
from asteroid_sdk.supervision.helpers.openai_helper import OpenAiSupervisionHelper
from asteroid_sdk.api.generated.asteroid_api_client.api.run.get_run import sync as get_run_sync

# Conditionally import Langfuse if enabled
if settings.langfuse_enabled:
    try:
        from langfuse.decorators import observe as langfuse_observe
    except ImportError:
        logging.warning(
            "Langfuse is enabled in settings but not installed. Falling back to no-op."
        )
        LangfuseOpenAI = None
        langfuse_observe = None
else:
    # If Langfuse is not enabled, do not import or do anything special
    LangfuseOpenAI = None
    langfuse_observe = None


def no_op_observe(*args, **kwargs):
    """A no-op decorator for when Langfuse is not enabled or not installed."""
    def decorator(func):
        return func
    return decorator


# Use langfuse observe if available, otherwise no-op
observe = langfuse_observe if langfuse_observe else no_op_observe

# Create a background event loop
background_loop = asyncio.new_event_loop()
tasks = set()
loop_running = True  # Flag to keep the loop running


def start_background_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    finally:
        pending = asyncio.all_tasks(loop)
        if pending:
            # Wait for pending tasks to complete
            loop.run_until_complete(asyncio.gather(*pending))
        loop.close()


# Start the background loop in a new thread
# Set daemon=True but handle shutdown properly
background_thread = threading.Thread(
    target=start_background_loop, args=(background_loop,), daemon=True
)
background_thread.start()


# Function to schedule tasks
def schedule_task(coro):
    if not loop_running:
        logging.warning("Attempted to schedule task after shutdown initiated")
        return
    future = asyncio.run_coroutine_threadsafe(coro, background_loop)
    tasks.add(future)
    future.add_done_callback(task_done)
    return future  # Return future so caller can wait if needed


def task_done(fut):
    tasks.discard(fut)
    try:
        fut.result()
    except Exception as e:
        logging.error(f"Background task failed: {e}")
        traceback.print_exc()


def shutdown_background_loop():
    global loop_running
    loop_running = False  # Signal the loop to stop accepting new tasks

    # Wait for all tasks to complete with a timeout
    wait_start = time.time()
    while tasks and (time.time() - wait_start) < 30:  # 30 second timeout
        time.sleep(0.1)

    if tasks:
        logging.warning(f"{len(tasks)} tasks still pending at shutdown")

    try:
        # Stop the loop
        background_loop.call_soon_threadsafe(background_loop.stop)
    except Exception as e:
        logging.warning(f"Error stopping background loop: {e}")

    # Give the thread a chance to finish cleanly
    background_thread.join(timeout=5)


# Register shutdown handler
atexit.register(shutdown_background_loop)


class CompletionsWrapper:
    """Wraps chat completions with logging and supervision capabilities."""

    def __init__(
        self,
        completions: Any,
        chat_supervision_manager: AsteroidChatSupervisionManager,
        run_id: UUID,
        execution_mode: str = "supervision",
    ):
        self._completions = completions
        self.chat_supervision_manager = chat_supervision_manager
        self.run_id = run_id
        self.execution_mode = execution_mode

    async def _wait_for_unpaused(self):
        """Wait until the run is no longer in paused state."""
        while True:
            run_status = get_run_sync(client=self.chat_supervision_manager.client, run_id=str(self.run_id))
            if run_status and run_status.status != "paused":
                break
            logging.info(f"Run {self.run_id} is paused, waiting for unpaused state...")
            await asyncio.sleep(1)  # Wait 1 second before checking again

    def create(
        self,
        *args,
        message_supervisors: Optional[List[List[Callable]]] = None,
        **kwargs,
    ) -> Any:
        # Wait for unpaused state before proceeding - blocks until complete
        future = schedule_task(self._wait_for_unpaused())
        future.result()  # This blocks until the future is done
        
        # If parallel tool calls not set to false (or doesn't exist, defaulting to true), then raise an error.
        # Parallel tool calls do not work at the moment due to conflicts when trying to 'resample'
        if kwargs.get("tools", None) and kwargs.get("parallel_tool_calls", True):
            # parallel_tool_calls is only supported by openai when tools are specified
            logging.warning(
                "Parallel tool calls are not supported, setting parallel_tool_calls=False"
            )
            kwargs["parallel_tool_calls"] = False

        # Depending on the execution mode, handle supervision synchronously
        if self.execution_mode == ExecutionMode.MONITORING:
            # Run in monitoring mode (asynchronous supervision)
            return self.create_with_async_supervision(
                *args, message_supervisors=message_supervisors, **kwargs
            )
        elif self.execution_mode == ExecutionMode.SUPERVISION:
            # Run in sync supervision mode
            return self.create_sync(
                *args, message_supervisors=message_supervisors, **kwargs
            )
        else:
            raise ValueError(f"Invalid execution mode: {self.execution_mode}")

    def create_with_async_supervision(
        self,
        *args,
        message_supervisors: Optional[List[List[Callable]]] = None,
        **kwargs,
    ) -> Any:
        @observe(name="openai_wrapper_create_async") #TODO: This is now throwing pydantic warnings
        def create_completion(*args, **kwargs):
            response = self._completions.create(*args, **kwargs)
            return response

        response = create_completion(*args, **kwargs)

        async def supervision_task():
            try:
                # Asynchronously log the request
                await self.chat_supervision_manager.log_request(kwargs, self.run_id)
            except AsteroidLoggingError as e:
                logging.warning(f"Failed to log request: {str(e)}")
            except Exception as e:
                logging.error(f"Unexpected error during request logging: {str(e)}")
                traceback.print_exc()

            try:
                await self.chat_supervision_manager.handle_language_model_interaction(
                    response=response,
                    request_kwargs=kwargs,
                    run_id=self.run_id,
                    execution_mode=self.execution_mode,
                    completions=self._completions,
                    args=args,
                    message_supervisors=message_supervisors,
                )
            except Exception as e:
                logging.warning(f"Failed to process supervision: {str(e)}")
                traceback.print_exc()

        # Schedule the supervision task and get future
        schedule_task(supervision_task())
        return response

    def create_sync(
        self,
        *args,
        message_supervisors: Optional[List[List[Callable]]] = None,
        **kwargs,
    ) -> Any:
        # Log the entire request payload synchronously
        try:
            # Use asyncio.run for one-off async calls
            asyncio.run(self.chat_supervision_manager.log_request(kwargs, self.run_id))
        except AsteroidLoggingError as e:
            logging.warning(f"Failed to log request: {str(e)}")

        @observe(name="openai_wrapper_create_sync") #TODO: This is now throwing pydantic warnings
        def create_completion(*args, **kwargs):
            response = self._completions.create(*args, **kwargs)
            return response

        response = create_completion(*args, **kwargs)

        try:
            # Use asyncio.run for the supervision handling
            supervised_response = asyncio.run(
                self.chat_supervision_manager.handle_language_model_interaction(
                    response=response,
                    request_kwargs=kwargs,
                    run_id=self.run_id,
                    execution_mode=self.execution_mode,
                    completions=self._completions,
                    args=args,
                    message_supervisors=message_supervisors,
                )
            )
            if supervised_response is not None:
                return supervised_response
            return response
        except OpenAIError as e:
            raise e


def asteroid_openai_client(
    openai_client: Any, run_id: UUID, execution_mode: str = "supervision"
) -> Any:
    """
    Wraps an OpenAI client instance with logging capabilities and registers supervisors.
    """
    if not openai_client:
        raise ValueError("Client is required")

    if not hasattr(openai_client, "chat"):
        raise ValueError("Invalid OpenAI client: missing chat attribute")

    try:
        client = Client(
            base_url=settings.api_url,
            headers={"X-Asteroid-Api-Key": f"{settings.api_key}"},
        )
        supervision_manager = _create_supervision_manager(client)
        openai_client.chat.completions = CompletionsWrapper(
            openai_client.chat.completions, supervision_manager, run_id, execution_mode
        )
        return openai_client
    except Exception as e:
        raise RuntimeError(f"Failed to wrap OpenAI client: {str(e)}") from e


def _create_supervision_manager(client):
    model_provider_helper = OpenAiSupervisionHelper()
    api_logger = APILogger(client, model_provider_helper)
    supervision_runner = SupervisionRunner(client, api_logger, model_provider_helper)
    supervision_manager = AsteroidChatSupervisionManager(
        client, api_logger, supervision_runner, model_provider_helper
    )
    return supervision_manager
