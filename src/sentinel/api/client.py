"""
API client for Sentinel backend communication.
"""

import requests
from typing import Dict, Any

class APIClient:
    """
    Client for interacting with the Sentinel API.
    """
    BASE_URL = "https://api.sentinel.com"

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def post(self, endpoint: str, json: Dict[str, Any]) -> requests.Response:
        """
        Sends a POST request to the Sentinel API.

        Args:
            endpoint (str): API endpoint (e.g., "/projects").
            json (Dict[str, Any]): JSON payload for the request.

        Returns:
            requests.Response: The response object.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.post(url, json=json)
        response.raise_for_status()
        return response
