from typing import Any, Callable, List, Optional, Dict
from uuid import UUID

from asteroid_sdk.api.generated.asteroid_api_client.models import Status
from asteroid_sdk.registration.helper import (
    create_run, register_project, register_task, register_tools_and_supervisors, submit_run_status
)
from asteroid_sdk.supervision.config import ExecutionMode, RejectionPolicy


def asteroid_init(
        project_name: str = "My Project",
        task_name: str = "My Agent",
        run_name: str = "My Run",
        tools: Optional[List[Callable]] = None,
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

    register_tools_and_supervisors(run_id, tools, execution_settings, message_supervisors)

    return run_id

def asteroid_end(run_id: UUID) -> None:
    """
    Stops supervision for a run.
    """
    submit_run_status(run_id, Status.COMPLETED)

def check_config_validity(execution_settings):
    if (execution_settings.get("execution_mode") == ExecutionMode.MONITORING
            and execution_settings.get("rejection_policy") == RejectionPolicy.RESAMPLE_WITH_FEEDBACK):
        raise ValueError("Monitoring mode does not support resample_with_feedback rejection policy")
