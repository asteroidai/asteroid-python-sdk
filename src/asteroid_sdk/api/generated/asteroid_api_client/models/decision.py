from enum import Enum


class Decision(str, Enum):
    APPROVE = "approve"
    ESCALATE = "escalate"
    MODIFY = "modify"
    REJECT = "reject"
    TERMINATE = "terminate"

    def __str__(self) -> str:
        return str(self.value)
