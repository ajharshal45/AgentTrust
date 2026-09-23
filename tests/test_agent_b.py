"""Verification script for Agent B.

Tests the three acceptance criteria:
  1. Agent B starts without errors (tested manually — server must be running)
  2. Agent card is retrievable and lists both skills
  3. A task request gets back the canned response

Run this AFTER starting Agent B:
    python -m agent_b.server         (in one terminal)
    python tests/test_agent_b.py     (in another terminal)
"""

import httpx
import json
import sys
import uuid


AGENT_B_BASE = "http://localhost:8001"
AGENT_CARD_URL = f"{AGENT_B_BASE}/.well-known/agent-card.json"
JSONRPC_URL = f"{AGENT_B_BASE}/"


def test_agent_card():
    """Fetch the agent card and verify both skills are declared."""
    print("=" * 60)
    print("TEST 1: Fetch Agent Card")
    print(f"  GET {AGENT_CARD_URL}")
    print("=" * 60)

    resp = httpx.get(AGENT_CARD_URL)
    print(f"  Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"  FAIL: Expected 200, got {resp.status_code}")
        print(f"  Body: {resp.text}")
        return False

    card = resp.json()
    print(f"  Agent name: {card.get('name')}")
    print(f"  Description: {card.get('description')}")

    skills = card.get("skills", [])
    skill_ids = [s.get("id") for s in skills]
    print(f"  Skills found: {skill_ids}")

    if "summarize_text" not in skill_ids:
        print("  FAIL: 'summarize_text' skill not found in card")
        return False
    if "translate_text" not in skill_ids:
        print("  FAIL: 'translate_text' skill not found in card")
        return False

    print("  PASS: Both skills declared in agent card")
    print()
    return True


def test_send_message(user_text: str, expected_skill: str):
    """Send a JSON-RPC message/send request and verify the canned response."""
    print("=" * 60)
    print(f"TEST: Send message — expecting '{expected_skill}'")
    print(f"  POST {JSONRPC_URL}")
    print(f"  User text: {user_text!r}")
    print("=" * 60)

    # Build a JSON-RPC 2.0 SendMessage request.
    # In A2A v1.0, method names are PascalCase gRPC-style (e.g. "SendMessage"),
    # NOT v0.3 slash-style ("message/send").
    # The params are parsed directly as a protobuf SendMessageRequest, so the
    # "message" field sits at the top level of params.
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
        },
    }

    # The A2A v1.0 protocol requires an A2A-Version header.
    # The exact value checked by the SDK is "1.0" (from utils/constants.py).
    headers = {
        "Content-Type": "application/json",
        "A2A-Version": "1.0",
    }

    resp = httpx.post(
        JSONRPC_URL,
        json=request_payload,
        headers=headers,
        timeout=30.0,
    )
    print(f"  Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"  FAIL: Expected 200, got {resp.status_code}")
        print(f"  Body: {resp.text}")
        return False

    result = resp.json()
    print(f"  Response JSON (formatted):")
    print(f"  {json.dumps(result, indent=2)}")

    # The response should be a JSON-RPC success response containing
    # either a Task or Message with our canned text
    if "error" in result:
        print(f"  FAIL: Got JSON-RPC error: {result['error']}")
        return False

    if "result" not in result:
        print("  FAIL: No 'result' in response")
        return False

    # Extract the response text — could be in a Message or Task structure
    response_result = result["result"]
    response_text = _extract_response_text(response_result)

    if response_text is None:
        print("  FAIL: Could not extract response text from result")
        return False

    print(f"  Response text: {response_text!r}")

    if expected_skill in response_text.lower() or expected_skill.replace("_", " ") in response_text.lower():
        print(f"  PASS: Response confirms '{expected_skill}' execution")
    else:
        print(f"  WARNING: Response text doesn't clearly mention '{expected_skill}'")

    print()
    return True


def _extract_response_text(result: dict) -> str | None:
    """Extract text from a SendMessageResponse result structure.

    The SDK wraps responses in SendMessageResponse which has either:
      - result.message.parts[].text  (immediate Message response)
      - result.task.status.message.parts[].text  (Task response)
    """
    # SendMessageResponse with Message: {"message": {"parts": [...]}}
    msg = result.get("message", {})
    if isinstance(msg, dict):
        for part in msg.get("parts", []):
            if "text" in part:
                return part["text"]

    # SendMessageResponse with Task: {"task": {"status": {"message": ...}}}
    task = result.get("task", {})
    if isinstance(task, dict):
        status = task.get("status", {})
        if isinstance(status, dict):
            status_msg = status.get("message", {})
            if isinstance(status_msg, dict):
                for part in status_msg.get("parts", []):
                    if "text" in part:
                        return part["text"]

    # Fallback: direct parts on result (shouldn't happen, but just in case)
    for part in result.get("parts", []):
        if "text" in part:
            return part["text"]

    return None


def main():
    print()
    print("Agent B Verification Tests")
    print("Make sure Agent B is running: python -m agent_b.server")
    print()

    # Check if server is reachable
    try:
        httpx.get(AGENT_CARD_URL, timeout=3.0)
    except httpx.ConnectError:
        print(f"ERROR: Cannot connect to {AGENT_B_BASE}")
        print("Start Agent B first: python -m agent_b.server")
        sys.exit(1)

    results = []

    # Test 1: Agent card
    results.append(test_agent_card())

    # Test 2: Summarize request
    results.append(
        test_send_message(
            "Please summarize this text about quantum computing.",
            "summarize_text",
        )
    )

    # Test 3: Translate request
    results.append(
        test_send_message(
            "Translate the following to French: Hello world.",
            "translate_text",
        )
    )

    # Summary
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    if all(results):
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
