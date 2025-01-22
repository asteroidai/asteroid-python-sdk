from typing import Protocol, List, Union, TYPE_CHECKING
from enum import Enum

from anthropic.types import Message, ToolUseBlock
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall, ChatCompletionMessage

from asteroid_sdk.api.generated.asteroid_api_client.models import ChatFormat

if TYPE_CHECKING:
    from asteroid_sdk.supervision.model.tool_call import ToolCall

AvailableProviderResponses = Union[ChatCompletion, Message]
AvailableProviderToolCalls = Union[ChatCompletionMessageToolCall, ToolUseBlock]
AvailableProviderMessageTypes = Union[ChatCompletionMessage, Message]

class Provider(str, Enum):
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"

class ModelProviderHelper(Protocol):
    def get_tool_call_from_response(self, response: AvailableProviderResponses) -> List['ToolCall']:
        ...
    def generate_fake_tool_call(self, response: AvailableProviderResponses) -> 'ToolCall':
        ...
    def generate_message_from_fake_tool_call(self, response: AvailableProviderResponses) -> AvailableProviderResponses:
        ...
    def upsert_tool_call(self, response: AvailableProviderResponses, tool_call: AvailableProviderToolCalls) -> AvailableProviderToolCalls:
        ...
    def generate_new_response_with_rejection_message(self, rejection_message) -> AvailableProviderResponses:
        ...
    def get_provider(self) -> Provider:
        ...
    def convert_model_kwargs_to_json(self, response: AvailableProviderMessageTypes) -> str:
        ...
    def resample_response(self, feedback_message, args, request_kwargs, completions):
        pass
