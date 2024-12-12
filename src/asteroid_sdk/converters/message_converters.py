import json
import logging
from typing import Any, Dict
from asteroid_sdk.api.generated.asteroid_api_client.types import UNSET
from asteroid_sdk.api.generated.asteroid_api_client.models.tool_call_arguments import ToolCallArguments
from asteroid_sdk.api.generated.asteroid_api_client.models.tool_call import ToolCall as ApiToolCall
from asteroid_sdk.api.generated.asteroid_api_client.models.message import Message
from asteroid_sdk.api.generated.asteroid_api_client.models.message_type import MessageType
from asteroid_sdk.api.generated.asteroid_api_client.models.message_role import MessageRole

def convert_anthropic_message(msg: Dict) -> Message:
    """
    Converts an Anthropic message dict to a Message object in the API model.
    """

    # Extract role
    role_str = msg.get('role', 'assistant')
    role_mapping = {
        'assistant': MessageRole.ASSISTANT,
        'user': MessageRole.USER,
        'system': MessageRole.SYSTEM,
    }
    role = role_mapping.get(role_str, MessageRole.ASSISTANT)

    # Extract content
    content = msg.get('content', '')

    content_str = ''
    tool_calls = []
    message_type = MessageType.TEXT  # Default to text

    if isinstance(content, str):
        # Content is a simple string
        content_str = content
    elif isinstance(content, list):
        # Content is a list of content blocks
        for content_block in content:
            block_type = content_block.get('type', 'text')
            if block_type == 'image':
                # Process image content blocks
                image_source = content_block.get('source', {})
                image_data = image_source.get('data', '')
                media_type = image_source.get('media_type', '')
                # Format content as data URI
                content_str = f"data:{media_type};base64,{image_data}"
                message_type = MessageType.IMAGE
                break  # Assume only one image per message
            elif block_type == 'text':
                text = content_block.get('text', '')
                content_str += text + '\n'
            elif block_type == 'tool_use':
                # Process as a tool use
                tool_use = content_block
                api_tool_call = convert_anthropic_tool_call(tool_use)
                tool_calls.append(api_tool_call)
            else:
                # Handle other content block types if needed; for now, we skip
                pass
        else:
            # No image found; set message type to text
            content_str = content_str.strip()
            message_type = MessageType.TEXT
    else:
        # Content is neither string nor list; convert to string
        content_str = str(content)

    # Construct the Message object
    message = Message(
        role=role,
        content=content_str,
        type=message_type,
        tool_calls=tool_calls if tool_calls else UNSET,
    )
    return message


def convert_anthropic_tool_call(tool_use: Dict) -> ApiToolCall:
    """
    Converts an Anthropic tool use dict to an ApiToolCall object.
    """
    from sentinel.api.generated.sentinel_api_client.models.tool_call import ToolCall as ApiToolCall
    from sentinel.api.generated.sentinel_api_client.models.tool_call_arguments import ToolCallArguments
    from sentinel.api.generated.sentinel_api_client.types import UNSET

    id_ = tool_use.get('id', '')
    name = tool_use.get('name', '')
    input_args = tool_use.get('input', {})
    type_ = 'tool_use'  # Define the type as 'tool_use'
    parse_error = UNSET  # No parse error in this context

    # Convert input_args to ToolCallArguments
    arguments_obj = ToolCallArguments.from_dict(input_args)

    tool_call = ApiToolCall(
        id=id_ if id_ else UNSET,
        function=name,
        arguments=arguments_obj,
        type=type_,
        parse_error=parse_error,
    )

    return tool_call

def convert_openai_message(openai_msg: Dict[str, Any]) -> Message:
    """
    Converts an OpenAI message dict to a Message object in the API model.
    """
    from sentinel.api.generated.sentinel_api_client.models.message import Message
    from sentinel.api.generated.sentinel_api_client.models.message_role import MessageRole
    from sentinel.api.generated.sentinel_api_client.models.message_type import MessageType
    from sentinel.api.generated.sentinel_api_client.types import UNSET

    role_str = openai_msg.get('role')
    content = openai_msg.get('content', '') or ''
    message_id = openai_msg.get('id', UNSET)
    source = openai_msg.get('source', UNSET)
    tool_calls_data = openai_msg.get('tool_calls', UNSET)

    # Map role string to MessageRole enum
    role_mapping = {
        'assistant': MessageRole.ASSISTANT,
        'user': MessageRole.USER,
        'system': MessageRole.SYSTEM,
        # 'tool': MessageRole.TOOL,
    }

    role = role_mapping.get(role_str, MessageRole.USER)

    # Determine message type and content
    message_type = MessageType.TEXT  # Default to TEXT
    if isinstance(content, list):
        if len(content) > 1:
            logging.warning("Message has multiple items in content")
        for item in content:
            if item.get('type') == 'image_url':
                message_type = MessageType.IMAGE_URL
                content = item['image_url']['url']
                if content.startswith("data"):
                    message_type = MessageType.IMAGE
                content = item['image_url']['url']
                break
            elif item.get('type') == 'text':
                content = item['text']

    # Convert tool_calls if any
    if tool_calls_data and tool_calls_data is not UNSET:
        tool_calls = [convert_openai_tool_call(tc) for tc in tool_calls_data]
    else:
        tool_calls = UNSET

    message = Message(
        role=role,
        content=content,
        id=message_id,
        type=message_type,
        source=source,
        tool_calls=tool_calls,
    )

    return message

def convert_openai_tool_call(tool_call_dict: Dict[str, Any]) -> ApiToolCall:
    """
    Converts an OpenAI tool call dict to a ToolCall object in the API model.
    """

    id_ = tool_call_dict.get('id', '')
    function = tool_call_dict.get('function', '')
    arguments = tool_call_dict.get('arguments', {})
    type_ = tool_call_dict.get('type', '')
    parse_error = tool_call_dict.get('parse_error', UNSET)
    
    # Ensure 'function' is a string
    if isinstance(function, dict):
        function = function.get('name', '')
    elif not isinstance(function, str):
        function = str(function)

    # Convert arguments to ToolCallArguments
    if isinstance(arguments, dict):
        arguments_obj = ToolCallArguments.from_dict(arguments)
    elif isinstance(arguments, str):
        try:
            arguments_obj = ToolCallArguments.from_dict(json.loads(arguments))
        except json.JSONDecodeError:
            arguments_obj = ToolCallArguments()
    else:
        arguments_obj = ToolCallArguments()

    tool_call = ApiToolCall(
        id=id_,
        function=function,
        arguments=arguments_obj,
        type=type_,
        parse_error=parse_error,
    )

    return tool_call
