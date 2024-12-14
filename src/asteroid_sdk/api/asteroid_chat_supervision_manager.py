"""
Shared logging functionality for API wrappers.
"""

import asyncio
import base64
import copy
import json
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID

from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message import (
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
)

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.generated.asteroid_api_client.api.run.create_new_chat import (
    sync_detailed as create_new_chat_sync_detailed,
)
from asteroid_sdk.api.generated.asteroid_api_client.api.tool import get_tool
from asteroid_sdk.api.generated.asteroid_api_client.models import SentinelChat, ChatIds
from asteroid_sdk.api.generated.asteroid_api_client.models.supervisor_type import SupervisorType
from asteroid_sdk.supervision.config import ExecutionMode
from asteroid_sdk.api.generated.asteroid_api_client.models.tool import Tool
from asteroid_sdk.registration.helper import (
    get_supervisor_chains_for_tool,
    send_supervision_request,
    send_supervision_result,
)
from asteroid_sdk.settings import settings
from asteroid_sdk.supervision.config import (
    MultiSupervisorResolution,
    RejectionPolicy,
    SupervisionDecision,
    SupervisionDecisionType,
    get_supervision_config,
)


class AsteroidLoggingError(Exception):
    """Raised when there's an error logging to Asteroid API."""
    pass


class AsteroidChatSupervisionManager:
    """Handles logging to the Asteroid API, including supervision and resampling."""

    def __init__(self, client: Client, api_logger: APILogger):
        """
        Initialize the API logger with the given API key.

        :param api_key: The API key for authenticating with the Sentinel API.
        """
        self.client = client
        self.api_logger = api_logger

    def log_request(self, request_data: Dict[str, Any], run_id: UUID) -> None:
        """
        Log the request data. Currently a no-op as the Asteroid API doesn't require request data
        to be sent separately; it is sent along with the response in `log_response`.

        :param request_data: The data of the request to log.
        :param run_id: The unique identifier for the run.
        """
        pass  # No action required.

    def handle_language_model_interaction(
        self,
        response: ChatCompletion,
        request_kwargs: Dict[str, Any],
        run_id: UUID,
        execution_mode: str,
        completions: Any,
        args: Any,
        chat_supervisors: Optional[List[Callable]] = None
    ) -> Optional[ChatCompletion]:
        """
        Send the raw response data to the Sentinel API, and process tool calls
        through supervision and resampling if necessary.

        :param response: The response from the OpenAI API.
        :param request_kwargs: The request keyword arguments used in the OpenAI API call.
        :param run_id: The unique identifier for the run.
        :param execution_mode: The execution mode for the logging.
        :param completions: The completions object (e.g., the OpenAI.Completions class).
        :param args: Additional arguments for the completions.create call.
        :param chat_supervisors: The chat supervisors to use for supervision.
        :return: Potentially modified response after supervision and resampling, or None.
        """
        try:
            response_data = response if isinstance(response, dict) else response.to_dict()
            create_new_chat_response = self.api_logger.log_llm_interaction(
                response,
                request_kwargs,
                run_id,
            )
            choice_ids = create_new_chat_response.choice_ids

            # Check for the presence of tool calls in the response
            response_data_tool_calls = response_data.get('choices', [{}])[0].get('message', {}).get('tool_calls')
            if not response_data_tool_calls:
                if not chat_supervisors:
                    print("No tool calls found in response and no chat supervisors provided, skipping supervision checks")
                    return None
                else:
                    print("No tool calls found in response, but chat supervisors provided, executing chat supervisors")
                    # TODO: Execute chat supervisors

            # Execute tool call supervisors
            # Retrieve the supervision configuration
            supervision_config = get_supervision_config()

            # Get the run by the run_id to retrieve the supervision context
            run = supervision_config.get_run_by_id(run_id)
            if not run:
                print(f"Run not found for ID: {run_id}")
                return None

            supervision_context = run.supervision_context
            # Update messages on the supervision context - This is so that the supervisor can see the messages history
            # TODO: The messages could be updated in a more elegant way
            supervision_context.update_messages(request_kwargs['messages'])

            # Extract execution settings from the supervision configuration

            new_response_messages = self.handle_tool_calls_from_llm_response(args, choice_ids, completions, execution_mode,
                                                                             request_kwargs, response, response_data_tool_calls,
                                                                             run_id, supervision_context)

            # Construct the new response with the potentially modified messages
            new_response = copy.deepcopy(response)
            for idx_message, message in enumerate(new_response_messages):
                new_response.choices[idx_message].message = message

            if execution_mode == ExecutionMode.MONITORING:
                return response
            return new_response
        except Exception as e:
            # Handle exceptions and raise a custom error
            print(f"\n=== ERROR DETAILS ===")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            if e.__traceback__ is not None:
                print(f"Error occurred at line {e.__traceback__.tb_lineno}")
            else:
                print("No traceback available.")
            raise AsteroidLoggingError(f"Failed to log response: {str(e)}") from e

    def handle_tool_calls_from_llm_response(
            self,
            args: Any,
            choice_ids: List[ChatIds],
            completions,
            execution_mode,
            request_kwargs,
            response,
            response_data_tool_calls,
            run_id: UUID,
            supervision_context
    ):
        supervision_config = get_supervision_config()
        allow_tool_modifications = supervision_config.execution_settings.get('allow_tool_modifications', False)
        rejection_policy = supervision_config.execution_settings.get('rejection_policy', 'resample_with_feedback')
        n_resamples = supervision_config.execution_settings.get('n_resamples', 3)
        multi_supervisor_resolution = supervision_config.execution_settings.get('multi_supervisor_resolution', 'all_must_approve')
        remove_feedback_from_context = supervision_config.execution_settings.get('remove_feedback_from_context', False)

        new_response_messages: List[Any] = []
        # Iterate over all the tool calls to process each one
        for idx, tool_call in enumerate(response_data_tool_calls):
            # Convert tool_call to ChatCompletionMessageToolCall if necessary
            tool_call = ChatCompletionMessageToolCall(**tool_call)
            tool_id = choice_ids[idx].tool_call_ids[0].tool_id
            tool_call_id = choice_ids[idx].tool_call_ids[0].tool_call_id

            # Process the tool call with supervision
            processed_tool_call, all_decisions, modified = self.process_tool_call(
                tool_call=tool_call,
                tool_id=tool_id,
                tool_call_id=tool_call_id,
                supervision_context=supervision_context,
                allow_tool_modifications=allow_tool_modifications,
                multi_supervisor_resolution=multi_supervisor_resolution,
                execution_mode=execution_mode
            )

            if modified and processed_tool_call:
                # If the tool call was modified, run the supervision process again without modifications allowed
                final_tool_call, all_decisions, modified = self.process_tool_call(
                    tool_call=processed_tool_call,
                    tool_id=tool_id,
                    tool_call_id=tool_call_id,
                    supervision_context=supervision_context,
                    allow_tool_modifications=False,
                    multi_supervisor_resolution=multi_supervisor_resolution,
                    execution_mode=execution_mode
                )
                new_response_messages.append(final_tool_call)
            elif not processed_tool_call:
                # If the tool call was rejected, handle based on the rejection policy
                if rejection_policy == RejectionPolicy.RESAMPLE_WITH_FEEDBACK:
                    # Attempt to resample the response with feedback
                    resampled_response = self.handle_rejection_with_resampling(
                        tool_call=tool_call,
                        all_decisions=all_decisions,
                        completions=completions,
                        request_kwargs=request_kwargs,
                        args=args,
                        run_id=run_id,
                        n_resamples=n_resamples,
                        supervision_context=supervision_context,
                        rejection_policy=rejection_policy,
                        multi_supervisor_resolution=multi_supervisor_resolution,
                        remove_feedback_from_context=remove_feedback_from_context,
                        execution_mode=execution_mode
                    )
                    if resampled_response:
                        new_response_messages.append(resampled_response)
                else:
                    # Handle other rejection policies if necessary
                    pass
            else:
                # Approved tool call, add the original message tool call
                new_response_messages.append(response.choices[idx].message)

        return new_response_messages


    def process_tool_call(
        self,
        tool_call: ChatCompletionMessageToolCall,
        tool_id: str,
        tool_call_id: str,
        supervision_context: Any,
        allow_tool_modifications: bool,
        multi_supervisor_resolution: str,
        execution_mode: str
    ) -> tuple[Optional[ChatCompletionMessageToolCall], Any, bool]:
        """
        Process a single tool call through supervision.

        :param tool_call: The tool call to process.
        :param tool_id: The ID of the tool being called.
        :param tool_call_id: The ID of the tool call.
        :param supervision_context: The context for supervision.
        :param multi_supervisor_resolution: How to resolve multiple supervisor decisions.
        :return: A tuple containing the processed tool call, decisions, and modification status.
        """

        # Get the supervisors chains for the tool
        supervisors_chains = get_supervisor_chains_for_tool(tool_id, self.client)

        # Retrieve the tool object
        tool = self.get_tool(tool_id)
        if not tool:
            return None, None, False

        if not supervisors_chains:
            print(f"No supervisors found for function {tool_id}. Executing function.")
            return tool_call, None, False

        # Run all supervisors in the chains
        supervisor_chain_decisions = self.run_supervisor_chains(
            supervisors_chains=supervisors_chains,
            tool=tool,
            tool_call=tool_call,
            tool_call_id=tool_call_id,
            supervision_context=supervision_context,
            multi_supervisor_resolution=multi_supervisor_resolution,
            execution_mode=execution_mode
        )

        final_supervisor_chain_decisions = [chain_decisions[-1] for chain_decisions in supervisor_chain_decisions]

        # Determine the outcome based on supervisor decisions
        if multi_supervisor_resolution == MultiSupervisorResolution.ALL_MUST_APPROVE and all(
                decision.decision == SupervisionDecisionType.APPROVE for decision in final_supervisor_chain_decisions
        ):
            # Approved
            return tool_call, supervisor_chain_decisions, False
        elif allow_tool_modifications and final_supervisor_chain_decisions[-1].decision == SupervisionDecisionType.MODIFY:
            # Modified
            return supervisor_chain_decisions[-1].modified.openai_tool_call, supervisor_chain_decisions, True
        else:
            # Rejected
            return None, supervisor_chain_decisions, False

    def get_tool(self, tool_id: UUID) -> Optional[Tool]:
        """
        Retrieve the tool object by its ID.

        :param tool_id: The ID of the tool.
        :return: The tool object if found, else None.
        """
        # Retrieve the tool from the API
        tool_response = get_tool.sync_detailed(tool_id=tool_id, client=self.client)
        if tool_response and tool_response.parsed and isinstance(tool_response.parsed, Tool):
            return tool_response.parsed
        print(f"Failed to get tool for ID {tool_id}. Skipping.")
        return None

    def run_supervisor_chains(
        self,
        supervisors_chains: Any,
        tool: Tool,
        tool_call: ChatCompletionMessageToolCall,
        tool_call_id: str,
        supervision_context: Any,
        multi_supervisor_resolution: str,
        execution_mode: str
    ) -> List[List[SupervisionDecision]]:
        """
        Run all supervisor chains for a tool call.

        :param supervisors_chains: The supervisor chains to run.
        :param tool: The tool being called.
        :param tool_call: The tool call.
        :param tool_call_id: The ID of the tool call.
        :param supervision_context: The supervision context.
        :param multi_supervisor_resolution: How to resolve multiple supervisor decisions.
        :return: A list of all supervision decisions.
        """
        all_decisions = []
        for supervisor_chain in supervisors_chains:
            chain_decisions = self.run_supervisors_in_chain(
                supervisor_chain=supervisor_chain,
                tool=tool,
                tool_call=tool_call,
                tool_call_id=tool_call_id,
                supervision_context=supervision_context,
                supervisor_chain_id=supervisor_chain.chain_id,
                execution_mode=execution_mode
            )
            all_decisions.extend([chain_decisions])
            last_decision = chain_decisions[-1]
            if multi_supervisor_resolution == MultiSupervisorResolution.ALL_MUST_APPROVE and last_decision.decision in [
                SupervisionDecisionType.ESCALATE,
                SupervisionDecisionType.REJECT,
                SupervisionDecisionType.TERMINATE
            ]:
                # If all supervisors must approve and one rejects, we can stop
                break
            elif last_decision.decision == SupervisionDecisionType.MODIFY:
                # If modified, we need to run the supervision again with the modified tool call
                break
        return all_decisions

    def run_supervisors_in_chain(
        self,
        supervisor_chain: Any,
        tool: Tool,
        tool_call: ChatCompletionMessageToolCall,
        tool_call_id: str,
        supervision_context: Any,
        supervisor_chain_id: str,
        execution_mode: str
    ) -> List[SupervisionDecision]:
        """
        Run each supervisor in a chain and collect decisions.

        :param supervisor_chain: The supervisor chain to run.
        :param tool: The tool being called.
        :param tool_call: The tool call.
        :param tool_call_id: The ID of the tool call.
        :param supervision_context: The supervision context.
        :param supervisor_chain_id: The ID of the supervisor chain.
        :return: A list of decisions from the supervisors.
        """
        chain_decisions = []
        for position_in_chain, supervisor in enumerate(supervisor_chain.supervisors):
            decision = self.execute_supervisor(
                supervisor=supervisor,
                tool=tool,
                tool_call=tool_call,
                tool_call_id=tool_call_id,
                position_in_chain=position_in_chain,
                supervision_context=supervision_context,
                supervisor_chain_id=supervisor_chain_id,
                execution_mode=execution_mode
            )
            if decision is None:
                # No decision made, break the chain
                break
            chain_decisions.append(decision)
            if decision.decision not in [SupervisionDecisionType.ESCALATE]:
                # If not escalating, stop processing
                break
        return chain_decisions

    def execute_supervisor(
        self,
        supervisor: Any,
        tool: Tool,
        tool_call: ChatCompletionMessageToolCall,
        tool_call_id: str,
        position_in_chain: int,
        supervision_context: Any,
        supervisor_chain_id: str,
        execution_mode: str
    ) -> Optional[SupervisionDecision]:
        """
        Execute a single supervisor and return its decision.

        :param supervisor: The supervisor to execute.
        :param tool: The tool being called.
        :param tool_call: The tool call.
        :param tool_call_id: The ID of the tool call.
        :param position_in_chain: The position of the supervisor in the chain.
        :param supervision_context: The supervision context.
        :param supervisor_chain_id: The ID of the supervisor chain.
        :param execution_mode: The execution mode.
        :return: The supervisor's decision, or None if no function found.
        """
        # Send supervision request
        supervision_request_id = send_supervision_request(
            tool_call_id=tool_call_id,
            supervisor_id=supervisor.id,
            supervisor_chain_id=supervisor_chain_id,
            position_in_chain=position_in_chain
        )

        # Get the supervisor function from the context
        supervisor_func = supervision_context.get_supervisor_by_id(supervisor.id)
        if not supervisor_func:
            print(f"No local supervisor function found for ID {supervisor.id}. Skipping.")
            return None


        if supervisor.type == SupervisorType.HUMAN_SUPERVISOR and execution_mode == ExecutionMode.MONITORING:
            # If the supervisor is a human superviso and we are in monitoring mode, we automatically approve
            decision = SupervisionDecision(decision=SupervisionDecisionType.APPROVE)
        else:
            # Call the supervisor function to get a decision
            decision = call_supervisor_function(
                supervisor_func=supervisor_func,
                tool=tool,
                tool_call=tool_call,
                supervision_context=supervision_context,
                supervision_request_id=supervision_request_id
            )
        print(f"Supervisor decision: {decision.decision}")

        # Send supervision result back if not a human supervisor
        if supervisor.type != SupervisorType.HUMAN_SUPERVISOR or execution_mode == ExecutionMode.MONITORING:
            send_supervision_result(
                tool_call_id=tool_call_id,
                supervision_request_id=supervision_request_id,
                decision=decision,
            )

        return decision

    def handle_rejection_with_resampling(
        self,
        tool_call: ChatCompletionMessageToolCall,
        all_decisions: Any,
        completions: Any,
        request_kwargs: Dict[str, Any],
        args: Any,
        run_id: UUID,
        n_resamples: int,
        supervision_context: Any,
        rejection_policy: str,
        multi_supervisor_resolution: str,
        remove_feedback_from_context: bool,
        execution_mode: str
    ) -> Optional[ChatCompletionMessage]:
        """
        Handle rejected tool calls by attempting to resample responses with supervisor feedback.

        :param tool_call: The original tool call.
        :param all_decisions: All decisions from supervisors.
        :param completions: The completions object.
        :param request_kwargs: The original request keyword arguments.
        :param args: Additional arguments.
        :param run_id: The unique identifier for the run.
        :param n_resamples: The number of resamples to attempt.
        :param supervision_context: The supervision context.
        :param rejection_policy: The rejection policy.
        :param multi_supervisor_resolution: How to resolve multiple supervisor decisions.
        :param remove_feedback_from_context: Whether to remove feedback from context.
        :return: A new ChatCompletionMessage if successful, else None.
        """
        # Create updated messages with the original messages and the original tool call
        updated_messages = copy.deepcopy(request_kwargs["messages"])
        resampled_tool_call = copy.deepcopy(tool_call)
        resampled_all_decisions = copy.deepcopy(all_decisions)

        for resample in range(n_resamples):
            # Add feedback to the context for all rejected, escalated and terminated supervisors
            feedback_from_supervisors = " ".join([
                f"Supervisor {idx}: Decision: {d.decision}, Explanation: {d.explanation} \n"
                for idx, d in enumerate(resampled_all_decisions)
                if d.decision in [SupervisionDecisionType.REJECT, SupervisionDecisionType.ESCALATE, SupervisionDecisionType.TERMINATE]
            ])

            # Create feedback message for the assistant
            tool_name = resampled_tool_call.function.name
            tool_kwargs = resampled_tool_call.function.arguments
            feedback_message = (
                f"User tried to execute tool: {tool_name} with arguments: {tool_kwargs}, but it was rejected by some supervisors. \n"
                f"{feedback_from_supervisors} \n"
                f"Please try again with the feedback!"
            )

            if "messages" in request_kwargs:
                updated_messages.append(
                    {
                        "role": "assistant",
                        "content": feedback_message
                    }
                )

            resampled_request_kwargs = copy.deepcopy(request_kwargs)
            resampled_request_kwargs["messages"] = updated_messages

            # Send the updated messages to the model for resampling
            resampled_response = completions.create(*args, **resampled_request_kwargs)

            # Convert resampled response and request to JSON strings and Base64 encode

            resampled_create_new_chat_response = self.api_logger.log_llm_interaction(
                resampled_response,
                resampled_request_kwargs,
                run_id
            )

            resampled_choice_ids = resampled_create_new_chat_response.choice_ids

            if not resampled_response.choices[0].message.tool_calls:
                print("No tool calls found in resampled response, skipping supervision checks")
                # TODO: If normal chat message is returned, we need to run chat supervisors if there are any
                continue

            resampled_tool_call = resampled_response.choices[0].message.tool_calls[0]
            resampled_tool_call_id = resampled_choice_ids[0].tool_call_ids[0].tool_call_id
            resampled_tool_id = resampled_choice_ids[0].tool_call_ids[0].tool_id

            # Run supervision again on the resampled tool call
            processed_tool_call, all_decisions, modified = self.process_tool_call(
                tool_call=resampled_tool_call,
                tool_id=resampled_tool_id,
                tool_call_id=resampled_tool_call_id,
                supervision_context=supervision_context,
                allow_tool_modifications=False,
                multi_supervisor_resolution=multi_supervisor_resolution,
                execution_mode=execution_mode
            )

            if not modified and processed_tool_call:
                # Approved, add the final tool call to the response
                # Change the role of the updated messages to "sentinel"
                # for message in updated_messages:
                #     message["role"] = "sentinel"
                return ChatCompletionMessage(
                    role="assistant",
                    tool_calls=[ChatCompletionMessageToolCall(**processed_tool_call)]
                )

        # All resamples were rejected
        # Summarize all feedback into one message to send back
        explanations = "Original user message: " + updated_messages[0]["content"] + "\n"
        explanations += " ".join([
            f"Resample {resample+1}: {message['role']}: {message['content']}\n"
            for resample, message in enumerate(updated_messages[1:])
        ])
        rejection_message = (
            f"The agent requested to execute a function but it was rejected by some supervisors.\n"
            f"We tried {n_resamples} times to get a valid response but it was rejected each time.\n"
            f"Here is the feedback from the supervisors: \n{explanations}\n"
            f"This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try something else!"
        )
        return ChatCompletionMessage(role="assistant", content=rejection_message)


def call_supervisor_function(
    supervisor_func: Any,
    tool: Tool,
    tool_call: ChatCompletionMessageToolCall,
    supervision_context: Any,
    supervision_request_id: UUID,
    decision: Optional[SupervisionDecision] = None
) -> SupervisionDecision:
    """
    Call the supervisor function, handling both synchronous and asynchronous functions.

    :param supervisor_func: The supervisor function to call.
    :param tool: The tool being supervised.
    :param tool_call: The tool call.
    :param supervision_context: The supervision context.
    :param supervision_request_id: The ID of the supervision request.
    :param decision: The previous decision, if any.
    :return: The decision made by the supervisor.
    """
    if asyncio.iscoroutinefunction(supervisor_func):
        decision = asyncio.run(
            supervisor_func(
                tool=tool,
                tool_call=tool_call,
                supervision_context=supervision_context,
                supervision_request_id=supervision_request_id,
                previous_decision=decision
            )
        )
    else:
        decision = supervisor_func(
            tool=tool,
            tool_call=tool_call,
            supervision_context=supervision_context,
            supervision_request_id=supervision_request_id,
            previous_decision=decision
        )
    return decision