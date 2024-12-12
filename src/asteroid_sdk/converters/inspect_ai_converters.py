from inspect_ai.solver import TaskState
from inspect_ai.tool import ToolCall, Tool
from inspect_ai.model import ChatMessage, ChatMessageAssistant, ChatMessageTool, ModelOutput, ChatMessageUser, ChatMessageSystem

from asteroid_sdk.api.generated.asteroid_api_client.models.message import Message
from asteroid_sdk.api.generated.asteroid_api_client.models.message_role import MessageRole
from asteroid_sdk.api.generated.asteroid_api_client.models.message_type import MessageType
from asteroid_sdk.api.generated.asteroid_api_client.types import UNSET
from asteroid_sdk.api.generated.asteroid_api_client.models.tool_call import ToolCall as ApiToolCall
from asteroid_sdk.api.generated.asteroid_api_client.models.tool_call_arguments import ToolCallArguments
from asteroid_sdk.api.generated.asteroid_api_client.models.tool import Tool as ApiTool
from asteroid_sdk.api.generated.asteroid_api_client.models.output import Output as ApiOutput
from asteroid_sdk.api.generated.asteroid_api_client.models.task_state import TaskState as APITaskState
from inspect_ai._util.content import Content, ContentText

def convert_task_state(task_state: TaskState) -> APITaskState:
    """
    Converts Inspect AI TaskState object into the Sentinel API client's TaskState model.
    They should be identical when serialized.
    """
    from asteroid_sdk.api.generated.asteroid_api_client.types import UNSET
    from asteroid_sdk.api.generated.asteroid_api_client.models.task_state import TaskState as APITaskState

    # Convert messages
    messages = [convert_message(msg) for msg in task_state.messages]

    # Convert tools - we can't do this because Inspect AI doesn't have tool names    
    tools: list[ApiTool] = []

    # Convert output
    output = convert_output(task_state.output)

    # Convert tool_choice
    tool_choice = UNSET

    return APITaskState(
        messages=messages,
        tools=tools,
        output=output,
        completed=False,
        tool_choice=tool_choice,
    )

def convert_message(msg: ChatMessage) -> Message:
    """
    Converts a ChatMessage to a Message in the API model.
    """

    # Convert content to a string
    if isinstance(msg.content, str):
        content_str = msg.content
    elif isinstance(msg.content, list):
        content_str = "\n".join([convert_content(content) for content in msg.content])
    else:
        content_str = ""
        
    if isinstance(msg, ChatMessageTool):
        tool_call_id = msg.tool_call_id
        function = msg.function
        content_str = f"Function {function} has been executed with result: {msg.content}."
        if msg.error:
            content_str = f"Function {function} has been executed with error: {msg.error}"
    else:
        tool_call_id = UNSET
        function = UNSET

    if isinstance(msg, ChatMessageAssistant) and msg.tool_calls:
        tool_calls = [convert_tool_call(tool_call) for tool_call in msg.tool_calls]
    else:
        tool_calls = UNSET

    return Message( 
        source=msg.source if msg.source else UNSET,
        role=MessageRole(msg.role) if msg.role != 'tool' else MessageRole.ASSISTANT,
        content=content_str,
        tool_calls=tool_calls,
        type=MessageType.TEXT #TODO: Add support for audio messages and images
    )

def convert_content(content: Content) -> str:
    # Convert Content to a string representation
    if isinstance(content, ContentText):
        return content.text
    elif hasattr(content, 'data_url'):
        return content.data_url  # For images or other content types
    else:
        return str(content)

def convert_tool_call(tool_call: ToolCall) -> ApiToolCall:
    return ApiToolCall(
        id=tool_call.id,
        function=tool_call.function,
        arguments=ToolCallArguments.from_dict(tool_call.arguments),
        type=tool_call.type
    )

def convert_output(output: ModelOutput) -> ApiOutput:
    from asteroid_sdk.api.generated.asteroid_api_client.models.output import Output as ApiOutput

    return ApiOutput(
        model=output.model if output.model else UNSET,
        choices=UNSET, #TODO: Implement if needed
        usage=UNSET
    )
