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
    SupervisionContext,
    ModifiedData
)
import json
from asteroid_sdk.supervision.protocols import Supervisor
from openai.types.chat import ChatCompletionMessage
from anthropic.types.message import Message as AnthropicMessage
from .decorators import supervisor
import jinja2
from asteroid_sdk.utils.utils import load_template
from jsonschema import validate, ValidationError, SchemaError
from pydantic import BaseModel
import anthropic
import logging
import google.generativeai as genai
import asyncio

from asteroid_sdk.settings import settings

# Try to import Langfuse's OpenAI if enabled
if settings.langfuse_enabled:
    try:
        from langfuse.openai import OpenAI as LangfuseOpenAI
    except ImportError:
        logging.warning(
            "Langfuse is enabled in settings but langfuse.openai could not be imported."
        )
        LangfuseOpenAI = None
else:
    LangfuseOpenAI = None

# Also import standard openai
import openai

DEFAULT_OPENAI_LLM_MODEL = "gpt-4o"
DEFAULT_ANTHROPIC_LLM_MODEL = "claude-3-5-sonnet-latest"
DEFAULT_GEMINI_LLM_MODEL = "gemini-1.5-flash"

# DEFAULT PROMPTS
LLM_SUPERVISOR_SYSTEM_PROMPT_TEMPLATE = load_template("default_llm_supervisor_system_template.jinja")
LLM_SUPERVISOR_SYSTEM_PROMPT_OUTPUT_TEMPLATE = load_template("default_llm_supervisor_system_output_template.jinja")

def preprocess_message(
    message: Union[ChatCompletionMessage, AnthropicMessage, GenerateContentResponse]
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

def create_message_history_context(
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Create a message history context for the supervisor by compressing the message history
    into a single user message that includes the role names and their messages.
    If there is an image, add a system message before the image explaining that the next
    message is a user message related to the context, then add the image to the messages list.

    Args:
        messages (List[Dict[str, Any]]): The message history.

    Returns:
        List[Dict[str, Any]]: A list containing compressed user messages and images.
    """
    
    
    output_messages = []
    accumulated_content = ""

    for index, message in enumerate(messages, start=1):
        role = message.get('role', 'Unknown').upper()
        content = message.get('content', '')

        # Handle content types
        if isinstance(content, str):
            accumulated_content += f"<{role.upper()} MESSAGE {index}>: {content.strip()}\n\n"
        elif isinstance(content, list):
            for part in content:
                if part.get('type') == 'text':
                    text = part.get('text', '').strip()
                    accumulated_content += f"<{role.upper()} MESSAGE {index}>: {text}\n\n"
                elif part.get('type') == 'image_url':
                    message = {
                        "role": "user",
                        "content": []
                    }
                    # Add accumulated content to output messages
                    if accumulated_content:
                        message["content"].append({
                            "type": "text",
                            "text": accumulated_content.strip()
                        })
                        accumulated_content = ""
                    # Add the image
                    message["content"].append(part)
                    output_messages.append(message)
                    

    # Append any remaining accumulated content
    if accumulated_content:
        output_messages.append({
            "role": "user",
            "content": accumulated_content.strip()
        })

    return output_messages

def llm_supervisor(
    instructions: str,
    provider: Optional[str] = "openai",
    supervisor_name: Optional[str] = None,
    description: Optional[str] = None,
    model: Optional[str] = DEFAULT_OPENAI_LLM_MODEL,
    system_prompt_template: Optional[str] = LLM_SUPERVISOR_SYSTEM_PROMPT_TEMPLATE,
    system_output_prompt_template: Optional[str] = LLM_SUPERVISOR_SYSTEM_PROMPT_OUTPUT_TEMPLATE,
    include_previous_messages: bool = True,
    allow_modification: bool = False,
) -> Supervisor:
    """
    Create a supervisor function that uses an LLM to make a supervision decision.
    Supports OpenAI (optionally with Langfuse) and Anthropic (optionally with Langfuse).
    If provider == "gemini", the functionality remains, but isn't a focus of this refactor.

    Parameters:
    - instructions (str): The supervision instructions.
    - supervisor_name (Optional[str]): Optional name for the supervisor.
    - description (Optional[str]): Optional description.
    - model (str): LLM model to use.
    - provider (str): LLM provider, 'openai', 'anthropic', or 'gemini'.
    - system_prompt_template (str): Template for system prompt (Jinja).
    - system_output_prompt_template (str): Template for system output prompt (Jinja).
    - include_previous_messages (bool): Whether to include the previous messages to the LLM.
    - allow_modification (bool): Whether to allow the LLM to propose modifications.

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
    if not system_output_prompt_template:
        system_output_prompt_template = LLM_SUPERVISOR_SYSTEM_PROMPT_OUTPUT_TEMPLATE

    # Compile the Jinja templates
    compiled_system_prompt_template = jinja2.Template(system_prompt_template)
    compiled_system_output_prompt_template = jinja2.Template(system_output_prompt_template)

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
        For OpenAI, uses ChatCompletion with function calling; for Anthropic, uses
        its associated Tool APIs. Supports Langfuse if enabled in settings.

        Args:
            message (Union[ChatCompletionMessage, AnthropicMessage]): The incoming message to supervise.
            supervision_context (Optional[SupervisionContext]): Additional context for supervision.
            ignored_attributes (List[str]): Attributes to ignore during supervision.
            supervision_request_id (Optional[UUID]): Optional request ID.
            previous_decision (Optional[SupervisionDecision]): Previous supervision decision.

        Returns:
            SupervisionDecision: The decision made by the supervisor.
        """

        # ------------------
        # 1. Preprocess data
        # ------------------
        preprocessed = preprocess_message(message)

        # Context for prompts
        system_message_context = {
            "instructions": instructions,
        }
        system_output_context = {
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
        system_prompt = compiled_system_prompt_template.render(**system_message_context).strip()
        system_output_prompt = compiled_system_output_prompt_template.render(**system_output_context).strip()

        # These steps build the JSON schema for the function/tool:
        supervision_decision_schema = SupervisionDecision.model_json_schema()
        if not allow_modification:
            # Hide "modified" if modifications are disabled
            supervision_decision_schema.pop("modified", None)
            if "modified" in supervision_decision_schema.get("properties", {}):
                supervision_decision_schema["properties"].pop("modified")

        # ------------------
        # 2. Provider blocks
        # ------------------
        if provider == "openai":
            # Decide if we can use Langfuse-wrapped or standard openai
            if settings.langfuse_enabled and LangfuseOpenAI is not None:
                openai_client = LangfuseOpenAI()
            else:
                openai.api_key = settings.openai_api_key
                openai_client = openai

            # Build messages for openai
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            if include_previous_messages and supervision_context:
                # Convert previous messages to user messages
                message_history_context = create_message_history_context(supervision_context.openai_messages)
                messages.extend(message_history_context)

            # Add final system-level instructions that shape function call
            messages.append(
                {"role": "system", "content": system_output_prompt}
            )

            functions = [
                {
                    "name": "supervision_decision",
                    "description": (
                        "Analyze the input based on the provided instructions and context, and make a "
                        "supervision decision: APPROVE, REJECT, ESCALATE, TERMINATE, or MODIFY. Provide a "
                        "concise and accurate explanation for your decision."
                        + (
                            " If you modify the input, include the modified content in the 'modified' field."
                            if allow_modification
                            else ""
                        )
                    ),
                    "parameters": supervision_decision_schema,
                }
            ]

            try:
                # IMPORTANT: For standard openai vs. langfuse, we might call the actual ChatCompletion differently:
                if settings.langfuse_enabled and LangfuseOpenAI is not None:
                    # If using the Langfuse-based client, we can do:
                    completion = openai_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        functions=functions,
                        function_call={"name": "supervision_decision"},
                        name="supervision_decision",  # for langfuse
                    ) #TODO: This might now be throwing pydantic warnings
                else:
                    # If fallback to standard openai:
                    completion = openai_client.chat.completions.create(
                        model=model,
                        messages=messages,
                        functions=functions,
                        function_call={"name": "supervision_decision"},
                    )

                response_message = completion.choices[0].message
                if response_message and getattr(response_message, "function_call", None):
                    response_args = response_message.function_call.arguments
                    response_data = json.loads(response_args)
                else:
                    raise ValueError("No valid function call in assistant's response.")

                # Check modifications
                if response_data.get("modified") and allow_modification:
                    modified_data = ModifiedData(
                        tool_name=response_data["modified"].get("tool_name"),
                        tool_kwargs=response_data["modified"].get("tool_args"),
                    )
                elif response_data.get("modified") and not allow_modification:
                    raise ValueError("LLM attempted to modify input, but modifications are not allowed.")
                else:
                    modified_data = None

                return SupervisionDecision(
                    decision=response_data.get("decision", "").lower().strip(),
                    modified=modified_data,
                    explanation=response_data.get("explanation", ""),
                )

            except Exception as e:
                return SupervisionDecision(
                    decision=SupervisionDecisionType.ESCALATE,
                    explanation=f"Error during OpenAI-based LLM supervision: {str(e)}",
                    modified=None,
                )

        elif provider == "anthropic":

            # Anthropic expects user messages. We'll fold the system prompt into the top-level system= param
            # And pass the final instructions as a user message.
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": system_output_prompt}
                    ],
                }
            ]

            tools = [
                {
                    "name": "supervision_decision",
                    "description": (
                        "Analyze the input (instructions, context) and produce a supervision decision: "
                        "APPROVE, REJECT, ESCALATE, TERMINATE, or MODIFY. Provide an explanation. "
                        + (
                            "If you modify the input, include the modified content in the 'modified' field."
                            if allow_modification
                            else ""
                        )
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

                # Check modifications
                if response_data.get("modified") and allow_modification:
                    mod_block = response_data["modified"]
                    modified_data = ModifiedData(
                        tool_name=mod_block.get("tool_name"),
                        tool_kwargs=mod_block.get("tool_args"),
                    )
                elif response_data.get("modified") and not allow_modification:
                    raise ValueError("LLM attempted to modify input, but modifications are not allowed.")
                else:
                    modified_data = None

                return SupervisionDecision(
                    decision=response_data.get("decision", "").lower().strip(),
                    modified=modified_data,
                    explanation=response_data.get("explanation", ""),
                )

            except Exception as e:
                return SupervisionDecision(
                    decision=SupervisionDecisionType.ESCALATE,
                    explanation=f"Error during Anthropic-based LLM supervision: {str(e)}",
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

    # Give the supervisor function a name and doc if specified
    supervisor_function.__name__ = supervisor_name if supervisor_name else "llm_supervisor"
    supervisor_function.__doc__ = description if description else supervisor_function.__doc__

    # Store some attributes for introspection
    supervisor_function.supervisor_attributes = {
        "instructions": instructions,
        "model": model,
        "provider": provider,
        "system_prompt_template": system_prompt_template,
        "system_output_prompt_template": system_output_prompt_template,
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


def browser_screen_supervisor(
    escalate_areas: Optional[List[Dict[str, int]]] = None,
    reject_areas: Optional[List[Dict[str, int]]] = None,
    expected_provider: str = "anthropic",
    expected_tool_name: str = "computer_use",
    supervisor_name: Optional[str] = None,
    description: Optional[str] = None,
) -> Supervisor:
    """
    A supervisor function ensuring that the last message is a screenshot, and that the current
    tool call is the expected computer-use tool. It then checks whether the user is clicking or
    typing within certain screen rectangles. If so, it may escalate or reject, depending on the
    areas configured.

    Parameters:
    -----------
    escalate_areas : Optional[List[Dict[str, int]]]
        A list of rectangular areas in the form:
           {"x": 100, "y": 100, "width": 50, "height": 50}
        If a click, drag, or typed action is in one of these areas, the decision is ESCALATE.

    reject_areas : Optional[List[Dict[str, int]]]
        A list of rectangular areas in the same shape as above. If the action is within one of these
        areas, the decision is REJECT.

    expected_provider : str
        Which LLM provider we expect this supervision to be used for, e.g. "anthropic" or "openai".
        If the message is not from the matching tool call, supervision is ESCALATE by default.

    expected_tool_name : str
        The name of the tool we expect to see, e.g. "computer_use". If the user calls a different
        tool, supervision is ESCALATE by default.

    supervisor_name : Optional[str]
        Name for this supervisor.

    description : Optional[str]
        Description for this supervisor.

    Returns:
    --------
    Supervisor:
        A callable that implements the logic described above.
    """
    if escalate_areas is None:
        escalate_areas = []
    if reject_areas is None:
        reject_areas = []

    @supervisor
    def supervisor_function(
        message: Union[ChatCompletionMessage, AnthropicMessage, GenerateContentResponse],
        supervision_context: Optional[SupervisionContext] = None,
        ignored_attributes: List[str] = [],
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs
    ) -> SupervisionDecision:
        # --------------------------------------------------------------------
        # 1) Confirm that the previous message was a screenshot
        #    If it wasn't, we REJECT.

        if supervision_context and len(supervision_context.messages) >= 2:
            last_msg = supervision_context.messages[-2]
            # Look for a tool call in the previous message
            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                # OpenAI style
                last_tool_call = last_msg.tool_calls[0]
                last_tool_name = getattr(last_tool_call.function, "name", None)
                last_action = getattr(last_tool_call.function, "arguments", {}).get("action")
            elif hasattr(last_msg, "content") and isinstance(last_msg.content, list):
                # Anthropic style
                last_tool_name = None
                last_action = None
                for block in last_msg.content:
                    if block.type == "tool_use":
                        last_tool_name = getattr(block, "name", None)
                        tool_input = getattr(block, "input", {})
                        if isinstance(tool_input, dict):
                            last_action = tool_input.get("action")
                        break
            elif isinstance(last_msg, GenerateContentResponse) and last_msg.parts:
                # Gemini/Google style
                last_tool_name = None
                last_action = None
                for part in last_msg.parts:
                    if part.function_call:
                        last_tool_name = part.function_call.name
                        last_action = part.function_call.args.get("action")
                        break
            else:
                last_tool_name = None
                last_action = None

            if last_tool_name != expected_tool_name or last_action != "screenshot":
                return SupervisionDecision(
                    decision=SupervisionDecisionType.REJECT,
                    explanation=(
                        f"browser_screen_supervisor: Expected last message to be a screenshot "
                        f"with tool '{expected_tool_name}', but found tool '{last_tool_name}' and action '{last_action}'."
                    ),
                    modified=None,
                )
        else:
            return SupervisionDecision(
                decision=SupervisionDecisionType.REJECT,
                explanation=(
                    "browser_screen_supervisor: Insufficient context to verify the last message "
                    "was a screenshot; rejecting."
                ),
                modified=None,
            )

        # --------------------------------------------------------------------
        # 2) Confirm that the current message calls the expected tool
        #    otherwise we ESCALATE.

        tool_name = None
        action = None
        coordinate = None

        if isinstance(message, ChatCompletionMessage):
            # OpenAI style
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                tool_name = getattr(tool_call.function, "name", None)
                action = tool_call.function.arguments.get("action")
                coordinate = tool_call.function.arguments.get("coordinate")
            else:
                return SupervisionDecision(
                    decision=SupervisionDecisionType.ESCALATE,
                    explanation="browser_screen_supervisor: No tool call present in message; escalating.",
                    modified=None,
                )
        elif isinstance(message, AnthropicMessage):
            # Anthropic style
            for block in message.content:
                if block.type == "tool_use":
                    tool_name = getattr(block, "name", None)
                    tool_input = getattr(block, "input", {})
                    if isinstance(tool_input, dict):
                        action = tool_input.get("action")
                        coordinate = tool_input.get("coordinate")
                    break
        elif isinstance(message, GenerateContentResponse):
            # Gemini/Google style
            if message.parts:
                for part in message.parts:
                    if part.function_call:
                        tool_name = part.function_call.name
                        action = part.function_call.args.get("action")
                        coordinate = part.function_call.args.get("coordinate")
                        break

        if tool_name != expected_tool_name:
            return SupervisionDecision(
                decision=SupervisionDecisionType.ESCALATE,
                explanation=(
                    f"browser_screen_supervisor: Unexpected tool '{tool_name}'. "
                    f"Expected '{expected_tool_name}'. Escalating."
                ),
                modified=None,
            )

        # --------------------------------------------------------------------
        # 3) Check if the user's action coordinates fall into any restricted area
        #    (escalate or reject). If the action is coordinate-based, we compare.

        def point_in_rect(pt_x: float, pt_y: float, rect: Dict[str, int]) -> bool:
            """Return True if (pt_x, pt_y) is within rect: {x, y, width, height}."""
            return (
                rect["x"] <= pt_x <= (rect["x"] + rect["width"])
                and rect["y"] <= pt_y <= (rect["y"] + rect["height"])
            )

        coordinate_actions = {
            "mouse_move",
            "left_click",
            "left_click_drag",
            "right_click",
            "middle_click",
            "double_click",
        }

        # If the action is coordinate-based
        if action in coordinate_actions and isinstance(coordinate, list) and len(coordinate) == 2:
            x, y = coordinate
            # Check escalate areas first
            for rect in escalate_areas:
                if point_in_rect(x, y, rect):
                    return SupervisionDecision(
                        decision=SupervisionDecisionType.ESCALATE,
                        explanation=(
                            f"browser_screen_supervisor: Coordinates ({x}, {y}) are within "
                            f"an escalate area: {rect}."
                        ),
                        modified=None,
                    )
            # Check reject areas
            for rect in reject_areas:
                if point_in_rect(x, y, rect):
                    return SupervisionDecision(
                        decision=SupervisionDecisionType.REJECT,
                        explanation=(
                            f"browser_screen_supervisor: Coordinates ({x}, {y}) are within "
                            f"a reject area: {rect}."
                        ),
                        modified=None,
                    )

        # For this minimal example, typing and key presses skip the area check
        # but you could add additional logic if desired.

        # --------------------------------------------------------------------
        # 4) If no rule triggered, we APPROVE
        return SupervisionDecision(
            decision=SupervisionDecisionType.APPROVE,
            explanation="browser_screen_supervisor: Approved; no restricted area triggered.",
            modified=None,
        )

    supervisor_function.__name__ = supervisor_name if supervisor_name else "browser_screen_supervisor"
    supervisor_function.__doc__ = description if description else supervisor_function.__doc__

    supervisor_function.supervisor_attributes = {
        "escalate_areas": escalate_areas,
        "reject_areas": reject_areas,
        "expected_tool_name": expected_tool_name,
        "expected_provider": expected_provider,
    }

    return supervisor_function