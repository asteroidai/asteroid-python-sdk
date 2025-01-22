from enum import Enum


class ChatFormat(str, Enum):
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OPENAI = "openai"

    def __str__(self) -> str:
        return str(self.value)
