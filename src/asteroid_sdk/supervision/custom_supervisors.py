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



def create_icontains_supervisor(
    values: List[str],
    action: str = 'escalate',
    replacement: Optional[str] = None,
    explanation_template: str = "Message contains disallowed content: '{matched}'.",
) -> Supervisor:
    """
    Factory function to create a supervisor that checks the message content for specified substrings.

    Args:
        values (List[str]): A list of substrings to search for in the message content, case insensitive.
        action (str): Action to take when a substring is found. Options are 'escalate'.
        explanation_template (str): Template for the explanation message. Use '{matched}' to include the matched text.

    Returns:
        Supervisor: A supervisor function that checks messages for substrings.
    """

    # Prepare lowercase substrings for case-insensitive comparison
    lower_values = [v.lower() for v in values]

    @supervisor
    def icontains_supervisor(
        message: Union[ChatCompletionMessage, Message],
        **kwargs
    ) -> SupervisionDecision:
        content = getattr(message, 'content', '') or ''
        content_lower = content.lower()

        for substring in lower_values:
            if substring in content_lower:
                explanation = explanation_template.format(matched=substring)
                if action == 'escalate':
                    return SupervisionDecision(
                        decision=SupervisionDecisionType.ESCALATE,
                        explanation=explanation,
                        modified=None
                    )
                elif action == 'modify' and replacement is not None:
                    modified_content = content.replace(substring, replacement)
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
            explanation="Message approved by icontains_supervisor.",
            modified=None
        )

    icontains_supervisor.__name__ = "icontains_supervisor"
    icontains_supervisor.supervisor_attributes = {
        "values": values,
        "action": action,
        "replacement": replacement,
        "explanation_template": explanation_template,
    }

    return icontains_supervisor


def create_icontains_all_supervisor(
    values: List[str],
    action: str = 'escalate',
    replacement: Optional[str] = None,
    explanation_template: str = "Message contains all disallowed contents: {matched}.",
) -> Supervisor:
    """
    Factory function to create a supervisor that checks if the message content contains all specified substrings.

    Args:
        values (List[str]): A list of substrings to search for in the message content, case insensitive.
        action (str): Action to take when all substrings are found. Options are 'escalate', 'modify'.
        replacement (Optional[str]): Replacement text if action is 'modify'.
        explanation_template (str): Template for the explanation message. Use '{matched}' to include the matched substrings.

    Returns:
        Supervisor: A supervisor function that checks messages for the presence of all specified substrings.
    """

    # Prepare lowercase substrings for case-insensitive comparison
    lower_values = [v.lower() for v in values]

    @supervisor
    def icontains_all_supervisor(
        message: Union[ChatCompletionMessage, Message],
        **kwargs
    ) -> SupervisionDecision:
        content = getattr(message, 'content', '') or ''
        content_lower = content.lower()

        matched_substrings = [v for v in lower_values if v in content_lower]

        if len(matched_substrings) == len(lower_values):
            explanation = explanation_template.format(matched=", ".join(matched_substrings))
            if action == 'escalate':
                return SupervisionDecision(
                    decision=SupervisionDecisionType.ESCALATE,
                    explanation=explanation,
                    modified=None
                )
            elif action == 'modify' and replacement is not None:
                modified_content = content
                for substring in matched_substrings:
                    modified_content = modified_content.replace(substring, replacement)
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
            explanation="Message approved by icontains_all_supervisor.",
            modified=None
        )

    icontains_all_supervisor.__name__ = "icontains_all_supervisor"
    icontains_all_supervisor.supervisor_attributes = {
        "values": values,
        "action": action,
        "replacement": replacement,
        "explanation_template": explanation_template,
    }

    return icontains_all_supervisor


def create_starts_with_supervisor(
    prefix: str,
    action: str = 'escalate',
    inverted: bool = False,
    replacement: Optional[str] = None,
    explanation_template: str = "Message {condition}: '{matched}'.",
) -> Supervisor:
    """
    Factory function to create a supervisor that checks if the message content starts with a specified prefix.

    Args:
        prefix (str): The prefix string to check at the start of the message content, case insensitive.
        action (str): Action to take when the condition is met. Options are 'escalate', 'modify'.
        inverted (bool): If True, the supervisor escalates when the message does NOT start with the prefix.
        replacement (Optional[str]): Replacement text if action is 'modify'.
        explanation_template (str): Template for the explanation message.
            Use '{condition}' to insert 'starts with' or 'does not start with',
            and '{matched}' to include the relevant text.

    Returns:
        Supervisor: A supervisor function that checks message starting condition.
    """

    # Prepare the prefix for case-insensitive comparison
    prefix_lower = prefix.lower()

    @supervisor
    def starts_with_supervisor(
        message: Union[ChatCompletionMessage, Message],
        **kwargs
    ) -> SupervisionDecision:
        content = getattr(message, 'content', '') or ''
        content_lower = content.lower()

        starts_with = content_lower.startswith(prefix_lower)

        # Determine if the condition is met based on inversion
        condition_met = starts_with if not inverted else not starts_with

        if condition_met:
            matched_text = prefix if not inverted else content.split()[0] if content.split() else ""
            condition_text = "starts with" if not inverted else "does not start with"
            explanation = explanation_template.format(condition=condition_text, matched=matched_text)

            if action == 'escalate':
                return SupervisionDecision(
                    decision=SupervisionDecisionType.ESCALATE,
                    explanation=explanation,
                    modified=None
                )
            elif action == 'modify' and replacement is not None:
                if not inverted:
                    # Remove the prefix
                    modified_content = content[len(prefix):].lstrip()
                else:
                    # Prepend the replacement
                    modified_content = replacement + content
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
            explanation="Message approved by starts_with_supervisor.",
            modified=None
        )

    starts_with_supervisor.__name__ = "starts_with_supervisor"
    starts_with_supervisor.supervisor_attributes = {
        "prefix": prefix,
        "action": action,
        "inverted": inverted,
        "replacement": replacement,
        "explanation_template": explanation_template,
    }

    return starts_with_supervisor


