"""
Wrapper for the OpenAI client to intercept requests and responses.
"""

import json
from typing import Any, Callable, List, Optional, Dict
from uuid import UUID
from openai import OpenAIError
from sentinel.api.logger import APILogger, SentinelLoggingError
from sentinel.settings import settings
from sentinel.registration.helper import create_run, register_project, register_task, APIClientFactory, register_tools_and_supervisors

class CompletionsWrapper:
    """Wraps chat completions with logging capabilities"""
    def __init__(
        self, 
        completions: Any, 
        logger: APILogger, 
        run_id: UUID,
        execution_mode: str = "supervision"
    ):
        self._completions = completions
        self.logger = logger
        self.run_id = run_id
        self.execution_mode = execution_mode
    
    def create(self, *args, **kwargs) -> Any:
        # Log the entire request payload
        try:
            self.logger.log_request(kwargs, self.run_id)
        except SentinelLoggingError as e:
            print(f"Warning: Failed to log request: {str(e)}")
        
        try:
            # Make API call
            response = self._completions.create(*args, **kwargs)

            if self.execution_mode == "supervision":
                # SYNC LOGGING + SUPERVISION
                try:
                    
                    new_response = self.logger.log_response(response, request_kwargs=kwargs, run_id=self.run_id, execution_mode=self.execution_mode, completions=self._completions, args=args)
                    if new_response is not None:
                        print(f"New response: {new_response}")
                        return new_response
                except Exception as e:
                    print(f"Warning: Failed to log response: {str(e)}")
            else:
                # ASYNC LOGGING + SUPERVISION
                print("Async logging + supervision not implemented yet")
                pass #TODO: Implement async logging
                
            return response
            
        except OpenAIError as e:
            try:
                raise e
            except SentinelLoggingError:
                raise e

def sentinel_openai_client(
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
        logger = APILogger(settings.api_key)
        openai_client.chat.completions = CompletionsWrapper(
            openai_client.chat.completions, 
            logger,
            run_id,
            execution_mode
        )
        return openai_client
    except Exception as e:
        raise RuntimeError(f"Failed to wrap OpenAI client: {str(e)}") from e

def sentinel_init(
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

def sentinel_end(run_id: UUID) -> None:
    """
    Stops supervision for a run.
    """
    pass
