import json
from typing import Any, Callable
from openai import OpenAI
from pydantic import BaseModel
from .config import PREFERRED_LLM_MODEL

client = OpenAI()

def create_schema_from_function(func: Callable) -> dict:
    """Create a JSON schema from a function's return type annotation."""
    return_type = func.__annotations__.get('return')
    if not return_type or not issubclass(return_type, BaseModel):
        raise ValueError("Function must have a Pydantic BaseModel return type annotation")
    
    return return_type.model_json_schema()

def sample_from_llm(func: Callable, *args, **kwargs) -> Any:
    """Sample a response from the LLM based on the function's signature and return type."""
    func_name = func.__name__
    func_doc = func.__doc__ or "No description available."
    schema = create_schema_from_function(func)
    
    # Prepare messages for the chat completion
    messages = [
        {
            "role": "system",
            "content": (
                f"You are simulating the API function '{func_name}'. {func_doc} "
                f"Provide a response that matches the following JSON schema: {json.dumps(schema)}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Please generate a valid response for the function '{func_name}' "
                f"with the following arguments: args={args}, kwargs={kwargs}"
            ),
        },
    ]

    try:
        completion = client.chat.completions.create(
            model=PREFERRED_LLM_MODEL,
            messages=messages,
            # Using functions and function_call as per the API
            functions=[
                {
                    "name": func_name,
                    "description": func_doc,
                    "parameters": schema,
                }
            ],
            function_call={"name": func_name},
            temperature=0,
        )
        
        # Parse the function call arguments from the response
        response = completion.choices[0].message.function_call.arguments
        response_data = json.loads(response)
        
        # Validate the response against the schema
        return_type = func.__annotations__['return']
        validated_response = return_type(**response_data)
        
        return validated_response
    except Exception as e:
        print(f"Error sampling from LLM: {str(e)}")
        raise ValueError(
            f"Failed to generate a valid response from LLM for function '{func_name}'"
        )
