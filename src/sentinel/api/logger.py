"""
Shared logging functionality for API wrappers.
"""

import base64
import json
from typing import Any, Dict
from uuid import UUID
from sentinel.api.generated.sentinel_api_client import Client
from sentinel.api.generated.sentinel_api_client.models.create_new_chat_completion_request_body import CreateNewChatCompletionRequestBody
from sentinel.api.generated.sentinel_api_client.models.create_new_chat_completion_response_body import CreateNewChatCompletionResponseBody
from sentinel.settings import settings
from sentinel.api.generated.sentinel_api_client.api.run.create_new_chat_completion_request import sync_detailed as create_new_chat_completion_request_sync_detailed
from sentinel.api.generated.sentinel_api_client.api.run.create_new_chat_completion_response import sync_detailed as create_new_chat_completion_response_sync_detailed


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
        """Send the raw request data to Sentinel API"""
        try:
            # Convert the request data to a string
            request_data_str = json.dumps(request_data)

            # Base 64 encode the request data
            request_data_base64 = base64.b64encode(request_data_str.encode()).decode()
            
            body = CreateNewChatCompletionRequestBody(
                request_data=request_data_base64
            )

            response = create_new_chat_completion_request_sync_detailed(
                client=self.client,
                run_id=run_id,
                body=body
            )

            if (
                response.status_code in [200, 201]
                and response.parsed is not None
            ):
                if isinstance(response.parsed, UUID):
                    print(f"Logged request for run {run_id}")
                else:
                    raise ValueError("Unexpected response type. Expected UUID.")
            else:
                raise ValueError(f"Failed to create run. Response: {response}")
        except Exception as e:
            raise SentinelLoggingError(f"Failed to log request: {str(e)}") from e
    
    def log_response(self, response_data: Dict[str, Any], run_id: UUID) -> None:
        """Send the raw response data to Sentinel API"""
        try:
            # Convert the response data to a string
            response_data_str = json.dumps(response_data)

            # Base 64 encode the response data
            response_data_base64 = base64.b64encode(response_data_str.encode()).decode()
            
            body = CreateNewChatCompletionResponseBody(
                response_data=response_data_base64
            )

            response = create_new_chat_completion_response_sync_detailed(
                client=self.client,
                run_id=run_id,
                body=body
            )
            
            if (
                response.status_code in [200, 201]
                and response.parsed is not None
            ):
                print(f"Logged response for run {run_id}")
            else:
                raise ValueError(f"Failed to log LLM response. Response: {response}") 
        except Exception as e:
            raise SentinelLoggingError(f"Failed to log response: {str(e)}") from e 
