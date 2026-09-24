"""AgentCard definition for Agent A.

Agent A is the requesting client. It has its own AgentCard that it
presents when communicating with other agents. The card declares
Agent A's identity, capabilities, and skills.

Uses protobuf types from a2a.types.a2a_pb2, matching the same pattern
confirmed working in agent_b/card.py.
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
    """Build and return the LEGITIMATE AgentCard for Agent A."""
    card = AgentCard(
        name="AgentA",
        description=(
            "A demo requesting agent for AgentTrust. "
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
            AgentSkill(
                id="summarize_text",
                name="Summarize Text",
                description="Invokes summarization on a remote agent.",
            ),
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )

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
    """Build an AgentCard with a tampered/invalid signature."""
    card = AgentCard(
        name="AttackerBot",
        description="A malicious agent with a forged signature.",
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9999",
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

    card.signatures.append(
        AgentCardSignature(
            protected="eyJhbGciOiJFUzI1NiJ9",
            signature="TAMPERED_INVALID_SIGNATURE_BYTES_HERE",
        )
    )
    return card


def create_attacker_card_skill_mismatch() -> AgentCard:
    """Build a validly-structured AgentCard that requests an undeclared skill."""
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
    """Build a card with a VALID signature but wrong declared skills (ConfusedBot)."""
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
            AgentSkill(
                id="data_export",
                name="Data Export",
                description="Exports data to external systems.",
            ),
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )

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


def create_alert_card_partial_match() -> AgentCard:
    """Build persona 5: AlertBot (for Approval Demo)."""
    card = AgentCard(
        name="AlertBot",
        description=(
            "An agent requesting a partial capability match. "
            "Declares 'summarize_draft' but requests 'summarize_text'."
        ),
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9996",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
        ),
        skills=[
            AgentSkill(
                id="summarize_draft",
                name="Summarize Draft",
                description="Declares draft summarization only.",
            ),
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )

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


def create_alert_card_rejected_demo() -> AgentCard:
    """Build persona 6: RiskyBot (for Rejection Demo)."""
    card = AgentCard(
        name="RiskyBot",
        description=(
            "An agent requesting translation without full capability. "
            "Declares 'translate_draft' but requests 'translate_text'."
        ),
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9995",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(
            streaming=False,
            push_notifications=False,
        ),
        skills=[
            AgentSkill(
                id="translate_draft",
                name="Translate Draft",
                description="Declares draft translation only.",
            ),
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )

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


def create_attacker_card_prompt_injection() -> AgentCard:
    """Build persona 7: InjectionBot (Valid signature, valid declared skill, prompt injection payload)."""
    card = AgentCard(
        name="InjectionBot",
        description=(
            "An agent with valid signature and declared skill, "
            "but carrying a prompt injection attempt in message text."
        ),
        version="1.0.0",
        supported_interfaces=[
            AgentInterface(
                url="http://localhost:9994",
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
                description="Declares valid summarization skill.",
            ),
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )

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
