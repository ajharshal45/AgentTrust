"""Prompt Injection Filter pipeline stage for AgentTrust."""

import re

from sentinel.stages.base import StageResult

# Explicit, documented list of prompt injection patterns (regexes)
# Note: This is a rule-based pattern matching heuristic, not an ML-based classifier.
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?prior",
    r"disregard\s+(all\s+)?previous",
    r"disregard\s+the\s+above",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"reveal\s+(your\s+)?system\s+configuration",
    r"dump\s+(your\s+)?instructions",
    r"system\s+override",
    r"bypass\s+security",
    r"override\s+instructions",
    r"forget\s+(all\s+)?previous",
]


def run(request_context: dict) -> StageResult:
    """Run prompt injection filtering stage on the request message text.

    Scans the actual message text content for known prompt override and instruction
    injection patterns.

    Args:
        request_context: Context dictionary containing 'message_text'.

    Returns:
        StageResult with verdict="pass" or verdict="block".
    """
    message_text = request_context.get("message_text", "")
    if not message_text:
        return StageResult(verdict="pass", reason=None, stage_name="injection_filter")

    for pattern in INJECTION_PATTERNS:
        match = re.search(pattern, message_text, re.IGNORECASE)
        if match:
            matched_str = match.group(0)
            return StageResult(
                verdict="block",
                reason=f"prompt injection detected: text matched pattern '{matched_str}'",
                stage_name="injection_filter",
            )

    return StageResult(verdict="pass", reason=None, stage_name="injection_filter")
