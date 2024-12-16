from enum import Enum


class AsteroidMessageRole(str, Enum):
    ASSISTANT = "assistant"
    ASTEROID = "asteroid"
    FUNCTION = "function"
    SYSTEM = "system"
    TOOL = "tool"
    USER = "user"

    def __str__(self) -> str:
        return str(self.value)
