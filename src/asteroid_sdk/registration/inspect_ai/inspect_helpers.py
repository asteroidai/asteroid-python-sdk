from typing import Callable
from inspect_ai._util.registry import registry_find
from inspect_ai.solver import TaskState, solver, Solver
from inspect_ai.tool import ToolCall
from inspect_ai import Task
from inspect_ai.dataset import Sample
from asteroid_sdk.registration.helper import create_run, register_project, register_task, submit_run_status, get_run, register_tools_and_supervisors_from_registry
    
from uuid import UUID
import logging
import yaml
import fnmatch
import time
from inspect_ai.scorer import (
    Score,
    Scorer,
    Target,
    accuracy,
    scorer,
    stderr,
)
from typing import Optional
from asteroid_sdk.api.generated.asteroid_api_client.models import Status


def _extract_tool_approvers(approve_func: Callable) -> Callable:
    """
    Extract the tool approvers from the Inspect approve function.
    """
    # Get the closure cells of the approve function
    if approve_func.__closure__ is None:
        raise ValueError("No closure found")
    
    # We know tool_approvers is in the first closure cell
    tool_approvers = approve_func.__closure__[0].cell_contents
    
    # Verify we got a callable
    assert callable(tool_approvers), "Expected tool_approvers to be callable"
    # Verify it has the correct name
    assert tool_approvers.__name__ == 'tool_approvers', "Expected function named 'tool_approvers'"
    # Verify it has the expected return type annotation
    assert 'Generator' in str(tool_approvers.__annotations__.get('return', '')), "Expected tool_approvers to return a Generator"
    
    return tool_approvers

def _register_inspect_approvals(run_id: UUID, tool_to_approvers: dict):
    """
    Registers the approvals and tools for the run using the provided tool-to-approvers mapping.

    Args:
        run_id (UUID): The ID of the run.
        tool_to_approvers (dict): A dictionary mapping tools to their respective approvers.
    """
    # Retrieve the run and its supervision context
    from asteroid_sdk.supervision.config import supervision_config
    run = supervision_config.get_run_by_id(run_id)
    if run is None:
        raise Exception(f"Run with ID {run_id} not found in supervision config.")
    supervision_context = run.supervision_context

    # Iterate over the tool-to-approvers mapping
    for tool_func, approvers in tool_to_approvers.items():
        if not approvers:
            logging.warning(f"No approvers assigned to tool '{tool_func.__name__}'. Skipping registration.")
            continue

        # Add the tool and its approvers to the supervision context
        supervision_context.add_supervised_function(
            function_name=tool_func.__name__,
            supervision_functions=[approvers],
            ignored_attributes=[],
            function=tool_func
        )
        # Register the tool with the Asteroid API directly, it's not needed to register the tool with the supervision context?

    # Register the tools and supervisors with the Asteroid API
    register_tools_and_supervisors_from_registry(run_id=run_id)
   
   
def _register_inspect_approvals_from_approval_file(run_id: UUID, approval_file: str):
    """
    Reads the inspect approval YAML file and registers the approvals and tools for the run.
    
    Args:
        run_id (UUID): The ID of the run.
        approval_file (str): The path to the inspect approval YAML file.
    """
    from asteroid_sdk.supervision.config import supervision_config 
    
    # Read the approval file
    with open(approval_file, 'r') as file:
        approvals = yaml.safe_load(file)

    client = supervision_config.client
    if client is None:
        raise Exception("Client not set in the supervision config. Please set the client before calling this function.")

    run = supervision_config.get_run_by_id(run_id)
    if run is None:
        raise Exception(f"Run with ID {run_id} not found in supervision config.")
    supervision_context = run.supervision_context

    supervised_tools = {}
    # For each approver in the approval file
    for approver in approvals.get('approvers', []):
        # Get the tools pattern (may be a wildcard)
        tools_pattern = approver.get('tools', '*')

        # Find tools from the registry matching the pattern
        tools = registry_find(lambda x: x.type == "tool")

        # Filter tools based on tools_pattern
        matching_tools = []
        for tool in tools:
            tool_name = tool.__registry_info__.name.removeprefix('inspect_ai/')
            # tools_pattern may be a list of patterns
            if isinstance(tools_pattern, list):
                if any(fnmatch.fnmatch(tool_name, pattern) for pattern in tools_pattern):
                    matching_tools.append(tool)
            else:
                if fnmatch.fnmatch(tool_name, tools_pattern):
                    matching_tools.append(tool)

        # For each matching tool, add supervised function to the supervision context
        for tool in matching_tools:
            # The tool is a function decorated with @tool in inspect_ai
            func = tool

            # Get the supervisor function (approval function)
            approver_name = approver.get('name')
            approval_funcs = registry_find(lambda x: x.type == "approver" and x.name == approver_name)

            if approver_name =='auto':
                logging.info(f"Auto approval function '{approver_name}' found in the registry. Not registering approval function.")
                continue

            if not approval_funcs:
                logging.warning(f"Approval function '{approver_name}' not found in the registry.")
                continue

            approval_func = approval_funcs[0]

            # Configure the approval function with attributes from the approval file
            supervisor_attributes = {k: v for k, v in approver.items() if k not in ['name', 'tools']}
            approval_func_initialised = approval_func(**supervisor_attributes)

            if func not in supervised_tools:
                supervised_tools[func] = [approval_func_initialised]
            else:
                supervised_tools[func].append(approval_func_initialised)

    for tool_func in supervised_tools:
        supervision_functions = supervised_tools[tool_func]
        supervision_context.add_supervised_function(
            function_name=tool_func.__name__,
            supervision_functions=[supervision_functions],
            ignored_attributes=[],
            function=tool_func
        )

    # Register the tools and supervisors with the Asteroid API
    register_tools_and_supervisors_from_registry(run_id=run_id)


def register_inspect_samples_with_asteroid(tasks: Task, project_id: UUID, approval: str) -> list[Sample]:
    """
    Registers samples with Asteroid by creating a project, task, and run.
    Maps tools to their respective approvers and registers the approvals.
    """
    samples = []
    for idx, sample in enumerate(tasks.dataset.samples):
        # We need to assign an ID to each sample and register the task
        if sample.id is None:
            print(f"Each sample must have an ID, adding {idx} to the ID")
            sample.id = f"{idx}"
        task_id = register_task(project_id=project_id, task_name=sample.id)
        run_id = create_run(project_id=project_id, task_id=task_id, run_name=sample.id)
        _register_inspect_approvals_from_approval_file(run_id=run_id, approval_file=approval)
        samples.append(sample)
    return samples    


def get_sample_result(sample_id: str, timeout: Optional[int] = 86400) -> str:
    """
    Retrieves the result of a sample run by its sample ID.

    Args:
        sample_id (str): The ID of the sample.
        client (Union[AuthenticatedClient, Client]): The client to use for the request.
        timeout (Optional[int]): The maximum time to wait for the result. If None, wait indefinitely.

    Returns:
        str: The result of the run.
    """
    from asteroid_sdk.supervision.config import get_supervision_config
    supervision_config = get_supervision_config()
    local_run = supervision_config.get_run_by_name(sample_id)
    run_id = local_run.run_id

    i = 0
    while timeout is None or i < timeout:
        run = get_run(run_id)
        logging.debug(f"Getting result for run {run_id}")
        if run.result != '':
            logging.debug(f"Run {run_id} is {run.result}")
            return run.result
        time.sleep(2)
        i += 2

    logging.warning(f"Timeout reached for run {run_id} without a result.")
    return ''



def update_run_status_by_sample_id(sample_id: str, status: Status) -> None:
    """
    Updates the status of a run by its sample ID.s

    Args:
        sample_id (str): The ID of the sample.
        status (str): The new status to set.
        client (Union[AuthenticatedClient, Client]): The client to use for the request.
    """
    from asteroid_sdk.supervision.config import get_supervision_config
    supervision_config = get_supervision_config()
    local_run = supervision_config.get_run_by_name(sample_id)
    run_id = local_run.run_id
    submit_run_status(run_id, status)
    logging.debug(f"Updated run {run_id} status to {status}")


@solver
def register_inspect_samples_with_asteroid_solver(project_name: str) -> Solver:
    """
    Registers samples with Asteroid by creating a project, task, and run.
    Maps tools to their respective approvers and registers the approvals.

    Args:
        project_name (str): The name of the project to register.

    Returns:
        Solver: An asynchronous solver function that processes the task state.
    """
    async def solve(state: TaskState, generate) -> TaskState:
        # Register project, task, and run
        sample_id = str(state.sample_id)
        project_id = register_project(project_name=project_name)
        task_id = register_task(project_id=project_id, task_name=sample_id)
        run_id = create_run(project_id=project_id, task_id=task_id, run_name=sample_id)
        
        # Extract tool approvers
        from inspect_ai.approval._apply import _tool_approver
        approver = _tool_approver.get(None)
        tool_approvers = _extract_tool_approvers(approver)
        
        # Find all registered tools
        tools = registry_find(lambda x: x.type == "tool")
        
        # Map tools to their approvers
        tool_to_approvers = {}
        for tool in tools:
            # Create a dummy tool call for this tool
            dummy_call = ToolCall(
                id="dummy-id",
                function=tool.__qualname__,
                arguments={},
                type="function"
            )
            
            # Get all approvers for this tool
            matching_approvers = list(tool_approvers(dummy_call))
            tool_to_approvers[tool] = matching_approvers
        
        # Register the tool-approver mappings
        _register_inspect_approvals(run_id=run_id, tool_to_approvers=tool_to_approvers)
        
        return state
    return solve


@scorer(metrics=[accuracy(), stderr()])
def asteroid_web_ui_scorer(timeout: Optional[int] = 86400, wait_for_result: bool = True) -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        """
        A scorer function for evaluating the results of a task run in the Asteroid UI.

        Args:
            state (TaskState): The current state of the task being evaluated.
            target (Target): The target to evaluate against.

        Returns:
            Score: A Score object containing the evaluation result.
        """
        # Update the run status to 'completed' in the Asteroid system
        update_run_status_by_sample_id(str((state.sample_id)), status=Status.COMPLETED)
        
        # Retrieve the result of the run if waiting for the result is enabled
        if wait_for_result:
            logging.info(f"Waiting for human to score sample in the web UI {state.sample_id}")
            result = get_sample_result(str(state.sample_id), timeout=timeout)
        else:
            result = ''
        
        # Return a Score object with a value of 1 if the result is 'passed', otherwise 0
        return Score(
            value=1 if result == 'passed' else 0,
            answer="",
            explanation="",
        )
    return score
