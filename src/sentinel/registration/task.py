"""
Handles task registration within a Sentinel project.
"""

from typing import Optional, Dict
from sentinel.api.client import APIClient
from sentinel.config import settings

def register_task(name: str, project_id: str, metadata: Optional[Dict] = None) -> str:
    """
    Registers a new task within a project.

    Args:
        name (str): Name of the task.
        project_id (str): ID of the project to associate the task with.
        metadata (Optional[Dict]): Additional metadata for the task.

    Returns:
        str: The newly created task ID.

    Raises:
        ValueError: If the task name already exists or invalid metadata format.
        ConnectionError: For network errors.
    """
    client = APIClient(api_key=settings.api_key)
    payload = {
        "name": name,
        "project_id": project_id,
        "metadata": metadata or {}
    }

    try:
        response = client.post("/tasks", json=payload)
        response.raise_for_status()
        task_id = response.json().get("task_id")
        return task_id
    except Exception as e:
        raise ValueError(f"Failed to register task: {e}")
