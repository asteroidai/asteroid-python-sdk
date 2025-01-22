"""
Utility functions for Inspect AI supervision.
"""

import json
import time
import uuid
from typing import List, Dict, Literal
from uuid import UUID

from inspect_ai.approval import Approval
from inspect_ai._util.registry import registry_lookup
from inspect_ai.model._chat_message import ChatMessage
from inspect_ai.solver import TaskState
from inspect_ai.tool import ToolCall
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)
from openai.types.completion_usage import CompletionUsage
from anthropic.types.message import Message as AnthropicMessage
from anthropic.types.content_block import ContentBlock
from anthropic.types.text_block import TextBlock
from anthropic.types.tool_use_block import ToolUseBlock
from anthropic.types.usage import Usage

from google.ai.generativelanguage_v1beta import FunctionCall, Content, Part, Candidate, GenerateContentResponse as BetaContent
from google.generativeai.types import GenerateContentResponse

from asteroid_sdk.supervision.config import SupervisionDecision

from asteroid_sdk.supervision.config import SupervisionDecision



def convert_tool_call_to_openai_tool_call(tool_call: ToolCall) -> ChatCompletionMessageToolCall:
    """
    Convert an Inspect AI ToolCall to OpenAI ChatCompletionMessageToolCall instance.

    Args:
        tool_call (ToolCall): The ToolCall instance from Inspect AI.

    Returns:
        ChatCompletionMessageToolCall: An instance representing the tool call.
    """
    function = Function(
        name=tool_call.function,
        arguments=json.dumps(tool_call.arguments),  # Serialize arguments as JSON string
    )
    openai_tool_call = ChatCompletionMessageToolCall(
        id=tool_call.id,
        function=function,
        type=tool_call.type,  # Should be 'function'
    )
    return openai_tool_call


def convert_state_messages_to_openai_messages(state_messages: List[ChatMessage]) -> List[Dict]:
    """
    Convert Inspect AI state messages to a list of dictionaries compatible with OpenAI's API.

    Args:
        state_messages (List[ChatMessage]): List of Inspect AI chat messages.

    Returns:
        List[Dict]: List of messages formatted for OpenAI API.
    """
    openai_messages = []
    for msg in state_messages:
        role = msg.role  # 'system', 'user', 'assistant', etc.
        content = msg.text  # Extract the text content from the message

        if hasattr(msg, 'error') and msg.error is not None:
            content = f"{content}\n\nError: {msg.error.message}"

        openai_msg = {
            "role": role,
            "content": content,
        }

        # If the message has tool_calls, include them
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            openai_tool_calls = [
                convert_tool_call_to_openai_tool_call(tc) for tc in msg.tool_calls
            ]
            openai_msg["tool_calls"] = openai_tool_calls

        openai_messages.append(openai_msg)
    return openai_messages


def convert_state_output_to_openai_response(state_output) -> ChatCompletion:
    """
    Convert Inspect AI state output to an OpenAI ChatCompletion instance.

    Args:
        state_output (ModelOutput): The output from Inspect AI model.

    Returns:
        ChatCompletion: An instance representing the response as per OpenAI's API.
    """
    # Generate a unique ID and timestamp
    response_id = "chatcmpl_" + str(uuid.uuid4())
    created_time = int(time.time())

    # Convert choices
    response_choices = []
    for idx, choice in enumerate(state_output.choices):
        message = choice.message  # Should be ChatMessageAssistant
        role = message.role  # Should be 'assistant'
        content = message.text  # Get text content

        openai_msg = ChatCompletionMessage(
            role=role,
            content=content,
            tool_calls=[
                convert_tool_call_to_openai_tool_call(tc) for tc in getattr(message, "tool_calls", [])
            ],
        )

        finish_reason = choice.stop_reason  # Map to OpenAI's expected finish reasons

        # Create the Choice instance
        openai_choice = Choice(
            index=idx,
            message=openai_msg,
            finish_reason=finish_reason,
        )
        response_choices.append(openai_choice)

    # Convert usage
    if state_output.usage:
        usage = CompletionUsage(
            prompt_tokens=state_output.usage.input_tokens,
            completion_tokens=state_output.usage.output_tokens,
            total_tokens=state_output.usage.total_tokens,
        )
    else:
        usage = None

    # Create the ChatCompletion instance
    chat_completion = ChatCompletion(
        id=response_id,
        object="chat.completion",
        created=created_time,
        model=state_output.model,
        choices=response_choices,
        usage=usage,
    )

    return chat_completion


def convert_state_messages_to_anthropic_messages(state_messages: List[ChatMessage]) -> List[Dict]:
    """
    Convert Inspect AI state messages to a list of dictionaries compatible with Anthropic's API.

    Args:
        state_messages (List[ChatMessage]): List of Inspect AI chat messages.

    Returns:
        List[Dict]: List of messages formatted for Anthropic API.
    """
    anthropic_messages = []
    for msg in state_messages:
        # Generate a unique ID for the message
        msg_id = str(uuid.uuid4())

        content_blocks = []

        # Add text content as a TextBlock
        if msg.text:
            text_block = {
                'type': 'text',
                'text': msg.text
            }
            content_blocks.append(text_block)

        if hasattr(msg, 'error') and msg.error is not None:
            content_blocks.append({'type': 'text', 'text': f"Error: {msg.error.message}"})

        # Include tool calls as ToolUseBlocks
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_use_block = {
                    'type': 'tool_use',
                    'id': str(tool_call.id),
                    'name': tool_call.function,
                    'input': tool_call.arguments
                }
                content_blocks.append(tool_use_block)

        anthropic_msg = {
            'id': msg_id,
            'content': content_blocks
        }
        anthropic_messages.append(anthropic_msg)
    return anthropic_messages

def convert_state_output_to_anthropic_response(state_output) -> AnthropicMessage:
    """
    Convert Inspect AI state output to an Anthropic Message instance.

    Args:
        state_output (ModelOutput): The output from Inspect AI model.

    Returns:
        Message: An Anthropic Message representing the response.
    """
    # Generate a unique ID for the message
    msg_id = 'msg_' + str(uuid.uuid4())

    # Assume state_output.choices is a list of choices; we'll use the first choice
    choice = state_output.choices[0]
    message = choice.message  # Should be ChatMessageAssistant

    content_blocks: List[ContentBlock] = []

    # Add text content as a TextBlock
    if message.text:
        text_block = TextBlock(
            text=message.text,
            type="text"
        )
        content_blocks.append(text_block)

    # Include tool calls as ToolUseBlocks
    if hasattr(message, 'tool_calls') and message.tool_calls:
        for tool_call in message.tool_calls:
            tool_use_block = ToolUseBlock(
                id=str(tool_call.id),
                name=tool_call.function,
                input=tool_call.arguments,
                type="tool_use"
            )
            content_blocks.append(tool_use_block)

    # Convert state_output.model to an instance of Model
    # model = Model(state_output.model)

    # Convert state_output.usage to an instance of Usage
    usage = Usage(
        input_tokens=state_output.usage.input_tokens,
        output_tokens=state_output.usage.output_tokens
    )

    anthropic_msg = AnthropicMessage(
        id=msg_id,
        content=content_blocks,
        model=state_output.model,
        role="assistant",
        type="message",
        usage=usage
    )

    return anthropic_msg


def transform_asteroid_approval_to_inspect_ai_approval(approval_decision: SupervisionDecision) -> Approval:
    """
    Transform an EntropyLabs SupervisionDecision to an InspectAI Approval
    """
    # Map the decision types
    decision_mapping: dict[str, Literal['approve', 'modify', 'reject', 'terminate', 'escalate']] = {
        "approve": "approve",
        "reject": "reject",
        "escalate": "escalate",
        "terminate": "terminate",
        "modify": "modify"
    }

    inspect_ai_decision = decision_mapping[approval_decision.decision]

    # Handle the 'modified' field
    modified = None
    if inspect_ai_decision == "modify" and approval_decision.modified is not None:
        # Create ToolCall instance directly from the modified data
        tool_name = approval_decision.modified.tool_name
        tool_kwargs = approval_decision.modified.tool_kwargs or {}
        modified = ToolCall(id=str(uuid.uuid4()), function=tool_name, arguments=tool_kwargs, type="function")


    return Approval(
        decision=inspect_ai_decision,
        modified=modified,
        explanation=approval_decision.explanation
    )

def convert_state_messages_to_gemini_messages(state_messages: List[ChatMessage]) -> List[Dict]:
    """
    Convert Inspect AI state messages to a list of dictionaries compatible with Gemini's API.

    Args:
        state_messages (List[ChatMessage]): List of Inspect AI chat messages.

    Returns:
        List[Dict]: List of messages formatted for Gemini API.
    """
    gemini_messages = []
    for msg in state_messages:
        content = {
            'role': msg.role,  # 'system', 'user', 'assistant'
            'parts': []
        }

        parts = []
        if msg.text:
            parts.append({'text': msg.text})

        # Include tool calls as appropriate
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                function_call = {
                    'function_call': {
                        'name': tool_call.function,
                        'args': tool_call.arguments
                    }
                }
                parts.append(function_call)
                
        if hasattr(msg, 'error') and msg.error is not None:
            parts.append({'text': f"Error: {msg.error.message}"})

        content['parts'] = parts
        gemini_messages.append(content)

    return gemini_messages

def convert_state_output_to_gemini_response(state_output) -> GenerateContentResponse:
    """
    Convert Inspect AI state output to a Gemini GenerateContentResponse instance.

    Args:
        state_output (ModelOutput): The output from Inspect AI model.

    Returns:
        GenerateContentResponse: An instance representing the response as per Gemini's API.
    """
    # Assume state_output.choices is a list of choices; we'll use the first choice
    choice = state_output.choices[0]
    message = choice.message  # Should be ChatMessageAssistant

    parts = []
    if message.text:
        parts.append(Part(text=message.text))

    # Include function calls as appropriate
    if hasattr(message, 'tool_calls') and message.tool_calls:
        for tool_call in message.tool_calls:
            function_call = FunctionCall(
                name=tool_call.function,
                args=tool_call.arguments
            )
            parts.append(Part(function_call=function_call))

    content = Content(parts=parts, role=message.role)
    candidate = Candidate(content=content)
    
    beta_response = BetaContent(candidates=[candidate])
    
    response = GenerateContentResponse.from_response(beta_response)
    return response