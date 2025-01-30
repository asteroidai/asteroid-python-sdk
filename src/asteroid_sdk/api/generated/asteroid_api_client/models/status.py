from enum import Enum


class Status(str, Enum):
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    PENDING = "pending"
    TIMEOUT = "timeout"

    def __str__(self) -> str:
        return str(self.value)
