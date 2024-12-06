"""
Shared logging functionality for API wrappers.
"""

import asyncio
import base64
import json
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID
from sentinel.registration.helper import get_supervisor_chains_for_tool
from sentinel.api.generated.sentinel_api_client.models.supervisor_type import SupervisorType
from sentinel.api.generated.sentinel_api_client.models.tool import Tool
from sentinel.settings import settings
from sentinel.api.generated.sentinel_api_client import Client
from sentinel.api.generated.sentinel_api_client.models import SentinelChat
from sentinel.api.generated.sentinel_api_client.api.run.create_new_chat import sync_detailed as create_new_chat_sync_detailed
from sentinel.api.generated.sentinel_api_client.api.tool import get_tool
# Get supervision config
from sentinel.supervision.config import SupervisionDecision, SupervisionDecisionType, get_supervision_config

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
    
    def log_response(self, response_data: Dict[str, Any], request_data: Dict[str, Any], run_id: UUID) -> None:
        """Send the raw response data to Sentinel API"""
        try:
            # Debug Step 1: Print raw input data
            print("\n=== Debug Step 1: Raw Input ===")
            print(f"Raw response_data type: {type(response_data)}")
            print(f"Raw response_data: {response_data}")
            print(f"Raw request_data type: {type(request_data)}")
            print(f"Raw request_data: {request_data}")
            
            # Debug Step 2: JSON Conversion
            print("\n=== Debug Step 2: JSON Conversion ===")
            try:
                # Use OpenAI's built-in serialization method
                if hasattr(response_data, 'model_dump_json'):
                    print("Using model_dump_json()")
                    response_data_str = response_data.model_dump_json()
                elif hasattr(response_data, 'to_dict'):
                    print("Using to_dict()")
                    response_data_str = json.dumps(response_data.to_dict())
                else:
                    print("Using direct json.dumps()")
                    response_data_str = json.dumps(response_data)
                    
                print(f"Response JSON string type: {type(response_data_str)}")
                print(f"Response JSON string: {response_data_str}")
                
                if isinstance(request_data, str):
                    request_data_str = request_data
                else:
                    request_data_str = json.dumps(request_data)
                print(f"Request JSON string type: {type(request_data_str)}")
                print(f"Request JSON string: {request_data_str}")
            except Exception as e:
                print(f"JSON conversion error: {str(e)}")
                print(f"Error occurred at line {e.__traceback__.tb_lineno}")
                raise
                
            # Debug Step 3: Base64 Encoding
            print("\n=== Debug Step 3: Base64 Encoding ===")
            try:
                if not isinstance(response_data_str, str):
                    print(f"Warning: response_data_str is not a string, it's a {type(response_data_str)}")
                    response_data_str = str(response_data_str)
                
                response_data_base64 = base64.b64encode(response_data_str.encode()).decode()
                print(f"Response base64 type: {type(response_data_base64)}")
                print(f"Response base64: {response_data_base64}")
                
                request_data_base64 = base64.b64encode(request_data_str.encode()).decode()
                print(f"Request base64 type: {type(request_data_base64)}")
                print(f"Request base64: {request_data_base64}")
            except Exception as e:
                print(f"Base64 encoding error: {str(e)}")
                print(f"Error occurred at line {e.__traceback__.tb_lineno}")
                raise
            
            # Debug Step 4: Create and Print Final Payload
            print("\n=== Debug Step 4: Final Payload ===")
            try:
                body = SentinelChat(
                    response_data=response_data_base64,
                    request_data=request_data_base64
                )
                print(f"Final body object type: {type(body)}")
                print(f"Final body object: {body}")
            except Exception as e:
                print(f"Body creation error: {str(e)}")
                print(f"Error occurred at line {e.__traceback__.tb_lineno}")
                raise

            # Send the request with error handling
            try:
                print("\n=== Debug Step 5: API Request ===")
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
                
            except Exception as e:
                print(f"API request error: {str(e)}")
                print(f"Error occurred at line {e.__traceback__.tb_lineno}")
                raise

            # Check if there are any tool calls before processing
            tool_calls = response_data.get('choices', [{}])[0].get('message', {}).get('tool_calls')
            if not tool_calls:
                print("No tool calls found in response, skipping supervision checks")
                return

            # Get the run by the ID
            supervision_config = get_supervision_config()
            run = supervision_config.get_run_by_id(run_id)
            if not run:
                print(f"Run not found for ID: {run_id}")
                return
            
            supervision_context = run.supervision_context
            client = self.client

            # Iterate over all the tool calls
            # Get the supervisors for that tool
            # Run each supervisor 
            for tool_call in tool_calls:
                tool_id = tool_call['id']
                supervisors_chains = get_supervisor_chains_for_tool(tool_id, client)
                
                tool_code = None
                # Define tool as Tool
                tool: Tool = None

                # Get the tool 
                tool_response = get_tool.sync_detailed(tool_id=tool_id, client=client)
                if tool_response:
                    # Ensure we have the tool object and not None or ErrorResponse
                    if tool_response.parsed:
                        if isinstance(tool_response.parsed, Tool):
                            tool = tool_response.parsed
                        else:
                            print(f"Unexpected tool type: {type(tool_response.parsed)}")
                    else:
                        print(f"Tool response is None")
                else:
                    print(f"Failed to get tool for ID {tool_id}. Skipping.")
                    continue

                
                # If no supervisors, we execute the function
                if not supervisors_chains:
                    print(f"No supervisors found for function {tool_id}. Executing function.")
                    continue

                all_decisions = []

                # Iterate over all the supervisor chains for the tool and run each supervisor
                for supervisor_chain in supervisors_chains:
                    chain_decisions = []
                    
                    # We send supervision request to the API
                    supervisors = supervisor_chain.supervisors
                    supervisor_chain_id = supervisor_chain.chain_id
                    for position_in_chain, supervisor in enumerate(supervisors):
                        print(f"Would send supervision request for supervisor {supervisor.id} in chain {supervisor_chain_id} at position {position_in_chain}")
                        # supervision_request_id = send_supervision_request(
                        #     supervisor_chain_id=supervisor_chain_id, 
                        #     supervisor_id=supervisor.id, 
                        #     request_group_id=tool_request_group.id, 
                        #     position_in_chain=position_in_chain
                        # )

                        decision = None
                        supervisor_func = supervision_context.get_supervisor_by_id(supervisor.id)
                        if supervisor_func is None:
                            print(f"No local supervisor function found for ID {supervisor.id}. Skipping.")
                            return None  # Continue to next supervisor

                        print(f"Executing supervisor function {supervisor_func}")
                        fakeUUID = UUID('00000000-0000-0000-0000-000000000000')
                        # Execute supervisor function
                        decision = call_supervisor_function(
                            supervisor_func, 
                            tool, 
                            supervision_context, 
                            # supervision_request_id=supervision_request_id, 
                            supervision_request_id=fakeUUID,
                            decision=decision
                        )
                        chain_decisions.append(decision)
                        print(f"Supervisor decision: {decision.decision}")

                        # Don't submit results for human supervision because it is handled by the server
                        if supervisor.type != SupervisorType.HUMAN_SUPERVISOR:
                            print(f"Would send supervision result for supervisor {supervisor.id} in chain {supervisor_chain_id} at position {position_in_chain}")
                            # We send the decision to the API
                        #     send_supervision_result(
                        #         supervision_request_id=supervision_request_id,
                        #         request_group_id=tool_request_group.id,
                        #         tool_id=tool_id,
                        #         supervisor_id=supervisor.id,
                        #         decision=decision,
                        #         client=client,
                        #         tool_request=tool_request, #TODO: Fix for n > 1
                        #         tool_args=tool_args, #TODO: If modified, send modified args and kwargs
                        #         tool_kwargs=tool_kwargs
                        # )
                        # Handle the decision
                        error_message = self.handle_supervision_decision(
                            decision, 
                            chain_decisions, 
                            tool
                        )
                        if error_message:
                            return error_message

                # Handle the final decisions
                final_error_message = self.handle_final_decisions(
                    all_decisions, 
                    tool
                )
                
                if final_error_message:
                    return final_error_message
        except Exception as e:
            print(f"\n=== ERROR DETAILS ===")
            print(f"Error type: {type(e)}")
            print(f"Error message: {str(e)}")
            print(f"Error occurred at line {e.__traceback__.tb_lineno}")
            raise SentinelLoggingError(f"Failed to log response: {str(e)}") from e

    def handle_supervision_decision(
        self,
        decision: SupervisionDecision,
        chain_decisions: List[SupervisionDecision],
        tool: Tool,
    ) -> Optional[str]:
        """Handle a supervision decision and return an error message if execution should stop"""
        
        if decision.decision == SupervisionDecisionType.APPROVE:
            return None
        
        elif decision.decision == SupervisionDecisionType.REJECT:
            explanations = " ".join([f"Decision: {d.decision}, Explanation: {d.explanation}" for d in chain_decisions])
            return (f"The agent requested to execute {tool.name} but it was rejected. "
                    f"Explanation: {decision.explanation}. "
                    f"Chain Explanations: {explanations}\n"
                    "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try different action using the feedback!")
                
        elif decision.decision == SupervisionDecisionType.ESCALATE:
            # Handled by caller - return None to continue to next supervisor
            return None
        
        elif decision.decision == SupervisionDecisionType.MODIFY:
            # Handled by caller - return None to continue processing
            return None
        
        elif decision.decision == SupervisionDecisionType.TERMINATE:
            explanations = " ".join([f"Decision: {d.decision}, Explanation: {d.explanation}" for d in chain_decisions])
            return (f"Execution of {tool.name} should be terminated. "
                    f"Explanation: {decision.explanation}. "
                    f"Chain Explanations: {explanations}\n"
                    "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try different action using the feedback!")
        
        else:
            explanations = " ".join([f"Decision: {d.decision}, Explanation: {d.explanation}" for d in chain_decisions])
            return (f"Execution of {tool.name} was cancelled due to an unknown supervision decision. "
                    f"Chain Explanations: {explanations}\n"
                    "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try different action using the feedback!")

    def handle_final_decisions(
        self,
        all_decisions: List[SupervisionDecision],
        tool: Tool,
        tool_args: List[Any],
        tool_kwargs: Dict[str, Any],
        ignored_attributes: List[str]
    ) -> Any:
        """Process all decisions and execute the function if approved"""
        
        # Check if all decisions are approve or modify
        if all(
            decision.decision in [SupervisionDecisionType.APPROVE, SupervisionDecisionType.MODIFY] 
            for decision in all_decisions
        ):
            return f"All decisions approved or modified. Executing {tool.name} with args: {tool_args} and kwargs: {tool_kwargs}"   
        else:
            explanations = " ".join([f"Supervisor {idx}: Decision: {d.decision}, Explanation: {d.explanation} \n" 
                                    for idx, d in enumerate(all_decisions)])
            return (f"The agent requested to execute a function but it was rejected by some supervisors.\n"
                    f"Chain Explanations: \n{explanations}\n"
                    "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try something else!")

def call_supervisor_function(
    supervisor_func, 
    tool, 
    supervision_context, 
    supervision_request_id: UUID, 
    decision: Optional[SupervisionDecision] = None
):
    if asyncio.iscoroutinefunction(supervisor_func):
        decision = asyncio.run(
            supervisor_func(
                tool, 
                supervision_context=supervision_context, 
                supervision_request_id=supervision_request_id, 
                decision=decision
            )
        )
    else:
        decision = supervisor_func(
            tool, 
            supervision_context=supervision_context, 
            supervision_request_id=supervision_request_id, 
            decision=decision
        )
    return decision
