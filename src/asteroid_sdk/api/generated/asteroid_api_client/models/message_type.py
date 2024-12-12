from enum import Enum


class MessageType(str, Enum):
    AUDIO = "audio"
    IMAGE = "image"
    IMAGE_URL = "image_url"
    TEXT = "text"

    def __str__(self) -> str:
        return str(self.value)
