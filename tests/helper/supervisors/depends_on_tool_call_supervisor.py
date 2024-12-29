import json

from anthropic.types import Message, ToolUseBlock
from openai.types.chat import ChatCompletionMessage

from asteroid_sdk.supervision import SupervisionDecision, SupervisionDecisionType
from asteroid_sdk.supervision.decorators import supervisor
from asteroid_sdk.supervision.helpers.model_provider_helper import AvailableProviderMessageTypes


def should_allow(message: AvailableProviderMessageTypes) -> bool:
    if isinstance(message, ChatCompletionMessage):
        args_string = message.tool_calls[0].function.arguments
        return json.loads(args_string)["allow"]
    elif isinstance(message, Message):
        for content_block in message.content:
            if type(content_block) == ToolUseBlock:
                return content_block.input.get("allow", False)

    raise ValueError("Message type not supported")


@supervisor
def depends_on_tool_call_supervisor(
        message: AvailableProviderMessageTypes,
        **kwargs
) -> SupervisionDecision:
    if should_allow(message):
        return SupervisionDecision(decision=SupervisionDecisionType.APPROVE)
    else:
        return SupervisionDecision(decision=SupervisionDecisionType.REJECT)
