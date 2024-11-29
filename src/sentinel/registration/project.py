"""
Handles project registration with Sentinel.
"""

from typing import Optional, List
from uuid import UUID
from sentinel.api.generated.sentinel_api_client.client import Client
from sentinel.api.generated.sentinel_api_client.models import CreateProjectBody
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

    client = Client(base_url=settings.api_url, token=settings.api_key)

    # Create new project
    project_data = CreateProjectBody(
        name=project_name, 
        run_result_tags=run_result_tags
    )

    try:
        response = client.project.create_project(json_body=project_data)
        if isinstance(response, UUID):
            # Store the project ID in settings
            settings.project_id = response
            return response
        else:
            raise ValueError("Unexpected response type. Expected UUID.")
    except Exception as e:
        raise ValueError(f"Failed to create project: {str(e)}")
