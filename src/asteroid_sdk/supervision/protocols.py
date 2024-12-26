from typing import Optional, Protocol, Union
from uuid import UUID
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from anthropic.types import Message
from .config import SupervisionDecision, SupervisionContext
        
class Supervisor(Protocol):
    """
    Protocol for supervisors.
    """

    def __call__(
        self,
        message: Union[ChatCompletionMessage, Message],
        supervision_context: Optional[SupervisionContext],
        ignored_attributes: list[str] = [],
        supervision_request_id: Optional[UUID] = None,
        previous_decision: Optional[SupervisionDecision] = None,
        **kwargs
    ) -> SupervisionDecision:
        ...