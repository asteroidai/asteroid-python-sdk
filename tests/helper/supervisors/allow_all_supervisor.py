from asteroid_sdk.supervision import SupervisionDecision, SupervisionDecisionType
from asteroid_sdk.supervision.decorators import supervisor
from asteroid_sdk.supervision.helpers.model_provider_helper import AvailableProviderMessageTypes


@supervisor
def allow_all_supervisor(
        message: AvailableProviderMessageTypes,
        **kwargs
) -> SupervisionDecision:
    return SupervisionDecision(decision=SupervisionDecisionType.APPROVE)
