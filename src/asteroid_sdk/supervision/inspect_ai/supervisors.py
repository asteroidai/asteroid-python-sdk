import logging
from typing import List, Dict, Optional, Set, Callable
from inspect_ai.approval import Approval, Approver, approver
from inspect_ai.solver import TaskState
from inspect_ai.tool import ToolCall, ToolCallView
from inspect_ai._util.registry import registry_lookup
from entropy_labs.sentinel_api_client.sentinel_api_client.client import Client
from uuid import UUID
from entropy_labs.supervision.config import supervision_config
from entropy_labs.supervision.config import SupervisionDecision, SupervisionDecisionType
from functools import wraps
from entropy_labs.supervision.inspect_ai.utils import generate_tool_call_suggestions
from entropy_labs.sentinel_api_client.sentinel_api_client.models.tool_request import (
    ToolRequest,
)
from entropy_labs.sentinel_api_client.sentinel_api_client.models.status import Status
from entropy_labs.supervision.inspect_ai.utils import tool_jsonable
from entropy_labs.supervision.config import SupervisionContext, convert_message

def prepare_approval(decision: SupervisionDecision) -> Approval:
    from entropy_labs.supervision.common import _transform_entropy_labs_approval_to_inspect_ai_approval
    return _transform_entropy_labs_approval_to_inspect_ai_approval(decision)

def get_tool_info(call_function: str, supervision_context: SupervisionContext) -> tuple[UUID, List[str]]:
    entry = supervision_context.get_supervised_function_entry(call_function)
    if entry:
        tool_id = entry['tool_id']
        ignored_attributes = entry['ignored_attributes']
        return tool_id, ignored_attributes
    else:
        raise Exception(f"Tool ID for function {call_function} not found in the registry.")

# Decorator for common Entropy Sentinel API interactions
def with_entropy_supervision(supervisor_name_param: Optional[str] = None, n: Optional[int] = None):
    """
    Decorator for common Entropy Sentinel API interactions.
    
    Args:
        supervisor_name_param: Name of the supervisor to use. If not provided, the name of the function will be used.
        n: Number of tool call suggestions to generate for human approval.
    """
    def decorator(approve_func: Callable):
        @wraps(approve_func)
        async def wrapper(
            message: str,
            call: ToolCall,
            view: ToolCallView,
            state: TaskState,
            **kwargs
        ) -> Approval:
            from entropy_labs.api.sentinel_api_client_helper import SupervisorType
            from entropy_labs.api.sentinel_api_client_helper import send_supervision_request
            from entropy_labs.sentinel_api_client.sentinel_api_client.models.arguments import Arguments
            from entropy_labs.api.sentinel_api_client_helper import (
                create_tool_request_group,
                get_supervisor_chains_for_tool,
                send_supervision_request,
                send_supervision_result,
                get_tool_request_groups,
                get_tool_request_group_status,
                get_tool_request_groups,
                get_tool_request_group_status,
                SupervisorType,
            )

            run_name = str(state.sample_id) # For Inspect AI, this is the run_name
            run = supervision_config.get_run_by_name(run_name)
            if run is None:
                raise Exception(f"Run with name {run_name} not found")
            supervision_context = run.supervision_context
            
            supervision_context.inspect_ai_state = state
            supervision_config.update_supervision_context_by_run_name(run.run_name, supervision_context)
            
            # Add messages from task_state to context
            client = supervision_config.client  # Get the Sentinel API client

            # Retrieve the tool_id from the registry
            tool_id, ignored_attributes = get_tool_info(call.function, supervision_context)
            tool_requests = [ToolRequest(tool_id=tool_id, 
                                         message=supervision_context.get_api_messages()[-1],
                                         arguments=Arguments.from_dict(call.arguments),
                                         task_state=supervision_context.to_task_state())]
            
            supervisor_attributes = getattr(approve_func, 'supervisor_attributes', {})
            if 'n' in supervisor_attributes:
                n = supervisor_attributes['n']
                if n > 1:
                    # Generate n-1 tool calls
                    last_messages, tool_options = await generate_tool_call_suggestions(state, n - 1 , call)
                    last_messages = [state.messages[-1]] + last_messages
                    tool_options = [tool_jsonable(call)] + tool_options
                    for i in range(n-1):
                        tool_id, ignored_attributes = get_tool_info(tool_options[i]['function'], supervision_context)
                        updated_task_state = supervision_context.to_task_state()
                        updated_task_state.messages[-1] = convert_message(last_messages[i])
                        tool_requests.append(ToolRequest(tool_id=tool_id, 
                                                        message=convert_message(last_messages[i]),
                                                        arguments=Arguments.from_dict(tool_options[i]['arguments']),
                                                        task_state=updated_task_state))
                        # TODO: We need to update the task state messages later in case the supervisor chooses different tool

            # Create ToolRequestGroup, we need to check first if the ToolRequestGroup for this run_id and tool_id exists
            tool_request_groups = get_tool_request_groups(run.run_id, tool_id, client)
            
            tool_request_group = None
            if tool_request_groups:
                # find tool request group that is pending or assigned
                for _tool_request_group in tool_request_groups:
                    tool_request_status = get_tool_request_group_status(_tool_request_group.id, client)
                    if tool_request_status in [Status.PENDING, Status.ASSIGNED]:
                        tool_request_group = _tool_request_group
                        break
            if not tool_request_group: # or (tool_request_status in [Status.COMPLETED, Status.FAILED, Status.TIMEOUT]):
                tool_request_group = create_tool_request_group(tool_id, tool_requests, client)
                if not tool_request_group:
                    raise Exception(f"Failed to create Tool Request Group")

            tool_requests = tool_request_group.tool_requests
            
            # Get the supervisor chains for the tool
            supervisor_chains = get_supervisor_chains_for_tool(tool_id, client)
            if not supervisor_chains:
                print(f"No supervisors found for tool ID {tool_id}.")
                return prepare_approval(SupervisionDecision(
                    decision=SupervisionDecisionType.APPROVE,
                    explanation="No supervisors configured. Approval granted."
                ))

            # Find the supervisor by name
            supervisor_name = supervisor_name_param or approve_func.__name__
            supervisor_id = None
            supervisor_chain_id = None
            position_in_chain = None
            for chain in supervisor_chains:
                for idx, supervisor in enumerate(chain.supervisors):
                    if supervisor.name == supervisor_name:
                        supervisor_id = supervisor.id
                        supervisor_chain_id = chain.chain_id
                        position_in_chain = idx
                        break
                if supervisor_id:
                    break

            if not supervisor_id or not supervisor_chain_id:
                raise Exception(f"No supervisor found with name '{supervisor_name}' for tool ID {tool_id}")
            if position_in_chain is None:
                raise Exception(f"Position in chain not found for supervisor {supervisor_name} in chain {supervisor_chain_id}")
                
            # Send supervision request
            supervision_request_id = send_supervision_request(
                supervisor_id=supervisor_id,
                supervisor_chain_id=supervisor_chain_id,
                request_group_id=tool_request_group.id,
                position_in_chain=position_in_chain
            )

            # Call the specific approval logic
            decision = await approve_func(
                message, call, view, state,
                supervision_context=supervision_context,
                supervision_request_id=supervision_request_id,
                client=client,
                **kwargs
            )
            print(f"Decision: {decision.decision} for supervision request ID: {supervision_request_id}")

            if supervisor.type != SupervisorType.HUMAN_SUPERVISOR:
                # Send the decision to the API
                send_supervision_result(
                    supervision_request_id=supervision_request_id,
                    request_group_id=tool_request_group.id,
                    tool_id=tool_id,
                    supervisor_id=supervisor_id,
                    decision=decision,
                    client=client,
                    tool_args=[],  # TODO: If modified, send modified args and kwargs
                    tool_kwargs=call.arguments,
                    tool_request=tool_requests[0] #TODO: Update for N > 1
                )
            # Handle modify decision
            if decision.decision == SupervisionDecisionType.MODIFY:
                decision.modified.original_inspect_ai_call = call
                
            print(f"Returning approval: {decision.decision}") 
            return prepare_approval(decision)

        # Set the __name__ of the wrapper function to the supervisor name or the outer function's name
        wrapper.__name__ = supervisor_name_param or approve_func.__name__
        return wrapper
    return decorator

# Updated Approvers

@approver
def bash_approver(
    allowed_commands: List[str],
    allow_sudo: bool = False,
    command_specific_rules: Optional[Dict[str, List[str]]] = None,
) -> Approver:
    async def approve(
        message: str,
        call: ToolCall,
        view: ToolCallView,
        state: Optional[TaskState] = None,
        supervision_context=None,
        supervision_request_id: Optional[UUID] = None,
        client: Optional[Client] = None,
    ) -> SupervisionDecision:
        """
        Bash approver for Inspect AI.
        """
        from entropy_labs.supervision.common import check_bash_command
        command = str(next(iter(call.arguments.values()))).strip()
        is_approved, explanation = check_bash_command(
            command, allowed_commands, allow_sudo, command_specific_rules
        )

        if is_approved:
            decision = SupervisionDecision(
                decision=SupervisionDecisionType.APPROVE, explanation=explanation
            )
        else:
            decision = SupervisionDecision(
                decision=SupervisionDecisionType.ESCALATE, explanation=explanation
            )
        return decision

    # Set attributes before applying the decorator
    approve.__name__ = "bash_approver"
    approve.supervisor_attributes = {
        "allowed_commands": allowed_commands,
        "allow_sudo": allow_sudo,
        "command_specific_rules": command_specific_rules
    }

    # Apply decorator after setting attributes
    decorated_approve = with_entropy_supervision(supervisor_name_param="bash_approver")(approve)
    return decorated_approve

@approver
def python_approver(
    allowed_modules: List[str],
    allowed_functions: List[str],
    disallowed_builtins: Optional[Set[str]] = None,
    sensitive_modules: Optional[Set[str]] = None,
    allow_system_state_modification: bool = False,
) -> Approver:
    async def approve(
        message: str,
        call: ToolCall,
        view: ToolCallView,
        state: Optional[TaskState] = None,
        supervision_context=None,
        supervision_request_id: Optional[UUID] = None,
        client: Optional[Client] = None,
    ) -> SupervisionDecision:
        """
        Python approver for Inspect AI.
        """
        from entropy_labs.supervision.common import check_python_code
        code = str(next(iter(call.arguments.values()))).strip()
        is_approved, explanation = check_python_code(
            code,
            allowed_modules,
            allowed_functions,
            disallowed_builtins,
            sensitive_modules,
            allow_system_state_modification
        )

        if is_approved:
            decision = SupervisionDecision(
                decision=SupervisionDecisionType.APPROVE, explanation=explanation
            )
        else:
            decision = SupervisionDecision(
                decision=SupervisionDecisionType.ESCALATE, explanation=explanation
            )
        return decision

    # Set attributes before applying the decorator
    approve.__name__ = "python_approver"
    approve.supervisor_attributes = {
        "allowed_modules": allowed_modules,
        "allowed_functions": allowed_functions,
        "disallowed_builtins": disallowed_builtins,
        "sensitive_modules": sensitive_modules,
        "allow_system_state_modification": allow_system_state_modification
    }

    # Apply decorator after setting attributes
    decorated_approve = with_entropy_supervision(supervisor_name_param="python_approver")(approve)
    return decorated_approve

@approver
def human_approver(
    agent_id: str,
    approval_api_endpoint: Optional[str] = None,
    n: int = 3,
    timeout: int = 300
) -> Approver:
    async def approve(
        message: str,
        call: ToolCall,
        view: ToolCallView,
        state: Optional[TaskState] = None,
        supervision_context=None,
        supervision_request_id: Optional[UUID] = None,
        client: Optional[Client] = None,
    ) -> SupervisionDecision:
        """
        Human approver for Inspect AI.
        """
        from entropy_labs.supervision.common import human_supervisor_wrapper
        if state is None:
            return SupervisionDecision(
                decision=SupervisionDecisionType.ESCALATE,
                explanation="TaskState is required for this approver."
            )
            
        # Handle n > 1 tool calls, generate suggestions
        # if n > 1:
        #     # generate n-1 tool calls
        #     last_messages, tool_options = await generate_tool_call_suggestions(state, n, call)
            # last_messages = [state.messages[-1]] + last_messages
            # tool_options = [tool_jsonable(call)] + tool_options
            # TODO: Implement n > 1 logic here for human supervisor

        approval_decision = human_supervisor_wrapper(
            task_state=state,
            call=call,
            timeout=timeout,
            use_inspect_ai=True,
            n=n,
            supervision_request_id=supervision_request_id,
            client=client
        )
        
        return approval_decision

    # Set attributes before applying the decorator
    approve.__name__ = "human_approver"
    approve.supervisor_attributes = {"timeout": timeout, "n": n}

    # Apply decorator after setting attributes
    decorated_approve = with_entropy_supervision(supervisor_name_param="human_approver", n=n)(approve)
    return decorated_approve

@approver
def llm_approver(
    instructions: str,
    openai_model: str,
    system_prompt: Optional[str] = None,
    include_context: bool = False,
    agent_id: Optional[str] = None
) -> Approver:
    async def approve(
        message: str,
        call: ToolCall,
        view: ToolCallView,
        state: Optional[TaskState] = None,
        supervision_context=None,
        supervision_request_id: Optional[UUID] = None,
        client: Optional[Client] = None,
    ) -> SupervisionDecision:
        """
        LLM approver for Inspect AI.
        """
        from entropy_labs.supervision.supervisors import llm_supervisor
        if state is None:
            return SupervisionDecision(
                decision=SupervisionDecisionType.ESCALATE,
                explanation="TaskState is required for this approver."
            )

        llm_supervisor_func = llm_supervisor(
            instructions=instructions,
            openai_model=openai_model,
            system_prompt=system_prompt,
            include_context=include_context
        )

        function_name = call.function
        func = registry_lookup('tool', function_name)
        approval_decision = llm_supervisor_func( # TODO: Support for n > 1
            func=func,
            supervision_context=supervision_context,
            ignored_attributes=[],
            tool_args=[],
            tool_kwargs=call.arguments,
            decision=None,
            supervision_request_id=supervision_request_id
        )
        return approval_decision

    # Set attributes before applying the decorator
    approve.__name__ = "llm_approver"
    approve.supervisor_attributes = {
        "instructions": instructions,
        "openai_model": openai_model,
        "system_prompt": system_prompt,
        "include_context": include_context
    }

    # Apply decorator after setting attributes
    decorated_approve = with_entropy_supervision(supervisor_name_param="llm_approver")(approve)
    return decorated_approve
