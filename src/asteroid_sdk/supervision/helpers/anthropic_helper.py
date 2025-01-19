import copy
import json
from typing import List

from anthropic.types import Message, ToolUseBlock, TextBlock, Usage
from openai.types.chat import ChatCompletionMessage

from asteroid_sdk.supervision.helpers.model_provider_helper import Provider
from asteroid_sdk.supervision.model.tool_call import ToolCall
from asteroid_sdk.registration.helper import MESSAGE_TOOL_NAME


class AnthropicSupervisionHelper:
    def get_tool_call_from_response(self, response: Message) -> List[ToolCall]:
        tools = []
        for content_block in response.content:
            if type(content_block) == ToolUseBlock:
                tool_call = ToolCall(
                    message_id=content_block.id,
                    tool_name=content_block.name,
                    tool_params=content_block.input, # TODO Maybe amend types here
                    language_model_tool_call=content_block,
                    message=copy.deepcopy(response)
                )
                tools.append(tool_call)

        return tools

    def generate_fake_tool_call(self, response: Message) -> ToolCall:
        assert isinstance(response.content[0], TextBlock)
        return ToolCall(
            message_id=response.id,
            tool_name=MESSAGE_TOOL_NAME,
            tool_params={"message": response.content[0].text},
            language_model_tool_call=ToolUseBlock(
                id=response.id,
                name=MESSAGE_TOOL_NAME,
                input={"message": response.content[0].text},
                type="tool_use"
            ),
            message=copy.deepcopy(response)
        )

    def generate_message_from_fake_tool_call(self, response: Message) -> Message:
        if isinstance(response.content[0], ToolUseBlock) and response.content[0].name == MESSAGE_TOOL_NAME:
            assert isinstance(response.content[0].input, dict)
            response.content = [TextBlock(text=response.content[0].input["message"], type="text")]
        return response

    def upsert_tool_call(self, response: Message, tool_call: ToolUseBlock) -> Message:
        """
        This method assumes that we only have one TextBlock in the response.content and we want to replace it with the ToolUseBlock.

        :param response: Message
        :param tool_call: Message
        :return: Message
        """
        response.content = [tool_call]
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

    def get_provider(self) -> Provider:
        return Provider.ANTHROPIC

    # TODO - Clean this up, just copied the method from main code
    def convert_model_kwargs_to_json(self, request_kwargs: Message) -> str:
        messages = request_kwargs.get("messages", [])
        for idx, message in enumerate(messages):
            if isinstance(message, ChatCompletionMessage):
                request_kwargs['messages'][idx] = message.to_dict()
            else:
                tool_calls = message.get("tool_calls", [])
                if tool_calls:
                    request_kwargs["messages"][idx]["tool_calls"] = [
                        t.to_dict() if hasattr(t, 'to_dict') else t for t in tool_calls
                    ]
        return json.dumps(request_kwargs)

    def resample_response(self, feedback_message, args, request_kwargs, completions):
        copied_kwargs = copy.deepcopy(request_kwargs)
        copied_kwargs['messages'].append({
            "role": "user",
            "content": feedback_message
        })
        return completions.create(*args, **copied_kwargs), copied_kwargs
