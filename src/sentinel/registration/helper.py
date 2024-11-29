"""
Handles helper functions for registration with Sentinel.
"""

from typing import Optional, List
from uuid import UUID, uuid4
from sentinel.api.generated.sentinel_api_client.client import Client
from sentinel.api.generated.sentinel_api_client.models import CreateProjectBody, CreateTaskBody
from sentinel.api.generated.sentinel_api_client.types import UNSET
from sentinel.api.generated.sentinel_api_client.api.project.create_project import sync_detailed as create_project_sync_detailed
from sentinel.api.generated.sentinel_api_client.api.task.create_task import sync_detailed as create_task_sync_detailed
from sentinel.api.generated.sentinel_api_client.api.run.create_run import sync_detailed as create_run_sync_detailed
from sentinel.config import settings

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
    project_data = CreateProjectBody(name=project_name, run_result_tags=run_result_tags)

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
                settings.project_id = response.parsed
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
                settings.task_id = response.parsed
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
        run_name = f"run-{uuid4()}"

    client = APIClientFactory.get_client()

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
                settings.run_id = response.parsed
                return response.parsed
            else:
                raise ValueError("Unexpected response type. Expected UUID.")
        else:
            raise ValueError(f"Failed to create run. Response: {response}")
    except Exception as e:
        raise ValueError(f"Failed to create run: {str(e)}")
