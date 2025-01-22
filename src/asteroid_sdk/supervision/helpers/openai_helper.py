import copy
import datetime
import json
from typing import List
from uuid import uuid4

from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message_tool_call import Function

from asteroid_sdk.api.generated.asteroid_api_client.models import ChatFormat
from asteroid_sdk.registration.helper import MESSAGE_TOOL_NAME
from asteroid_sdk.supervision.helpers.model_provider_helper import Provider
from asteroid_sdk.supervision.model.tool_call import ToolCall


class OpenAiSupervisionHelper:
    def get_tool_call_from_response(self, response: ChatCompletion) -> List[ToolCall]:
        tools = []

        if not response.choices[0].message.tool_calls:
            return tools

        for tool_call in response.choices[0].message.tool_calls:
            arguments = json.loads(tool_call.function.arguments)
            call = ToolCall(
                message_id=tool_call.id,
                tool_name=tool_call.function.name,
                tool_params=arguments,
                language_model_tool_call=tool_call,
                message=copy.deepcopy(response.choices[0].message)
            )
            tools.append(call)
        return tools

    def generate_fake_tool_call(self, response: ChatCompletion) -> ToolCall:
        text_response = response.choices[0].message.content
        arguments = {"message": text_response}
        chat_tool_call = ChatCompletionMessageToolCall(
            id=str(uuid4()),
            function=Function(
                name=MESSAGE_TOOL_NAME,
                arguments=json.dumps(arguments)
            ),
            type='function'
        )

        return ToolCall(
            message_id=chat_tool_call.id,
            tool_name=chat_tool_call.function.name,
            tool_params=arguments,
            language_model_tool_call=chat_tool_call,
            message=copy.deepcopy(response.choices[0].message)
        )

    def generate_message_from_fake_tool_call(self, response: ChatCompletion) -> ChatCompletion:
        if response.choices[0].message.tool_calls and isinstance(response.choices[0].message.tool_calls[0], ChatCompletionMessageToolCall) and response.choices[0].message.tool_calls[0].function.name == MESSAGE_TOOL_NAME:
            response.choices[0].message.content = json.loads(response.choices[0].message.tool_calls[0].function.arguments)["message"]
            response.choices[0].message.tool_calls = []
        return response

    def upsert_tool_call(self, response: ChatCompletion, tool_call: ChatCompletionMessageToolCall) -> ChatCompletion:
        """
        This method assumes that we only have one tool call in the response.choices[0].message.tool_calls. No protection
        is added, so if there is more than 1 there, it'll overwrite them all

        :param response: ChatCompletion
        :param tool_call: ChatCompletionMessageToolCall
        :return: ChatCompletion
        """
        response.choices[0].message.tool_calls = [tool_call]
        return response

    # Not sure about this implementation, maybe add a `response` from llm so we can just clone + modify that
    def generate_new_response_with_rejection_message(self, rejection_message) -> ChatCompletion:
        return ChatCompletion(
            id=str(uuid4()),
            choices=[
                Choice(
                    message=ChatCompletionMessage(
                        content=rejection_message,
                        tool_calls=[],
                        role='assistant'
                    ),
                    finish_reason='stop',
                    index=0,
                )
            ],
            created=int(datetime.datetime.now().timestamp()),
            model= 'n/a',
            object= 'chat.completion',
        )


    def get_provider(self) -> Provider:
        return Provider.OPENAI

    # TODO - Clean this up, just copied the method from main code
    def convert_model_kwargs_to_json(self, request_kwargs: ChatCompletion) -> str:
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
