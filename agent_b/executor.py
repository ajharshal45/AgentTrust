"""AgentExecutor implementation for Agent B.

This is a demo executor that returns canned responses confirming which
task type it executed. No real AI/NLP logic — the point of this project
is the trust/security layer (AgentTrust), not agent intelligence.

SDK contract (from agent_executor.py source):
  - AgentExecutor has two abstract methods: execute() and cancel()
  - execute() receives a RequestContext and an EventQueue
  - For an immediate (non-streaming) response: enqueue a single Message
    object — the framework treats a Message as a final event and closes
    the response.
  - Event type is: Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
    (all protobuf types from a2a.types.a2a_pb2)
"""

import logging

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types.a2a_pb2 import Message, Part, Role

logger = logging.getLogger(__name__)

# Keywords used to match which skill the user is asking for.
# Simple substring matching — this is a demo, not production routing.
SUMMARIZE_KEYWORDS = ["summarize", "summary", "summarise", "brief"]
TRANSLATE_KEYWORDS = ["translate", "translation", "convert", "french", "spanish"]


class AgentBExecutor(AgentExecutor):
    """Canned-response executor for Agent B.

    Determines which skill was requested (summarize or translate) by
    simple keyword matching on the user's input text, then returns a
    confirmation message. If no skill matches, returns a generic
    acknowledgment.
    """

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Process an incoming request and enqueue a canned response.

        Uses context.get_user_input() to extract the text from the
        user's message parts (confirmed to exist on RequestContext at
        context.py line 82).
        """
        user_input = context.get_user_input()
        logger.info("Agent B received request: %s", user_input[:100])

        # Determine which skill was requested via simple keyword matching
        input_lower = user_input.lower()
        if any(kw in input_lower for kw in SUMMARIZE_KEYWORDS):
            skill_name = "summarize_text"
            response_text = f"[Agent B] Executed summarize_text on: {user_input}"
        elif any(kw in input_lower for kw in TRANSLATE_KEYWORDS):
            skill_name = "translate_text"
            response_text = f"[Agent B] Executed translate_text on: {user_input}"
        else:
            skill_name = "unknown"
            response_text = (
                f"[Agent B] Received request but could not match a declared "
                f"skill. Input was: {user_input}"
            )

        logger.info("Agent B matched skill: %s", skill_name)

        # Enqueue a single Message as the response.
        # Per the SDK docstring: "Immediate response: Enqueue a SINGLE
        # Message object" — the framework treats this as a final event.
        response_message = Message(
            role=Role.ROLE_AGENT,
            parts=[Part(text=response_text)],
        )
        await event_queue.enqueue_event(response_message)

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Handle a cancellation request.

        For this demo, there's nothing to cancel (responses are
        immediate), so this is a no-op. A real implementation would
        signal the running task to stop and publish a
        TaskStatusUpdateEvent with TASK_STATE_CANCELED.
        """
        logger.info("Agent B cancel requested (no-op for demo)")
