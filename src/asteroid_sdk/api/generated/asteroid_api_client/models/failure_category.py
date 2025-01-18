from enum import Enum


class FailureCategory(str, Enum):
    HALLUCINATION = "hallucination"
    INCORRECT_TOOL_USAGE = "incorrect_tool_usage"
    INVALID_OUTPUT_FORMAT = "invalid_output_format"
    LOGICAL_ERROR = "logical_error"
    OTHER = "other"
    PERMISSION_ERROR = "permission_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    RUNTIME_ERROR = "runtime_error"
    SAFETY_VIOLATION = "safety_violation"
    TIMEOUT = "timeout"

    def __str__(self) -> str:
        return str(self.value)
