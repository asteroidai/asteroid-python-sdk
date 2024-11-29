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
            self.logger.log_request(kwargs, conversation_id)
        except SentinelLoggingError as e:
            print(f"Warning: Failed to log request: {str(e)}")
        
        try:
            # Make API call
            response = self._completions.create(*args, **kwargs)
            
            # Log the entire response
            try:
                response_data = response if isinstance(response, dict) else response.dict()
                self.logger.log_response(response_data, conversation_id)
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

def wrap_client(client: Any, project_name: str = "My Project", task_name: str = "My Agent") -> Any:
    """
    Wraps an OpenAI client instance with logging capabilities and registers supervisors.
    """
    if not client:
        raise ValueError("Client is required")
    
    if not hasattr(client, 'chat'):
        raise ValueError("Invalid OpenAI client: missing chat attribute")
        
    try:
        # Register project if no project_id exists
        if not settings.project_id:
            project_id = register_project(project_name)
            print(f"Registered new project '{project_name}' with ID: {project_id}")
        
        # Register all supervised functions and their supervisors
        supervised_functions = registry.get_supervised_functions()
        for func_name, func_info in supervised_functions.items():
            print(f"Registering supervised function: {func_name}")
            # Here you would call your API to register the function and its supervisors
            # Using the APIClientFactory to get the client
            # TODO: Implement the API calls to register tools and supervisors

        
        logger = APILogger(settings.api_key)
        client.chat.completions = CompletionsWrapper(client.chat.completions, logger)
        return client
    except Exception as e:
        raise RuntimeError(f"Failed to wrap OpenAI client: {str(e)}") from e
