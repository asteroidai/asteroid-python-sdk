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
        def wrapper(*args, **kwargs):
            # Execute the function directly
            return func(*args, **kwargs)
            
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
