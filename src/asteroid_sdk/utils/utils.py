from typing import Any, get_origin, get_args, Callable, Any, Union, Optional
import random
import string
import inspect
import importlib.resources

def load_template(template_file: str, prompts_package: str = 'asteroid_sdk.supervision.prompts') -> str:
    """
    Load a Jinja template from the specified prompts package.

    Args:
        template_file (str): The filename of the Jinja template.
        prompts_package (str): The package path where prompts are stored.

    Returns:
        str: The loaded template content.

    Raises:
        ValueError: If the template file is not found.
    """
    try:
        with importlib.resources.open_text(prompts_package, template_file) as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError(f"Template file '{template_file}' not found in '{prompts_package}'.")

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
    
    