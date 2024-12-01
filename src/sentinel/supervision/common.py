import ast
import shlex
from typing import List, Dict, Optional, Tuple, Set, Literal
from inspect_ai.solver import TaskState
from inspect_ai.tool import ToolCall
from inspect_ai.approval import Approval
from entropy_labs.supervision.config import SupervisionDecision, SupervisionDecisionType
from entropy_labs.api.sentinel_api_client_helper import get_human_supervision_decision_api
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from entropy_labs.sentinel_api_client.sentinel_api_client.client import Client
from uuid import UUID

def prompt_user_cli_approval(
    task_state: TaskState,
    tool_call: ToolCall,
    use_inspect_ai: bool = False,
    n: int = 1
) -> SupervisionDecision:
    """Prompt the user for approval via CLI with detailed and formatted information."""

    if use_inspect_ai:
        # Use the input_screen context manager to align with inspect_ai's console handling
        from inspect_ai.util._console import input_screen
        with input_screen(width=None) as console:
            _display_approval_prompt(console, task_state, tool_call)

            # Prompt user for decision
            decision = console.input(
                "\n[bold]Choose an action[/bold]: Approve (a), Reject (r), Escalate (e), Terminate (t) [a]: "
            ).strip().lower() or 'a'

            if decision == 'a':
                decision_str = SupervisionDecisionType.APPROVE
                explanation = "User approved via CLI."
            elif decision == 'r':
                explanation = console.input("Enter reason for rejection: ")
                decision_str = SupervisionDecisionType.REJECT
            elif decision == 'e':
                decision_str = SupervisionDecisionType.ESCALATE
                explanation = "User escalated via CLI."
            else:
                decision_str = SupervisionDecisionType.TERMINATE
                explanation = "User terminated via CLI."
    else:
        console = Console()
        _display_approval_prompt(console, task_state, tool_call)

        # Prompt user for decision
        decision = Prompt.ask(
            "\n[bold]Choose an action[/bold]: Approve (a), Reject (r), Escalate (e), Terminate (t)",
            choices=["a", "r", "e", "t"],
            default="a"
        )

        if decision.lower() == 'a':
            decision_str = SupervisionDecisionType.APPROVE
            explanation = "User approved via CLI."
        elif decision.lower() == 'r':
            explanation = Prompt.ask("Enter reason for rejection")
            decision_str = SupervisionDecisionType.REJECT
        elif decision.lower() == 'e':
            decision_str = SupervisionDecisionType.ESCALATE
            explanation = "User escalated via CLI."
        else:
            decision_str = SupervisionDecisionType.TERMINATE
            explanation = "User terminated via CLI."

    return SupervisionDecision(decision=decision_str, explanation=explanation)

def _display_approval_prompt(console: Console, task_state: TaskState, tool_call: ToolCall):
    """Helper function to display the approval prompt using the given console."""

    # Display Task State Information
    task_info = [
        f"[bold]Sample ID:[/bold] {task_state.sample_id}",
        f"[bold]Epoch:[/bold] {task_state.epoch}",
        f"[bold]Model:[/bold] {task_state._model}",
        f"[bold]Input:[/bold] {task_state._input}",
        f"[bold]Completed:[/bold] {task_state.completed}"
    ]
    task_panel = Panel(
        "\n".join(task_info),
        title="[bold blue]Task State[/bold blue]",
        border_style="green"
    )

    # Display Latest Messages
    messages = "\n".join([
        f"[bold]{msg.role.capitalize()}:[/bold] {msg.text}"
        for msg in task_state.messages[-5:]
    ])
    messages_panel = Panel(
        messages,
        title="[bold blue]Conversation History (Last 5 Messages)[/bold blue]",
        border_style="yellow"
    )

    # Display Tool Call Information
    formatted_arguments = "\n".join([
        f"    [cyan]{key}[/cyan]: {value}" for key, value in tool_call.arguments.items()
    ])
    tool_call_info = [
        f"[bold]Function:[/bold] {tool_call.function}",
        f"[bold]Arguments:[/bold]\n{formatted_arguments}",
        f"[bold]Type:[/bold] {tool_call.type}"
    ]
    if tool_call.parse_error:
        tool_call_info.append(f"[bold]Parse Error:[/bold] {tool_call.parse_error}")
    tool_panel = Panel(
        "\n".join(tool_call_info),
        title="[bold blue]Tool Call Details[/bold blue]",
        border_style="magenta"
    )

    # Combine and display all panels
    console.print(task_panel)
    console.print(messages_panel)
    console.print(tool_panel)

def check_bash_command(
    command: str,
    allowed_commands: List[str],
    allow_sudo: bool = False,
    command_specific_rules: Optional[Dict[str, List[str]]] = None
) -> Tuple[bool, str]:
    """
    Check if a bash command is allowed based on the given rules.

    Args:
        command (str): The bash command to check.
        allowed_commands (List[str]): List of allowed bash commands.
        allow_sudo (bool, optional): Whether to allow sudo commands. Defaults to False.
        command_specific_rules (Optional[Dict[str, List[str]]], optional): Dictionary of command-specific rules.

    Returns:
        Tuple[bool, str]: A tuple containing a boolean (True if approved, False if rejected) and an explanation string.
    """
    dangerous_chars = ["&", "|", ";", ">", "<", "`", "$", "(", ")"]
    command_specific_rules = command_specific_rules or {}

    if not command.strip():
        return False, "Empty command"

    try:
        tokens = shlex.split(command)
    except ValueError as e:
        return False, f"Invalid command syntax: {str(e)}"

    if any(char in command for char in dangerous_chars):
        return False, f"Command contains potentially dangerous characters: {', '.join(char for char in dangerous_chars if char in command)}"

    base_command = tokens[0]

    if base_command == "sudo":
        if not allow_sudo:
            return False, "sudo is not allowed"
        if len(tokens) < 2:
            return False, "Invalid sudo command"
        base_command = tokens[1]
        tokens = tokens[1:]

    if base_command not in allowed_commands:
        return False, f"Command '{base_command}' is not in the allowed list. Allowed commands: {', '.join(allowed_commands)}"

    if base_command in command_specific_rules:
        allowed_subcommands = command_specific_rules[base_command]
        if len(tokens) > 1 and tokens[1] not in allowed_subcommands:
            return False, f"{base_command} subcommand '{tokens[1]}' is not allowed. Allowed subcommands: {', '.join(allowed_subcommands)}"

    return True, f"Command '{command}' is approved."

def check_python_code(
    code: str,
    allowed_modules: List[str],
    allowed_functions: List[str],
    disallowed_builtins: Optional[Set[str]] = None,
    sensitive_modules: Optional[Set[str]] = None,
    allow_system_state_modification: bool = False
) -> Tuple[bool, str]:
    """
    Check if Python code uses only allowed modules and functions, and applies additional safety checks.

    Args:
        code (str): The Python code to check.
        allowed_modules (List[str]): List of allowed Python modules.
        allowed_functions (List[str]): List of allowed functions.
        disallowed_builtins (Optional[Set[str]]): Set of disallowed built-in functions.
        sensitive_modules (Optional[Set[str]]): Set of sensitive modules to be blocked.
        allow_system_state_modification (bool): Whether to allow modification of system state.

    Returns:
        Tuple[bool, str]: A tuple containing a boolean (True if approved, False if rejected) and an explanation string.
    """
    allowed_modules_set = set(allowed_modules)
    allowed_functions_set = set(allowed_functions)
    disallowed_builtins = disallowed_builtins or {"eval", "exec", "compile", "__import__", "open", "input"}
    sensitive_modules = sensitive_modules or {"os", "sys", "subprocess", "socket", "requests"}

    if not code.strip():
        return False, "Empty code"

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Invalid Python syntax: {str(e)}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in allowed_modules_set:
                    return False, f"Module '{alias.name}' is not in the allowed list. Allowed modules: {', '.join(allowed_modules)}"
                if alias.name in sensitive_modules:
                    return False, f"Module '{alias.name}' is considered sensitive and not allowed."
        elif isinstance(node, ast.ImportFrom):
            if node.module not in allowed_modules_set:
                return False, f"Module '{node.module}' is not in the allowed list. Allowed modules: {', '.join(allowed_modules)}"
            if node.module in sensitive_modules:
                return False, f"Module '{node.module}' is considered sensitive and not allowed."
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in disallowed_builtins:
                    return False, f"Built-in function '{node.func.id}' is not allowed for security reasons."
                if node.func.id not in allowed_functions_set:
                    return False, f"Function '{node.func.id}' is not in the allowed list. Allowed functions: {', '.join(allowed_functions)}"

        if not allow_system_state_modification:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr.startswith("__"):
                        return False, "Modification of system state (dunder attributes) is not allowed."

    return True, "Python code is approved."

def human_supervisor_wrapper(task_state: TaskState, call: ToolCall, timeout: int = 300, use_inspect_ai: bool = False, n: int = 1, supervision_request_id: Optional[UUID] = None, client: Optional[Client] = None) -> SupervisionDecision:
    """
    Wrapper for human supervisor that handles both CLI and backend API approval.
    """
    
    if client is None: #TODO: Fix handling of the backend API endpoint, it can be configured at too many places
        supervisor_decision = prompt_user_cli_approval(task_state=task_state, tool_call=call, use_inspect_ai=use_inspect_ai, n=n)
    else:
        # Use backend API for supervision 
        assert supervision_request_id is not None
        assert client is not None
        supervisor_decision = get_human_supervision_decision_api(supervision_request_id=supervision_request_id, client=client, timeout=timeout, use_inspect_ai=use_inspect_ai)
    return supervisor_decision



def _transform_entropy_labs_approval_to_inspect_ai_approval(approval_decision: SupervisionDecision) -> Approval:
    """
    Transform an EntropyLabs SupervisionDecision to an InspectAI Approval
    """
    # Map the decision types
    decision_mapping: dict[str, Literal['approve', 'modify', 'reject', 'terminate', 'escalate']] = {
        "approve": "approve",
        "reject": "reject",
        "escalate": "escalate",
        "terminate": "terminate",
        "modify": "modify"
    }

    inspect_ai_decision = decision_mapping[approval_decision.decision]

    # Handle the 'modified' field
    modified = None
    if inspect_ai_decision == "modify" and approval_decision.modified is not None:
        # Create ToolCall instance directly from the modified data
        original_call = approval_decision.modified.original_inspect_ai_call
        # TODO: Figure this one out for N > 1
        tool_kwargs = approval_decision.modified.tool_kwargs or {}
        if original_call is not None:
            modified = ToolCall(id=original_call.id, function=original_call.function, arguments=tool_kwargs, type=original_call.type)


    return Approval(
        decision=inspect_ai_decision,
        modified=modified,
        explanation=approval_decision.explanation
    )
