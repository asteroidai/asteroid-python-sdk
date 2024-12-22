from typing import Dict, Any, TYPE_CHECKING
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from anthropic.types import Message

if TYPE_CHECKING:
    from asteroid_sdk.supervision.helpers.model_provider_helper import AvailableProviderToolCalls


class ToolCall:
    def __init__(self, message_id: str, tool_name: str, tool_params: Dict[str, Any], language_model_tool_call: Any, message: ChatCompletionMessage | Message):
        self.message_id: str = message_id
        self.tool_name: str = tool_name
        self.tool_params: Dict[str, Any] = tool_params
        self.language_model_tool_call: 'AvailableProviderToolCalls' = language_model_tool_call
        self.message: ChatCompletionMessage | Message = message

    def __str__(self):
        return f"ToolCall(tool_name={self.tool_name}, tool_params={self.tool_params})"
