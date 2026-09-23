"""AgentCard definition for Agent A.

Agent A is the requesting client. It has its own AgentCard that it
presents when communicating with other agents. The card declares
Agent A's identity, capabilities, and skills.

Uses protobuf types from a2a.types.a2a_pb2, matching the same pattern
confirmed working in agent_b/card.py.

CHANGES FOR A2ASentinel STEP:
  - Added 'summarize_text' to legitimate card's declared skills.
    Reason: Agent A requests summarization from Agent B. The capability-
    match check verifies the requested skill (inferred from message text
    as 'summarize_text') is in the CALLER's declared skills. Without
    this, even the legitimate persona would be blocked.

  - Added a real HMAC-SHA256 signature to the legitimate card via
    sentinel.keys.sign_card_dict(). Reason: the signature check needs
    something cryptographically valid to verify against. A missing or
    empty signatures field is always rejected by the sentinel.
"""

from google.protobuf.json_format import MessageToDict

from a2a.types.a2a_pb2 import (
    AgentCapabilities,
    AgentCard,
    AgentCardSignature,
    AgentInterface,
    AgentSkill,
)
from sentinel.keys import (
    card_dict_to_signing_payload,
    compute_signature,
    make_protected_header,
)


def create_agent_a_card() -> AgentCard:
    """Build and return the LEGITIMATE AgentCard for Agent A.

    Includes a real HMAC-SHA256 JWS signature (via sentinel.keys) so
    that A2ASentinel's signature check passes. Also declares both
    'request_summary' and 'summarize_text' so the capability-match
    check passes when requesting summarization from Agent B.
    """
    # Build the card first (without signature)
    card = AgentCard(
        name="AgentA",
        description=(
            "A demo requesting agent for A2ASentinel. "
            "Requests text summarization from other agents."
        ),
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:8000",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
        ),
        skills=[
            AgentSkill(
                id="request_summary",
                name="Request Summary",
                description="Requests another agent to summarize text.",
                examples=["Ask Agent B to summarize this document."],
            ),
            # Added for sentinel capability-match: Agent A sends summarization
            # requests, so it must declare this skill in its own card.
            AgentSkill(
                id="summarize_text",
                name="Summarize Text",
                description="Invokes summarization on a remote agent.",
            ),
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )

    # Compute a real HMAC-SHA256 signature over the card's canonical form.
    # sentinel.keys.sign_card_dict() serializes the card (minus the
    # signatures field) to canonical JSON and signs with DEMO_SECRET_KEY.
    card_dict = MessageToDict(card)
    protected = make_protected_header()
    payload_b64 = card_dict_to_signing_payload(card_dict)
    signature_value = compute_signature(protected, payload_b64)

    card.signatures.append(
        AgentCardSignature(
            protected=protected,
            signature=signature_value,
        )
    )
    return card


def create_attacker_card_invalid_signature() -> AgentCard:
    """Build an AgentCard with a tampered/invalid signature.

    This simulates an attacker who presents a card with a fake JWS
    signature. When A2ASentinel checks signatures, this should be
    BLOCKED.

    Without A2ASentinel in place, Agent B will accept this because
    Agent B itself doesn't verify caller cards.
    """
    card = AgentCard(
        name="AttackerBot",
        description="A malicious agent with a forged signature.",
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9999",  # fake address
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
        ),
        skills=[
            AgentSkill(
                id="summarize_text",
                name="Summarize Text",
                description="Claims to do summarization (but is actually malicious).",
            ),
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )
    # Inject a fake JWS signature — this is deliberately invalid/forged.
    # In A2A v1.0, the signatures field holds AgentCardSignature objects
    # with 'protected' (base64url-encoded JWS header) and 'signature'
    # (base64url-encoded signature bytes). We put garbage here.
    from a2a.types.a2a_pb2 import AgentCardSignature

    card.signatures.append(
        AgentCardSignature(
            protected="eyJhbGciOiJFUzI1NiJ9",  # {"alg":"ES256"} — looks real
            signature="TAMPERED_INVALID_SIGNATURE_BYTES_HERE",  # obviously forged
        )
    )
    return card


def create_attacker_card_skill_mismatch() -> AgentCard:
    """Build a validly-structured AgentCard that requests an undeclared skill.

    This simulates an attacker whose card declares skill X but who
    sends a request for skill Y (one that Agent B has but the attacker
    hasn't declared). When A2ASentinel checks capability-match, this
    should be BLOCKED because the requested task doesn't match the
    caller's declared skills.

    Without A2ASentinel, Agent B will happily execute the request
    because it only checks its OWN skills, not the caller's.
    """
    return AgentCard(
        name="SneakyBot",
        description="An agent that tries to access skills it hasn't declared.",
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9998",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
        ),
        skills=[
            # Declares only "web_search" — does NOT declare "summarize_text"
            # or "translate_text" or "delete_database"
            AgentSkill(
                id="web_search",
                name="Web Search",
                description="Only knows how to search the web.",
            ),
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )


def create_attacker_card_capability_mismatch() -> AgentCard:
    """Build a card with a VALID signature but wrong declared skills.

    This is the fourth persona: ConfusedBot. It has a properly computed
    HMAC-SHA256 signature (passes check 1), but its declared skills list
    contains only 'data_export' — it then sends a request that triggers
    Agent B's 'translate_text' skill, which it has NOT declared.

    This gives a live end-to-end demonstration that check 2
    (capability-match) fires independently from check 1 (signature).
    The sentinel output will read:
      BLOCKED (reason: capability mismatch: ...)
    NOT the signature reason.
    """
    card = AgentCard(
        name="ConfusedBot",
        description=(
            "An agent with a valid signature but mismatched capability claims. "
            "Declares only 'data_export' but requests translation."
        ),
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9997",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
        ),
        skills=[
            # Declares 'data_export' — completely unrelated to what it requests
            AgentSkill(
                id="data_export",
                name="Data Export",
                description="Exports data to external systems.",
            ),
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )

    # Compute a REAL valid HMAC-SHA256 signature — this card WILL pass
    # check 1 (signature), but will be blocked at check 2 (capability-match)
    # because 'translate_text' is not in its declared skills ['data_export'].
    card_dict = MessageToDict(card)
    protected = make_protected_header()
    payload_b64 = card_dict_to_signing_payload(card_dict)
    signature_value = compute_signature(protected, payload_b64)

    card.signatures.append(
        AgentCardSignature(
            protected=protected,
            signature=signature_value,
        )
    )
    return card
