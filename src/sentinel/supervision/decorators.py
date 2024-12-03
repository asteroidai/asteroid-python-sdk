import asyncio
from typing import Any, Callable, List, Optional
from functools import wraps

from .config import supervision_config, SupervisionDecisionType, SupervisionDecision
from ..mocking.policies import MockPolicy
from ..utils.utils import create_random_value
from .llm_sampling import sample_from_llm
import random
from uuid import UUID
from sentinel.api.generated.sentinel_api_client.models.supervisor_type import SupervisorType
from sentinel.api.generated.sentinel_api_client.models.tool_request import ToolRequest
from sentinel.api.generated.sentinel_api_client.models.arguments import Arguments
from sentinel.api.generated.sentinel_api_client.models.message import Message
from sentinel.api.generated.sentinel_api_client.models.task_state import TaskState
from sentinel.api.generated.sentinel_api_client.models.tool_request_group import ToolRequestGroup

def supervise(
    mock_policy: Optional[MockPolicy] = None,
    mock_responses: Optional[List[Any]] = None,
    supervision_functions: Optional[List[List[Callable]]] = None,
    ignored_attributes: Optional[List[str]] = None
):
    """
    Decorator that supervises a function.
    
    Args:
        mock_policy           (Optional[MockPolicy]): Mock policy to use. Defaults to None.
        mock_responses        (Optional[List[Any]]): Mock responses to use. Defaults to None.
        supervision_functions (Optional[List[List[Callable]]]): Supervision functions to use. Defaults to None.
        ignored_attributes    (Optional[List[str]]): Ignored attributes. Defaults to None.
    """
    if (
        supervision_functions 
        and len(supervision_functions) == 1 
        and isinstance(supervision_functions[0], list)
    ):
        supervision_functions = [supervision_functions[0]]

    def decorator(func):
        # Register the supervised function in SupervisionConfig's pending functions
        supervision_config.register_pending_supervised_function(
            func, 
            supervision_functions, 
            ignored_attributes
        )

        @wraps(func)
        def wrapper(*tool_args, **tool_kwargs):
            
            from sentinel.registration.helper import create_tool_request_group, get_supervisor_chains_for_tool, send_supervision_request, send_supervision_result, _serialize_arguments

            supervision_context = supervision_config.get_all_runs()[0].supervision_context
            client = supervision_config.client  # Get the Sentinel API client
            # TODO: This for now assumes there is only one run
            
            print(f"\n--- Supervision ---")
            print(f"Function Name: {func.__qualname__}")
            print(f"Description: {func.__doc__}")
            print(f"Arguments: {tool_args}, {tool_kwargs.keys()}")

            # Retrieve the tool_id from the registry
            entry = supervision_context.get_supervised_function_entry(func.__qualname__)
            if entry:
                tool_id = entry['tool_id']
                ignored_attributes = entry['ignored_attributes']
                run_id = entry['run_id']
            else:
                raise Exception(f"Tool ID for function {func.__name__} not found in the registry.")
            
            # TODO if n > 1, it would be handled here
            arguments_dict = _serialize_arguments(tool_args, tool_kwargs)
            
            tool_requests = [ToolRequest(tool_id=tool_id, 
                                         message=supervision_context.get_api_messages()[-1],
                                         arguments=Arguments.from_dict(arguments_dict), 
                                         task_state=supervision_context.to_task_state())]
            tool_request_group = create_tool_request_group(tool_id, tool_requests, client)
            tool_request = tool_request_group.tool_requests[0] #TODO: Fix for n > 1
            supervisors_chains = get_supervisor_chains_for_tool(tool_id, client)

            # Determine effective mock policy
            effective_mock_policy = (
                supervision_config.global_mock_policy
                if supervision_config.override_local_policy
                else (mock_policy or supervision_config.global_mock_policy)
            )
            # Handle mocking
            if effective_mock_policy != MockPolicy.NO_MOCK:
                mock_result = handle_mocking(func, effective_mock_policy, mock_responses, *tool_args, **tool_kwargs)
                print(f"Mocking function execution. Mock result: {mock_result}")
                return mock_result
            # Supervision logic
            if not supervisors_chains:
                print(f"No supervisors found for function {func.__name__}. Executing function.")
                return func(*tool_args, **tool_kwargs)
            all_decisions = []
            for supervisor_chain in supervisors_chains:
                chain_decisions = []
                # We send supervision request to the API
                supervisors = supervisor_chain.supervisors
                supervisor_chain_id = supervisor_chain.chain_id
                for position_in_chain, supervisor in enumerate(supervisors):
                    supervision_request_id = send_supervision_request(
                        supervisor_chain_id=supervisor_chain_id, 
                        supervisor_id=supervisor.id, 
                        request_group_id=tool_request_group.id, 
                        position_in_chain=position_in_chain
                    )

                    decision = None
                    supervisor_func = supervision_context.get_supervisor_by_id(supervisor.id)
                    if supervisor_func is None:
                        print(f"No local supervisor function found for ID {supervisor.id}. Skipping.")
                        return None  # Continue to next supervisor

                    # Execute supervisor function
                    decision = call_supervisor_function(
                        supervisor_func, 
                        func, 
                        supervision_context, 
                        supervision_request_id=supervision_request_id, 
                        ignored_attributes=ignored_attributes, 
                        tool_args=tool_args, 
                        tool_kwargs=tool_kwargs, 
                        decision=decision
                    )
                    chain_decisions.append(decision)
                    print(f"Supervisor decision: {decision.decision}")

                    if supervisor.type != SupervisorType.HUMAN_SUPERVISOR:
                        # We send the decision to the API
                        send_supervision_result(
                            supervision_request_id=supervision_request_id,
                            request_group_id=tool_request_group.id,
                            tool_id=tool_id,
                            supervisor_id=supervisor.id,
                            decision=decision,
                            client=client,
                            tool_request=tool_request, #TODO: Fix for n > 1
                            tool_args=tool_args, #TODO: If modified, send modified args and kwargs
                            tool_kwargs=tool_kwargs
                    )
                    # Handle the decision
                    if decision.decision == SupervisionDecisionType.APPROVE:
                        all_decisions.append(decision)
                        break
                    elif decision.decision == SupervisionDecisionType.REJECT:
                        explanations = " ".join([f"Decision: {d.decision}, Explanation: {d.explanation}" for d in chain_decisions])
                        return (f"The agent requested to execute {func.__qualname__} but it was rejected. "
                                f"Explanation: {decision.explanation}. "
                                f"Chain Explanations: {explanations}\n"
                                "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try different action using the feedback!")
                    elif decision.decision == SupervisionDecisionType.ESCALATE:
                        # if last decision in chain is escalate, we continue to the next supervisor chain
                        if position_in_chain == len(supervisors) - 1:
                            all_decisions.append(decision)
                        continue
                    elif decision.decision == SupervisionDecisionType.MODIFY:
                        all_decisions.append(decision)
                        break
                    elif decision.decision == SupervisionDecisionType.TERMINATE:
                        explanations = " ".join([f"Decision: {d.decision}, Explanation: {d.explanation}" for d in chain_decisions])
                        return (f"Execution of {func.__qualname__} should be terminated. "
                                f"Explanation: {decision.explanation}. "
                                f"Chain Explanations: {explanations}\n"
                                "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try different action using the feedback!")
                    else:
                        print(f"Unknown decision: {decision.decision}. Cancelling execution.")
                        explanations = " ".join([f"Decision: {d.decision}, Explanation: {d.explanation}" for d in chain_decisions])
                        return (f"Execution of {func.__qualname__} was cancelled due to an unknown supervision decision. "
                                f"Chain Explanations: {explanations}\n"
                                "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try different action using the feedback!")

            # Check decisions and apply modifications if any
            if all(
                decision.decision in [SupervisionDecisionType.APPROVE, SupervisionDecisionType.MODIFY] 
                for decision in all_decisions
            ):
                print("All decisions approved or modified.")
                # Start with original arguments
                final_args = list(tool_args)
                final_kwargs = tool_kwargs.copy()

                # Apply modifications while respecting ignored_attributes
                for decision in all_decisions:
                    if decision.decision == SupervisionDecisionType.MODIFY and decision.modified:
                        #TODO: Make sure this works correctly
                        tool_args = decision.modified.tool_args
                        # Update keyword arguments
                        if decision.modified.tool_kwargs:
                            for key, value in decision.modified.tool_kwargs.items():
                                if ignored_attributes and key in ignored_attributes:
                                    continue
                                final_kwargs[key] = value
                        break

                # Call the function with modified arguments
                return func(*final_args, **final_kwargs)
            else:
                explanations = " ".join([f"Supervisor {idx}: Decision: {d.decision}, Explanation: {d.explanation} \n" for idx, d in enumerate(all_decisions)])
                return (f"The agent requested to execute a function but it was rejected by some supervisors.\n"
                        f"Chain Explanations: \n{explanations}\n"
                        "This is not a message from the user but from a supervisor system that is helping the agent to improve its behavior. You should try something else!")
        return wrapper
    return decorator


def call_supervisor_function(supervisor_func, func, supervision_context, supervision_request_id: UUID, ignored_attributes: List[str], tool_args: List[Any], tool_kwargs: dict[str, Any], decision: Optional[SupervisionDecision] = None):
    if asyncio.iscoroutinefunction(supervisor_func):
        decision = asyncio.run(supervisor_func(
            func, supervision_context=supervision_context, supervision_request_id=supervision_request_id, ignored_attributes=ignored_attributes, tool_args=tool_args, tool_kwargs=tool_kwargs, decision=decision
        ))
    else:
        decision = supervisor_func(
            func, supervision_context=supervision_context, supervision_request_id=supervision_request_id, ignored_attributes=ignored_attributes, tool_args=tool_args, tool_kwargs=tool_kwargs, decision=decision
        )
    return decision

def handle_mocking(func, mock_policy, mock_responses, *args, **kwargs):
    """Handle different mock policies."""
    if mock_policy == MockPolicy.NO_MOCK:
        return func(*args, **kwargs)
    elif mock_policy == MockPolicy.SAMPLE_LIST:
        if mock_responses:
            return random.choice(mock_responses)
        else:
            raise ValueError("No mock responses provided for SAMPLE_LIST policy")
    elif mock_policy == MockPolicy.SAMPLE_RANDOM:
        tool_return_type = func.__annotations__.get('return', None)
        if tool_return_type:
            return create_random_value(tool_return_type)
        else:
            raise ValueError("No return type specified for the function")
    elif mock_policy == MockPolicy.SAMPLE_PREVIOUS_CALLS:
        try:
            return supervision_config.get_mock_response(func.__name__)  # TODO: Make sure this works
        except ValueError as e:
            print(f"Warning: {str(e)}. Falling back to actual function execution.")
            return func(*args, **kwargs)
    elif mock_policy == MockPolicy.SAMPLE_LLM:
        return sample_from_llm(func, *args, **kwargs)
    else:
        raise ValueError(f"Unsupported mock policy: {mock_policy}")
