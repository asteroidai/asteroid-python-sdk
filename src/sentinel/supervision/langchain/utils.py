from typing import Any, List, Dict
import uuid
from datetime import datetime
from inspect_ai.solver import TaskState
from inspect_ai.model import ChatMessage, ChatMessageAssistant, ChatMessageSystem, ChatMessageTool, ChatMessageUser, ModelName
from inspect_ai.tool import ToolCall
from inspect_ai.tool._tool_call import ToolCallError
import json

def extract_messages_from_events(events: List[Dict[str, Any]]) -> List[ChatMessage]:
    """
    Extract messages from LangChain events.

    Args:
        events (List[Dict[str, Any]]): The list of LangChain events.

    Returns:
        List[ChatMessage]: A list of ChatMessage objects representing the conversation.
    """
    messages = []
    for event in events:
        if event['event'] == 'on_chat_model_start':
            # Extract messages from the start event
            message_batches = event['data'].get('messages', [])
            for batch in message_batches:
                for msg_dict in batch:
                    msg_type = msg_dict.get('type')
                    if msg_type != 'human':
                        continue  # Skip non-human messages
                    content = msg_dict.get('data', {}).get('content', '').strip()
                    if not content:
                        continue  # Skip empty messages
                    
                    # Check for duplicate last user message
                    if messages:
                        last_user_messages = [msg for msg in messages if msg.role == 'user']
                        if len(last_user_messages) > 0 and last_user_messages[-1].content == content:
                            continue  # Skip adding duplicate user message

                    messages.append(
                        ChatMessageUser(
                            role='user',
                            content=content,
                            source='input'
                        )
                    )
        elif event['event'] == 'on_llm_end':
            # Assistant response
            response = event['data'].get('response', {})
            generations = response.get('generations', [])
            for generation_list in generations:
                for generation in generation_list:
                    message = generation.get('message', {})
                    content = message.get('content', '')
                    additional_kwargs = message.get('additional_kwargs', {})
                    tool_calls = additional_kwargs.get('tool_calls', None)
                    if tool_calls:
                        tool_calls_list = []
                        # Assistant made a function call
                        for tool_call in tool_calls:
                            tool_call_id = tool_call.get('id', '')
                            function = tool_call.get('function', {})
                            function_name = function.get('name')
                            arguments = function.get('arguments', '')
                            # parse arguments to json
                            try:
                                arguments = json.loads(arguments)
                            except json.JSONDecodeError:
                                arguments = {}
                            tool_call_type = tool_call.get('type', '')
                            tool_call = ToolCall(
                                id=tool_call_id,
                                function=function_name,
                                arguments=arguments,
                                type=tool_call_type
                            )
                            tool_calls_list.append(tool_call)
                        messages.append(
                            ChatMessageAssistant(
                                role='assistant',
                                content=content,
                                tool_calls=tool_calls_list,
                                source='generate'
                            )
                        )
                    else:
                        # Regular assistant message
                        messages.append(
                            ChatMessageAssistant(
                                role='assistant',
                                content=content,
                                tool_calls=[],
                                source='generate'
                            )
                        )
        elif event['event'] == 'on_tool_end':
            # Tool response
            output = event['data'].get('output', {})
            content = output.get('content', '')
            tool_call_id = output.get('tool_call_id', '')
            function_name = output.get('name', '')
            error_data = output.get('error', None)
            error = None
            if error_data:
                error = ToolCallError(
                    type=error_data.get('type', ''),
                    message=error_data.get('message', '')
                )
            messages.append(
                ChatMessageTool(
                    role='tool',
                    content=content,
                    tool_call_id=tool_call_id,
                    function=function_name,
                    error=error,
                    source='generate'
                )
            )
        elif event['event'] == 'on_tool_error':
            # Tool error response
            error_message = event['data'].get('error', '')
            run_id = event.get('run_id', '')
            # You might want to map run_id to tool_call_id and function_name if available
            messages.append(
                ChatMessageTool(
                    role='tool',
                    content='',
                    tool_call_id=run_id,  # Placeholder, update if you have mapping
                    function=None,        # Placeholder, update if you have mapping
                    error=ToolCallError(
                        type='ToolError',
                        message=error_message
                    ),
                    source='generate'
                )
            )
    return messages


