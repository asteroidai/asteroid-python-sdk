"""
Initialization module for the Sentinel SDK.
"""

from typing import Optional
from sentinel.config import settings
from sentinel.registration.project import register_project
from sentinel.wrappers import patch_all_clients
from sentinel.api.client import APIClient

def init(api_key: str, project_id: Optional[str] = None):
    """
    Initializes the SDK and performs all necessary setup.

    Args:
        api_key (str): Your Sentinel API key.
        project_id (Optional[str]): Existing project ID. Registers a new project if not provided.

    Raises:
        ValueError: If the API key is invalid or project ID format is incorrect.
        ConnectionError: If there are network connectivity issues.
    """
    # Validate API key
    if not api_key or not isinstance(api_key, str):
        raise ValueError("Invalid API key provided.")

    settings.api_key = api_key

    # Initialize API client
    client = APIClient(api_key=api_key)

    if project_id:
        settings.project_id = project_id
    else:
        # Call register_project if project_id not provided
        settings.project_id = register_project(name="Default Project")

    # Automatically patch supported LLM clients
    patch_all_clients()
