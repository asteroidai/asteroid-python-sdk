"""
Registry for supervised functions and their associated supervisors.
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from functools import wraps
import inspect

@dataclass
class SupervisorInfo:
    """Information about a supervisor function."""
    name: str
    function: Callable
    description: Optional[str] = None

@dataclass
class SupervisedFunction:
    """Information about a function and its associated supervisors."""
    function: Callable
    supervisors: List[List[SupervisorInfo]]
    name: str
    description: str
    signature: inspect.Signature

class SupervisionRegistry:
    """Registry for supervised functions and their supervisors."""
    
    _instance = None
    _supervised_functions: Dict[str, SupervisedFunction] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupervisionRegistry, cls).__new__(cls)
        return cls._instance
    
    def register_function(self, func: Callable, supervisors: List[List[SupervisorInfo]]) -> None:
        """Register a function and its supervisors."""
        func_name = func.__name__
        func_doc = func.__doc__ or ""
        func_signature = inspect.signature(func)
        
        self._supervised_functions[func_name] = SupervisedFunction(
            function=func,
            supervisors=supervisors,
            name=func_name,
            description=func_doc.strip(),
            signature=func_signature
        )
    
    def get_supervised_functions(self) -> Dict[str, SupervisedFunction]:
        """Get all registered supervised functions."""
        return self._supervised_functions
    
    def clear(self) -> None:
        """Clear the registry."""
        self._supervised_functions.clear()

# Global registry instance
registry = SupervisionRegistry()

def supervise(supervision_functions: List[List[Callable]]):
    """
    Decorator to register a function with its supervisors.
    
    Args:
        supervision_functions: List of lists of supervisor functions.
            Each inner list represents a chain of supervisors.
    """
    def decorator(func: Callable) -> Callable:
        # Convert supervisor functions to SupervisorInfo objects
        supervisor_chains = []
        for chain in supervision_functions:
            supervisor_chain = []
            for supervisor_func in chain:
                supervisor_info = SupervisorInfo(
                    name=supervisor_func.__name__,
                    function=supervisor_func,
                    description=supervisor_func.__doc__
                )
                supervisor_chain.append(supervisor_info)
            supervisor_chains.append(supervisor_chain)
        
        # Register the function with its supervisors
        registry.register_function(func, supervisor_chains)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator
