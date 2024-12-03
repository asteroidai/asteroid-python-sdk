"""
Shared logging functionality for API wrappers.
"""

import base64
import json
from typing import Any, Dict
from uuid import UUID
from sentinel.settings import settings
from sentinel.api.generated.sentinel_api_client import Client
from sentinel.api.generated.sentinel_api_client.models import SentinelChat
from sentinel.api.generated.sentinel_api_client.api.run.create_new_chat import sync_detailed as create_new_chat_sync_detailed

class SentinelLoggingError(Exception):
    """Raised when there's an error logging to Sentinel API"""
    pass

class APILogger:
    """Handles logging to the Sentinel API"""
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required for logging")
        self.client = Client(base_url=settings.api_url)
    
    def log_request(self, request_data: Dict[str, Any], run_id: UUID) -> None:
        """No op as Sentinel API doesn't need request data, it is sent when the response is received"""
        pass
    
    def log_response(self, response_data: Dict[str, Any], request_data: Dict[str, Any], run_id: UUID) -> None:
        """Send the raw response data to Sentinel API"""
        try:
            # Base 64 encode the response data
            # Print the type of the response data
            print(f"Response data type: {type(response_data)}")
            response_data_str = json.dumps(response_data)
            response_data_base64 = base64.b64encode(response_data_str.encode()).decode()

            # Base 64 encode the request data
            print(f"Request data type: {type(request_data)}")
            request_data_str = json.dumps(request_data)
            request_data_base64 = base64.b64encode(request_data_str.encode()).decode()
            
            body = SentinelChat(
                response_data=response_data_base64,
                request_data=request_data_base64
            )

            response = create_new_chat_sync_detailed(
                client=self.client,
                run_id=run_id,
                body=body
            )

            # Response contains all the tool calls
            # Iterate over all the tool calls
            # Get the supervisors for that tool
            # Run each supervisor 
            
            if (
                response.status_code in [200, 201]
                and response.parsed is not None
            ):
                print(f"Logged response for run {run_id}")
            else:
                raise ValueError(f"Failed to log LLM response. Response: {response}") 
        except Exception as e:
            raise SentinelLoggingError(f"Failed to log response: {str(e)}") from e 
