"""AgentCard definition for Agent B.

Declares Agent B's identity, capabilities, and two skills:
  - summarize_text: summarizes input text
  - translate_text: translates input text

Uses protobuf types from a2a.types.a2a_pb2 (the v1.0 wire types that
the server routes and DefaultRequestHandler actually consume).
"""

from a2a.types.a2a_pb2 import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)

# Port Agent B runs on — referenced here and in server.py
AGENT_B_PORT = 8001
AGENT_B_HOST = "localhost"
AGENT_B_URL = f"http://{AGENT_B_HOST}:{AGENT_B_PORT}"


def create_agent_b_card() -> AgentCard:
    """Build and return the AgentCard for Agent B.

    This card is served at /.well-known/agent-card.json and also passed
    to the DefaultRequestHandler so it can validate incoming requests
    against declared capabilities.
    """
    return AgentCard(
        name="AgentB",
        description=(
            "A demo task-executing agent for AgentTrust. "
            "Supports text summarization and translation (canned responses)."
        ),
        version="1.0.0",
        # v1.0 uses supported_interfaces (list of AgentInterface) instead of
        # the v0.3 top-level "url" field. Each interface specifies a URL and
        # protocol binding.
        supported_interfaces=[
            AgentInterface(
                url=AGENT_B_URL,
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
                description="Summarizes the provided input text into a shorter form.",
                examples=[
                    "Summarize this article about climate change.",
                    "Give me a brief summary of the following text.",
                ],
            ),
            AgentSkill(
                id="translate_text",
                name="Translate Text",
                description="Translates the provided input text into another language.",
                examples=[
                    "Translate this paragraph to French.",
                    "Convert the following English text to Spanish.",
                ],
            ),
        ],
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )
