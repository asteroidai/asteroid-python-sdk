from typing import Callable, Dict, List, Optional, Set, Any
from entropy_labs.supervision.config import SupervisionDecisionType, SupervisionDecision, supervision_config, SupervisionContext
from inspect_ai.tool import ToolCall
from entropy_labs.sentinel_api_client.sentinel_api_client.client import Client
from uuid import UUID

def human_supervisor(agent_id: str = "default_agent", timeout: int = 300, n: int = 1):
    async def supervisor(func: Callable, supervision_context: SupervisionContext, supervision_request_id: Optional[UUID] = None, ignored_attributes: List[str] = [], 
                         tool_args: List[Any] = [], tool_kwargs: dict[str, Any] = {}, decision: Optional[SupervisionDecision] = None) -> SupervisionDecision:
        """
        Human supervisor that requests approval via backend API or CLI.
        """
        from entropy_labs.supervision.common import human_supervisor_wrapper
        
        context = supervision_config.context
        
        # TODO: Reuse Supervise Protocol

        # Create TaskState from context - Right now we are using Inspect AI TaskState format to send to the backend, we need to transform langchain format to TaskState format
        task_state = context.to_task_state()
        id = 'tool_id'
        tool_call = ToolCall(id=id,function=func.__name__, arguments=tool_kwargs, type='function')
        client = supervision_config.client
        
        supervisor_decision = human_supervisor_wrapper(task_state=task_state, call=tool_call, timeout=timeout, use_inspect_ai=False, n=n, supervision_request_id=supervision_request_id, client=client)

        return supervisor_decision

    supervisor.__name__ = human_supervisor.__name__
    supervisor.supervisor_attributes = {"timeout": timeout, "n": n}
    return supervisor

def bash_supervisor(
    allowed_commands: List[str],
    allow_sudo: bool = False,
    command_specific_rules: Optional[Dict[str, List[str]]] = None
):
    """
    Decorator that creates a supervisor function to check bash commands.
    
    Args:
        allowed_commands (List[str]): List of allowed bash commands.
        allow_sudo (bool): Whether to allow sudo commands. Defaults to False.
        command_specific_rules (Optional[Dict[str, List[str]]]): Dictionary of command-specific rules.
    
    Returns:
        Callable: A supervisor function that checks bash commands.
    """
    def supervisor(func: Callable, ignored_attributes: List[str] = [], tool_kwargs: dict[str, Any] = {}) -> SupervisionDecision:
        from entropy_labs.supervision.common import check_bash_command
        
        command = tool_kwargs.get('command', '')
        is_approved, explanation = check_bash_command(
            command, allowed_commands, allow_sudo, command_specific_rules
        )
        if is_approved:
            return SupervisionDecision(
                decision=SupervisionDecisionType.APPROVE,
                explanation=explanation
            )
        else:
            return SupervisionDecision(
                decision=SupervisionDecisionType.REJECT,
                explanation=explanation
            )
    
    supervisor.__name__ = bash_supervisor.__name__
    supervisor.supervisor_attributes = {"allowed_commands": allowed_commands, "allow_sudo": allow_sudo, "command_specific_rules": command_specific_rules}
    return supervisor

def python_supervisor(
    allowed_modules: List[str],
    allowed_functions: List[str],
    disallowed_builtins: Optional[Set[str]] = None,
    sensitive_modules: Optional[Set[str]] = None,
    allow_system_state_modification: bool = False
):
    """
    Decorator that creates a supervisor function to check Python code.
    
    Args:
        allowed_modules (List[str]): List of allowed Python modules.
        allowed_functions (List[str]): List of allowed functions.
        disallowed_builtins (Optional[Set[str]]): Set of disallowed built-in functions.
        sensitive_modules (Optional[Set[str]]): Set of sensitive modules to be blocked.
        allow_system_state_modification (bool): Whether to allow modification of system state.
    
    Returns:
        Callable: A supervisor function that checks Python code.
    """
    def supervisor(func: Callable, ignored_attributes: List[str] = [], tool_kwargs: dict[str, Any] = {}) -> SupervisionDecision:
        from entropy_labs.supervision.common import check_python_code
        
        code = tool_kwargs.get('code', '')
        is_approved, explanation = check_python_code(
            code, allowed_modules, allowed_functions, disallowed_builtins,
            sensitive_modules, allow_system_state_modification
        )
        if is_approved:
            return SupervisionDecision(
                decision=SupervisionDecisionType.APPROVE,
                explanation=explanation
            )
        else:
            return SupervisionDecision(
                decision=SupervisionDecisionType.REJECT,
                explanation=explanation
            )
    
    supervisor.__name__ = python_supervisor.__name__
    supervisor.supervisor_attributes = {"allowed_modules": allowed_modules, "allowed_functions": allowed_functions, "disallowed_builtins": disallowed_builtins, "sensitive_modules": sensitive_modules, "allow_system_state_modification": allow_system_state_modification}
    return supervisor
