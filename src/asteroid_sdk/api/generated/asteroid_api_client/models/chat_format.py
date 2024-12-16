from enum import Enum


class ChatFormat(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"

    def __str__(self) -> str:
        return str(self.value)
