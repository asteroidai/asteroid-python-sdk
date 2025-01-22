import asyncio
import concurrent.futures
import copy
import datetime
import time
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID

import jinja2

from asteroid_sdk.api.api_logger import APILogger
from asteroid_sdk.api.generated.asteroid_api_client import Client
from asteroid_sdk.api.generated.asteroid_api_client.api.tool import get_tool
from asteroid_sdk.api.generated.asteroid_api_client.models import ChoiceIds
from asteroid_sdk.api.generated.asteroid_api_client.models.supervisor_chain import SupervisorChain
from asteroid_sdk.api.generated.asteroid_api_client.models.supervisor_type import SupervisorType
from asteroid_sdk.api.generated.asteroid_api_client.models.tool import Tool
from asteroid_sdk.registration.helper import (
    get_supervisor_chains_for_tool,
    send_supervision_request,
    send_supervision_result,
    generate_fake_message_tool_call
)
from asteroid_sdk.supervision import SupervisionContext
from asteroid_sdk.supervision.config import ExecutionMode
from asteroid_sdk.supervision.config import (
    MultiSupervisorResolution,
    RejectionPolicy,
    SupervisionDecision,
    SupervisionDecisionType,
    get_supervision_config,
)
from asteroid_sdk.supervision.helpers.model_provider_helper import AvailableProviderResponses, ModelProviderHelper
from asteroid_sdk.supervision.model.tool_call import ToolCall
from asteroid_sdk.utils.utils import load_template

import logging

class SupervisionRunner:

    def __init__(
            self,
            client: Client,
            api_logger: APILogger,
            model_provider_helper: ModelProviderHelper
    ):
        self.client = client
        self.api_logger = api_logger
        self.model_provider_helper = model_provider_helper

    async def handle_tool_calls_from_llm_response(
            self,
            args: Any,
            choice_ids: List[ChoiceIds],
            completions: Any, # TODO - THIS IS WRONG, it should be API client, not responses
            execution_mode: str,
            request_kwargs: Dict[str, Any],
            response: AvailableProviderResponses,
            response_data_tool_calls: List[ToolCall],
            run_id: UUID,
            supervision_context: SupervisionContext,
            message_supervisors: Optional[List[List[Callable]]] = None
    ) -> AvailableProviderResponses:
        supervision_config = get_supervision_config()
        allow_message_modifications = supervision_config.execution_settings.get('allow_message_modifications', False)
        rejection_policy = supervision_config.execution_settings.get('rejection_policy', 'resample_with_feedback')
        n_resamples = supervision_config.execution_settings.get('n_resamples', 1)
        multi_supervisor_resolution = supervision_config.execution_settings.get('multi_supervisor_resolution', 'all_must_approve')

        new_response = copy.deepcopy(response)
        # TODO - Check if this is still relevant
        #  We do not allow multiple tool calls with resampling, it should work without. Tested with Gemini and nothing else
        decisions: List[Dict] = []
        for idx, tool_call in enumerate(response_data_tool_calls):
            tool_id = UUID(choice_ids[0].tool_call_ids[idx].tool_id)
            tool_call_id = UUID(choice_ids[0].tool_call_ids[idx].tool_call_id)

            # Process the tool call with supervision
            processed_tool_call, supervisor_decisions, modified = await self.process_tool_call(
                tool_call=tool_call,
                tool_id=tool_id,
                tool_call_id=tool_call_id,
                supervision_context=supervision_context,
                allow_message_modifications=allow_message_modifications,
                multi_supervisor_resolution=multi_supervisor_resolution,
                execution_mode=execution_mode
            )

            if not modified and processed_tool_call:
                # Approved, add the final tool call to the response
                self.model_provider_helper.upsert_tool_call(
                    response=new_response,
                    tool_call=processed_tool_call.language_model_tool_call
                )
                decisions.append({'tool_call': tool_call, 'supervisor_decisions': supervisor_decisions})

            if modified and processed_tool_call:
                # If the tool call was modified, run the supervision process again without modifications allowed
                final_tool_call, supervisor_decisions, modified = await self.process_tool_call(
                    tool_call=processed_tool_call,
                    tool_id=tool_id,
                    tool_call_id=tool_call_id,
                    supervision_context=supervision_context,
                    allow_message_modifications=False,
                    multi_supervisor_resolution=multi_supervisor_resolution,
                    execution_mode=execution_mode
                )
                self.model_provider_helper.upsert_tool_call(
                    response=new_response,
                    tool_call=final_tool_call.language_model_tool_call
                )
                decisions.append({'tool_call': tool_call, 'supervisor_decisions': supervisor_decisions})
            elif not processed_tool_call:
                # If the tool call was rejected, handle based on the rejection policy
                # NOTE - this does not work currently for multiple tool calls. We're only accepting one tool call for
                #  OpenAI/Anthropic. We accept multiple (as we can't lock it down) for Gemini, but we'll never hit this
                #  code with Gemini. When we allow resampling on Gemini, we need to think about this
                if rejection_policy == RejectionPolicy.RESAMPLE_WITH_FEEDBACK:
                    # Attempt to resample the response with feedback
                    resampled_response = await self.handle_rejection_with_resampling(
                        failed_tool_call=tool_call,
                        failed_all_decisions=supervisor_decisions,
                        completions=completions,
                        request_kwargs=request_kwargs,
                        args=args,
                        run_id=run_id,
                        n_resamples=n_resamples,
                        supervision_context=supervision_context,
                        multi_supervisor_resolution=multi_supervisor_resolution,
                        execution_mode=execution_mode,
                        message_supervisors=message_supervisors
                    )
                    # If resampled response contains tool calls (ie it succeeded), then succeed
                    new_response = resampled_response
                else:
                    decisions.append({'tool_call': tool_call, 'supervisor_decisions': supervisor_decisions})

        # Tom's comment: This is truly horrible
        # David's comment: Agreed, I assume the goal was to save the rejection result, but we also need to return it
        if multi_supervisor_resolution == MultiSupervisorResolution.ALL_MUST_APPROVE:
            for supervisor_decisions in decisions:
                for tool_call_decisions in supervisor_decisions.get('supervisor_decisions'):
                    # We only check the last decision in the chain as that's the one that will be used
                    if tool_call_decisions[-1].decision in [SupervisionDecisionType.REJECT, SupervisionDecisionType.ESCALATE,
                                                SupervisionDecisionType.TERMINATE]:
                        rejection_result = self._create_rejection_result(decisions)
                        # Log the interaction
                        self.api_logger.log_llm_interaction(
                            rejection_result,
                            request_kwargs,
                            run_id
                        )
                        # We need to return the rejection result
                        new_response = rejection_result
                        break
        else:
            raise ValueError("Multi supervisor resolution must be all_must_approve")

        return new_response


    def _create_rejection_result(self, all_call_decisions):
        result_info = []

        for decision in all_call_decisions:
            feedback_from_supervisors = " ".join([
                f"Chain {chain_number}: Supervisor {supervisor_number_in_chain}: Decision: {decision.decision}, Explanation: {decision.explanation} \n"
                for chain_number, decisions_for_chain in enumerate(decision.get('supervisor_decisions'))
                for supervisor_number_in_chain, decision in enumerate(decisions_for_chain)
            ])
            tool_result_info = {
                "name": decision['tool_call'].tool_name,
                "params": decision['tool_call'].tool_params,
                "explanations": feedback_from_supervisors
            }
            result_info.append(tool_result_info)

        # Load and render the feedback message template
        feedback_template_content = load_template('partial_rejection_message_template.jinja')
        feedback_template = jinja2.Template(feedback_template_content)
        feedback_message = feedback_template.render(tools=result_info)

        return self.model_provider_helper.generate_new_response_with_rejection_message(feedback_message)

    def resampled_response_successful(self, resampled_response):
        return resampled_response and resampled_response.tool_calls

    async def process_tool_call(
            self,
            tool_call: ToolCall,
            tool_id: UUID,
            tool_call_id: UUID,
            supervision_context: Any,
            allow_message_modifications: bool,
            multi_supervisor_resolution: str,
            execution_mode: str
    ) -> tuple[Optional[ToolCall], Any, bool]:
        """
        Process a single tool call through supervision.

        :param tool_call: The tool call to process.
        :param tool_id: The ID of the tool being called.
        :param tool_call_id: The ID of the tool call.
        :param supervision_context: The context for supervision.
        :param allow_message_modifications: Whether to allow message modifications.
        :param multi_supervisor_resolution: How to resolve multiple supervisor decisions.
        :return: A tuple containing the processed tool call, decisions, and modification status.
        """

        # Get the supervisors chains for the tool
        supervisors_chains = get_supervisor_chains_for_tool(tool_id)

        # Retrieve the tool object
        tool = self.get_tool(tool_id)
        if not tool:
            return None, None, False

        if not supervisors_chains:
            logging.info(f"No supervisors found for function {tool_id}. Executing function.")
            return tool_call, None, False

        # Run all supervisors in the chains
        supervisor_chain_decisions = await self.run_supervisor_chains(
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
        elif allow_message_modifications and final_supervisor_chain_decisions[-1].decision == SupervisionDecisionType.MODIFY:
            # Modified # TODO: Is this working? - Probably not
            return final_supervisor_chain_decisions[-1].modified.openai_tool_call, supervisor_chain_decisions, True
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
        logging.info(f"Failed to get tool for ID {tool_id}. Skipping.")
        return None


    async def run_supervisor_chains(
            self,
            supervisors_chains: Any,
            tool: Tool,
            tool_call: ToolCall,
            tool_call_id: UUID,
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

        tasks = [
            self.run_supervisors_in_chain(
                supervisor_chain,
                tool,
                tool_call,
                tool_call_id,
                supervision_context,
                supervisor_chain.chain_id,
                execution_mode
            )
            for supervisor_chain in supervisors_chains
        ]

        results = await asyncio.gather(*tasks)

        for chain_decisions in results:
            all_decisions.append(chain_decisions)
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

    async def run_supervisors_in_chain(
            self,
            supervisor_chain: SupervisorChain,
            tool: Tool,
            tool_call: ToolCall,
            tool_call_id: UUID,
            supervision_context: Any,
            supervisor_chain_id: UUID,
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
            decision = await self.execute_supervisor(
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

    async def execute_supervisor(
            self,
            supervisor: Any,
            tool: Tool,
            tool_call: ToolCall,
            tool_call_id: UUID,
            position_in_chain: int,
            supervision_context: Any,
            supervisor_chain_id: UUID,
            execution_mode: str,
            supervisor_func: Optional[Callable] = None
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

        if not supervisor_func:
            # Get the supervisor function from the context
            supervisor_func = supervision_context.get_supervisor_func_by_id(supervisor.id)
            if not supervisor_func:
                logging.info(f"No local supervisor function found for ID {supervisor.id}. Skipping.")
                return None

        if supervisor.type == SupervisorType.HUMAN_SUPERVISOR and execution_mode == ExecutionMode.MONITORING:
            # If the supervisor is a human supervisor and we are in monitoring mode, we automatically approve
            decision = SupervisionDecision(decision=SupervisionDecisionType.APPROVE)
        else:
            # Call the supervisor function to get a decision
            decision = await self.call_supervisor_function(
                supervisor_func=supervisor_func,
                tool=tool,
                tool_call=tool_call,
                supervision_context=supervision_context,
                supervision_request_id=supervision_request_id
            )
        logging.info(f"Supervisor decision: {decision.decision}")

        # Send supervision result back
        send_supervision_result(
            tool_call_id=tool_call_id,
            supervision_request_id=supervision_request_id,
            decision=decision,
        )

        return decision

    async def handle_rejection_with_resampling(
            self,
            failed_tool_call: ToolCall,
            failed_all_decisions: Any,
            completions: Any,
            request_kwargs: Dict[str, Any],
            args: Any,
            run_id: UUID,
            n_resamples: int,
            supervision_context: Any,
            multi_supervisor_resolution: str,
            execution_mode: str,
            message_supervisors: Optional[List[List[Callable]]] = None
    ) -> Optional[AvailableProviderResponses]:
        """
        Handle rejected tool calls by attempting to resample responses with supervisor feedback.

        :param failed_tool_call: The original tool call.
        :param failed_all_decisions: All decisions from supervisors.
        :param completions: The completions object.
        :param request_kwargs: The original request keyword arguments.
        :param args: Additional arguments.
        :param run_id: The unique identifier for the run.
        :param n_resamples: The number of resamples to attempt.
        :param supervision_context: The supervision context.
        :param multi_supervisor_resolution: How to resolve multiple supervisor decisions.
        :param execution_mode: The execution mode.
        :param message_supervisors: The message supervisors to use for supervision.
        :return: A new ChatCompletionMessage if successful, else None.
        """
        # Load the resample prompt template
        resample_prompt_template = load_template('resample_prompt.jinja')
        resample_prompt_content = jinja2.Template(resample_prompt_template).render()

        for resample in range(n_resamples):
            feedback_message = self._get_feedback_message(failed_all_decisions, failed_tool_call)

            resampled_response, resampled_request_kwargs = self.model_provider_helper.resample_response(
                feedback_message,
                args,
                request_kwargs,
                completions # Maybe we should inject the client straight into the ModelProviderHelper, instead of passing through here
            )

            resampled_tool_calls = self.model_provider_helper.get_tool_call_from_response(resampled_response)

            if not resampled_tool_calls:
                if message_supervisors:
                    logging.info("No tool calls found in resampled response, but we have message supervisors")
                    # Create fake message tool call
                    resampled_response, resampled_tool_calls = generate_fake_message_tool_call(
                        response=resampled_response,
                        supervision_context=supervision_context,
                        model_provider_helper=self.model_provider_helper
                    )

            # Log the interaction
            resampled_create_new_chat_response = self.api_logger.log_llm_interaction(
                resampled_response,
                resampled_request_kwargs,
                run_id
            )

            if not resampled_tool_calls:
                # There was no tool call found in the resampled response, so we return the message as is
                return resampled_response

            resampled_tool_call_id = resampled_create_new_chat_response.choice_ids[0].tool_call_ids[0].tool_call_id
            resampled_tool_id = resampled_create_new_chat_response.choice_ids[0].tool_call_ids[0].tool_id

            # Run supervision again on the resampled tool call
            processed_tool_call, resampled_all_decisions, modified = await self.process_tool_call(
                tool_call=resampled_tool_calls[0],  # Only allow one tool_call
                tool_id=UUID(resampled_tool_id),
                tool_call_id=UUID(resampled_tool_call_id),
                supervision_context=supervision_context,
                allow_message_modifications=False,
                multi_supervisor_resolution=multi_supervisor_resolution,
                execution_mode=execution_mode
            )

            if not modified and processed_tool_call:
                # Approved, return the final tool call
                return resampled_response

            # Update the failed tool call and decisions for the next iteration
            failed_tool_call = resampled_tool_calls[0]
            failed_all_decisions = resampled_all_decisions

        # All resamples were rejected
        # Summarize all feedback into one message to send back

        # Build the explanations variable
        # NOTE - Below will fail with n-resamples set to 0, but probably would do this anyway
        updated_messages = resampled_request_kwargs['messages']
        explanations = "\n".join([
            f"Resample {idx+1}: {message['content']}"
            for idx, message in enumerate(updated_messages[-n_resamples:])
        ])

        # Load and render the rejection message template
        rejection_template_content = load_template('rejection_message_template.jinja')
        rejection_template = jinja2.Template(rejection_template_content)
        rejection_message = rejection_template.render(
            tool_name=failed_tool_call.tool_name,
            tool_params=failed_tool_call.tool_params,
            n_resamples=n_resamples,
            explanations=explanations
        )
        # TODO - should we add a `Choice` in here- or just return the message? Currently, we're returning the message and
        #  putting it into an already existing choice- which means the `stop-reason` is not being overwritten
        #  (eg. it says `tool_calls`)
        return self.model_provider_helper.generate_new_response_with_rejection_message(rejection_message)

    def _get_feedback_message(self, failed_all_decisions, failed_tool_call):
        feedback_from_supervisors = " ".join([
            f"Chain {chain_number}: Supervisor {supervisor_number_in_chain}: Decision: {decision.decision}, Explanation: {decision.explanation} \n"
            for chain_number, decisions_for_chain in enumerate(failed_all_decisions)
            for supervisor_number_in_chain, decision in enumerate(decisions_for_chain)
            if decision.decision in [SupervisionDecisionType.REJECT, SupervisionDecisionType.ESCALATE,
                                     SupervisionDecisionType.TERMINATE]
        ])
        # Load and render the feedback message template
        feedback_template_content = load_template('feedback_message_template.jinja')
        feedback_template = jinja2.Template(feedback_template_content)
        feedback_message = feedback_template.render(
            tool_name=failed_tool_call.tool_name,
            tool_params=failed_tool_call.tool_params,
            feedback_from_supervisors=feedback_from_supervisors
        )
        return feedback_message

    async def call_supervisor_function(
            self,
            supervisor_func: Callable,
            tool: Tool,
            tool_call: ToolCall,
            supervision_context: SupervisionContext,
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
        # Call the supervisor function
        decision = supervisor_func(
            message=tool_call.message,
            supervision_context=supervision_context,
            supervision_request_id=supervision_request_id,
            previous_decision=decision
        )
        # If the result is a coroutine, await it
        if asyncio.iscoroutine(decision):
            decision = await decision
        return decision
