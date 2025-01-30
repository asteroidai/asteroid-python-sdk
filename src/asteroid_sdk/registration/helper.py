"""
Handles helper functions for registration with asteroid.
"""

from datetime import datetime, timezone
import inspect
from typing import Any, Callable, Dict, Optional, List, Tuple
from uuid import UUID, uuid4
import time
import copy
import logging
import json

from asteroid_sdk.api.generated.asteroid_api_client.client import Client
from asteroid_sdk.api.generated.asteroid_api_client.models import CreateProjectBody, CreateTaskBody
from asteroid_sdk.api.generated.asteroid_api_client.models.chain_request import ChainRequest
from asteroid_sdk.api.generated.asteroid_api_client.models.create_run_body import CreateRunBody
from asteroid_sdk.api.generated.asteroid_api_client.models.create_run_tool_body import CreateRunToolBody
from asteroid_sdk.api.generated.asteroid_api_client.models.create_run_tool_body_attributes import CreateRunToolBodyAttributes
from asteroid_sdk.api.generated.asteroid_api_client.models.supervisor_attributes import SupervisorAttributes
from asteroid_sdk.api.generated.asteroid_api_client.models.supervisor_type import SupervisorType
from asteroid_sdk.api.generated.asteroid_api_client.types import UNSET
from asteroid_sdk.api.generated.asteroid_api_client.api.project.create_project import sync_detailed as create_project_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.task.create_task import sync_detailed as create_task_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.tool.create_run_tool import sync_detailed as create_run_tool_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.tool_call.get_tool_call_history import sync_detailed as get_tool_call_history_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.tool_call.get_tool_call_history import sync_detailed as get_tool_call_history_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.run.create_run import sync_detailed as create_run_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervisor.create_supervisor import sync_detailed as create_supervisor_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervisor.create_tool_supervisor_chains import sync_detailed as create_tool_supervisor_chains_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervision.create_supervision_request import sync_detailed as create_supervision_request_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervision.create_supervision_result import sync_detailed as create_supervision_result_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervision.get_supervision_request_status import sync_detailed as get_supervision_status_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervision.get_supervision_result import sync_detailed as get_supervision_result_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervisor.get_tool_supervisor_chains import sync_detailed as get_tool_supervisor_chains_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.run.update_run_status import sync_detailed as update_run_status_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.run.get_run import sync_detailed as get_run_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.run.get_run_messages import sync_detailed as get_run_messages_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.models.supervisor import Supervisor
from asteroid_sdk.api.generated.asteroid_api_client.models.supervisor_chain import SupervisorChain
from asteroid_sdk.api.generated.asteroid_api_client.models.supervision_request import SupervisionRequest
from asteroid_sdk.api.generated.asteroid_api_client.models.supervision_result import SupervisionResult
from asteroid_sdk.api.generated.asteroid_api_client.models.decision import Decision
from asteroid_sdk.api.generated.asteroid_api_client.models.status import Status
from asteroid_sdk.api.generated.asteroid_api_client.models.run import Run
from asteroid_sdk.api.generated.asteroid_api_client.models.create_run_body import CreateRunBody
from asteroid_sdk.api.generated.asteroid_api_client.models.asteroid_message import AsteroidMessage
from asteroid_sdk.supervision.config import SupervisionContext, get_supervision_config
from asteroid_sdk.supervision.helpers.model_provider_helper import ModelProviderHelper, AvailableProviderResponses
from asteroid_sdk.supervision.model.tool_call import ToolCall
from asteroid_sdk.api.generated.asteroid_api_client.models.tool import Tool
from asteroid_sdk.utils.utils import get_function_code
from asteroid_sdk.settings import settings
from asteroid_sdk.supervision.config import SupervisionDecision, SupervisionDecisionType, ModifiedData

class APIClientFactory:
    """Factory for creating API clients with proper authentication."""
    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """Get or create a singleton client instance."""
        if cls._instance is None:
            cls._instance = Client(
                base_url=settings.api_url,
                headers={"X-Asteroid-Api-Key": f"{settings.api_key}"}
            )
        return cls._instance

 # Define the 'chat_tool' function
MESSAGE_TOOL_NAME = "message_tool"
def message_tool(message: str) -> None:
    """
    A special tool to represent normal messages without tool calls for supervision purposes.
    """
    pass


def register_project(
    project_name: str,
    run_result_tags: Optional[List[str]] = None
) -> UUID:
    """
    Registers a new project using the asteroid API.
    """
    if run_result_tags is None:
        run_result_tags = ["passed", "failed"]

    client = APIClientFactory.get_client()
    project_data = CreateProjectBody(
        name=project_name,
        run_result_tags=run_result_tags
    )

    supervision_config = get_supervision_config()

    try:
        response = create_project_sync_detailed(
            client=client,
            body=project_data
        )

        if (
            response.status_code in [200, 201]
            and response.parsed is not None
        ):
            if isinstance(response.parsed, UUID):
                supervision_config.add_project(project_name, response.parsed)
                return response.parsed
            else:
                raise ValueError("Unexpected response type. Expected UUID.")
        else:
            raise ValueError(f"Failed to create project. Response: {response}")
    except Exception as e:
        raise ValueError(f"Failed to create project: {str(e)}")

def register_task(
    project_id: UUID,
    task_name: str,
    task_description: Optional[str] = None
) -> UUID:
    """
    Registers a new task under a project using the asteroid API.
    """
    if not project_id:
        raise ValueError("Project ID is required")
    if not task_name:
        raise ValueError("Task name is required")

    client = APIClientFactory.get_client()
    supervision_config = get_supervision_config()

    # Retrieve project by ID
    project = supervision_config.get_project_by_id(project_id)
    if not project:
        raise ValueError(
            f"Project with ID '{project_id}' not found in supervision config."
        )
    project_name = project.project_name

    try:
        response = create_task_sync_detailed(
            client=client,
            project_id=project_id,
            body=CreateTaskBody(
                name=task_name,
                description=task_description if task_description else UNSET
            )
        )

        if (
            response.status_code in [200, 201]
            and response.parsed is not None
        ):
            if isinstance(response.parsed, UUID):
                task_id = response.parsed
                supervision_config.add_task(project_name, task_name, task_id)

                return response.parsed
            else:
                raise ValueError("Unexpected response type. Expected UUID.")
        else:
            raise ValueError(f"Failed to create task. Response: {response}")
    except Exception as e:
        raise ValueError(f"Failed to create task: {str(e)}")

def create_run(
    project_id: UUID,
    task_id: UUID,
    run_name: Optional[str] = None,
    run_id: Optional[UUID] = None
) -> UUID:
    """
    Creates a new run for a task under a project using the asteroid API.
    """

    if run_name is None:
        run_name = f"run-{uuid4().hex[:8]}"

    client = APIClientFactory.get_client()

    supervision_config = get_supervision_config()

    # Retrieve project and task by IDs
    project = supervision_config.get_project_by_id(project_id)
    if not project:
        raise ValueError(f"Project with ID '{project_id}' not found in supervision config.")
    project_name = project.project_name

    task = supervision_config.get_task_by_id(task_id)
    if not task:
        raise ValueError(f"Task with ID '{task_id}' not found in supervision config.")
    if task.task_name not in project.tasks:
        raise ValueError(f"Task '{task.task_name}' does not belong to project '{project_name}'.")
    task_name = task.task_name

    try:
        response = create_run_sync_detailed(
            client=client,
            task_id=task_id,
            body=CreateRunBody(
                name=run_name if run_name else UNSET,
                run_id=run_id if run_id else UNSET
            )
        )

        if (
            response.status_code in [200, 201]
            and response.parsed is not None
        ):
            if isinstance(response.parsed, UUID):
                run_id = response.parsed
                # Add the run to the task
                supervision_config.add_run(
                    project_name=project_name,
                    task_name=task_name,
                    run_name=run_name,
                    run_id=run_id
                )
                return run_id
            else:
                raise ValueError("Unexpected response type. Expected UUID.")
        else:
            raise ValueError(f"Failed to create run. Response: {response}")
    except Exception as e:
        raise ValueError(f"Failed to create run: {str(e)}")


def get_run(run_id: UUID) -> Run:
    """
    Retrieves a run using the Sentinel API.

    Args:
        run_id (UUID): The ID of the run to retrieve.

    Returns:
        Union[ErrorResponse, Run]: The retrieved run or an error response.
    """
    
    client = APIClientFactory.get_client()
    try:
        response = get_run_sync_detailed(run_id=run_id, client=client)
        if not isinstance(response.parsed, Run):
            raise Exception(f"Error retrieving run: {response.parsed}")
        return response.parsed
    except Exception as e:
        raise Exception(f"Error retrieving run: {e}")

def register_supervisor_chains(
    tool_id: UUID,
    supervisor_chain_ids: List[List[UUID]],
):
    """
    Associates supervisor chains with a given tool.

    Args:
        tool_id (UUID): The UUID of the tool to associate supervisors with.
        supervisor_chain_ids (List[List[UUID]]): A list of lists of supervisor IDs, where each inner list represents a supervisor chain.
    """
    client = APIClientFactory.get_client()

    # Associate the supervisor chains with the tool
    if supervisor_chain_ids:
        chain_requests = [ChainRequest(supervisor_ids=supervisor_ids) for supervisor_ids in supervisor_chain_ids]
        association_response = create_tool_supervisor_chains_sync_detailed(
            tool_id=tool_id,
            client=client,
            body=chain_requests
        )
        if association_response.status_code in [200, 201]:
            logging.info(f"Supervisors assigned to tool with ID {tool_id}")
        else:
            raise Exception(f"Failed to assign supervisors to tool with ID {tool_id}. Response: {association_response}")
    else:
        logging.info(f"No supervisors to assign to tool with ID {tool_id}")


def register_tool(
    run_id: UUID,
    tool: Callable | Dict[str, Any],
    ignored_attributes: Optional[List[str]] = None,
) -> Tool:
    """
    Registers a tool with the API. The tool can be provided as a function or a dictionary description.

    Args:
        run_id (UUID): The ID of the run to associate the tool with.
        tool (Callable | Dict[str, Any]): The tool to register, either as a function or a dictionary.
        ignored_attributes (Optional[List[str]]): Attributes to ignore during registration.

    Returns:
        Tool: The registered tool object.
    """
    client = APIClientFactory.get_client()

    # Determine tool details based on its type
    if isinstance(tool, dict):
        tool_name = tool['name']
        attributes = CreateRunToolBodyAttributes.from_dict(
            src_dict=tool.get('input_schema', {}).get('properties', {})
        )
        func_code = tool.get('code', '')
        description = tool.get('description', '')
    else:
        tool_name = tool.__name__
        func_signature = inspect.signature(tool)
        func_arguments = {
            param.name: str(param.annotation) if param.annotation is not param.empty else 'Any'
            for param in func_signature.parameters.values()
        }
        attributes = CreateRunToolBodyAttributes.from_dict(src_dict=func_arguments)
        func_code = get_function_code(tool)
        description = tool.__doc__ if tool.__doc__ else tool.__qualname__

    # Prepare tool data for registration
    tool_data = CreateRunToolBody(
        name=tool_name,
        description=description,
        attributes=attributes,
        ignored_attributes=ignored_attributes or [],
        code=func_code
    )

    # Register the tool with the API
    tool_response = create_run_tool_sync_detailed(
        run_id=run_id,
        client=client,
        body=tool_data,
    )
    if not (tool_response.status_code in [200, 201] and tool_response.parsed):
        raise Exception(f"Failed to register tool '{tool_name}'. Response: {tool_response}")

    # Update the supervision context with the new tool ID
    tool_api: Tool = tool_response.parsed
    logging.info(f"Tool '{tool_name}' registered in the API")
    return tool_api

def register_tools_and_supervisors_from_registry(
    run_id: UUID,
    message_supervisors: Optional[List[Callable]] = None
):
    """
    Registers tools and their associated supervisors with the backend API.

    Args:
        run_id (UUID): The ID of the run to register tools and supervisors for.
        message_supervisors (Optional[List[Callable]]): Supervisors for message tools, if any.
    """
    supervision_config = get_supervision_config()

    # Retrieve the run from the supervision configuration
    run = supervision_config.get_run_by_id(run_id)
    if run is None:
        raise Exception(f"Run with ID {run_id} not found in supervision config.")
    supervision_context = run.supervision_context

    supervised_functions = supervision_context.supervised_functions_registry

    # Register message supervisors if provided
    if message_supervisors is not None:
        supervision_context.add_supervised_function(
            function_name=MESSAGE_TOOL_NAME,
            supervision_functions=[message_supervisors],
            function=message_tool
        )
        supervised_functions[MESSAGE_TOOL_NAME] = supervision_context.supervised_functions_registry[MESSAGE_TOOL_NAME]

    # Register each tool and its supervisors
    for tool_name, data in supervised_functions.items():
        supervision_functions = data['supervision_functions']
        ignored_attributes = data['ignored_attributes']
        func = data['function']

        # Add the run_id to the supervised function
        supervision_context.add_run_id_to_supervised_function(tool_name, run_id)

        # Register the tool
        tool = register_tool(run_id=run_id, tool=func, ignored_attributes=ignored_attributes)
        tool_id = tool.id
        
        # Add the tool_id to the supervision context
        supervision_context.update_tool_id(function_name=tool_name, tool_id=tool_id)

        # Create and register supervisor chains
        supervisor_chain_ids = create_supervisor_chain(run_id=run_id, supervision_functions=supervision_functions)
        if tool_name != MESSAGE_TOOL_NAME:
            if tool_id is UNSET:
                raise ValueError(f"Tool ID is UNSET. Tool name: {tool_name}")
            register_supervisor_chains(tool_id=tool_id, supervisor_chain_ids=supervisor_chain_ids)

def create_supervisor_chain(run_id: UUID, supervision_functions: Optional[List[List[Callable]]] = None) -> List[List[UUID]]:
    """
    Creates and registers supervisor chains from a list of supervisor functions.

    Args:
        run_id (UUID): The ID of the run to associate the supervisor chains with.
        supervision_functions (Optional[List[List[Callable]]]): A list of lists of supervisor functions.

    Returns:
        List[List[UUID]]: A list of lists of supervisor IDs, representing the supervisor chains.
    """
    supervision_config = get_supervision_config()
    project_id = list(supervision_config.projects.values())[0].project_id
    supervision_context = supervision_config.get_run_by_id(run_id).supervision_context

    supervisor_chain_ids: List[List[UUID]] = []

    # Handle case with no supervision functions
    if not supervision_functions:
        supervisor_chain_ids.append([])
        from asteroid_sdk.supervision.base_supervisors import auto_approve_supervisor
        supervisor_func = auto_approve_supervisor
        supervisor_id = register_supervisor(
            supervisor_name=getattr(supervisor_func, '__name__', 'auto_approve_supervisor'),
            supervisor_description=getattr(supervisor_func, '__doc__', 'Automatically approves any input.'),
            supervisor_type=SupervisorType.NO_SUPERVISOR,
            supervisor_code=get_function_code(supervisor_func),
            supervisor_attributes=getattr(supervisor_func, 'supervisor_attributes', {}),
            project_id=project_id,
            supervisor_func=supervisor_func,
            supervision_context=supervision_context
        )
        supervisor_chain_ids[0] = [supervisor_id]
    else:
        # Register each supervisor function in the chain
        for idx, supervisor_func_list in enumerate(supervision_functions):
            supervisor_chain_ids.append([])
            for supervisor_func in supervisor_func_list:
                supervisor_id = register_supervisor(
                    supervisor_name=getattr(supervisor_func, '__name__', 'supervisor_name'),
                    supervisor_description=getattr(supervisor_func, '__doc__', 'supervisor_description'),
                    supervisor_type=SupervisorType.HUMAN_SUPERVISOR if getattr(supervisor_func, '__name__', '') in ['human_supervisor', 'human_approver'] else SupervisorType.CLIENT_SUPERVISOR,
                    supervisor_code=get_function_code(supervisor_func),
                    supervisor_attributes=getattr(supervisor_func, 'supervisor_attributes', {}),
                    project_id=project_id,
                    supervisor_func=supervisor_func,
                    supervision_context=supervision_context
                )
                supervisor_chain_ids[idx].append(supervisor_id)
    return supervisor_chain_ids

def register_supervisor(supervisor_name: str,
                        supervisor_description: str,
                        supervisor_type: SupervisorType,
                        supervisor_code: str,
                        supervisor_attributes: Dict[str, Any],
                        project_id: UUID, 
                        supervisor_func: Callable,
                        supervision_context: SupervisionContext) -> UUID:
    """
    Registers a single supervisor with the API and returns its ID.

    Args:
        supervisor_name (str): The name of the supervisor.
        supervisor_description (str): A description of the supervisor's function.
        supervisor_type (SupervisorType): The type of supervisor (e.g., HUMAN_SUPERVISOR).
        supervisor_code (str): The code associated with the supervisor.
        supervisor_attributes (Dict[str, Any]): Attributes of the supervisor.
        project_id (UUID): The ID of the project to associate the supervisor with.
        supervisor_func (Callable): The supervisor function.
        supervision_context (SupervisionContext): The context for supervision.

    Returns:
        UUID: The ID of the registered supervisor.
    """
    client = APIClientFactory.get_client()

    # Prepare supervisor data for registration
    supervisor_data = Supervisor(
        name=supervisor_name,
        description=supervisor_description,
        created_at=datetime.now(timezone.utc),
        type=supervisor_type,
        code=supervisor_code,
        attributes=SupervisorAttributes.from_dict(src_dict=supervisor_attributes)
    )

    # Register the supervisor with the API
    supervisor_response = create_supervisor_sync_detailed(
        project_id=project_id,
        client=client,
        body=supervisor_data
    )

    if (
        supervisor_response.status_code in [200, 201] and
        supervisor_response.parsed is not None
    ):
        supervisor_id = supervisor_response.parsed

        if isinstance(supervisor_id, UUID):
            supervision_context.add_local_supervisor(supervisor_id, supervisor_func)
        else:
            raise ValueError("Invalid supervisor_id: Expected UUID")

        logging.info(f"Supervisor '{supervisor_name}' registered with ID: {supervisor_id}")
        return supervisor_id
    else:
        raise Exception(f"Failed to register supervisor '{supervisor_name}'. Response: {supervisor_response}")

def get_supervisor_chains_for_tool(tool_id: UUID) -> List[SupervisorChain]:
    """
    Retrieve the supervisor chains for a specific tool.
    """

    client = APIClientFactory.get_client()

    supervisors_list: List[SupervisorChain] = []
    try:
        supervisors_response = get_tool_supervisor_chains_sync_detailed(
            tool_id=tool_id,
            client=client,
        )
        if supervisors_response is not None and supervisors_response.parsed is not None:
            supervisors_list = supervisors_response.parsed  # List[SupervisorChain]
            logging.info(f"Retrieved {len(supervisors_list)} supervisor chains from the API.")
        else:
            logging.info("No supervisors found for this tool and run.")
    except Exception as e:
        logging.error(f"Error retrieving supervisors: {e}")

    return supervisors_list


def send_supervision_request(tool_call_id: UUID, supervisor_id: UUID, supervisor_chain_id: UUID, position_in_chain: int) -> UUID:
    client = APIClientFactory.get_client()

    supervision_request = SupervisionRequest(
        position_in_chain=position_in_chain,
        supervisor_id=supervisor_id
    )
    logging.info(f"Sending supervision request for tool call ID: {tool_call_id}, supervisor ID: {supervisor_id}, supervisor chain ID: {supervisor_chain_id}, position in chain: {position_in_chain}")
    try:
        supervision_request_response = create_supervision_request_sync_detailed(
            client=client,
            tool_call_id=tool_call_id,
            chain_id=supervisor_chain_id,
            supervisor_id=supervisor_id,
            body=supervision_request
        )
        if (
            supervision_request_response.status_code in [200, 201] and
            supervision_request_response.parsed is not None
        ):
            supervision_request_id = supervision_request_response.parsed
            logging.info(f"Created supervision request with ID: {supervision_request_id}")
            if isinstance(supervision_request_id, UUID):
                return supervision_request_id
            else:
                raise ValueError("Invalid supervision request ID received.")
        else:
            raise Exception(f"Failed to create supervision request. Response: {supervision_request_response}")
    except Exception as e:
        logging.error(f"Error creating supervision request: {e}")
        raise


def send_supervision_result(
    supervision_request_id: UUID,
    decision: SupervisionDecision,
    tool_call_id: UUID,
):
    """
    Send the supervision result to the API.
    """
    client = APIClientFactory.get_client()
    # Map SupervisionDecisionType to Decision enum
    decision_mapping = {
        SupervisionDecisionType.APPROVE: Decision.APPROVE,
        SupervisionDecisionType.REJECT: Decision.REJECT,
        SupervisionDecisionType.MODIFY: Decision.MODIFY,
        SupervisionDecisionType.ESCALATE: Decision.ESCALATE,
        SupervisionDecisionType.TERMINATE: Decision.TERMINATE,
    }

    api_decision = decision_mapping.get(decision.decision)
    if not api_decision:
        raise ValueError(f"Unsupported decision type: {decision.decision}")

    # if decision.modified is not None:
        # TODO: Handling modified decisions might be needed here

    # Create the SupervisionResult object
    supervision_result = SupervisionResult(
        supervision_request_id=supervision_request_id,
        created_at=datetime.now(timezone.utc),
        decision=api_decision,
        reasoning=decision.explanation or "",
        toolcall_id=tool_call_id
    )
    # Send the supervision result to the API
    try:
        response = create_supervision_result_sync_detailed(
            supervision_request_id=supervision_request_id,
            client=client,
            body=supervision_result
        )
        if response.status_code in [200, 201]:
            logging.info(f"Successfully submitted supervision result for supervision request ID: {supervision_request_id}")
        else:
            raise Exception(f"Failed to submit supervision result. Response: {response}")
    except Exception as e:
        logging.error(f"Error submitting supervision result: {e}")
        raise



def wait_for_human_decision(supervision_request_id: UUID, timeout: int = 86400) -> Status:
    start_time = time.time()

    client = APIClientFactory.get_client()
    while True:
        try:
            response = get_supervision_status_sync_detailed(
                client=client,
                supervision_request_id=supervision_request_id
            )
            if response.status_code == 200 and response.parsed is not None:
                status = response.parsed.status
                if isinstance(status, Status) and status in [Status.FAILED, Status.COMPLETED, Status.TIMEOUT]:
                    # Map status to SupervisionDecision
                    logging.debug(f"Polling for human decision completed. Status: {status}")
                    return status
                else:
                    logging.debug("Waiting for human supervisor decision...")
            else:
                logging.warning(f"Unexpected response while polling for supervision status: {response}")
        except Exception as e:
            logging.error(f"Error while polling for supervision status: {e}")

        if time.time() - start_time > timeout:
            logging.warning(f"Timed out waiting for human supervision decision. Timeout: {timeout} seconds")
            return Status.TIMEOUT

        time.sleep(5)  # Wait for 5 seconds before polling again




def get_human_supervision_decision_api(
    supervision_request_id: UUID,
    timeout: int = 86400) -> SupervisionDecision:
    """Get the supervision decision from the backend API."""

    client = APIClientFactory.get_client()
    supervision_status = wait_for_human_decision(supervision_request_id=supervision_request_id, timeout=timeout)

    # get supervision results
    if supervision_status == 'completed':
        # Get the decision from the API
        response = get_supervision_result_sync_detailed(
            client=client,
            supervision_request_id=supervision_request_id
        )
        if response.status_code == 200 and response.parsed:
            supervision_result = response.parsed
            return map_result_to_decision(supervision_result)
        else:
            return SupervisionDecision(
                decision=SupervisionDecisionType.ESCALATE,
                explanation=f"Failed to retrieve supervision results. Response: {response}"
            )
    elif supervision_status == 'failed':
        return SupervisionDecision(decision=SupervisionDecisionType.ESCALATE,
                                   explanation="The human supervisor failed to provide a decision.")
    elif supervision_status == 'assigned':
        return SupervisionDecision(decision=SupervisionDecisionType.ESCALATE,
                                   explanation="The human supervisor is currently busy and has not yet provided a decision.")
    elif supervision_status == 'timeout':
        return SupervisionDecision(decision=SupervisionDecisionType.ESCALATE,
                                   explanation="Timeout waiting for human supervisor decision.")
    elif supervision_status == 'pending':
        return SupervisionDecision(decision=SupervisionDecisionType.ESCALATE,
                                   explanation="The human supervisor has not yet provided a decision.")

    # Default return statement in case no conditions are met
    return SupervisionDecision(
        decision=SupervisionDecisionType.ESCALATE,
        explanation="Unexpected supervision status."
    )

def map_result_to_decision(result: SupervisionResult) -> SupervisionDecision:
    decision_map = {
        'approve': SupervisionDecisionType.APPROVE,
        'reject': SupervisionDecisionType.REJECT,
        'modify': SupervisionDecisionType.MODIFY,
        'escalate': SupervisionDecisionType.ESCALATE,
        'terminate': SupervisionDecisionType.TERMINATE
    }
    decision_type = decision_map.get(result.decision.value.lower(), SupervisionDecisionType.ESCALATE)
    modified_output = None
    if decision_type == SupervisionDecisionType.MODIFY:  
        client = APIClientFactory.get_client()
        try:
            assert result.toolcall_id is not UNSET
            tool_call_history = get_tool_call_history_sync_detailed(tool_call_id=result.toolcall_id, client=client)
            if tool_call_history.status_code == 200 and tool_call_history.parsed is not None:
                tool_call_history = tool_call_history.parsed
                tool_name = tool_call_history[-1].name
                kwargs = json.loads(tool_call_history[-1].arguments)
                modified_output = ModifiedData(
                    tool_name=tool_name,
                    tool_kwargs=kwargs,
                )
        except Exception as e:
            logging.error(f"Error getting tool call history: {e}")
        
        client = APIClientFactory.get_client()
        try:
            assert result.toolcall_id is not UNSET
            tool_call_history = get_tool_call_history_sync_detailed(tool_call_id=result.toolcall_id, client=client)
            if tool_call_history.status_code == 200 and tool_call_history.parsed is not None:
                tool_call_history = tool_call_history.parsed
                tool_name = tool_call_history[-1].name
                kwargs = json.loads(tool_call_history[-1].arguments)
                modified_output = ModifiedData(
                    tool_name=tool_name,
                    tool_kwargs=kwargs,
                )
        except Exception as e:
            logging.error(f"Error getting tool call history: {e}")
        
    return SupervisionDecision(
        decision=decision_type,
        explanation=result.reasoning,
        modified=modified_output
    )

def submit_run_status(run_id: UUID, status: Status):
    try:
        client = APIClientFactory.get_client()
        response = update_run_status_sync_detailed(
            client=client,
            run_id=run_id,
            body=status
        )
        if response.status_code in [204]:
            logging.info(f"Successfully submitted run status for run ID: {run_id}")
        else:
            raise Exception(f"Failed to submit run status. Response: {response}")
    except Exception as e:
        logging.error(f"Error submitting run status: {e}, Response: {response}")
        raise


def generate_fake_message_tool_call(
        response: AvailableProviderResponses, # Could maybe change this to be a union of openai + anthropic types?
        supervision_context: SupervisionContext,
        model_provider_helper: ModelProviderHelper,
        message_supervisors: Optional[List[List[Callable]]] = None,
) -> Tuple[AvailableProviderResponses, List[ToolCall]]: # Could maybe change this to be a union of openai + anthropic types?
    """
    Generate a fake chat tool call when no tool calls are present in the response.

    :param client: The API client used for making API calls.
    :param response: The original ChatCompletion response from the OpenAI API.
    :param supervision_context: The supervision context associated with the run.
    :param model_provider_helper: The model provider helper used to generate fake tool calls.
    :param message_supervisors: A list of message supervisor callables. If provided, the supervisor chains will be registered with the Asteroid API.
    :return: A tuple containing the modified response and the list of tool calls.
    """
    logging.info("No tool calls found in response, but message supervisors provided, executing message supervisors")

    modified_response = copy.deepcopy(response)
    chat_tool_call = model_provider_helper.generate_fake_tool_call(modified_response)

    model_provider_helper.upsert_tool_call(modified_response, chat_tool_call.language_model_tool_call)

    if message_supervisors:
        # Retrieve supervisor IDs based on the provided chat supervisors
        message_supervisor_ids = [
            [supervision_context.get_supervisor_id_by_name(message_supervisor.__name__) for message_supervisor in message_supervisors_chain]
            for message_supervisors_chain in message_supervisors
        ]

        # Get the tool ID for the chat tool
        tool_entry = supervision_context.get_supervised_function_entry(MESSAGE_TOOL_NAME)
        if tool_entry is None:
            raise ValueError(f"Tool entry for {MESSAGE_TOOL_NAME} not found")
        tool_id = tool_entry.get("tool_id")


        # Register the supervisor chains with the Asteroid API client
        register_supervisor_chains(
            tool_id=tool_id,
            supervisor_chain_ids=message_supervisor_ids
        )

    return modified_response, [chat_tool_call]


def get_run_messages(run_id: UUID, index: int) -> List[AsteroidMessage]:
    client = APIClientFactory.get_client()
    try:
        response = get_run_messages_sync_detailed(
            client=client,
            run_id=run_id,
            index=index
        )
        if response.status_code == 200 and response.parsed is not None:
            return response.parsed
        else:
            raise Exception(f"Failed to get run messages. Response: {response}")
    except Exception as e:
        logging.error(f"Error getting run messages: {e}")
        raise
