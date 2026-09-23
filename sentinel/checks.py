"""A2ASentinel security checks.

Two checks, run in order, short-circuiting on first failure:
  1. Signature check — verify the caller's AgentCard JWS signature
  2. Capability-match check — verify the requested skill is declared
     in the caller's AgentCard

Each check function returns (passed: bool, reason: str).
"""

from sentinel.keys import (
    card_dict_to_signing_payload,
    verify_signature,
)

# Same keyword lists as agent_b/executor.py — used to infer which
# skill the caller is requesting from the message text.
SUMMARIZE_KEYWORDS = ["summarize", "summary", "summarise", "brief"]
TRANSLATE_KEYWORDS = ["translate", "translation", "convert", "french", "spanish"]


def infer_requested_skill(message_text: str) -> str:
    """Infer which skill is being requested from the message text.

    Uses the same keyword matching as Agent B's executor, so the
    inferred skill matches what Agent B would actually execute.

    Returns a skill ID string, or "unknown" if no match.
    """
    text_lower = message_text.lower()
    if any(kw in text_lower for kw in SUMMARIZE_KEYWORDS):
        return "summarize_text"
    if any(kw in text_lower for kw in TRANSLATE_KEYWORDS):
        return "translate_text"
    return "unknown"


def check_signature(caller_card: dict) -> tuple[bool, str]:
    """Check 1: Verify the caller's AgentCard has a valid JWS signature.

    Validates that:
      - The 'signatures' field exists and is non-empty
      - At least one signature has both 'protected' and 'signature' fields
      - The signature cryptographically verifies against the card payload
        using our demo HMAC-SHA256 key

    Args:
        caller_card: The caller's AgentCard as a dict (from JSON).

    Returns:
        (True, "") if the signature is valid.
        (False, reason) if validation fails.
    """
    signatures = caller_card.get("signatures")
    if not signatures or not isinstance(signatures, list):
        return False, "no signatures field in caller's AgentCard"

    # Check each signature — we only need ONE valid one
    payload_b64 = card_dict_to_signing_payload(caller_card)

    for sig_entry in signatures:
        protected = sig_entry.get("protected", "")
        signature = sig_entry.get("signature", "")

        if not protected or not signature:
            continue  # skip malformed entries, check next

        if verify_signature(protected, payload_b64, signature):
            return True, ""

    return False, "all signatures failed cryptographic verification"


def check_capability_match(
    caller_card: dict, requested_skill: str
) -> tuple[bool, str]:
    """Check 2: Verify the requested skill is declared in the caller's card.

    The principle: an agent should only request tasks that correspond
    to skills it has declared in its own AgentCard. If AgentA declares
    'summarize_text' as its skill, it's authorized to request
    summarization from Agent B. If it only declares 'web_search' but
    requests 'translate_text', that's a capability mismatch.

    Args:
        caller_card: The caller's AgentCard as a dict.
        requested_skill: The skill ID inferred from the request text.

    Returns:
        (True, "") if the requested skill matches a declared skill.
        (False, reason) if there's a mismatch.
    """
    skills = caller_card.get("skills", [])
    declared_skill_ids = [s.get("id", "") for s in skills if isinstance(s, dict)]

    if not declared_skill_ids:
        return False, "caller's AgentCard declares no skills"

    if requested_skill == "unknown":
        # Can't determine what's being requested — allow through
        # (Agent B will handle unrecognized requests itself)
        return True, ""

    if requested_skill in declared_skill_ids:
        return True, ""

    return (
        False,
        f"requested skill '{requested_skill}' not in caller's declared "
        f"skills {declared_skill_ids}",
    )
