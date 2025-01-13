"""
Supervisors for handling approvals in the Asteroid SDK via Inspect AI.
"""

from functools import wraps
from typing import List, Dict, Optional, Callable, Union
from uuid import UUID
from anthropic.types.message import Message as AnthropicMessage

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.supervision_runner import SupervisionRunner
from asteroid_sdk.registration.helper import get_supervisor_chains_for_tool
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
from inspect_ai.tool import ToolCall, ToolCallView

from asteroid_sdk.supervision.helpers.anthropic_helper import AnthropicSupervisionHelper
from asteroid_sdk.supervision.helpers.openai_helper import OpenAiSupervisionHelper
from .utils import (
    transform_asteroid_approval_to_inspect_ai_approval,
    convert_state_messages_to_openai_messages,
    convert_state_output_to_openai_response,
    convert_state_messages_to_anthropic_messages,
    convert_state_output_to_anthropic_response,
)

def with_asteroid_supervision(
    supervisor_name_param: Optional[str] = None, n: Optional[int] = None
):
    """
    Decorator for common Asteroid API interactions during supervision.

    Args:
        supervisor_name_param (Optional[str]): Name of the supervisor to use. If not provided, the function's name will be used.
        n (Optional[int]): Number of tool call suggestions to generate for human approval.
    """

    def decorator(approve_func: Callable):
        @wraps(approve_func)
        async def wrapper(
            inspect_message: Optional[str] = None,
            call: Optional[ToolCall] = None,
            view: Optional[ToolCallView] = None,
            state: Optional[TaskState] = None,
            **kwargs,
        ) -> Approval:
            """
            Wrapper function to handle supervision logic.

            Args:
                inspect_message (Optional[str]): Message from Inspect AI.
                call (Optional[ToolCall]): Tool call object.
                view (Optional[ToolCallView]): Tool call view.
                state (Optional[TaskState]): Current task state.
                **kwargs: Additional arguments.

            Returns:
                Approval: The approval decision.
            """
            # Retrieve the supervision run
            run_name = str(state.sample_id)
            run = supervision_config.get_run_by_name(run_name)
            if run is None:
                raise Exception(f"Run with name {run_name} not found")
            supervision_context = run.supervision_context
            run_id = run.run_id

            # Determine the model type
            if state.model.api == "openai":
                model_provider_helper = OpenAiSupervisionHelper()

                # Convert state messages to OpenAI format
                openai_messages = convert_state_messages_to_openai_messages(state.messages[:-1])

                # Prepare request kwargs
                request_kwargs = {
                    "messages": openai_messages,
                    "model": state.model.name,
                }

                # Convert state output to OpenAI response
                response = convert_state_output_to_openai_response(state.output)
                supervision_context.update_messages(
                    request_kwargs["messages"]
                )

            elif state.model.api == "anthropic":
                model_provider_helper = AnthropicSupervisionHelper()

                # Convert state messages to Anthropic format
                anthropic_messages = convert_state_messages_to_anthropic_messages(state.messages[:-1])

                # Prepare request kwargs
                request_kwargs = {
                    "messages": anthropic_messages,
                    "model": state.model.name,
                }

                # Convert state output to Anthropic response
                response = convert_state_output_to_anthropic_response(state.output)
                supervision_context.update_messages(
                    request_kwargs["messages"],
                    anthropic=True,
                    system_message=request_kwargs.get("system", None),
                )

            else:
                raise Exception(f"Model API {state.model.api} not supported")

            # Initialize API logger and supervision runner
            client = Client(
                base_url=settings.api_url,
                headers={"X-Asteroid-Api-Key": f"{settings.api_key}"},
            )
            api_logger = APILogger(client, model_provider_helper)
            supervision_runner = SupervisionRunner(client, api_logger, model_provider_helper)

            # Log the interaction
            create_new_chat_response = api_logger.log_llm_interaction(
                response,
                request_kwargs,
                run_id,
            )
            choice_ids = create_new_chat_response.choice_ids

            tool_id = choice_ids[0].tool_call_ids[0].tool_id
            tool_call_id = choice_ids[0].tool_call_ids[0].tool_call_id

            tool = supervision_runner.get_tool(tool_id)
            response_data_tool_calls = model_provider_helper.get_tool_call_from_response(response)
            tool_call = response_data_tool_calls[0]

            # Get supervisor chains for the tool
            supervisor_chains = get_supervisor_chains_for_tool(tool_id)
            if not supervisor_chains:
                print(f"No supervisors found for tool ID {tool_id}.")
                return transform_asteroid_approval_to_inspect_ai_approval(
                    SupervisionDecision(
                        decision=SupervisionDecisionType.APPROVE,
                        explanation="No supervisors configured. Approval granted.",
                    )
                )

            # Find the supervisor by name
            supervisor_name = supervisor_name_param or approve_func.__name__
            supervisor_chain_id = None
            position_in_chain = None
            supervisor = None
            for chain in supervisor_chains:
                for idx, _supervisor in enumerate(chain.supervisors):
                    if _supervisor.name == supervisor_name:
                        supervisor = _supervisor
                        position_in_chain = idx
                        supervisor_chain_id = chain.chain_id
                        break
                if supervisor:
                    break

            if supervisor is None:
                raise Exception(f"Supervisor {supervisor_name} not found in any chain")

            # Execute the supervisor
            decision = await supervision_runner.execute_supervisor(
                supervisor=supervisor,
                tool=tool,
                tool_call=tool_call,
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

            # Handle modify decision
            if decision.decision == SupervisionDecisionType.MODIFY:
                decision.modified.original_inspect_ai_call = call

            print(f"Returning approval: {decision.decision}")
            return transform_asteroid_approval_to_inspect_ai_approval(decision)

        wrapper.__name__ = supervisor_name_param or approve_func.__name__
        return wrapper

    return decorator


@approver
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

        # Call the supervisor function to get the decision
        decision = human_supervisor_func(
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


@approver
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
