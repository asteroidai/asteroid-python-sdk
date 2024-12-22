import re
from typing import Union, List, Optional, Pattern
from openai.types.chat import ChatCompletionMessage
from anthropic.types.message import Message
from asteroid_sdk.supervision.decorators import supervisor
from asteroid_sdk.supervision.config import (
    SupervisionDecision,
    SupervisionDecisionType,
)
from asteroid_sdk.supervision.protocols import Supervisor
import copy


def create_regex_supervisor(
    patterns: List[Union[str, Pattern]],
    action: str = 'escalate',
    replacement: Optional[str] = None,
    explanation_template: str = "Message contains disallowed content: '{matched}'.",
) -> Supervisor:
    """
    Factory function to create a supervisor that checks the message content against specified regex patterns.

    Args:
        patterns (List[Union[str, Pattern]]): A list of regex patterns or specific phrases to search for in the message content.
            Examples:
               - Specific phrases: ["thanks for sharing", "I appreciate your feedback"]
               - Regex patterns: [r"\\bthanks?\\s+for\\s+sharing\\b", r"\\bI\\s+appreciate\\s+.*\\b"]
        action (str): Action to take when a pattern matches. Options are 'escalate', 'modify'.
        replacement (Optional[str]): Replacement text if action is 'modify'.
        explanation_template (str): Template for the explanation message. Use '{matched}' to include the matched text.

    Returns:
        Supervisor: A supervisor function that checks messages against the regex patterns.
    """

    # Compile patterns for efficiency
    compiled_patterns = [re.compile(p, re.IGNORECASE) if isinstance(p, str) else p for p in patterns]

    @supervisor
    def regex_supervisor(
        message: Union[ChatCompletionMessage, Message],
        **kwargs
    ) -> SupervisionDecision:
        content = getattr(message, 'content', '') or ''
        for pattern in compiled_patterns:
            match = pattern.search(content)
            if match:
                matched_text = match.group(0)
                explanation = explanation_template.format(matched=matched_text)

                if action == 'escalate':
                    return SupervisionDecision(
                        decision=SupervisionDecisionType.ESCALATE,
                        explanation=explanation,
                        modified=None
                    )

                elif action == 'modify' and replacement is not None:
                    modified_content = pattern.sub(replacement, content)
                    # Create a modified message
                    modified_message = copy.deepcopy(message)
                    modified_message.content = modified_content
                    return SupervisionDecision(
                        decision=SupervisionDecisionType.MODIFY,
                        explanation=explanation,
                        modified=modified_message
                    )

                else:
                    return SupervisionDecision(
                        decision=SupervisionDecisionType.ESCALATE,
                        explanation=f"Invalid action '{action}' or missing replacement.",
                        modified=None
                    )

        return SupervisionDecision(
            decision=SupervisionDecisionType.APPROVE,
            explanation="Message approved by regex_supervisor.",
            modified=None
        )

    regex_supervisor.__name__ = "regex_supervisor"
    regex_supervisor.supervisor_attributes = {
        "patterns": [p.pattern if isinstance(p, re.Pattern) else p for p in compiled_patterns],
        "action": action,
        "replacement": replacement,
        "explanation_template": explanation_template,
    }

    return regex_supervisor