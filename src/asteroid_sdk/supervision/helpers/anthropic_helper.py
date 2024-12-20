import copy
from typing import List
from uuid import uuid4

from anthropic.types import Message, ToolUseBlock, TextBlock, Usage

from asteroid_sdk.api.generated.asteroid_api_client.models import ChatFormat
from asteroid_sdk.registration.helper import CHAT_TOOL_NAME
from asteroid_sdk.supervision.model.tool_call import ToolCall


class AnthropicSupervisionHelper:
    def get_tool_call_from_response(self, response: Message) -> List[ToolCall]:
        tools = []
        for content_block in response.content:
            if type(content_block) == ToolUseBlock:
                tool_call = ToolCall(
                    message_id=content_block.id,
                    tool_name=content_block.name,
                    tool_params=content_block.input, # TODO Maybe amend types here
                    language_model_tool_call=content_block
                )
                tools.append(tool_call)

        return tools

    def generate_fake_tool_call(self, response: Message) -> ToolCall:
        return ToolCall(
            message_id=response.id,
            tool_name=CHAT_TOOL_NAME,
            tool_params={"message": response.content[0]},
            language_model_tool_call=response
        )

    def upsert_tool_call(self, response: Message, tool_call: ToolUseBlock) -> Message:
        """
        This method assumes that we only have one tool call in the response.choices[0].message.tool_calls. No protection
        is added, so if there is more than 1 there, it'll overwrite them all.

        :param response: Message
        :param tool_call: Message
        :return: Message
        """
        for i, content_block in enumerate(response.content):
            if type(content_block) == ToolUseBlock:
                # Only change if a tool_call already exists
                response.content[i] = tool_call
                return response

        # If no tool_call exist already, append it
        response.content.append(tool_call)

        return response

    # Not sure about this implementation, maybe add a `response` from llm so we can just clone + modify that
    def generate_new_response_with_rejection_message(self, rejection_message) -> Message:
        text = TextBlock(
            text=rejection_message,
            type="text"
        )
        return Message(
            id="test_id",
            content=[text],
            model="test-model",
            role="assistant",
            type="message",
            usage=Usage(
                input_tokens=0,
                output_tokens=0,
            ),
        )

    def get_message_format(self) -> ChatFormat:
        return ChatFormat.ANTHROPIC
