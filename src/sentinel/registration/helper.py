"""
Handles helper functions for registration with Sentinel.
"""

from typing import Optional, List
from uuid import UUID
from sentinel.api.generated.sentinel_api_client.client import Client
from sentinel.api.generated.sentinel_api_client.models import CreateProjectBody
from sentinel.api.generated.sentinel_api_client.api.project.create_project import sync_detailed as create_project_sync_detailed
from sentinel.config import settings

def register_project(
    project_name: str, 
    run_result_tags: Optional[List[str]] = None
) -> UUID:
    """
    Registers a new project using the Sentinel API.

    Args:
        project_name (str): The name of the project to create.
        run_result_tags (Optional[List[str]]): Tags for run results. Defaults to ["passed", "failed"].

    Returns:
        UUID: The project ID.

    Raises:
        ValueError: If project registration fails.
    """
    if run_result_tags is None:
        run_result_tags = ["passed", "failed"]

    client = Client(base_url=settings.api_url)

    # Create new project
    project_data = CreateProjectBody(name=project_name, run_result_tags=run_result_tags)

    # Print api url and api key
    print(f"API URL: {settings.api_url}")
    print(f"API Key: {settings.api_key}")

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
                # Store the project ID in settings
                settings.project_id = response.parsed
                return response.parsed
            else:
                raise ValueError("Unexpected response type. Expected UUID.")
        else:
            raise ValueError(f"Failed to create project. Response: {response}")
    except Exception as e:
        raise ValueError(f"Failed to create project: {str(e)}")
