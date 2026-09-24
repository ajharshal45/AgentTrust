"""Agent A client — sends requests to Agent B.

Uses raw httpx POST requests (not the SDK's ClientFactory) because:

  SDK DISCREPANCY: Agent B's AgentCard sets `protocol_version="1.0"` on
  its AgentInterface but omits `protocol_binding`. The SDK's
  ClientFactory.create() at line 337-344 iterates card.supported_interfaces
  and checks `supported_interface.protocol_binding in client_set`. With
  an empty protocol_binding, this never matches, and create() raises
  ValueError("no compatible transports found.").

  Fixing this would require modifying Agent B's card to include
  protocol_binding="JSONRPC", but the task says "Do not modify agent_b/".
  Since the attacker personas also need raw request control (for forged
  payloads), using httpx directly is the cleanest consistent approach.

  We still use the SDK's protobuf types (Message, Part, Role,
  SendMessageRequest) for constructing payloads, keeping type consistency
  with Agent B.

Confirmed working patterns (from agent_b's verified test_agent_b.py):
  - JSON-RPC method: "SendMessage" (PascalCase, v1.0)
  - Role: "ROLE_USER" / "ROLE_AGENT" (protobuf enum string names)
  - Part: {"text": "..."} (direct field, no TextPart)
  - Response: result.message.parts[].text (SendMessageResponse wrapper)
  - Header: A2A-Version: 1.0
"""

import json
import uuid

import httpx

from a2a.types.a2a_pb2 import AgentCard

# Agent B's endpoint (same constants as agent_b/card.py)
AGENT_B_URL = "http://localhost:8001"
AGENT_B_JSONRPC_URL = f"{AGENT_B_URL}/"


def send_request(
    agent_card: AgentCard,
    user_text: str,
    target_url: str = AGENT_B_JSONRPC_URL,
) -> dict:
    """Send a SendMessage JSON-RPC request to the target agent.

    Args:
        agent_card: The calling agent's AgentCard (for identification).
                    In a real A2A flow, this would be presented to the
                    target agent or interceptor for verification.
        user_text: The text content to send in the message.
        target_url: The JSON-RPC endpoint URL of the target agent.

    Returns:
        The parsed JSON response dict from the target agent.
    """
    # Build the JSON-RPC 2.0 envelope
    request_payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "SendMessage",
        "params": {
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": user_text}],
                "messageId": str(uuid.uuid4()),
            },
            # Attach the caller's agent card as metadata so that an
            # interceptor (AgentTrust) can inspect it. The A2A protocol
            # doesn't have a built-in "attach caller card" field in
            # SendMessageRequest, so we use the metadata extension point.
            "metadata": {
                "caller_agent_card": _card_to_dict(agent_card),
            },
        },
    }

    headers = {
        "Content-Type": "application/json",
        "A2A-Version": "1.0",
    }

    resp = httpx.post(
        target_url,
        json=request_payload,
        headers=headers,
        timeout=30.0,
    )
    return resp.json()


def extract_response_text(result: dict) -> str | None:
    """Extract text from a SendMessageResponse result structure.

    Handles both Message and Task response shapes (same logic as
    test_agent_b.py, confirmed working).
    """
    if "result" not in result:
        return None

    response_result = result["result"]

    # SendMessageResponse with Message: {"message": {"parts": [...]}}
    msg = response_result.get("message", {})
    if isinstance(msg, dict):
        for part in msg.get("parts", []):
            if "text" in part:
                return part["text"]

    # SendMessageResponse with Task: {"task": {"status": {"message": ...}}}
    task = response_result.get("task", {})
    if isinstance(task, dict):
        status = task.get("status", {})
        if isinstance(status, dict):
            status_msg = status.get("message", {})
            if isinstance(status_msg, dict):
                for part in status_msg.get("parts", []):
                    if "text" in part:
                        return part["text"]

    return None


def _card_to_dict(card: AgentCard) -> dict:
    """Convert a protobuf AgentCard to a JSON-serializable dict.

    Uses protobuf's MessageToDict for proper field name conversion.
    """
    from google.protobuf.json_format import MessageToDict

    return MessageToDict(card)


def print_result(
    persona_name: str,
    user_text: str,
    response: dict,
) -> bool:
    """Pretty-print the result of a request.

    Returns True if the request succeeded (got a result), False if error.
    """
    print(f"  Request text: {user_text!r}")

    if "error" in response:
        print(f"  ERROR: {json.dumps(response['error'], indent=4)}")
        return False

    text = extract_response_text(response)
    if text:
        print(f"  Response: {text!r}")
        return True
    else:
        print(f"  Response (raw): {json.dumps(response, indent=2)}")
        return True  # got a response, just couldn't extract text
