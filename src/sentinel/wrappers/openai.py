"""
Wrapper for the OpenAI client to intercept requests and responses.
"""

from typing import Any
from uuid import uuid4
from openai import OpenAIError
from sentinel.api.logger import APILogger, SentinelLoggingError
from sentinel.config import settings
from sentinel.registration.helper import create_run, register_project, register_task, APIClientFactory
from sentinel.supervision.registry import registry
import inspect

class CompletionsWrapper:
    """Wraps chat completions with logging capabilities"""
    def __init__(self, completions: Any, logger: APILogger):
        self._completions = completions
        self.logger = logger
    
    def create(self, *args, **kwargs) -> Any:
        # Extract or generate conversation ID
        conversation_id = kwargs.pop('conversation_id', str(uuid4()))
        
        # Log the entire request payload
        try:
            self.logger.log_request(kwargs)
        except SentinelLoggingError as e:
            print(f"Warning: Failed to log request: {str(e)}")
        
        try:
            # Make API call
            response = self._completions.create(*args, **kwargs)
            
            # Log the entire response
            try:
                response_data = response if isinstance(response, dict) else response.dict()
                self.logger.log_response(response_data)
            except Exception as e:
                print(f"Warning: Failed to log response: {str(e)}")
            
            return response
            
        except OpenAIError as e:
            # Log the error
            try:
                error_data = {
                    "error": str(e),
                    "error_type": e.__class__.__name__,
                    "request": kwargs
                }
                self.logger.log_response(error_data, conversation_id)
            except SentinelLoggingError:
                pass
            
            raise

def wrap_client(openai_client: Any, project_name: str = "My Project", task_name: str = "My Agent") -> Any:
    """
    Wraps an OpenAI client instance with logging capabilities and registers supervisors.
    """
    if not openai_client:
        raise ValueError("Client is required")
    
    if not hasattr(openai_client, 'chat'):
        raise ValueError("Invalid OpenAI client: missing chat attribute")
        
    try:
        # Register project if no project_id exists
        if not settings.project_id:
            project_id = register_project(project_name)
            print(f"Registered new project '{project_name}' with ID: {project_id}")

        # Register task if no task_id exists
        if not settings.task_id:
            task_id = register_task(project_id, task_name)
            print(f"Registered new task '{task_name}' with ID: {task_id}")

        # Register run if no run_id exists
        if not settings.run_id:
            run_id = create_run(project_id, task_id)
            print(f"Registered new run with ID: {run_id}")
        
        # Register all supervised functions and their supervisors
        supervised_functions = registry.get_supervised_functions()
        for func_name, func_info in supervised_functions.items():
            print(f"\nInspecting function: {func_name}")
            
            # Inspect the supervisors
            for chain in func_info.supervisors:
                for supervisor in chain:
                    print("\nSupervisor Details:")
                    print(f"Name: {supervisor.name}")
                    print(f"Source code:\n{inspect.getsource(supervisor.function)}")
                    print(f"Arguments: {inspect.signature(supervisor.function)}")
                    
                    # You can also call the function if needed
                    # result = supervisor.function("test_action", "test_context")
                    
        logger = APILogger(settings.api_key)
        openai_client.chat.completions = CompletionsWrapper(openai_client.chat.completions, logger)
        return openai_client
    except Exception as e:
        raise RuntimeError(f"Failed to wrap OpenAI client: {str(e)}") from e
