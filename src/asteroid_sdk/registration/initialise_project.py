from typing import Any, Callable, List, Optional, Dict
from uuid import UUID

from asteroid_sdk.api.generated.asteroid_api_client.models import Status
from asteroid_sdk.registration.helper import (
    create_run, register_project, register_task, register_tools_and_supervisors_from_registry, submit_run_status,
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
        message_supervisors: Optional[List[Callable]] = None
) -> UUID:
    """
    Initializes supervision for a project, task, and run.
    """
    check_config_validity(execution_settings)

    project_id = register_project(project_name)
    print(f"Registered new project '{project_name}' with ID: {project_id}")
    task_id = register_task(project_id, task_name)
    print(f"Registered new task '{task_name}' with ID: {task_id}")
    run_id = create_run(project_id, task_id, run_name)
    print(f"Registered new run with ID: {run_id}")

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

def check_config_validity(execution_settings):
    if (execution_settings.get("execution_mode") == ExecutionMode.MONITORING
            and execution_settings.get("rejection_policy") == RejectionPolicy.RESAMPLE_WITH_FEEDBACK):
        raise ValueError("Monitoring mode does not support resample_with_feedback rejection policy")
