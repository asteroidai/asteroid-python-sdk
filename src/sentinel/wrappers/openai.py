"""
Wrapper for the OpenAI client to intercept requests and responses.
"""

import json
from typing import Any, Callable, List, Optional
from uuid import UUID, uuid4
from openai import OpenAIError
from sentinel.api.logger import APILogger, SentinelLoggingError
from sentinel.settings import settings
from sentinel.registration.helper import create_run, register_project, register_task, APIClientFactory, register_tools_and_supervisors
import inspect
from sentinel.supervision.config import get_supervision_config, get_supervision_context

class CompletionsWrapper:
    """Wraps chat completions with logging capabilities"""
    def __init__(
        self, 
        completions: Any, 
        logger: APILogger, 
        run_id: UUID
    ):
        self._completions = completions
        self.logger = logger
        self.run_id = run_id
    
    def create(self, *args, **kwargs) -> Any:
        # Log the entire request payload
        try:
            self.logger.log_request(kwargs, self.run_id)
        except SentinelLoggingError as e:
            print(f"Warning: Failed to log request: {str(e)}")
        
        try:
            # Make API call
            response = self._completions.create(*args, **kwargs)

            # Log the entire response
            try:
                response_data = response if isinstance(response, dict) else response.dict()
                request_data = kwargs
                self.logger.log_response(response_data, request_data, self.run_id)
            except Exception as e:
                print(f"Warning: Failed to log response: {str(e)}")
            
            return response
            
        except OpenAIError as e:
            try:
                raise e
            except SentinelLoggingError:
                raise e

def sentinel_openai_client(
    openai_client: Any, 
    run_id: UUID,
) -> Any:
    """
    Wraps an OpenAI client instance with logging capabilities and registers supervisors.
    """
    if not openai_client:
        raise ValueError("Client is required")
    
    if not hasattr(openai_client, 'chat'):
        raise ValueError("Invalid OpenAI client: missing chat attribute")
        
    try:
        logger = APILogger(settings.api_key)
        openai_client.chat.completions = CompletionsWrapper(
            openai_client.chat.completions, 
            logger,
            run_id
        )
        return openai_client
    except Exception as e:
        raise RuntimeError(f"Failed to wrap OpenAI client: {str(e)}") from e

def sentinel_init(
    project_name: str = "My Project", 
    task_name: str = "My Agent", 
    run_name: str = "My Run",
    tools: Optional[List[Callable]] = None
) -> None:
    """
    Initializes supervision for a project, task, and run.
    """

    project_id = register_project(project_name)
    print(f"Registered new project '{project_name}' with ID: {project_id}")
    task_id = register_task(project_id, task_name)
    print(f"Registered new task '{task_name}' with ID: {task_id}")
    run_id = create_run(project_id, task_id, run_name)
    print(f"Registered new run with ID: {run_id}")

    register_tools_and_supervisors(run_id, tools)

    return run_id

def sentinel_end(run_id: UUID) -> None:
    """
    Stops supervision for a run.
    """
    pass
