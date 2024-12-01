"""
Handles helper functions for registration with Sentinel.
"""

from datetime import datetime, timezone
import inspect
from typing import Any, Callable, Optional, List
from uuid import UUID, uuid4

from sentinel.api.generated.sentinel_api_client.client import Client
from sentinel.api.generated.sentinel_api_client.models import CreateProjectBody, CreateTaskBody
from sentinel.api.generated.sentinel_api_client.models.chain_request import ChainRequest
from sentinel.api.generated.sentinel_api_client.models.create_run_tool_body import CreateRunToolBody
from sentinel.api.generated.sentinel_api_client.models.create_run_tool_body_attributes import CreateRunToolBodyAttributes
from sentinel.api.generated.sentinel_api_client.models.supervisor_attributes import SupervisorAttributes
from sentinel.api.generated.sentinel_api_client.models.supervisor_type import SupervisorType
from sentinel.api.generated.sentinel_api_client.types import UNSET
from sentinel.api.generated.sentinel_api_client.api.project.create_project import sync_detailed as create_project_sync_detailed
from sentinel.api.generated.sentinel_api_client.api.task.create_task import sync_detailed as create_task_sync_detailed
from sentinel.api.generated.sentinel_api_client.api.tool.create_run_tool import sync_detailed as create_run_tool_sync_detailed
from sentinel.api.generated.sentinel_api_client.api.run.create_run import sync_detailed as create_run_sync_detailed
from sentinel.api.generated.sentinel_api_client.api.supervisor.create_supervisor import sync_detailed as create_supervisor_sync_detailed
from sentinel.api.generated.sentinel_api_client.api.supervisor.create_tool_supervisor_chains import sync_detailed as create_tool_supervisor_chains_sync_detailed
from sentinel.api.generated.sentinel_api_client.models.supervisor import Supervisor

from sentinel.supervision.config import SupervisionContext, get_supervision_config
from sentinel.supervision.supervisors import auto_approve_supervisor
from sentinel.utils.utils import get_function_code
from sentinel.settings import settings

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
                headers={"Authorization": f"Bearer {settings.api_key}"}
            )
        return cls._instance

def register_project(
    project_name: str, 
    run_result_tags: Optional[List[str]] = None
) -> UUID:
    """
    Registers a new project using the Sentinel API.
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
    Registers a new task under a project using the Sentinel API.
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
    Creates a new run for a task under a project using the Sentinel API.
    """
    if not project_id:
        raise ValueError("Project ID is required")
    if not task_id:
        raise ValueError("Task ID is required")
    
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

def register_tools_and_supervisors(run_id: UUID, tools: Optional[List[Callable | StructuredTool]] = None):
    """
    Registers tools and supervisors with the backend API.
    """
    supervision_config = get_supervision_config()

    client = APIClientFactory.get_client()

    # Access the registries from the context
    run = supervision_config.get_run_by_id(run_id)
    if run is None:
        raise Exception(f"Run with ID {run_id} not found in supervision config.")
    supervision_context = run.supervision_context

    # TODO: Do this better
    project_id = list(supervision_config.projects.values())[0].project_id 

    # TODO: Make sure this is correct
    if tools is None: 
        # If no tools are provided, register all tools and supervisors
        supervised_functions = supervision_context.supervised_functions_registry
    else:
        # If list of tools is provided, only register the tools and supervisors for the provided tools  
        supervised_functions = {}
        for tool in tools:
            # Check if tool is StructuredTool
            if isinstance(tool, StructuredTool):
                supervised_functions[tool.func.__qualname__] = supervision_context.supervised_functions_registry[tool.func.__qualname__]
            else:
                print(f"Tool is {tool}")
                supervised_functions[tool.__qualname__] = supervision_context.supervised_functions_registry[tool.__qualname__]


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

        # Pass the extracted arguments to ToolAttributes.from_dict
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
            tool_id = tool_response.parsed
            supervision_context.update_tool_id(func, tool_id)
            print(f"Tool '{tool_name}' registered with ID: {tool_id}")
        else:
            raise Exception(f"Failed to register tool '{tool_name}'. Response: {tool_response}")

        # Register supervisors and associate them with the tool
        supervisor_chain_ids: List[List[UUID]] = []
        if supervision_functions == []:
            supervisor_chain_ids.append([])
            supervisor_func = auto_approve_supervisor()
            supervisor_info: dict[str, Any] = {
                    'func': supervisor_func,
                    'name': getattr(supervisor_func, '__name__', 'supervisor_name'),
                    'description': getattr(supervisor_func, '__doc__', 'supervisor_description'),
                    'type': SupervisorType.NO_SUPERVISOR,
                    'code': get_function_code(supervisor_func),
                    'supervisor_attributes': getattr(supervisor_func, 'supervisor_attributes', {})
            }
            supervisor_id = register_supervisor(client, supervisor_info, project_id, supervision_context)
            supervisor_chain_ids[0] = [supervisor_id]
        else:
            for idx, supervisor_func_list in enumerate(supervision_functions):
                supervisor_chain_ids.append([])
                for supervisor_func in supervisor_func_list:
                    supervisor_info: dict[str, Any] = {
                        'func': supervisor_func,
                        'name': getattr(supervisor_func, '__name__', None) or 'supervisor_name',
                        'description': getattr(supervisor_func, '__doc__', None) or 'supervisor_description',
                        'type': SupervisorType.HUMAN_SUPERVISOR if getattr(supervisor_func, '__name__', 'supervisor_name') in ['human_supervisor', 'human_approver'] else SupervisorType.CLIENT_SUPERVISOR,
                        'code': get_function_code(supervisor_func),
                        'supervisor_attributes': getattr(supervisor_func, 'supervisor_attributes', {})
                    }
                    supervisor_id = register_supervisor(client, supervisor_info, project_id, supervision_context)
                    supervisor_chain_ids[idx].append(supervisor_id)

        # Ensure tool_id is a UUID before proceeding
        if tool_id is UNSET or not isinstance(tool_id, UUID):
            raise ValueError("Invalid tool_id: Expected UUID")

        print(f"Associating supervisors with tool '{tool_name}' for run ID {run_id}")
        if supervisor_chain_ids:
            chain_requests = [ChainRequest(supervisor_ids=supervisor_ids) for supervisor_ids in supervisor_chain_ids]
            association_response = create_tool_supervisor_chains_sync_detailed(
                tool_id=tool_id,
                client=client,
                body=chain_requests
            )
            if association_response.status_code in [200, 201]:
                print(f"Supervisors assigned to tool '{tool_name}' for run ID {run_id}")
            else:
                raise Exception(f"Failed to assign supervisors to tool '{tool_name}'. Response: {association_response}")
        else:
                print(f"No supervisors to assign to tool '{tool_name}'")

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
    