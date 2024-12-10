"""
Shared logging functionality for API wrappers.
"""

import asyncio
import base64
import json
import copy
from typing import Any, Dict, List, Optional, Callable
from openai.types.chat.chat_completion_message import ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletion
from uuid import UUID
from sentinel.registration.helper import get_supervisor_chains_for_tool, send_supervision_request, send_supervision_result
from sentinel.api.generated.sentinel_api_client.models.supervisor_type import SupervisorType
from sentinel.api.generated.sentinel_api_client.models.tool import Tool
from sentinel.settings import settings
from sentinel.api.generated.sentinel_api_client import Client
from sentinel.api.generated.sentinel_api_client.models import SentinelChat
from sentinel.api.generated.sentinel_api_client.api.run.create_new_chat import sync_detailed as create_new_chat_sync_detailed
from sentinel.api.generated.sentinel_api_client.api.tool import get_tool
# Get supervision config
from sentinel.supervision.config import SupervisionDecision, SupervisionDecisionType, get_supervision_config, RejectionPolicy, MultiSupervisorResolution

class SentinelLoggingError(Exception):
    """Raised when there's an error logging to Sentinel API"""
    pass

class APILogger:
    """Handles logging to the Sentinel API"""
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required for logging")
        self.client = Client(base_url=settings.api_url)
    
    def log_request(self, request_data: Dict[str, Any], run_id: UUID) -> None:
        """No op as Sentinel API doesn't need request data, it is sent when the response is received"""
        pass
    
    def debug_print_raw_input(self, response_data: Dict[str, Any], request_kwargs: Dict[str, Any]) -> None:
        """Print raw input data for debugging."""
        print(f"Raw response_data type: {type(response_data)}")
        print(f"Raw response_data: {response_data}")
        print(f"Raw request_data type: {type(request_kwargs)}")
        print(f"Raw request_data: {request_kwargs}")

    def convert_to_json(self, response_data: Dict[str, Any], request_kwargs: Dict[str, Any]) -> tuple[str, str]:
        """Convert response and request data to JSON strings."""
        if hasattr(response_data, 'model_dump_json'):
            response_data_str = response_data.model_dump_json()
        elif hasattr(response_data, 'to_dict'):
            response_data_str = json.dumps(response_data.to_dict())
        else:
            response_data_str = json.dumps(response_data)
        
        if isinstance(request_kwargs, str):
            request_data_str = request_kwargs
        else:
            messages = request_kwargs.get("messages", [])
            if messages:
                for idx, message in enumerate(messages):
                    tool_calls = message.get("tool_calls", [])
                    if tool_calls:
                        request_kwargs["messages"][idx]["tool_calls"] = [t.to_dict() for t in tool_calls if type(t) is not dict]
            request_data_str = json.dumps(request_kwargs)
        
        return response_data_str, request_data_str

    def encode_to_base64(self, response_data_str: str, request_data_str: str) -> tuple[str, str]:
        """Encode JSON strings to Base64."""
        if not isinstance(response_data_str, str):
            response_data_str = str(response_data_str)
        
        response_data_base64 = base64.b64encode(response_data_str.encode()).decode()
        request_data_base64 = base64.b64encode(request_data_str.encode()).decode()
        
        return response_data_base64, request_data_base64

    def log_response(self, response: ChatCompletion, request_kwargs: Dict[str, Any], run_id: UUID, execution_mode: str, completions: Any, args: Any) -> ChatCompletion | None:
        """Send the raw response data to Sentinel API"""
        try:
            # Debug Step 1: Print raw input data
            print("\n=== Debug Step 1: Raw Input ===")
            response_data = response if isinstance(response, dict) else response.to_dict()
            self.debug_print_raw_input(response_data, request_kwargs)
            
            # Debug Step 2: JSON Conversion
            print("\n=== Debug Step 2: JSON Conversion ===")
            response_data_str, request_data_str = self.convert_to_json(response_data, request_kwargs)
            print(f"Response JSON string type: {type(response_data_str)}")
            print(f"Response JSON string: {response_data_str}")
            print(f"Request JSON string type: {type(request_data_str)}")
            print(f"Request JSON string: {request_data_str}")
            
            # Debug Step 3: Base64 Encoding
            print("\n=== Debug Step 3: Base64 Encoding ===")
            response_data_base64, request_data_base64 = self.encode_to_base64(response_data_str, request_data_str)
            print(f"Response base64 type: {type(response_data_base64)}")
            print(f"Response base64: {response_data_base64}")
            print(f"Request base64 type: {type(request_data_base64)}")
            print(f"Request base64: {request_data_base64}")

            # Create final payload
            body = self.create_final_payload(response_data_base64, request_data_base64)

            # Send the request
            create_new_chat_response = self.send_api_request(run_id, body)
            choice_ids = create_new_chat_response.choice_ids

            # Check if there are any tool calls before processing
            response_data_tool_calls = response_data.get('choices', [{}])[0].get('message', {}).get('tool_calls')
            if not response_data_tool_calls:
                print("No tool calls found in response, skipping supervision checks")
                return None
            
            # Get the run by the ID
            supervision_config = get_supervision_config()
            run = supervision_config.get_run_by_id(run_id)
            if not run:
                print(f"Run not found for ID: {run_id}")
                return None
            
            supervision_context = run.supervision_context
            
            allow_tool_modifications = supervision_config.execution_settings.get('allow_tool_modifications', False)
            rejection_policy = supervision_config.execution_settings.get('rejection_policy', 'resample_with_feedback')
            n_resamples = supervision_config.execution_settings.get('n_resamples', 3)
            multi_supervisor_resolution = supervision_config.execution_settings.get('multi_supervisor_resolution', 'all_must_approve')
            remove_feedback_from_context = supervision_config.execution_settings.get('remove_feedback_from_context', False)

            # Iterate over all the tool calls
            # Get the supervisors for that tool
            # Run each supervisor 
            new_response_messages: List[Any] = []
            for idx, tool_call in enumerate(response_data_tool_calls):
                tool_call = ChatCompletionMessageToolCall(**tool_call)
                tool_id = choice_ids[idx].tool_call_ids[0].tool_id
                tool_call_id = choice_ids[idx].tool_call_ids[0].tool_call_id
                # Process the tool call
                processed_tool_call, all_decisions, modified = self.process_tool_call(
                    tool_call=tool_call,
                    tool_id=tool_id,
                    tool_call_id=tool_call_id,
                    supervision_context=supervision_context,
                    completions=completions,
                    request_kwargs=request_kwargs,
                    args=args,
                    allow_tool_modifications=allow_tool_modifications,
                    rejection_policy=rejection_policy,
                    n_resamples=n_resamples,
                    multi_supervisor_resolution=multi_supervisor_resolution,
                    remove_feedback_from_context=remove_feedback_from_context
                )
                if modified and processed_tool_call:
                    # Modified, we need to run it again against the supervisors
                    # This time without allowing the tool to be modified to prevent infinite loops
                    final_tool_call, all_decisions, modified = self.process_tool_call(
                        tool_call=processed_tool_call,
                        tool_id=tool_id,
                        tool_call_id=tool_call_id,
                        supervision_context=supervision_context,
                        completions=completions,
                        request_kwargs=request_kwargs,
                        args=args,
                        allow_tool_modifications=False,
                        rejection_policy=rejection_policy,
                        n_resamples=n_resamples,
                        multi_supervisor_resolution=multi_supervisor_resolution,
                        remove_feedback_from_context=remove_feedback_from_context
                    )
                    new_response_messages[idx] = final_tool_call
                elif not processed_tool_call:
                    # Rejected, decide based on the rejection policy
                    if rejection_policy == RejectionPolicy.RESAMPLE_WITH_FEEDBACK:
                        updated_messages = copy.deepcopy(request_kwargs["messages"])
                        for resample in range(n_resamples):
                            # Add feedback to the context for all rejected, escalated and terminated supervisors
                            feedback_from_supervisors = " ".join([f"Supervisor {idx}: Decision: {d.decision}, Explanation: {d.explanation} \n" for idx, d in enumerate(all_decisions) if d.decision in [SupervisionDecisionType.REJECT, SupervisionDecisionType.ESCALATE, SupervisionDecisionType.TERMINATE]])
                            # TODO: Improve the feedback message
                            
                            tool_name = tool_call.function.name
                            tool_kwargs = tool_call.function.arguments
                            feedback_message = f"User tried to execute tool: {tool_name} with arguments: {tool_kwargs}, but it was rejected by some supervisors. \n {feedback_from_supervisors} \n Please try again with the feedback!"
                            
                            if "messages" in request_kwargs:
                                updated_messages.append(
                                    {
                                        "role": "assistant",
                                        "content": feedback_message
                                    }
                                )
                            # TODO: Send the updated messages to Sentinel as well?    
                            
                            resampled_request_kwargs = copy.deepcopy(request_kwargs)
                            resampled_request_kwargs["messages"] = updated_messages
                            
                            # Run the model again
                            resampled_response = completions.create(*args, **resampled_request_kwargs)
                            resampled_response_data_str, resampled_request_data_str = self.convert_to_json(resampled_response.to_dict(), resampled_request_kwargs)
                            resampled_response_data_base64, resampled_request_data_base64 = self.encode_to_base64(resampled_response_data_str, resampled_request_data_str)
                            body = self.create_final_payload(resampled_response_data_base64, resampled_request_data_base64)

                            # Send the request
                            resampled_create_new_chat_response = self.send_api_request(run_id, body) #TODO: Add parameter to say this is a resample
                            resampled_choice_ids = resampled_create_new_chat_response.choice_ids # TODO: There are no choice_ids returned from the API
                            if resampled_response.choices[0].message.tool_calls:
                                if not resampled_response.choices[0].message.tool_calls:
                                    print("No tool calls found in resampled response, skipping supervision checks")
                                    # TODO: If normal chat message is returned, we need to run chat supervisors if there are any
                                    continue
                                resampled_tool_call = resampled_response.choices[0].message.tool_calls[0]
                                resampled_tool_call_id = resampled_choice_ids[0].tool_call_ids[0].tool_call_id 
                                resampled_tool_id = resampled_choice_ids[0].tool_call_ids[0].tool_id
                                # Run supervision again
                                processed_tool_call, all_decisions, modified = self.process_tool_call( #TODO: double check this
                                    tool_call=resampled_tool_call,
                                    tool_id=resampled_tool_id,
                                    tool_call_id=resampled_tool_call_id,
                                    supervision_context=supervision_context,
                                    completions=completions,
                                    request_kwargs=resampled_request_kwargs,
                                    args=args,
                                    allow_tool_modifications=False,
                                    rejection_policy=rejection_policy,
                                    n_resamples=n_resamples,
                                    multi_supervisor_resolution=multi_supervisor_resolution,
                                    remove_feedback_from_context=remove_feedback_from_context
                                )
                                if not modified and processed_tool_call:
                                    new_response_messages.append(processed_tool_call)
                                    break
                        else:
                            explanations = " ".join([f"Supervisor {idx}: Decision: {d.decision}, Explanation: {d.explanation} \n" for idx, d in enumerate(all_decisions)])
                            rejection_message = f"The agent requested to execute a function but it was rejected by some supervisors.\n Chain Explanations: \n{explanations}\n This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try something else!"
                            new_response_messages.append(ChatCompletionMessage(role="assistant", content=rejection_message))
                        
                else:
                    # Approved
                    new_response_messages.append(request_kwargs["messages"][idx])
            new_response = copy.deepcopy(response)
            for messages in new_response_messages:
                new_response.choices[idx].message = messages
            return new_response
        except Exception as e:
            print(f"\n=== ERROR DETAILS ===")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            print(f"Error occurred at line {e.__traceback__.tb_lineno}")
            raise SentinelLoggingError(f"Failed to log response: {str(e)}") from e

    def process_tool_call(self, tool_call: ChatCompletionMessageToolCall, tool_id, tool_call_id, supervision_context, completions, request_kwargs, args, allow_tool_modifications, rejection_policy, n_resamples, multi_supervisor_resolution, remove_feedback_from_context) -> tuple[ChatCompletionMessageToolCall | None, Any, bool]:
        """Process a single tool call."""
        function = tool_call.function
        tool_name = function.name
        tool_kwargs = json.loads(function.arguments)
        
        supervisors_chains = get_supervisor_chains_for_tool(tool_id, self.client)
        
        tool = self.get_tool(tool_id)
        if not tool:
            return None, None, False

        if not supervisors_chains:
            print(f"No supervisors found for function {tool_id}. Executing function.")
            return None, None, False

        all_decisions = self.run_supervisor_chains(
            supervisors_chains, tool, tool_call, tool_call_id, supervision_context, allow_tool_modifications, rejection_policy, n_resamples, multi_supervisor_resolution, remove_feedback_from_context
        )
        
        # Check if all decisions are approve or modify
        if multi_supervisor_resolution == MultiSupervisorResolution.ALL_MUST_APPROVE and all(
            decision.decision in [SupervisionDecisionType.APPROVE] 
            for decision in all_decisions
        ):
            # Approved
            return tool_call, all_decisions, False
        elif allow_tool_modifications and all_decisions[-1].decision == SupervisionDecisionType.MODIFY:
            # Modified
            return all_decisions[-1].modified.openai_tool_call, all_decisions, True # TODO: double check this
        else:
            # Rejected
            return None, all_decisions, False
            


    def get_tool(self, tool_id):
        """Retrieve the tool object by its ID."""
        tool_response = get_tool.sync_detailed(tool_id=tool_id, client=self.client)
        if tool_response and tool_response.parsed and isinstance(tool_response.parsed, Tool):
            return tool_response.parsed
        print(f"Failed to get tool for ID {tool_id}. Skipping.")
        return None

    def run_supervisor_chains(self, supervisors_chains, tool, tool_call, tool_call_id, supervision_context, allow_tool_modifications, rejection_policy, n_resamples, multi_supervisor_resolution, remove_feedback_from_context):
        """Run all supervisor chains for a tool call."""
        all_decisions = []
        for supervisor_chain in supervisors_chains:
            chain_decisions = self.run_supervisors_in_chain(
                supervisor_chain, tool, tool_call, tool_call_id, supervision_context, allow_tool_modifications, rejection_policy, n_resamples, multi_supervisor_resolution, remove_feedback_from_context
            )
            all_decisions.extend(chain_decisions)
            last_decision = chain_decisions[-1]
            if multi_supervisor_resolution == MultiSupervisorResolution.ALL_MUST_APPROVE and last_decision.decision in [SupervisionDecisionType.ESCALATE, SupervisionDecisionType.REJECT, SupervisionDecisionType.TERMINATE]:
                break
                # if all have to approve and one rejects, we can stop
            elif last_decision.decision == SupervisionDecisionType.MODIFY:
                break
                # we need to run the supervision again with the modified tool call
        return all_decisions

    def run_supervisors_in_chain(self, supervisor_chain, tool, tool_call, tool_call_id, supervision_context, allow_tool_modifications, rejection_policy, n_resamples, multi_supervisor_resolution, remove_feedback_from_context):
        """Run each supervisor in a chain and collect decisions."""
        chain_decisions = []
        for position_in_chain, supervisor in enumerate(supervisor_chain.supervisors):
            decision = self.execute_supervisor(
                supervisor, tool, tool_call, tool_call_id, position_in_chain, supervision_context, supervisor_chain.chain_id
            )
            if decision is None:
                break
            elif decision:
                chain_decisions.append(decision)
            if decision.decision not in [SupervisionDecisionType.ESCALATE]:
                break
            
        return chain_decisions

    def execute_supervisor(self, supervisor, tool, tool_call, tool_call_id, position_in_chain, supervision_context, supervisor_chain_id):
        """Execute a single supervisor and return its decision."""
        supervision_request_id = send_supervision_request(
            tool_call_id=tool_call_id, 
            supervisor_id=supervisor.id, 
            supervisor_chain_id=supervisor_chain_id, 
            position_in_chain=position_in_chain
        )

        supervisor_func = supervision_context.get_supervisor_by_id(supervisor.id)
        if not supervisor_func:
            print(f"No local supervisor function found for ID {supervisor.id}. Skipping.")
            return None

        decision = call_supervisor_function(
            supervisor_func=supervisor_func,
            tool=tool,
            tool_call=tool_call, 
            supervision_context=supervision_context, 
            supervision_request_id=supervision_request_id
        )
        print(f"Supervisor decision: {decision.decision}")

        if supervisor.type != SupervisorType.HUMAN_SUPERVISOR:
            send_supervision_result(
                tool_call_id=tool_call_id,
                supervision_request_id=supervision_request_id,
                decision=decision,
            )
        
        return decision

    # def handle_supervision_decision(
    #     self,
    #     decision: SupervisionDecision,
    #     chain_decisions: List[SupervisionDecision],
    #     tool: Tool,
    #     tool_call: dict,
    #     allow_tool_modifications: bool,
    #     rejection_policy: str,
    #     n_resamples: int,
    #     multi_supervisor_resolution: str,
    #     remove_feedback_from_context: bool,
    #     completions: Any,
    #     args: Any
    # ) -> Optional[str]:
    #     """Handle a supervision decision and return an error message if execution should stop"""
        
    #     if decision.decision == SupervisionDecisionType.APPROVE:
    #         return None
        
    #     elif decision.decision == SupervisionDecisionType.REJECT:
    #         explanations = " ".join([f"Decision: {d.decision}, Explanation: {d.explanation}" for d in chain_decisions])
    #         return (f"The agent requested to execute {tool.name} but it was rejected. "
    #                 f"Explanation: {decision.explanation}. "
    #                 f"Chain Explanations: {explanations}\n"
    #                 "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try different action using the feedback!")
                
    #     elif decision.decision == SupervisionDecisionType.ESCALATE:
    #         # Handled by caller - return None to continue to next supervisor
    #         return None
        
    #     elif decision.decision == SupervisionDecisionType.MODIFY:
    #         # Handled by caller - return None to continue processing
    #         return None
        
    #     elif decision.decision == SupervisionDecisionType.TERMINATE:
    #         explanations = " ".join([f"Decision: {d.decision}, Explanation: {d.explanation}" for d in chain_decisions])
    #         return (f"Execution of {tool.name} should be terminated. "
    #                 f"Explanation: {decision.explanation}. "
    #                 f"Chain Explanations: {explanations}\n"
    #                 "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try different action using the feedback!")
        
    #     else:
    #         explanations = " ".join([f"Decision: {d.decision}, Explanation: {d.explanation}" for d in chain_decisions])
    #         return (f"Execution of {tool.name} was cancelled due to an unknown supervision decision. "
    #                 f"Chain Explanations: {explanations}\n"
    #                 "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try different action using the feedback!")

    # def handle_final_decisions(
    #     self,
    #     all_decisions: List[SupervisionDecision],
    #     tool: Tool,
    #     tool_kwargs: Dict[str, Any],
    #     ignored_attributes: List[str] = []
    # ) -> Any:
    #     """Process all decisions and execute the function if approved"""
        
    #     # Check if all decisions are approve or modify
    #     if all(
    #         decision.decision in [SupervisionDecisionType.APPROVE, SupervisionDecisionType.MODIFY] 
    #         for decision in all_decisions
    #     ):
    #         return f"All decisions approved or modified. Executing {tool.name} with kwargs: {tool_kwargs}"   
    #     else:
    #         explanations = " ".join([f"Supervisor {idx}: Decision: {d.decision}, Explanation: {d.explanation} \n" 
    #                                 for idx, d in enumerate(all_decisions)])
    #         return (f"The agent requested to execute a function but it was rejected by some supervisors.\n"
    #                 f"Chain Explanations: \n{explanations}\n"
    #                 "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try something else!")

    def create_final_payload(self, response_data_base64: str, request_data_base64: str) -> SentinelChat:
        """Create the final payload for the API request."""
        
        try:
            body = SentinelChat(
                response_data=response_data_base64,
                request_data=request_data_base64
            )
            print(f"Final body object type: {type(body)}")
            print(f"Final body object: {body}")
            return body
        except Exception as e:
            print(f"Body creation error: {str(e)}")
            print(f"Error occurred at line {e.__traceback__.tb_lineno}")
            raise

    def send_api_request(self, run_id: UUID, body: SentinelChat) -> Any:
        """Send the API request and handle the response."""
        
        try:
            print(f"Sending request to Sentinel API with body: {body}")
            response = create_new_chat_sync_detailed(
                client=self.client,
                run_id=run_id,
                body=body
            )
            print(f"API Response status code: {response.status_code}")
            print(f"API Response content: {response.content}")
            
            if response.status_code not in [200, 201]:
                raise ValueError(f"Failed to log LLM response. Status code: {response.status_code}, Response: {response.content}")
            
            if response.parsed is None:
                raise ValueError("Response was successful but parsed content is None")
            
            print(f"Successfully logged response for run {run_id}")
            print(f"Parsed response: {response.parsed}")
            return response.parsed
        except Exception as e:
            print(f"API request error: {str(e)}")
            print(f"Error occurred at line {e.__traceback__.tb_lineno}")
            raise

def call_supervisor_function(
    supervisor_func, 
    tool: Tool,
    tool_call: dict, 
    supervision_context, 
    supervision_request_id: UUID, 
    decision: Optional[SupervisionDecision] = None
):
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
