from typing import Any, Callable, List, Optional
from functools import wraps

from .config import supervision_config
from ..mocking.policies import MockPolicy

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
