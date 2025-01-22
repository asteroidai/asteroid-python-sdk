"""
Supervisors for handling approvals in the Asteroid SDK via Inspect AI.
"""

from functools import wraps
from typing import List, Optional, Callable, Union
from uuid import UUID
import json
from anthropic.types.message import Message as AnthropicMessage

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.supervision_runner import SupervisionRunner
from asteroid_sdk.registration.helper import get_supervisor_chains_for_tool, get_run_messages, APIClientFactory
from asteroid_sdk.settings import settings
from asteroid_sdk.supervision.base_supervisors import human_supervisor, llm_supervisor
from asteroid_sdk.supervision.config import (
    supervision_config,
    SupervisionDecision,
    SupervisionDecisionType,
    SupervisionContext,
)
from inspect_ai.approval import Approval, Approver, approver
from inspect_ai.model._chat_message import ChatMessage
from inspect_ai.solver import TaskState
from inspect_ai.tool import ToolCall as InspectAIToolCall, ToolCallView as InspectAIToolCallView

from anthropic.types.text_block import TextBlock
from anthropic.types.tool_use_block import ToolUseBlock
from anthropic.types.text_block import TextBlock
from anthropic.types.tool_use_block import ToolUseBlock
from asteroid_sdk.supervision.helpers.anthropic_helper import AnthropicSupervisionHelper
from asteroid_sdk.supervision.helpers.openai_helper import OpenAiSupervisionHelper
from asteroid_sdk.supervision.helpers.gemini_helper import GeminiHelper
from .utils import (
    transform_asteroid_approval_to_inspect_ai_approval,
    convert_state_messages_to_openai_messages,
    convert_state_output_to_openai_response,
    convert_state_messages_to_anthropic_messages,
    convert_state_output_to_anthropic_response,
    convert_state_messages_to_gemini_messages,
    convert_state_output_to_gemini_response,
)
import logging
from asteroid_sdk.supervision.helpers.model_provider_helper import Provider

# Mappings for model provider helpers and conversion functions
MODEL_PROVIDER_HELPERS = {
    "openai": OpenAiSupervisionHelper,
    "anthropic": AnthropicSupervisionHelper,
    "google": GeminiHelper,
}

CONVERT_STATE_MESSAGES_TO_MESSAGES = {
    "openai": convert_state_messages_to_openai_messages,
    "anthropic": convert_state_messages_to_anthropic_messages,
    "google": convert_state_messages_to_gemini_messages,
}

CONVERT_STATE_OUTPUT_TO_RESPONSE = {
    "openai": convert_state_output_to_openai_response,
    "anthropic": convert_state_output_to_anthropic_response,
    "google": convert_state_output_to_gemini_response,
}

EXTRACT_TOOL_CALLS_FROM_RESPONSE = {
    "openai": lambda response: response.choices[0].message.tool_calls,
    "anthropic": lambda response: [
        content_block for content_block in response.content if isinstance(content_block, ToolUseBlock)
    ],
    "google": lambda response: GeminiHelper().get_tool_call_from_response(response),
}

def with_asteroid_supervision(
    supervisor_name_param: Optional[str] = None,
    n: Optional[int] = None
):
    """
    Decorator for common Asteroid API interactions during supervision.

    Args:
        supervisor_name_param (Optional[str]): Name of the supervisor to use.
            If not provided, the function's name will be used.
        n (Optional[int]): Number of tool call suggestions to generate for human approval.
    """

    def decorator(approve_func: Callable):
        @wraps(approve_func)
        async def wrapper(
            inspect_message: Optional[str] = None,
            call: Optional[InspectAIToolCall] = None,
            view: Optional[InspectAIToolCallView] = None,
            state: Optional[TaskState] = None,
            **kwargs,
        ) -> Approval:
            """
            Wrapper function to handle supervision logic.

            Args:
                inspect_message (Optional[str]): Message from Inspect AI.
                call (Optional[InspectAIToolCall]): Tool call object.
                view (Optional[InspectAIToolCallView]): Tool call view.
                state (Optional[TaskState]): Current task state.
                **kwargs: Additional arguments.

            Returns:
                Approval: The approval decision.
            """

            # Retrieve the supervision run using the sample ID from the state
            run_name = str(state.sample_id)
            run = supervision_config.get_run_by_name(run_name)
            if run is None:
                raise Exception(f"Run with name {run_name} not found")
            supervision_context = run.supervision_context
            run_id = run.run_id

            # Determine the model provider helper based on the model API
            if state.model.api == "openai":
                model_provider_helper = OpenAiSupervisionHelper()
            elif state.model.api == "anthropic":
                model_provider_helper = AnthropicSupervisionHelper()
            elif state.model.api == "google":
                model_provider_helper = GeminiHelper()
            else:
                raise Exception(f"Model API {state.model.api} not supported")
            
            # Initialize the client, API logger, and supervision runner
            client = APIClientFactory.get_client()
            api_logger = APILogger(client, model_provider_helper)
            supervision_runner = SupervisionRunner(client, api_logger, model_provider_helper)

            # Get the existing messages for the run
            asteroid_messages = get_run_messages(run_id=run_id, index=0)

            # Initialize variables for tool call and tool IDs
            tool_call_idx = None
            tool_id = None
            tool_call_id = None
            tool_call_data = None
            tool = None

            if len(asteroid_messages) != 0:
                # Get the last message from the run
                last_message = asteroid_messages[-1]
                if last_message.tool_calls:
                    # Match Asteroid's tool call ID to the Inspect AI tool call ID
                    for idx, _tool_call in enumerate(last_message.tool_calls):
                        if state.model.api == "google":
                            if _tool_call.name == call.function and json.loads(_tool_call.arguments) == call.arguments:
                                tool_call_idx = idx
                                tool_id = _tool_call.tool_id
                                tool_call_id = _tool_call.id
                                tool_call_data = _tool_call # TODO: This might need fixing we might have to instantiate new ToolCall, not pass AsteroidToolCall
                                tool = supervision_runner.get_tool(tool_id)
                                break
                        else:
                            if _tool_call.id == call.id:
                                tool_call_idx = idx
                                tool_id = _tool_call.tool_id
                                tool_call_id = _tool_call.id
                                tool_call_data = _tool_call
                                tool = supervision_runner.get_tool(tool_id)
                                break
                        
            # If no existing messages or tool call not found, log the first message
            if len(asteroid_messages) == 0 or tool_call_idx is None:
                # Handle provider-specific logic
                if state.model.api == "openai":
                    # OpenAI provider handling
                    request_kwargs, response, response_tool_calls = handle_openai_provider(state, supervision_context)
                elif state.model.api == "anthropic":
                    # Anthropic provider handling
                    request_kwargs, response, response_tool_calls = handle_anthropic_provider(state, supervision_context)
                elif state.model.api == "google":
                    # Google provider handling
                    request_kwargs, response, response_tool_calls = handle_google_provider(state, supervision_context)
                else:
                    raise Exception(f"Model API {state.model.api} not supported")

                # Log the interaction with the LLM and get the choice IDs
                create_new_chat_response = api_logger.log_llm_interaction(
                    response,
                    request_kwargs,
                    run_id,
                )
                choice_ids = create_new_chat_response.choice_ids

                # Match Asteroid's tool call ID to the Inspect AI tool call ID
                tool_call_idx, tool_id, tool_call_id = match_tool_call_ids(
                    response_tool_calls, call, choice_ids, state.model.api
                )
                tool = supervision_runner.get_tool(tool_id)
                tool_call_data = model_provider_helper.get_tool_call_from_response(response)[tool_call_idx]

            # Get supervisor chains for the tool
            supervisor_chains = get_supervisor_chains_for_tool(tool_id)
            if not supervisor_chains:
                logging.info(f"No supervisors found for tool ID {tool_id}.")
                return transform_asteroid_approval_to_inspect_ai_approval(
                    SupervisionDecision(
                        decision=SupervisionDecisionType.APPROVE,
                        explanation="No supervisors configured. Approval granted.",
                    )
                )

            # Find the supervisor by name within the supervisor chains
            supervisor_name = supervisor_name_param or approve_func.__name__
            supervisor, supervisor_chain_id, position_in_chain = find_supervisor_in_chains(
                supervisor_chains, supervisor_name
            )
            if supervisor is None:
                raise Exception(f"Supervisor {supervisor_name} not found in any chain")

            # Execute the supervisor and get the decision
            decision = await supervision_runner.execute_supervisor(
                supervisor=supervisor,
                tool=tool,
                tool_call=tool_call_data,
                tool_call_id=tool_call_id,
                position_in_chain=position_in_chain,
                supervision_context=supervision_context,
                supervisor_chain_id=supervisor_chain_id,
                execution_mode="supervision",
                supervisor_func=approve_func,
            )

            if decision is None:
                raise Exception(
                    f"No decision made for supervisor {supervisor_name} in chain {supervisor_chain_id}"
                )

            # Handle modify decision and attach original call if needed
            if decision.decision == SupervisionDecisionType.MODIFY and decision.modified is not None:
                decision.modified.original_inspect_ai_call = call
            logging.info(f"Returning approval: {decision.decision}")
            return transform_asteroid_approval_to_inspect_ai_approval(decision)

        # Set the wrapper function name
        wrapper.__name__ = supervisor_name_param or approve_func.__name__
        return wrapper

    return decorator

def handle_openai_provider(state: TaskState, supervision_context: SupervisionContext):
    """
    Handle OpenAI provider-specific logic.

    Args:
        state (TaskState): Current task state.
        supervision_context (SupervisionContext): The supervision context.

    Returns:
        Tuple of (request_kwargs, response, response_tool_calls)
    """
    # Convert state messages to OpenAI format
    openai_messages = convert_state_messages_to_openai_messages(state.messages[:-1])

    # Prepare request kwargs
    request_kwargs = {
        "messages": openai_messages,
        "model": state.model.name,
    }

    # Convert state output to OpenAI response
    response = convert_state_output_to_openai_response(state.output)

    # Update the supervision context with messages
    supervision_context.update_messages(request_kwargs, provider=Provider.OPENAI)

    # Extract tool calls from the response
    response_tool_calls = response.choices[0].message.tool_calls

    return request_kwargs, response, response_tool_calls

def handle_anthropic_provider(state: TaskState, supervision_context: SupervisionContext):
    """
    Handle Anthropic provider-specific logic.

    Args:
        state (TaskState): Current task state.
        supervision_context (SupervisionContext): The supervision context.

    Returns:
        Tuple of (request_kwargs, response, response_tool_calls)
    """
    # Convert state messages to Anthropic format
    anthropic_messages = convert_state_messages_to_anthropic_messages(state.messages[:-1])

    # Prepare request kwargs
    request_kwargs = {
        "messages": anthropic_messages,
        "model": state.model.name,
    }

    # Convert state output to Anthropic response
    response = convert_state_output_to_anthropic_response(state.output)

    # Update the supervision context with messages
    supervision_context.update_messages(
        request_kwargs,
        provider=Provider.ANTHROPIC,
        system_message=request_kwargs.get("system", None),
    )

    # Extract tool calls from the response
    response_tool_calls = [
        content_block for content_block in response.content if isinstance(content_block, ToolUseBlock)
    ]

    return request_kwargs, response, response_tool_calls

def handle_google_provider(state: TaskState, supervision_context: SupervisionContext):
    """
    Handle Google provider-specific logic.

    Args:
        state (TaskState): Current task state.
        supervision_context (SupervisionContext): The supervision context.

    Returns:
        Tuple of (request_kwargs, response, response_tool_calls)
    """
    # Convert state messages to Gemini format
    gemini_messages = convert_state_messages_to_gemini_messages(state.messages[:-1])

    # Prepare request kwargs
    request_kwargs = {
        "contents": gemini_messages,
        "model": state.model.name,
    }

    # Convert state output to Gemini response
    response = convert_state_output_to_gemini_response(state.output)

    # Update the supervision context with messages
    supervision_context.update_messages(request_kwargs, provider=Provider.GEMINI)

    # Extract tool calls from the response
    response_tool_calls = GeminiHelper().get_tool_call_from_response(response)

    return request_kwargs, response, response_tool_calls

def match_tool_call_ids(response_tool_calls: List, call: InspectAIToolCall, choice_ids: List,
                        provider: str):
    """
    Match Asteroid's tool call ID to the Inspect AI tool call ID.

    Args:
        response_tool_calls (List): List of tool calls from the response.
        call (ToolCall): The original ToolCall object from Inspect AI.
        choice_ids (List): List of choice IDs from the API response.
        provider (str): The model provider.
    Returns:
        Tuple of (tool_call_idx, tool_id, tool_call_id)
    """
    for idx, _tool_call in enumerate(response_tool_calls):
        if provider == "google":
            # There are no ids in Gemini we need to match on the function name and arguments
            if _tool_call.tool_name == call.function and _tool_call.tool_params == call.arguments:
                break
        else: 
            if _tool_call.id == call.id:
                break
    tool_id = choice_ids[0].tool_call_ids[idx].tool_id
    tool_call_id = choice_ids[0].tool_call_ids[idx].tool_call_id
    return idx, tool_id, tool_call_id

def find_supervisor_in_chains(supervisor_chains: List, supervisor_name: str):
    """
    Find the supervisor by name within the supervisor chains.

    Args:
        supervisor_chains (List): List of supervisor chains.
        supervisor_name (str): Name of the supervisor to find.

    Returns:
        Tuple of (supervisor, supervisor_chain_id, position_in_chain)
    """
    for chain in supervisor_chains:
        for idx, _supervisor in enumerate(chain.supervisors):
            if _supervisor.name == supervisor_name:
                supervisor = _supervisor
                position_in_chain = idx
                supervisor_chain_id = chain.chain_id
                return supervisor, supervisor_chain_id, position_in_chain
    return None, None, None

@approver(name="human_approver")
def human_approver(timeout: int = 86400, n: int = 3) -> Approver:
    """
    Human approver function for Inspect AI.

    Args:
        timeout (int): Timeout for the human approval (in seconds).
        n (int): Number of tool call suggestions to generate for human approval.

    Returns:
        Approver: The human approver.
    """

    async def approve(
        message: Optional[Union[ChatMessage, AnthropicMessage]] = None,
        supervision_context: Optional[SupervisionContext] = None,
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs,
    ) -> Approval:
        """
        Approve function for human supervision.

        Args:
            message (Optional[Union[ChatMessage, AnthropicMessage]]): The message to approve.
            supervision_context (Optional[SupervisionContext]): The supervision context.
            supervision_request_id (Optional[UUID]): The supervision request ID.
            previous_decision (Optional[SupervisionDecision]): The previous supervision decision.
            **kwargs: Additional arguments.

        Returns:
            Approval: The approval decision.
        """
        if supervision_request_id is None:
            raise ValueError("Supervision request ID is required")
        
        # Instantiate the human supervisor function
        human_supervisor_func = human_supervisor(
            timeout=timeout,
            n=n,
        )

        # Call the supervisor function to get the decision asynchronously
        decision = await human_supervisor_func(
            message=message,
            supervision_request_id=supervision_request_id,
            **kwargs,
        )
        
        return decision

    # Set supervisor attributes
    approve.__name__ = "human_approver"
    approve.supervisor_attributes = {
        "timeout": timeout,
        "n": n,
    }

    # Apply the decorator
    decorated_approve = with_asteroid_supervision(
        supervisor_name_param="human_approver"
    )(approve)
    return decorated_approve


@approver(name="llm_approver")
def llm_approver(
    instructions: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    system_prompt: Optional[str] = None,
    include_previous_messages: bool = False,
    allow_modification: bool = False,
) -> Approver:
    """
    LLM approver function for Inspect AI.

    Args:
        instructions (str): Instructions for the LLM.
        model (Optional[str]): Model name.
        provider (Optional[str]): Model provider.
        system_prompt (Optional[str]): System prompt template.
        include_previous_messages (bool): Whether to include previous messages.
        allow_modification (bool): Whether to allow modification.

    Returns:
        Approver: The LLM approver.
    """

    async def approve(
        message: Optional[Union[ChatMessage, AnthropicMessage]] = None,
        supervision_context: Optional[SupervisionContext] = None,
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs,
    ) -> Approval:
        """
        Approve function for LLM supervision.

        Args:
            message (Optional[Union[ChatMessage, AnthropicMessage]]): The message to approve.
            supervision_context (Optional[SupervisionContext]): The supervision context.
            supervision_request_id (Optional[UUID]): The supervision request ID.
            previous_decision (Optional[SupervisionDecision]): The previous supervision decision.
            **kwargs: Additional arguments.

        Returns:
            Approval: The approval decision.
        """
        # Instantiate the LLM supervisor function
        llm_supervisor_func = llm_supervisor(
            instructions=instructions,
            model=model,
            provider=provider,
            system_prompt_template=system_prompt,
            include_previous_messages=include_previous_messages,
            allow_modification=allow_modification,
        )

        # Call the supervisor function to get the decision
        decision = llm_supervisor_func(
            message=message,
            supervision_context=supervision_context,
            ignored_attributes=[],
            supervision_request_id=supervision_request_id,
            previous_decision=previous_decision,
        )
        return decision

    # Set supervisor attributes
    approve.__name__ = "llm_approver"
    approve.supervisor_attributes = {
        "instructions": instructions,
        "model": model,
        "system_prompt": system_prompt,
        "include_previous_messages": include_previous_messages,
    }

    # Apply the decorator
    decorated_approve = with_asteroid_supervision(
        supervisor_name_param="llm_approver"
    )(approve)
    return decorated_approve
