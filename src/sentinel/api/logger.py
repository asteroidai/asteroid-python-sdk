"""
Shared logging functionality for API wrappers.
"""

from typing import Any, Dict
from sentinel.api.generated.sentinel_api_client import Client
from sentinel.config import settings

class SentinelLoggingError(Exception):
    """Raised when there's an error logging to Sentinel API"""
    pass

class APILogger:
    """Handles logging to the Sentinel API"""
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required for logging")
        self.client = Client(base_url=settings.api_url, token=api_key)
    
    def log_request(self, request_data: Dict[str, Any], conversation_id: str) -> None:
        """Send the raw request data to Sentinel API"""
        try:
            payload = {
                "conversation_id": conversation_id,
                "data": request_data
            }
            # Update this to use the generated client's method
            self.client.requests.create_request(json_body=payload)
        except Exception as e:
            raise SentinelLoggingError(f"Failed to log request: {str(e)}") from e
    
    def log_response(self, response_data: Dict[str, Any], conversation_id: str) -> None:
        """Send the raw response data to Sentinel API"""
        try:
            payload = {
                "conversation_id": conversation_id,
                "data": response_data
            }
            # Update this to use the generated client's method
            self.client.responses.create_response(json_body=payload)
        except Exception as e:
            raise SentinelLoggingError(f"Failed to log response: {str(e)}") from e 
