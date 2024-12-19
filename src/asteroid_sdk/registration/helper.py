"""
Handles helper functions for registration with asteroid.
"""

from datetime import datetime, timezone
import inspect
from typing import Any, Callable, Dict, Optional, List, Tuple
from uuid import UUID, uuid4
import time
import copy
import json
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function

from asteroid_sdk.api.generated.asteroid_api_client.client import Client
from asteroid_sdk.api.generated.asteroid_api_client.models import CreateProjectBody, CreateTaskBody
from asteroid_sdk.api.generated.asteroid_api_client.models.chain_request import ChainRequest
from asteroid_sdk.api.generated.asteroid_api_client.models.create_run_tool_body import CreateRunToolBody
from asteroid_sdk.api.generated.asteroid_api_client.models.create_run_tool_body_attributes import CreateRunToolBodyAttributes
from asteroid_sdk.api.generated.asteroid_api_client.models.supervisor_attributes import SupervisorAttributes
from asteroid_sdk.api.generated.asteroid_api_client.models.supervisor_type import SupervisorType
from asteroid_sdk.api.generated.asteroid_api_client.types import UNSET
from asteroid_sdk.api.generated.asteroid_api_client.api.project.create_project import sync_detailed as create_project_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.task.create_task import sync_detailed as create_task_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.tool.create_run_tool import sync_detailed as create_run_tool_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.run.create_run import sync_detailed as create_run_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervisor.create_supervisor import sync_detailed as create_supervisor_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervisor.create_tool_supervisor_chains import sync_detailed as create_tool_supervisor_chains_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervision.create_supervision_request import sync_detailed as create_supervision_request_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervision.create_supervision_result import sync_detailed as create_supervision_result_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervision.get_supervision_request_status import sync_detailed as get_supervision_status_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervision.get_supervision_result import sync_detailed as get_supervision_result_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.supervisor.get_tool_supervisor_chains import sync_detailed as get_tool_supervisor_chains_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.api.run.update_run_status import sync_detailed as update_run_status_sync_detailed
from asteroid_sdk.api.generated.asteroid_api_client.models.supervisor import Supervisor
from asteroid_sdk.api.generated.asteroid_api_client.models.supervisor_chain import SupervisorChain
from asteroid_sdk.api.generated.asteroid_api_client.models.supervision_request import SupervisionRequest
from asteroid_sdk.api.generated.asteroid_api_client.models.supervision_result import SupervisionResult
from asteroid_sdk.api.generated.asteroid_api_client.models.decision import Decision
from asteroid_sdk.api.generated.asteroid_api_client.models.status import Status

from asteroid_sdk.supervision.config import SupervisionContext, get_supervision_config
from asteroid_sdk.supervision.helpers.model_provider_helper import ModelProviderHelper, AvailableProviderResponses, \
    AvailableProviderToolCalls
from asteroid_sdk.supervision.model.tool_call import ToolCall
from asteroid_sdk.utils.utils import get_function_code
from asteroid_sdk.settings import settings

from asteroid_sdk.supervision.config import SupervisionDecision, SupervisionDecisionType
from langchain_core.tools.structured import StructuredTool

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
CHAT_TOOL_NAME = "chat_tool"
def chat_tool(message: str) -> None:
    """
    A special tool to represent chat messages for supervision purposes.
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

def register_supervisor_chains(
    client,
    tool_id: UUID,
    supervisor_chain_ids: List[List[UUID]],
):
    """
    Associates supervisor chains with a given tool.

    Args:
        client: The API client used for making API calls.
        tool_id (UUID): The UUID of the tool to associate supervisors with.
        supervisor_chain_ids (List[List[UUID]]): A list of lists of supervisor IDs, where each inner list represents a supervisor chain.
    """
    # Associate the supervisor chains with the tool
    if supervisor_chain_ids:
        chain_requests = [ChainRequest(supervisor_ids=supervisor_ids) for supervisor_ids in supervisor_chain_ids]
        association_response = create_tool_supervisor_chains_sync_detailed(
            tool_id=tool_id,
            client=client,
            body=chain_requests
        )
        if association_response.status_code in [200, 201]:
            print(f"Supervisors assigned to tool with ID {tool_id}")
        else:
            raise Exception(f"Failed to assign supervisors to tool with ID {tool_id}. Response: {association_response}")
    else:
        print(f"No supervisors to assign to tool with ID {tool_id}")



def register_tools_and_supervisors(
    run_id: UUID,
    tools: Optional[List[Callable]] = None,
    execution_settings: Dict[str, Any] = {},
    chat_supervisors: Optional[List[List[Callable]]] = None
):
    """
    Registers tools and supervisors with the backend API.
    """
    supervision_config = get_supervision_config()
    supervision_config.set_execution_settings(execution_settings)

    client = APIClientFactory.get_client()

    # Access the registries from the context
    run = supervision_config.get_run_by_id(run_id)
    if run is None:
        raise Exception(f"Run with ID {run_id} not found in supervision config.")
    supervision_context = run.supervision_context

    # Get the project ID
    project_id = list(supervision_config.projects.values())[0].project_id

    # Determine which functions to register
    if tools is None:
        # If no tools are provided, register all tools and supervisors
        supervised_functions = supervision_context.supervised_functions_registry
    else:
        # Register only the provided tools
        supervised_functions = {}
        for tool in tools:
            # Check if tool is StructuredTool
            if isinstance(tool, StructuredTool):
                func_name = tool.func.__qualname__
                supervised_functions[func_name] = supervision_context.supervised_functions_registry[func_name]
            else:
                func_name = tool.__qualname__
                supervised_functions[func_name] = supervision_context.supervised_functions_registry[func_name]
    if chat_supervisors is not None:
        supervision_context.add_supervised_function(chat_tool, supervision_functions=[chat_supervisors])
        supervised_functions[CHAT_TOOL_NAME] = supervision_context.supervised_functions_registry[CHAT_TOOL_NAME]


    for tool_name, data in supervised_functions.items():
        supervision_functions = data['supervision_functions']
        ignored_attributes = data['ignored_attributes']
        func = data['function']

        # Add the run_id to the supervised function
        supervision_context.add_run_id_to_supervised_function(func, run_id)

        # Extract function arguments using inspect
        func_signature = inspect.signature(func)
        func_arguments = {
            param.name: str(param.annotation) if param.annotation is not param.empty else 'Any'
            for param in func_signature.parameters.values()
        }

        # Create attributes for the tool
        attributes = CreateRunToolBodyAttributes.from_dict(src_dict=func_arguments)

        # Register the tool
        tool_data = CreateRunToolBody(
            name=tool_name,
            description=str(func.__doc__) if func.__doc__ else tool_name,
            attributes=attributes,
            ignored_attributes=ignored_attributes,
            code=get_function_code(func)
        )
        tool_response = create_run_tool_sync_detailed(
            run_id=run_id,
            client=client,
            body=tool_data
        )
        if (
            tool_response.status_code in [200, 201] and
            tool_response.parsed is not None
        ):
            # Update the tool_id in the registry
            tool = tool_response.parsed
            tool_id = tool.id
            supervision_context.update_tool_id(func, tool_id)
            print(f"Tool '{tool_name}' registered with ID: {tool_id}")
        else:
            raise Exception(f"Failed to register tool '{tool_name}'. Response: {tool_response}")

        # Register supervisors and collect supervisor IDs
        supervisor_chain_ids: List[List[UUID]] = []
        if not supervision_functions:
            supervisor_chain_ids.append([])
            from asteroid_sdk.supervision.supervisors import auto_approve_supervisor
            supervisor_func = auto_approve_supervisor()
            supervisor_info: Dict[str, Any] = {
                'func': supervisor_func,
                'name': getattr(supervisor_func, '__name__', 'auto_approve_supervisor'),
                'description': getattr(supervisor_func, '__doc__', 'Automatically approves any input.'),
                'type': SupervisorType.NO_SUPERVISOR,
                'code': get_function_code(supervisor_func),
                'supervisor_attributes': getattr(supervisor_func, 'supervisor_attributes', {})
            }
            supervisor_id = register_supervisor(client, supervisor_info, project_id, supervision_context)
            supervisor_chain_ids[0] = [supervisor_id]
        else:
            for idx, supervisor_func_list in enumerate(supervision_functions):
                supervisor_chain_ids.append([]) if tool_name != CHAT_TOOL_NAME else supervisor_chain_ids
                for supervisor_func in supervisor_func_list:
                    supervisor_info: Dict[str, Any] = {
                        'func': supervisor_func,
                        'name': getattr(supervisor_func, '__name__', 'supervisor_name'),
                        'description': getattr(supervisor_func, '__doc__', 'supervisor_description'),
                        'type': SupervisorType.HUMAN_SUPERVISOR if getattr(supervisor_func, '__name__', '') in ['human_supervisor', 'human_approver'] else SupervisorType.CLIENT_SUPERVISOR,
                        'code': get_function_code(supervisor_func),
                        'supervisor_attributes': getattr(supervisor_func, 'supervisor_attributes', {})
                    }
                    supervisor_id = register_supervisor(client, supervisor_info, project_id, supervision_context)
                    if tool_name != CHAT_TOOL_NAME:
                        supervisor_chain_ids[idx].append(supervisor_id)

        # Ensure tool_id is a UUID before proceeding
        if tool_id is UNSET or not isinstance(tool_id, UUID):
            raise ValueError("Invalid tool_id: Expected UUID")

        # Call the function to associate supervisor chains with the tool
        print(f"Associating supervisors with tool '{tool_name}' for run ID {run_id}")
        register_supervisor_chains(
            client=client,
            tool_id=tool_id,
            supervisor_chain_ids=supervisor_chain_ids,
        )

def register_supervisor(client: Client, supervisor_info: dict, project_id: UUID, supervision_context: SupervisionContext) -> UUID:
    """Registers a single supervisor with the API and returns its ID."""
    supervisor_data = Supervisor(
        name=supervisor_info['name'],
        description=supervisor_info['description'],
        created_at=datetime.now(timezone.utc),
        type=supervisor_info['type'],
        code=supervisor_info['code'],
        attributes=SupervisorAttributes.from_dict(src_dict=supervisor_info['supervisor_attributes'])
    )

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
            supervision_context.add_local_supervisor(supervisor_id, supervisor_info['func'], supervisor_info['name'])
        else:
            raise ValueError("Invalid supervisor_id: Expected UUID")

        print(f"Supervisor '{supervisor_info['name']}' registered with ID: {supervisor_id}")
        return supervisor_id
    else:
        raise Exception(f"Failed to register supervisor '{supervisor_info['name']}'. Response: {supervisor_response}")

def get_supervisor_chains_for_tool(tool_id: UUID, client: Client) -> List[SupervisorChain]:
    """
    Retrieve the supervisor chains for a specific tool.
    """

    supervisors_list: List[SupervisorChain] = []
    try:
        supervisors_response = get_tool_supervisor_chains_sync_detailed(
            tool_id=tool_id,
            client=client,
        )
        if supervisors_response is not None and supervisors_response.parsed is not None:
            supervisors_list = supervisors_response.parsed  # List[SupervisorChain]
            print(f"Retrieved {len(supervisors_list)} supervisor chains from the API.")
        else:
            print("No supervisors found for this tool and run.")
    except Exception as e:
        print(f"Error retrieving supervisors: {e}")

    return supervisors_list


def send_supervision_request(tool_call_id: UUID, supervisor_id: UUID, supervisor_chain_id: UUID, position_in_chain: int) -> UUID:
    client = APIClientFactory.get_client()

    supervision_request = SupervisionRequest(
        position_in_chain=position_in_chain,
        supervisor_id=supervisor_id
    )

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
            print(f"Created supervision request with ID: {supervision_request_id}")
            if isinstance(supervision_request_id, UUID):
                return supervision_request_id
            else:
                raise ValueError("Invalid supervision request ID received.")
        else:
            raise Exception(f"Failed to create supervision request. Response: {supervision_request_response}")
    except Exception as e:
        print(f"Error creating supervision request: {e}, Response: {supervision_request_response}")
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
            print(f"Successfully submitted supervision result for supervision request ID: {supervision_request_id}")
        else:
            raise Exception(f"Failed to submit supervision result. Response: {response}")
    except Exception as e:
        print(f"Error submitting supervision result: {e}, Response: {response}")
        raise



def wait_for_human_decision(supervision_request_id: UUID, timeout: int = 300) -> Status:
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
                    print(f"Polling for human decision completed. Status: {status}")
                    return status
                else:
                    print("Waiting for human supervisor decision...")
            else:
                print(f"Unexpected response while polling for supervision status: {response}")
        except Exception as e:
            print(f"Error while polling for supervision status: {e}")

        if time.time() - start_time > timeout:
            print(f"Timed out waiting for human supervision decision. Timeout: {timeout} seconds")
            return Status.TIMEOUT

        time.sleep(5)  # Wait for 5 seconds before polling again




def get_human_supervision_decision_api(
    supervision_request_id: UUID,
    timeout: int = 300) -> SupervisionDecision:
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
                                   explanation="The human supervisor did not provide a decision within the timeout period.")
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
    if decision_type == SupervisionDecisionType.MODIFY and result.toolrequest is not UNSET:  #TODO: Make the modified output work
        modified_output = result.toolrequest  # Assuming toolrequest contains the modified output
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
            print(f"Successfully submitted run status for run ID: {run_id}")
        else:
            raise Exception(f"Failed to submit run status. Response: {response}")
    except Exception as e:
        print(f"Error submitting run status: {e}, Response: {response}")
        raise


def generate_fake_chat_tool_call(
        client: Client,
        response: AvailableProviderResponses, # Could maybe change this to be a union of openai + anthropic types?
        supervision_context: Any,
        model_provider_helper: ModelProviderHelper,
        chat_supervisors: Optional[List[List[Callable]]] = None,
) -> Tuple[AvailableProviderResponses, List[ToolCall]]: # Could maybe change this to be a union of openai + anthropic types?
    """
    Generate a fake chat tool call when no tool calls are present in the response.

    :param client: The API client used for making API calls.
    :param response: The original ChatCompletion response from the OpenAI API.
    :param supervision_context: The supervision context associated with the run.
    :param model_provider_helper: The model provider helper used to generate fake tool calls.
    :param chat_supervisors: A list of chat supervisor callables. If provided, the supervisor chains will be registered with the Asteroid API.
    :return: A tuple containing the modified response and the list of tool calls.
    """
    print("No tool calls found in response, but chat supervisors provided, executing chat supervisors")

    modified_response = copy.deepcopy(response)
    chat_tool_call = model_provider_helper.generate_fake_tool_call(modified_response)

    model_provider_helper.upsert_tool_call(modified_response, chat_tool_call.language_model_tool_call)

    if chat_supervisors:
        # Retrieve supervisor IDs based on the provided chat supervisors
        chat_supervisor_ids = [
            [supervision_context.get_supervisor_id_by_func(chat_supervisor) for chat_supervisor in chat_supervisors_chain]
            for chat_supervisors_chain in chat_supervisors
        ]

        # Get the tool ID for the chat tool
        tool_id = supervision_context.get_supervised_function_entry(CHAT_TOOL_NAME).get("tool_id")

        # Register the supervisor chains with the Asteroid API client
        register_supervisor_chains(
            client=client,
            tool_id=tool_id,
            supervisor_chain_ids=chat_supervisor_ids
        )

    return modified_response, [chat_tool_call]
