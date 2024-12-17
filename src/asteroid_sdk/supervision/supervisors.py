from typing import Callable, Optional, Protocol, Any
from functools import wraps
from uuid import UUID

from asteroid_sdk.api.generated.asteroid_api_client.models.tool import Tool
from asteroid_sdk.registration.helper import get_human_supervision_decision_api
from .config import (
    SupervisionDecision,
    SupervisionDecisionType,
    SupervisionContext,
    PREFERRED_LLM_MODEL,
    ModifiedData,
)
import json
from openai import OpenAI
from openai.types.chat.chat_completion_message import ChatCompletionMessageToolCall, ChatCompletionMessage

client = OpenAI()

class ToolCallSupervisor(Protocol):
    """
    Protocol for tool call supervisors.
    """

    def __call__(
        self,
        tool: Tool,
        tool_call: ChatCompletionMessageToolCall,
        supervision_context: SupervisionContext,
        ignored_attributes: list[str] = [],
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs
    ) -> SupervisionDecision:
        """
        Makes a decision based on the function, its arguments,
        and the supervision context.

        Args:
            func (Callable): The function being supervised.
            tool_call (dict): The tool call to be supervised.
            ignored_attributes (List[str]): Attributes to ignore.
            tool_kwargs (dict[str, Any]): Keyword arguments for the function.
            supervision_context (SupervisionContext): Additional context.
            supervision_request_id (Optional[UUID]): ID of the supervision request.
            previous_decision (Optional[SupervisionDecision]): Decision made by the previous supervisor that escalated to this Supervisor.
        Returns:
            SupervisionDecision: The decision made by the supervisor.
        """
        ...


class ChatSupervisor(Protocol):
    """
    Protocol for chat supervisors.
    """

    def __call__(
        self,
        message: str,
        supervision_context: Optional[SupervisionContext],
        ignored_attributes: list[str] = [],
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs
    ) -> SupervisionDecision:
        ...

DEFAULT_SYSTEM_PROMPT = (
    "You are an AI safety reviewer. Your task is to evaluate the following function call "
    "and decide whether it should be approved, rejected, escalated, terminated, or modified. "
    "Provide your decision along with an explanation."
)

def llm_supervisor(
    instructions: str,
    supervisor_name: Optional[str] = None,
    description: Optional[str] = None,
    openai_model: str = PREFERRED_LLM_MODEL,
    system_prompt: Optional[str] = None,
    include_context: bool = False
) -> ToolCallSupervisor:
    """
    Create a supervisor function that uses an LLM to make a supervision decision.
    """
    if system_prompt is None:
        system_prompt = """
Your goal is to review the agent's function call based on the provided policies, rules, and context. 
You need to decide whether the function call should be approved, rejected, escalated, terminated, or modified. 
Provide your decision along with a clear explanation. If you choose to modify the function call, specify the modified arguments in the following format:

ModifiedData:
- tool_args: [list of modified positional arguments]
- tool_kwargs: {dictionary of modified keyword arguments}
"""

    def supervisor(
        tool: Tool,
        tool_call: ChatCompletionMessageToolCall,
        supervision_context: SupervisionContext,
        ignored_attributes: list[str] = [],
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs
    ) -> SupervisionDecision:
        """
        LLM supervisor that makes a decision based on the function call, its arguments, and the supervision instructions.
        """
        # Prepare tool arguments string
        tool_args = []
        tool_kwargs = json.loads(tool_call.function.arguments)
        tool_args_str = ", ".join([f"{i}: {repr(arg)}" for i, arg in enumerate(tool_args)])
        tool_kwargs_str = ", ".join(
            [f"{k}={repr(v)}" for k, v in tool_kwargs.items() if k not in ignored_attributes] +
            [f"{k}=<value hidden> - Assume the value is correct" for k in ignored_attributes]
        )
        if tool_args_str and tool_kwargs_str:
            arguments_str = f"Positional Arguments:\n{tool_args_str}\nKeyword Arguments:\n{tool_kwargs_str}"
        elif tool_args_str:
            arguments_str = f"Positional Arguments:\n{tool_args_str}"
        elif tool_kwargs_str:
            arguments_str = f"Keyword Arguments:\n{tool_kwargs_str}"
        else:
            arguments_str = "The function does not require any arguments."

        # Prepare the assistant's instructions
        instructions_content = "Instructions:\n" + instructions 
        
        if previous_decision is not None:
            instructions_content += "\n\nDecision made by the previous supervisor:\nDecision: " + previous_decision.decision + "\nExplanation: " + str(previous_decision.explanation)

        if include_context and supervision_context:
            # Convert SupervisionContext into a textual description
            context_description = supervision_context.to_text()
            instructions_content += f"""
This is the conversation between the AI customer support assistant and the customer:
{context_description}
"""

        instructions_content += f"""
The AI agent is attempting to call the following function:

Function Name:
{tool.name}

Function Description:
{tool.description}

Function Implementation:


Arguments Passed to the Function:
{arguments_str}

Given the context and your specific instructions, you need to decide whether the function call should be **approved**, **rejected**, **escalated**, **terminated**, or **modified**. Provide your decision along with a clear and concise explanation. If you choose to modify the function call, specify the modified arguments in the following format:

ModifiedData:
- tool_args: [List[Any]
- tool_kwargs: [Dict[str, Any]]
"""

        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": instructions_content.strip()},
        ]

        # Define the function schema for SupervisionDecision
        supervision_decision_schema = SupervisionDecision.model_json_schema()

        # Prepare the function definition for the OpenAI API
        functions = [
            {
                "name": "supervision_decision",
                "description": "Make a supervision decision for the given function call. If you modify the function call, include the modified arguments or keyword arguments in the 'modified' field.",
                "parameters": supervision_decision_schema,
            }
        ]

        try:
            # Call the OpenAI API
            completion = client.chat.completions.create(
                model=openai_model,
                messages=messages,
                functions=functions,
                function_call={"name": "supervision_decision"},
            )

            # Extract the function call arguments from the response
            message = completion.choices[0].message
            if message.function_call:
                response_args = message.function_call.arguments
                response_data = json.loads(response_args)
            else:
                raise ValueError("No valid function call in assistant's response.")

            # Parse the 'modified' field, only including fields that have changed
            modified_data = None
            if response_data.get("modified"):
                modified_fields = response_data["modified"]
                modified_data = ModifiedData(
                    tool_args=modified_fields.get("tool_args", tool_args),
                    tool_kwargs=modified_fields.get("tool_kwargs", tool_kwargs)
                )

            decision = SupervisionDecision(
                decision=response_data.get("decision"),
                modified=modified_data,
                explanation=response_data.get("explanation")
            )
            return decision

        except Exception as e:
            print(f"Error during LLM supervision: {str(e)}")
            return SupervisionDecision(
                decision=SupervisionDecisionType.ESCALATE,
                explanation=f"Error during LLM supervision: {str(e)}",
                modified=None
            )

    supervisor.__name__ = supervisor_name if supervisor_name else llm_supervisor.__name__
    supervisor.__doc__ = description if description else supervisor.__doc__
    supervisor.supervisor_attributes = {
        "instructions": instructions,
        "openai_model": openai_model,
        "system_prompt": system_prompt,
        "include_context": include_context
    }
    return supervisor


def human_supervisor(
    timeout: int = 300,
    n: int = 1,
) -> ToolCallSupervisor:
    """
    Create a supervisor function that requires human approval via backend API or CLI.

    Args:
        timeout (int): Timeout in seconds for waiting for the human decision.
        n (int): Number of approvals required.

    Returns:
        Supervisor: A supervisor function that implements human supervision.
    """
    def supervisor(
        tool: Tool,
        tool_call: ChatCompletionMessageToolCall,
        supervision_context: SupervisionContext,
        ignored_attributes: list[str] = [],
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs
    ) -> SupervisionDecision:
        """
        Human supervisor that requests approval via backend API or CLI.

        Args:
            tool (Tool): The tool being supervised.
            tool_call (ChatCompletionMessageToolCall): The tool call to be supervised.
            supervision_context (SupervisionContext): Additional context.
            ignored_attributes (List[str]): Attributes to ignore.
            supervision_request_id (Optional[UUID]): ID of the supervision request.
            previous_decision (Optional[SupervisionDecision]): Decision made by the previous supervisor.

        Returns:
            SupervisionDecision: The decision made by the supervisor.
        """

        # Get the human supervision decision
        supervisor_decision = get_human_supervision_decision_api(
            supervision_request_id=supervision_request_id,
            timeout=timeout,
        )

        return supervisor_decision

    supervisor.__name__ = human_supervisor.__name__
    supervisor.supervisor_attributes = {"timeout": timeout, "n": n}
    return supervisor


def auto_approve_supervisor() -> ToolCallSupervisor:
    """Creates a supervisor that automatically approves any input."""
    def supervisor(
        tool: Tool,
        tool_call: ChatCompletionMessageToolCall,
        supervision_context: SupervisionContext,
        ignored_attributes: list[str] = [],
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs
    ) -> SupervisionDecision:
        return SupervisionDecision(
            decision=SupervisionDecisionType.APPROVE,
            explanation="No supervisor found for this function. It's automatically approved.",
            modified=None
        )
    supervisor.__name__ = auto_approve_supervisor.__name__
    supervisor.supervisor_attributes = {}
    return supervisor

def tool_supervisor_decorator(**config_kwargs) -> Callable:
    """Decorator to create a supervisor function with arbitrary configuration parameters."""
    def decorator(func: Callable) -> ToolCallSupervisor:
        @wraps(func)
        def wrapper(
            tool: Tool,
            tool_call: ChatCompletionMessageToolCall,
            supervision_context: SupervisionContext,
            ignored_attributes: list[str] = [],
            supervision_request_id: Optional[UUID] = None,
            previous_decision: Optional[SupervisionDecision] = None,
            **kwargs
        ) -> SupervisionDecision:
            # Pass the configuration parameters to the supervisor function
            return func(
                tool=tool,
                tool_call=tool_call,
                supervision_context=supervision_context,
                ignored_attributes=ignored_attributes,
                supervision_request_id=supervision_request_id,
                previous_decision=previous_decision,
                config_kwargs=config_kwargs,
                **kwargs
            )
        return wrapper
    return decorator


def chat_supervisor_decorator(**config_kwargs) -> Callable:
    """Decorator to create a chat supervisor function with arbitrary configuration parameters."""
    def decorator(func: Callable) -> ChatSupervisor:
        @wraps(func)
        def wrapper(
            message: str,
            supervision_context: Optional[SupervisionContext] = None,
            ignored_attributes: list[str] = [],
            supervision_request_id: Optional[UUID] = None,
            previous_decision: Optional[SupervisionDecision] = None,
            **kwargs
        ) -> SupervisionDecision:
            # Pass the configuration parameters to the supervisor function
            return func(
                message=message,
                supervision_context=supervision_context,
                ignored_attributes=ignored_attributes,
                supervision_request_id=supervision_request_id,
                previous_decision=previous_decision,
                config_kwargs=config_kwargs,
                **kwargs
            )
        return wrapper
    return decorator

