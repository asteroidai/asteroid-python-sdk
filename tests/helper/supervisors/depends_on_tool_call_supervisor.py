from typing import Any

from asteroid_sdk.supervision import SupervisionDecision, SupervisionDecisionType
from asteroid_sdk.supervision.model.tool_call import ToolCall
from asteroid_sdk.supervision.supervisors import tool_supervisor_decorator


@tool_supervisor_decorator()
def depends_on_tool_call_supervisor(
        tool_call: ToolCall,
        config_kwargs: dict[str, Any],
        **kwargs
) -> SupervisionDecision:
    if tool_call.tool_params.get('allow'):
        return SupervisionDecision(decision=SupervisionDecisionType.APPROVE)
    else:
        return SupervisionDecision(decision=SupervisionDecisionType.REJECT)
