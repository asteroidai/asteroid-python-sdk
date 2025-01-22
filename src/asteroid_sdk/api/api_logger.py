"""
Shared logging functionality for API wrappers.
"""

import base64
import copy
import json
import logging
from typing import Any, Dict
from uuid import UUID

from anthropic.types import Message
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message import (
    ChatCompletionMessage,
)
from google.generativeai.types import GenerateContentResponse
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.generated.asteroid_api_client.api.run.create_new_chat import (
    sync_detailed as create_new_chat_sync_detailed,
)
from asteroid_sdk.api.generated.asteroid_api_client.models import ChatIds, AsteroidChat, ChatFormat
from asteroid_sdk.supervision.helpers.model_provider_helper import ModelProviderHelper, Provider

provider_to_chat_format = {
    "openai": ChatFormat.OPENAI,
    "anthropic": ChatFormat.ANTHROPIC,
    "gemini": ChatFormat.GEMINI,
}

class APILogger:
    def __init__(self, client: Client, model_provider_helper: ModelProviderHelper):
        self.client = client
        self.model_provider_helper = model_provider_helper

    def log_llm_interaction(
            self,
            response: ChatCompletion | Message | GenerateContentResponse,
            request_kwargs: Dict[str, Any],
            run_id: UUID,
    ) -> ChatIds:

        response_data_str, request_data_str = self._convert_to_json(response, request_kwargs)
        response_data_base64, request_data_base64 = self._encode_to_base64(response_data_str, request_data_str)

        body = AsteroidChat(
            response_data=response_data_base64,
            request_data=request_data_base64,
            format_=provider_to_chat_format[self.model_provider_helper.get_provider().value]
        )

        return self._send_chats_to_asteroid_api(run_id, body)

    def _send_chats_to_asteroid_api(self, run_id: UUID, body: AsteroidChat) -> ChatIds:
        """
        Send the API request to the Asteroid API and handle the response.

        :param run_id: The unique identifier for the run.
        :param body: The payload to send to the API.
        :return: The parsed response from the API.
        """
        try:
            response = create_new_chat_sync_detailed(
                client=self.client,
                run_id=run_id,
                body=body
            )

            if response.status_code not in [200, 201]:
                raise ValueError(
                    f"Failed to log LLM response. Status code: {response.status_code}, Response: {response.content}")

            if response.parsed is None:
                raise ValueError("Response was successful but parsed content is None")

            logging.info(f"Successfully logged response for run {run_id}")
            return response.parsed
        except Exception as e:
            logging.error(f"API request error: {str(e)}")
            logging.error(f"Error occurred at line {e.__traceback__.tb_lineno}")
            raise

    def _convert_to_json(
            self, response: ChatCompletion | Message | GenerateContentResponse, request_kwargs: Any
    ) -> tuple[str, str]:
        """
        Convert the response and request data to JSON strings.

        :param response: The response data to convert.
        :param request_kwargs: The request keyword arguments to convert.
        :return: A tuple containing the response and request data as JSON strings.
        """
        # Convert response_data to a JSON string
        # TODO - Confirm I can remove the bit that I've removed. We were already converting to a dict above
        # TODO - David note - The reason for this is that sometimes the main object was dict but contained other objects that were not dicts, that's why the below code was needed - It might be redundant but would need to be tested

        # response_data = response if isinstance(response, dict) else response.to_dict()
        # if hasattr(response_data, 'model_dump_json'):
        #     response_data_str = response_data.model_dump_json()
        # elif hasattr(response_data, 'to_dict'):
        #     response_data = response if isinstance(response, dict) else response.to_dict()
        #     response_data_str = json.dumps(response_data.to_dict())
        # else:
        #     response_data_str = json.dumps(response_data)

        # TODO - probably remove below aswell, it's custom types testing
        # if self.model_provider_helper.get_provider() in [Provider.OPENAI, Provider.ANTHROPIC]:
        #     response_dict = response.to_dict()
        #     response_data_str = json.dumps(response_dict)
        # elif self.model_provider_helper.get_provider() == Provider.GEMINI:
        #     response_data_str = response._pb.SerializeToString()

        response_dict = response.to_dict()
        response_data_str = json.dumps(response_dict)

        # Convert request_kwargs to a JSON string
        if isinstance(request_kwargs, str):
            request_data_str = request_kwargs
        else:
            # Ensure tool_calls are converted to dictionaries
            request_data_str = self.model_provider_helper.convert_model_kwargs_to_json(request_kwargs)

        return response_data_str, request_data_str

    def _encode_to_base64(
            self, response_data_str: str, request_data_str: str
    ) -> tuple[str, str]:
        """
        Encode the response and request JSON strings to Base64.

        :param response_data_str: The response data as a JSON string.
        :param request_data_str: The request data as a JSON string.
        :return: A tuple containing the Base64-encoded response and request data.
        """
        # Ensure the data is a string
        if not isinstance(response_data_str, str):
            response_data_str = str(response_data_str)
        if not isinstance(request_data_str, str):
            request_data_str = str(request_data_str)

        # Encode to Base64
        response_data_base64 = base64.b64encode(response_data_str.encode()).decode()
        request_data_base64 = base64.b64encode(request_data_str.encode()).decode()

        return response_data_base64, request_data_base64
