from typing import Any, get_origin, get_args, Callable, Dict, Any, Union, Optional
import random
import string
import inspect


def create_random_value(return_type: type) -> Any:
    origin = get_origin(return_type)
    args = get_args(return_type)

    if origin is None:
        if return_type == int:
            return random.randint(-1000, 1000)
        elif return_type == float:
            return random.uniform(-1000.0, 1000.0)
        elif return_type == str:
            return ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        elif return_type == bool:
            return random.choice([True, False])
        else:
            raise ValueError(f"Unsupported simple type: {return_type}")
    elif origin is list:
        return [create_random_value(args[0]) for _ in range(random.randint(1, 5))]
    elif origin is dict:
        key_type, value_type = args
        return {create_random_value(key_type): create_random_value(value_type) for _ in range(random.randint(1, 5))}
    elif origin is Union:
        return create_random_value(random.choice(args))
    elif origin is Optional:
        return random.choice([None, create_random_value(args[0])])
    else:
        raise ValueError(f"Unsupported complex type: {return_type}")

def get_function_code(func: Callable) -> str:
    """Retrieve the source code of a function."""
    try:
        return inspect.getsource(func)
    except Exception as e:
        return f"Error retrieving source code: {str(e)}"
    
    