from typing import Any, Callable, List, Optional, Union
from functools import wraps
from uuid import UUID

from .config import supervision_config
from ..mocking.policies import MockPolicy
from .config import SupervisionDecision, SupervisionContext
from asteroid_sdk.supervision.protocols import Supervisor
from openai.types.chat import ChatCompletionMessage
from anthropic.types.message import Message 
import functools


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
            # TODO: Log the function call
            return func(*args, **kwargs)

        return wrapper
    return decorator


def supervisor(func: Callable) -> Supervisor:
    """
    Decorator to wrap user-defined supervisor functions and ensure they conform to the Supervisor protocol.

    Args:
        func (Callable): The user-defined supervision function.

    Returns:
        Supervisor: A supervisor function that conforms to the Supervisor protocol.
    """

    @functools.wraps(func)
    def wrapper(
        message: Union[ChatCompletionMessage, Message],
        supervision_context: Optional[SupervisionContext] = None,
        ignored_attributes: List[str] = [],
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs
    ) -> SupervisionDecision:
        return func(
            message=message,
            supervision_context=supervision_context,
            ignored_attributes=ignored_attributes,
            supervision_request_id=supervision_request_id,
            previous_decision=previous_decision,
            **kwargs
        )

    # Preserve any attributes set on the original function
    wrapper.supervisor_attributes = getattr(func, 'supervisor_attributes', {})
    return wrapper
