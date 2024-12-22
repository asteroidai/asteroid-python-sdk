from typing import Any

from asteroid_sdk.supervision import SupervisionDecision, SupervisionDecisionType
from asteroid_sdk.supervision.model.tool_call import ToolCall
from asteroid_sdk.supervision.base_supervisors import tool_supervisor_decorator


@tool_supervisor_decorator(strategy="allow_all") #TODO: Rethink the decorator design, it can't be configured with parameters in this way
def allow_all_supervisor(
        tool_call: ToolCall,
        config_kwargs: dict[str, Any],
        **kwargs
) -> SupervisionDecision:
    # Supervisor implementation using configuration parameters
    print(f"Supervisor received tool_call: {tool_call}")
    strategy = config_kwargs.get("strategy","")
    if strategy == "allow_all":
        return SupervisionDecision(decision=SupervisionDecisionType.APPROVE)
    else:
        return SupervisionDecision(decision=SupervisionDecisionType.REJECT)
