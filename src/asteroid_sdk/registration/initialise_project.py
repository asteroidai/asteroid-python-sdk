from typing import Any, Callable, List, Optional, Dict
from uuid import UUID

from asteroid_sdk import settings
from asteroid_sdk.api.generated.asteroid_api_client.client import Client
from asteroid_sdk.api.generated.asteroid_api_client.models import Status
from asteroid_sdk.registration.helper import (
    APIClientFactory, create_run, register_project, register_task, register_tools_and_supervisors_from_registry, submit_run_status,
    register_tool, create_supervisor_chain, register_supervisor_chains
)
from asteroid_sdk.supervision.config import ExecutionMode, RejectionPolicy, get_supervision_config
from asteroid_sdk.api.generated.asteroid_api_client.types import UNSET

import logging

def asteroid_init(
        project_name: str = "My Project",
        task_name: str = "My Agent",
        run_name: str = "My Run",
        execution_settings: Dict[str, Any] = {},
        message_supervisors: Optional[List[Callable]] = None,
        run_id: Optional[UUID] = None,
        api_key: Optional[str] = None
) -> UUID:
    """
    Initializes supervision for a project, task, and run.

    Args:
        project_name: Name of the project
        task_name: Name of the task
        run_name: Name of the run
        execution_settings: Dictionary of execution settings
        message_supervisors: Optional list of message supervisor functions
        run_id: Optional UUID for the run
        api_key: Optional API key to override the default from environment variables
    """
    if api_key:
        # If the user provided an API key, override the client in settings
        logging.info("Overriding API key env variable with provided API key")
        APIClientFactory._instance = Client(
            base_url=settings.api_url,
            headers={"X-Asteroid-Api-Key": api_key}
        )

    project_id = register_project(project_name)
    logging.info(f"Registered new project '{project_name}' with ID: {project_id}")
    task_id = register_task(project_id, task_name)
    logging.info(f"Registered new task '{task_name}' with ID: {task_id}")
    run_id = create_run(project_id, task_id, run_name, run_id)
    logging.info(f"Registered new run with ID: {run_id}")

    supervision_config = get_supervision_config()
    supervision_config.set_execution_settings(execution_settings)

    register_tools_and_supervisors_from_registry(run_id=run_id, 
                                               message_supervisors=message_supervisors)

    return run_id

def register_tool_with_supervisors(
    tool: Dict[str, Any] | Callable,
    supervision_functions: Optional[List[List[Callable]]] = None,
    run_id: Optional[UUID] = None,
    ignored_attributes: Optional[List[str]] = None
) -> None:
    """
    Registers a tool using a JSON description.

    Args:
        tool (Dict[str, Any] | Callable): Tool description or function to register.
        supervision_functions (Optional[List[List[Callable]]]): Supervision functions to use.
        run_id (Optional[UUID]): Run ID for immediate registration.
        ignored_attributes (Optional[List[str]]): Attributes to ignore in supervision.
    """
    
    if run_id is not None:
        # Register the tool and supervisors immediately
        tool_api = register_tool(
            run_id=run_id, 
            tool=tool,
            ignored_attributes=ignored_attributes
        )
    
        supervisor_chain_ids = create_supervisor_chain(
            run_id=run_id, 
            supervision_functions=supervision_functions
        )
        
        if tool_api.id is UNSET:
            raise ValueError(f"Tool ID is UNSET. Tool name: {tool_api.name}")
        
        register_supervisor_chains(
            tool_id=tool_api.id, 
            supervisor_chain_ids=supervisor_chain_ids
        )
        
        # Register the tool and supervisors in the supervision context
        supervision_config = get_supervision_config()

        # Add the tool and supervisors to the supervision context as well
        run = supervision_config.get_run_by_id(run_id)
        if run is None:
            raise Exception(f"Run with ID {run_id} not found in supervision config.")
        
        supervision_context = run.supervision_context
        supervision_context.add_supervised_function(
            function_name=tool_api.name,
            supervision_functions=supervision_functions,
            ignored_attributes=ignored_attributes,
            function=tool,
            tool_id=tool_api.id
        )
        
        logging.info(
            f"Registered tool '{tool_api.name}' with ID {tool_api.id} and {len(supervisor_chain_ids)} supervisor chains."
        )
    else:
        # Store in pending tool descriptions for later registration 
        supervision_config = get_supervision_config()
        supervision_config.register_pending_supervised_function(
            tool=tool,
            supervision_functions=supervision_functions,
            ignored_attributes=ignored_attributes,
        )


def asteroid_end(run_id: UUID) -> None:
    """
    Stops supervision for a run.
    """
    submit_run_status(run_id, Status.COMPLETED)
