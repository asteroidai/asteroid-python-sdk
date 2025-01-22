"""
Wrapper for the Gemini client to intercept requests and responses.
"""

import asyncio
import threading
import time
import atexit
import logging
import traceback
from copy import deepcopy
from typing import Any, Callable, List, Optional
from uuid import UUID

from google.generativeai import GenerativeModel

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.asteroid_chat_supervision_manager import (
    AsteroidChatSupervisionManager,
    AsteroidLoggingError,
)
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.supervision_runner import SupervisionRunner
from asteroid_sdk.settings import settings
from asteroid_sdk.supervision.config import (
    ExecutionMode,
    RejectionPolicy,
    get_supervision_config,
)
from asteroid_sdk.supervision.helpers.gemini_helper import GeminiHelper

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

class GeminiGenerateContentWrapper:
    """Wraps generate_content with logging capabilities"""

    def __init__(
        self,
        gemini_model: GenerativeModel,  # TODO - rename this var
        chat_supervision_manager: AsteroidChatSupervisionManager,
        run_id: UUID,
        execution_mode: str = "supervision",
    ):
        self._gemini_model = gemini_model
        self.chat_supervision_manager = chat_supervision_manager
        self.run_id = run_id
        self.execution_mode = execution_mode

    def generate_content(
        self,
        *args,
        message_supervisors: Optional[List[List[Callable]]] = None,
        **kwargs,
    ) -> Any:
        # TODO - Check if there's any other config that we need to sort out here
        # if kwargs.get("tool_choice", {}) and not kwargs["tool_choice"].get("disable_parallel_tool_use", False):
        #     logging.warning("Parallel tool calls are not supported, setting disable_parallel_tool_use=True")
        #     kwargs["tool_choice"]["disable_parallel_tool_use"] = True

        if self.execution_mode == ExecutionMode.MONITORING:
            # Run in async mode
            return self.generate_content_with_async_supervision(
                *args, message_supervisors=message_supervisors, **kwargs
            )
        elif self.execution_mode == ExecutionMode.SUPERVISION:
            # Run in sync mode
            return self.generate_content_sync(
                *args, message_supervisors=message_supervisors, **kwargs
            )
        else:
            raise ValueError(f"Invalid execution mode: {self.execution_mode}")

    def generate_content_with_async_supervision(
        self,
        *args,
        message_supervisors: Optional[List[List[Callable]]] = None,
        **kwargs,
    ) -> Any:
        # Make the Gemini API call synchronously
        response = self._gemini_model.generate_content(*args, **kwargs)

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
                    completions=self._gemini_model,
                    args=args,
                    message_supervisors=message_supervisors,
                )
            except Exception as e:
                logging.warning(f"Failed to process supervision: {str(e)}")
                traceback.print_exc()

        # Schedule the supervision task
        schedule_task(supervision_task())
        return response

    def generate_content_sync(
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
            print(f"Warning: Failed to log request: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error during request logging: {str(e)}")
            traceback.print_exc()

        # Make the Gemini API call
        response = self._gemini_model.generate_content(*args, **kwargs)

        try:
            # Use asyncio.run for the supervision handling
            supervised_response = asyncio.run(
                self.chat_supervision_manager.handle_language_model_interaction(
                    response=response,
                    request_kwargs=kwargs,
                    run_id=self.run_id,
                    execution_mode=self.execution_mode,
                    completions=self._gemini_model,
                    args=args,
                    message_supervisors=message_supervisors,
                )
            )
            if supervised_response is not None:
                print(f"New response: {supervised_response}")
                return supervised_response
            return response
        except Exception as e:
            print(f"Warning: Failed to process supervision: {str(e)}")
            traceback.print_exc()
            return response

def asteroid_gemini_wrap_model_generate_content(
    model: GenerativeModel,
    run_id: UUID,
    execution_mode: str = "supervision",
    rejection_policy: RejectionPolicy = RejectionPolicy.NO_RESAMPLE,
) -> GenerativeModel:
    """
    Wraps a Gemini client instance with logging capabilities and registers supervisors.
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
        client = Client(
            base_url=settings.api_url,
            headers={"X-Asteroid-Api-Key": f"{settings.api_key}"},
        )
        supervision_manager = _create_supervision_manager(client)
        original_model = deepcopy(model)
        wrapper = GeminiGenerateContentWrapper(
            original_model,
            supervision_manager,
            run_id,
            execution_mode,
        )
        model.generate_content = wrapper.generate_content
        return model
    except Exception as e:
        raise RuntimeError(f"Failed to wrap Gemini client: {str(e)}") from e

def _create_supervision_manager(client):
    model_provider_helper = GeminiHelper()
    api_logger = APILogger(client, model_provider_helper)
    supervision_runner = SupervisionRunner(
        client, api_logger, model_provider_helper
    )
    supervision_manager = AsteroidChatSupervisionManager(
        client, api_logger, supervision_runner, model_provider_helper
    )
    return supervision_manager
