from typing import Optional, Union, List, Dict, Any, Callable, Tuple, Type
from uuid import UUID

from google.ai.generativelanguage_v1beta import ToolConfig, FunctionCallingConfig
from google.generativeai.types.content_types import ToolConfigType, Mode

from asteroid_sdk.api.generated.asteroid_api_client.models.tool import Tool
from asteroid_sdk.registration.helper import get_human_supervision_decision_api
from google.generativeai.types import GenerateContentResponse

from .config import (
    SupervisionDecision,
    SupervisionDecisionType,
    SupervisionContext
)
import json
from openai import OpenAI
from asteroid_sdk.supervision.protocols import Supervisor
from openai.types.chat import ChatCompletionMessage
from anthropic.types.message import Message as AnthropicMessage
from .decorators import supervisor
import jinja2
from asteroid_sdk.utils.utils import load_template
from jsonschema import validate, ValidationError, SchemaError
from pydantic import BaseModel
import anthropic
import google.generativeai as genai
import os
import asyncio

DEFAULT_OPENAI_LLM_MODEL = "gpt-4o"
DEFAULT_ANTHROPIC_LLM_MODEL = "claude-3-5-sonnet-latest"
DEFAULT_GEMINI_LLM_MODEL = "gemini-1.5-flash"

# DEFAULT PROMPTS
LLM_SUPERVISOR_SYSTEM_PROMPT_TEMPLATE = load_template("default_llm_supervisor_system_template.jinja")
LLM_SUPERVISOR_ASSISTANT_PROMPT_TEMPLATE = load_template("default_llm_supervisor_assistant_template.jinja")

def preprocess_message(
    message: Union[ChatCompletionMessage, AnthropicMessage]
) -> Dict[str, Any]:
    """
    Preprocess the incoming message to extract simple variables for the template.

    Args:
        message (Union[ChatCompletionMessage, AnthropicMessage]): The incoming message.

    Returns:
        Dict[str, Any]: A dictionary with preprocessed data.
    """
    preprocessed = {
        "message_content": "",
        "tool_call_name": None,
        "tool_call_description": None,
        "tool_call_arguments": None,
    }

    # TODO - this forces us back to one tool call again. I think this bit is the reason that we want to pass around a
    #  ToolCall object, instead of the raw message. We can pass the user/supervisor the raw message if we want,
    #  but we're just back to decoding again here
    if isinstance(message, ChatCompletionMessage):
        # OpenAI message handling
        if message.tool_calls:
            tool_call = message.tool_calls[0]  # Assuming first tool call
            preprocessed["tool_call_name"] = tool_call.function.name
            # Assuming function.description is available; if not, adjust accordingly
            preprocessed["tool_call_description"] = getattr(tool_call.function, 'description', "")
            preprocessed["tool_call_arguments"] = tool_call.function.arguments
        else:
            preprocessed["message_content"] = message.content or ""
    elif isinstance(message, AnthropicMessage):
        # Anthropic message handling
        tool_call_found = False
        for content_block in message.content:
            if content_block.type == "tool_use":
                tool_call = content_block
                preprocessed["tool_call_name"] = getattr(tool_call, 'name', None)
                preprocessed["tool_call_description"] = getattr(tool_call, 'description', "")
                preprocessed["tool_call_arguments"] = json.dumps(getattr(tool_call, 'input', {}))
                tool_call_found = True
                break
        if not tool_call_found:
            # Concatenate text blocks to get the message content
            preprocessed["message_content"] = ''.join(
                block.text for block in message.content if block.type == "text"
            )
    elif isinstance(message, GenerateContentResponse):
        # Gemini message handling
        # TODO - ensure that this is actually doing the correct thing
        tool_call_found = False
        if message.parts:
            for part in message.parts:
                if part.function_call:
                    tool_call_found = True
                    tool_call = message.parts[0]
                    preprocessed["tool_call_name"] = tool_call.function_call.name
                    preprocessed["tool_call_description"] = getattr(tool_call.function_call, 'description', "")
                    preprocessed["tool_call_arguments"] = {arg: value for arg, value in tool_call.function_call.args.items()}
        if tool_call_found == False:
            preprocessed["message_content"] = message.choices[0].message.content
    else:
        raise ValueError("Unsupported message type")

    return preprocessed

def llm_supervisor(
    instructions: str,
    provider: Optional[str] = "openai",
    supervisor_name: Optional[str] = None,
    description: Optional[str] = None,
    model: Optional[str] = DEFAULT_OPENAI_LLM_MODEL,
    system_prompt_template: Optional[str] = LLM_SUPERVISOR_SYSTEM_PROMPT_TEMPLATE,
    assistant_prompt_template: Optional[str] = LLM_SUPERVISOR_ASSISTANT_PROMPT_TEMPLATE,
    include_previous_messages: bool = True,
    allow_modification: bool = False,
) -> Supervisor:
    """
    Create a supervisor function that uses an LLM to make a supervision decision.
    Supports both OpenAI and Anthropic models by preprocessing them into simple variables.

    Parameters:
    - instructions (str): The supervision instructions.
    - supervisor_name (Optional[str]): Optional name for the supervisor.
    - description (Optional[str]): Optional description.
    - model (str): LLM model to use.
    - provider (str): LLM provider, 'openai' or 'anthropic'.
    - system_prompt_template (str): Template for system prompt.
    - assistant_prompt_template (str): Template for assistant prompt.
    - include_previous_messages (bool): Whether to include the previous messages to the LLM.
    - allow_modification (bool): Whether to allow modification.

    Returns:
    - Supervisor: A callable supervisor function.
    """
    if not provider:
        provider = "openai"
    if not model:
        model = DEFAULT_OPENAI_LLM_MODEL
    if provider == "anthropic" and model == DEFAULT_OPENAI_LLM_MODEL:
        model = DEFAULT_ANTHROPIC_LLM_MODEL
    if provider == "gemini" and model == DEFAULT_OPENAI_LLM_MODEL:
        model = DEFAULT_GEMINI_LLM_MODEL
    if not system_prompt_template:
        system_prompt_template = LLM_SUPERVISOR_SYSTEM_PROMPT_TEMPLATE
    if not assistant_prompt_template:
        assistant_prompt_template = LLM_SUPERVISOR_ASSISTANT_PROMPT_TEMPLATE



    # Compile the Jinja templates
    compiled_system_prompt_template = jinja2.Template(system_prompt_template)
    compiled_assistant_prompt_template = jinja2.Template(assistant_prompt_template)

    @supervisor
    def supervisor_function(
        message: Union[ChatCompletionMessage, AnthropicMessage],
        supervision_context: Optional[SupervisionContext] = None,
        ignored_attributes: List[str] = [],
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs
    ) -> SupervisionDecision:
        """
        The supervisor function that processes a message and returns a supervision decision.

        Args:
            message (Union[ChatCompletionMessage, AnthropicMessage]): The incoming message to supervise.
            supervision_context (Optional[SupervisionContext]): Additional context for supervision.
            ignored_attributes (List[str]): Attributes to ignore during supervision.
            supervision_request_id (Optional[UUID]): Optional request ID.
            previous_decision (Optional[SupervisionDecision]): Previous supervision decision.

        Returns:
            SupervisionDecision: The decision made by the supervisor.
        """

        # Preprocess the message to extract simple variables
        preprocessed = preprocess_message(message)

        # Prepare the context for the prompt templates
        system_message_context = {"instructions": instructions}
        assistant_message_context = {
            "previous_messages": (
                supervision_context.messages_to_text()
                if supervision_context and include_previous_messages
                else ""
            ),
            "previous_decision": {
                "decision": previous_decision.decision,
                "explanation": previous_decision.explanation,
            }
            if previous_decision
            else None,
            "tool_call_name": preprocessed.get("tool_call_name"),
            "tool_call_description": preprocessed.get("tool_call_description"),
            "tool_call_arguments": preprocessed.get("tool_call_arguments"),
            "message_content": preprocessed.get("message_content"),
            "allow_modification": allow_modification,
        }

        # Render the prompts using the templates
        system_prompt = compiled_system_prompt_template.render(**system_message_context)
        assistant_prompt = compiled_assistant_prompt_template.render(**assistant_message_context)

        # Prepare messages and function/tool definitions based on the provider
        if provider == "openai":

            openai_client = OpenAI()

            messages = [
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": assistant_prompt.strip()},
            ]

            # Define the function schema for SupervisionDecision
            supervision_decision_schema = SupervisionDecision.model_json_schema()

            functions = [
                {
                    "name": "supervision_decision",
                    "description": (
                        "Analyze the input based on the provided instructions and context, and make a "
                        "supervision decision: APPROVE, REJECT, ESCALATE, TERMINATE, or MODIFY. Provide a "
                        "concise and accurate explanation for your decision. If you modify the input, include "
                        "the modified content in the 'modified' field."
                    ),
                    "parameters": supervision_decision_schema,
                }
            ]

            try:
                # OpenAI API call
                completion = openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    functions=functions,
                    function_call={"name": "supervision_decision"},
                )

                # Extract the function call arguments from the response
                response_message = completion.choices[0].message

                if response_message and response_message.function_call:
                    response_args = response_message.function_call.arguments
                    response_data = json.loads(response_args)
                else:
                    raise ValueError("No valid function call in assistant's response.")

                # Parse the 'modified' field
                modified_data = response_data.get("modified")

                decision = SupervisionDecision(
                    decision=response_data.get("decision").lower(),
                    modified=modified_data,
                    explanation=response_data.get("explanation"),
                )
                return decision

            except Exception as e:
                print(f"Error during LLM supervision: {str(e)}")
                return SupervisionDecision(
                    decision=SupervisionDecisionType.ESCALATE,
                    explanation=f"Error during LLM supervision: {str(e)}",
                    modified=None,
                )

        elif provider == "anthropic":
            # Convert messages to the format expected by Anthropic
            messages = [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": assistant_prompt.strip()}],
                }
            ]

            # Define the tool schema for SupervisionDecision
            supervision_decision_schema = SupervisionDecision.model_json_schema()

            tools = [
                {
                    "name": "supervision_decision",
                    "description": (
                        "Analyze the input based on the provided instructions and context, and make a "
                        "supervision decision: APPROVE, REJECT, ESCALATE, TERMINATE, or MODIFY. Provide a "
                        "concise and accurate explanation for your decision. If you modify the input, include "
                        "the modified content in the 'modified' field."
                    ),
                    "input_schema": supervision_decision_schema,
                }
            ]

            tool_choice = {"type": "tool", "name": "supervision_decision"}

            try:
                # Initialize the AnthropIc client
                anthropic_client = anthropic.Anthropic()

                # Anthropic API call
                completion = anthropic_client.messages.create(
                    model=model,
                    system=system_prompt,
                    max_tokens=1024,
                    tools=tools,
                    tool_choice=tool_choice,
                    messages=messages,
                )

                # Extract the tool output from the response
                response_data = completion.content[0].input
                # Parse the 'modified' field
                modified_data = response_data.get("modified")

                decision = SupervisionDecision(
                    decision=response_data.get("decision").lower(),
                    modified=modified_data,
                    explanation=response_data.get("explanation"),
                )
                return decision

            except Exception as e:
                print(f"Error during LLM supervision: {str(e)}")
                return SupervisionDecision(
                    decision=SupervisionDecisionType.ESCALATE,
                    explanation=f"Error during LLM supervision: {str(e)}",
                    modified=None,
                )

        elif provider == "gemini":
            # NOTE- System role is added when client it generated
            contents = [
                {"role": "user", 'parts': [{"text": assistant_prompt.strip()}]}
            ]
            # Got to manually define the below as the API is so strict that the`.model_json_schema()` method won't work
            supervision_decision_schema = genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    'decision': genai.protos.Schema(type=genai.protos.Type.STRING, enum=SupervisionDecisionType),
                    'explanation': genai.protos.Schema(type=genai.protos.Type.STRING),
                },
            )

            functions = [
                {
                    "name": "supervision_decision",
                    "description": (
                        "Analyze the input based on the provided instructions and context, and make a "
                        "supervision decision: APPROVE, REJECT, ESCALATE, TERMINATE, or MODIFY. Provide a "
                        "concise and accurate explanation for your decision. If you modify the input, include "
                        "the modified content in the 'modified' field."
                    ),
                    "parameters": supervision_decision_schema,
                }
            ]

            genai.configure()
            gemini_model = genai.GenerativeModel(
                model,
                system_instruction=assistant_prompt.strip(),
                tool_config={"function_calling_config": {
                    "mode": "ANY",
                    "allowed_function_names": ["supervision_decision"],
                }},
            )

            result = gemini_model.generate_content(
                contents=contents,
                tools=functions
            )

            # Extract the function call arguments from the response
            for part in result.parts:
                if part.function_call:
                    params = {arg: value for arg, value in part.function_call.args.items()}
                    break

            # TODO- Note modified does not work yet!
            decision = SupervisionDecision(
                decision=params.get("decision").lower(),
                modified=None,
                explanation=params.get("explanation"),
            )
            return decision


        else:
            raise ValueError(f"Unsupported provider: {provider}")

    supervisor_function.__name__ = supervisor_name if supervisor_name else "llm_supervisor"
    supervisor_function.__doc__ = description if description else "LLM-based supervisor."

    supervisor_function.supervisor_attributes = {
        "instructions": instructions,
        "model": model,
        "provider": provider,
        "system_prompt_template": system_prompt_template,
        "assistant_prompt_template": assistant_prompt_template,
        "include_previous_messages": include_previous_messages,
        "allow_modification": allow_modification,
    }

    return supervisor_function


def human_supervisor(
    timeout: int = 86400,
    n: int = 1,
) -> Supervisor:
    """
    Create a supervisor function that requires human approval via backend API.

    Args:
        timeout (int): Timeout in seconds for waiting for the human decision.
        n (int): Number of samples to do.

    Returns:
        Supervisor: A supervisor function that implements human supervision.
    """

    @supervisor
    async def supervisor_function(
        message: Union[ChatCompletionMessage, AnthropicMessage],
        supervision_request_id: Optional[UUID] = None,
        **kwargs
    ) -> SupervisionDecision:
        """
        Human supervisor that requests approval via backend API or CLI.

        Args:
            supervision_request_id (UUID): ID of the supervision request.

        Returns:
            SupervisionDecision: The decision made by the supervisor.
        """
        if supervision_request_id is None:
            raise ValueError("Supervision request ID is required")

        # Get the human supervision decision asynchronously
        supervisor_decision = await asyncio.to_thread(
            get_human_supervision_decision_api,
            supervision_request_id=supervision_request_id,
            timeout=timeout,
        )
        return supervisor_decision

    supervisor_function.__name__ = "human_supervisor"
    supervisor_function.supervisor_attributes = {"timeout": timeout, "n": n}

    return supervisor_function


@supervisor
def auto_approve_supervisor(
    message: Union[ChatCompletionMessage, AnthropicMessage],
    **kwargs
) -> SupervisionDecision:
    """Create a supervisor that automatically approves any input."""
    return SupervisionDecision(
        decision=SupervisionDecisionType.APPROVE,
        explanation="Automatically approved.",
        modified=None
    )

def json_output_supervisor(
    expected_schema: Type[BaseModel],
    custom_validation_function: Optional[Callable[[Any], Tuple[bool, str]]] = None,
    supervisor_name: Optional[str] = None,
    description: Optional[str] = None,
) -> Supervisor:
    """
    Create a supervisor function that checks if the output is valid JSON and
    adheres to the specified Pydantic schema.

    Parameters:
    - expected_schema (Type[BaseModel]): A Pydantic model defining the expected schema.
    - custom_validation_function (Optional[Callable[[Any], Tuple[bool, str]]]): A custom validation
      function that takes the parsed object and returns (is_valid, error_message).
    - supervisor_name (Optional[str]): Optional name for the supervisor.
    - description (Optional[str]): Optional description.

    Returns:
    - Supervisor: A callable supervisor function.
    """
    @supervisor
    def supervisor_function(
        message: Union[ChatCompletionMessage, AnthropicMessage],
        supervision_context: Optional[SupervisionContext] = None,
        ignored_attributes: List[str] = [],
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs
    ) -> SupervisionDecision:
        # --- [Extracting message content] ---
        if isinstance(message, ChatCompletionMessage):
            # OpenAI message handling
            message_content = message.content or ""
        elif isinstance(message, AnthropicMessage):
            # Anthropic message handling
            message_content = ''
            for block in message.content:
                if block.type == "text" and hasattr(block, 'text'):
                    message_content += block.text

        # --- [Attempt to parse the message content as JSON] ---
        try:
            json_output = json.loads(message_content)
        except json.JSONDecodeError as e:
            explanation = f"Output is not valid JSON: {str(e)}"
            return SupervisionDecision(
                decision=SupervisionDecisionType.ESCALATE,
                explanation=explanation,
                modified=None
            )

        # --- [Validate using Pydantic model] ---
        try:
            parsed_output = expected_schema.model_validate(json_output)
        except ValidationError as e:
            explanation = f"JSON output validation error: {e}"
            return SupervisionDecision(
                decision=SupervisionDecisionType.ESCALATE,
                explanation=explanation,
                modified=None
            )

        # --- [Custom validation function] ---
        if custom_validation_function:
            is_valid, error_message = custom_validation_function(parsed_output)
            if not is_valid:
                return SupervisionDecision(
                    decision=SupervisionDecisionType.ESCALATE,
                    explanation=error_message,
                    modified=None
                )

        # --- [Approve if all validations pass] ---
        return SupervisionDecision(
            decision=SupervisionDecisionType.APPROVE,
            explanation="JSON output is valid and matches the expected schema.",
            modified=None
        )

    supervisor_function.__name__ = supervisor_name if supervisor_name else "json_output_supervisor"
    supervisor_function.__doc__ = description if description else "Supervisor that validates JSON outputs using Pydantic schemas."

    supervisor_function.supervisor_attributes = {
        "expected_schema": expected_schema,
        "custom_validation_function": custom_validation_function,
    }

    return supervisor_function
