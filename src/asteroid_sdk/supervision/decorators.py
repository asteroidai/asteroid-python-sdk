from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps
from uuid import UUID

from .config import SupervisionDecision, SupervisionContext, get_supervision_config
from asteroid_sdk.supervision.protocols import Supervisor
from openai.types.chat import ChatCompletionMessage
from anthropic.types.message import Message 
import functools

def supervise(
    supervision_functions: Optional[List[List[Callable]]] = None,
    ignored_attributes: Optional[List[str]] = None,    
):
    """
    Decorator to supervise a tool.

    Can be used in the following ways:
    
    - As a decorator for functions without tool and run_id:
      @supervise(supervision_functions=..., ignored_attributes=...)
      def my_tool(...): ...

    Args:
        supervision_functions (Optional[List[List[Callable]]]): Supervision functions to use.
        ignored_attributes    (Optional[List[str]]): Attributes to ignore in supervision.
        
    """
    supervision_config = get_supervision_config()
    def decorator(func):
        # Store in pending supervised functions for later registration
        supervision_config.register_pending_supervised_function(
            tool=func,
            supervision_functions=supervision_functions,
            ignored_attributes=ignored_attributes,
        )

        @wraps(func)
        def wrapper(*args, **kwargs):
            # TODO: Add logging here?
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
