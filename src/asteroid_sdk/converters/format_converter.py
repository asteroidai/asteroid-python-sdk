"""
Converts client-specific request formats to a standard format.
"""

from typing import Dict, Any

def convert_to_standard_format(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts input data to the standard format.

    Args:
        data (Dict[str, Any]): Original request data.

    Returns:
        Dict[str, Any]: Standardized request data.
    """
    standard_data = {
        "messages": data.get("messages", []),
        "model": data.get("model", ""),
        "temperature": data.get("temperature", 1.0),
        "max_tokens": data.get("max_tokens", 256),
        "additional_params": {
            k: v for k, v in data.items()
            if k not in ["messages", "model", "temperature", "max_tokens"]
        }
    }
    return standard_data
