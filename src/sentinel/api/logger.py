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
            # Debug Step 1: Print raw input data
            print("\n=== Debug Step 1: Raw Input ===")
            print(f"Raw response_data: {response_data}")
            print(f"Raw request_data: {request_data}")
            
            # Debug Step 2: JSON Conversion
            print("\n=== Debug Step 2: JSON Conversion ===")
            try:
                # Use OpenAI's built-in serialization method
                if hasattr(response_data, 'model_dump_json'):
                    response_data_str = response_data.model_dump_json()
                elif hasattr(response_data, 'to_dict'):
                    response_data_str = json.dumps(response_data.to_dict())
                else:
                    response_data_str = json.dumps(response_data)
                    
                print(f"Response JSON string: {response_data_str}")
                request_data_str = json.dumps(request_data)
                print(f"Request JSON string: {request_data_str}")
            except Exception as e:
                print(f"JSON conversion error: {str(e)}")
                
            # Debug Step 3: Base64 Encoding
            print("\n=== Debug Step 3: Base64 Encoding ===")
            try:
                response_data_base64 = base64.b64encode(response_data_str.encode()).decode()
                print(f"Response base64: {response_data_base64}")
                request_data_base64 = base64.b64encode(request_data_str.encode()).decode()
                print(f"Request base64: {request_data_base64}")
            except Exception as e:
                print(f"Base64 encoding error: {str(e)}")
            
            # Debug Step 4: Print Final Payload
            print("\n=== Debug Step 4: Final Payload ===")
            body = SentinelChat(
                response_data=response_data_base64,
                request_data=request_data_base64
            )
            print(f"Final body object: {body}")
            
            # Send the request
            response = create_new_chat_sync_detailed(
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
                print(f"\n=== Error Response ===")
                print(f"Status Code: {response.status_code}")
                print(f"Response Content: {response.content}")
                raise ValueError(f"Failed to log LLM response. Response: {response}")
        except Exception as e:
            raise SentinelLoggingError(f"Failed to log response: {str(e)}") from e
