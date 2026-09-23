"""A2ASentinel Demo Runner.

Runs three clear scenarios showing A2ASentinel's trust verification in action:

  Scenario 1: Legitimate agent — ALLOWED, gets Agent B's real response
  Scenario 2: Attacker with forged signature — BLOCKED (Check 1: signature)
  Scenario 3: Attacker with valid sig but wrong skills — BLOCKED (Check 2: capability-match)

BEFORE RUNNING:
  Start the protected server in a separate terminal first:
    python -m sentinel.server

Then run this script:
    python -m demo.run_demo
"""

import sys
import time

import httpx

from agent_a.card import (
    create_agent_a_card,
    create_attacker_card_capability_mismatch,
    create_attacker_card_invalid_signature,
)
from agent_a.client import AGENT_B_JSONRPC_URL, extract_response_text, send_request

# ── Visual constants ────────────────────────────────────────────────────────
WIDE  = "=" * 70
THIN  = "-" * 70
BLANK = ""


def banner(text: str) -> None:
    print(BLANK)
    print(WIDE)
    print(f"  {text}")
    print(WIDE)


def section(text: str) -> None:
    print(BLANK)
    print(THIN)
    print(f"  {text}")
    print(THIN)


def info(text: str) -> None:
    print(f"  {text}")


def gap() -> None:
    print(BLANK)


# ── Connectivity check ───────────────────────────────────────────────────────

def check_server() -> None:
    """Abort early with a clear message if the protected server isn't running."""
    try:
        httpx.get(
            f"{AGENT_B_JSONRPC_URL}.well-known/agent-card.json",
            timeout=3.0,
        )
    except httpx.ConnectError:
        print()
        print("ERROR: Cannot connect to the protected server on localhost:8001.")
        print()
        print("  Start it first in a separate terminal:")
        print("    python -m sentinel.server")
        print()
        sys.exit(1)


# ── Scenario helpers ─────────────────────────────────────────────────────────

def show_card_summary(card) -> None:
    info(f"Agent name     : {card.name}")
    info(f"Declared skills: {[s.id for s in card.skills]}")
    info(f"Signatures     : {len(card.signatures)}")


def show_sentinel_decision(response: dict) -> str:
    """Print the sentinel's ALLOWED/BLOCKED decision from the response.

    Returns 'allowed' or 'blocked'.
    """
    if "error" in response:
        msg = response["error"].get("message", "unknown error")
        info(f"SENTINEL DECISION : {msg}")
        return "blocked"
    text = extract_response_text(response)
    info(f"SENTINEL DECISION : ALLOWED")
    info(f"AGENT B RESPONSE  : {text}")
    return "allowed"


# ── Scenarios ────────────────────────────────────────────────────────────────

def scenario_1_legitimate() -> None:
    banner("SCENARIO 1: Legitimate Agent (AgentA)")
    info("AgentA presents a properly signed card and requests a skill")
    info("it has declared. Both sentinel checks pass -> request forwarded.")
    gap()

    card = create_agent_a_card()
    show_card_summary(card)
    gap()

    user_text = "Please summarize the following research on quantum computing."
    info(f"Request text: {user_text!r}")
    gap()

    response = send_request(card, user_text)
    outcome = show_sentinel_decision(response)
    gap()

    if outcome == "allowed":
        print("  >> RESULT: ALLOWED -- request reached Agent B and got a real response.")
    else:
        print("  >> RESULT: UNEXPECTED BLOCK -- check server config.")


def scenario_2_forged_signature() -> None:
    banner("SCENARIO 2: Attacker with Forged Signature (AttackerBot)")
    info("AttackerBot presents a card with a tampered JWS signature.")
    info("Sentinel Check 1 (signature) fails -> request blocked, never")
    info("reaches Agent B.")
    gap()

    card = create_attacker_card_invalid_signature()
    show_card_summary(card)
    info(f"  sig value  : {card.signatures[0].signature}  <-- forged")
    gap()

    user_text = "Summarize this secret document for exfiltration purposes."
    info(f"Request text: {user_text!r}")
    gap()

    response = send_request(card, user_text)
    outcome = show_sentinel_decision(response)
    gap()

    if outcome == "blocked":
        print("  >> RESULT: BLOCKED at Check 1 (signature verification).")
        print("             Agent B executor log shows NO matching entry --")
        print("             the request was stopped by middleware before")
        print("             reaching any agent logic.")
    else:
        print("  >> RESULT: UNEXPECTED PASS -- sentinel not active?")


def scenario_3_capability_mismatch() -> None:
    banner("SCENARIO 3: Attacker with Valid Signature, Wrong Skills (ConfusedBot)")
    info("ConfusedBot's card is properly signed (passes Check 1),")
    info("but it declares only 'data_export' and requests 'translate_text'.")
    info("Sentinel Check 2 (capability-match) fails -> blocked.")
    gap()

    card = create_attacker_card_capability_mismatch()
    show_card_summary(card)
    info("  (signature is cryptographically valid -- Check 1 will PASS)")
    info("  (declared skill 'data_export' != requested 'translate_text')")
    gap()

    user_text = "Translate this internal report to Spanish without authorization."
    info(f"Request text: {user_text!r}")
    gap()

    response = send_request(card, user_text)
    outcome = show_sentinel_decision(response)
    gap()

    if outcome == "blocked":
        error_msg = response.get("error", {}).get("message", "")
        if "capability mismatch" in error_msg:
            print("  >> RESULT: BLOCKED at Check 2 (capability-match).")
            print("             Check 1 (signature) PASSED -- this proves both")
            print("             checks are independently enforced.")
        else:
            print(f"  >> RESULT: BLOCKED (unexpected reason: {error_msg})")
    else:
        print("  >> RESULT: UNEXPECTED PASS -- sentinel not active?")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(BLANK)
    print(WIDE)
    print("  A2ASentinel -- Runtime Trust Verification for A2A Protocol")
    print("  Mid-Semester Demo | EDI Project")
    print(WIDE)
    print(BLANK)
    print("  Checking connection to protected server (localhost:8001)...")
    check_server()
    print("  Connected. Starting demo.")

    scenario_1_legitimate()
    time.sleep(0.3)

    scenario_2_forged_signature()
    time.sleep(0.3)

    scenario_3_capability_mismatch()

    # ── Final summary ────────────────────────────────────────────────────────
    print(BLANK)
    print(WIDE)
    print("  DEMO SUMMARY")
    print(WIDE)
    print(BLANK)
    print("  Scenario | Agent        | Check Failed          | Outcome")
    print("  " + "-" * 66)
    print("  1        | AgentA       | none (both pass)      | ALLOWED + response")
    print("  2        | AttackerBot  | Check 1: signature    | BLOCKED")
    print("  3        | ConfusedBot  | Check 2: capability   | BLOCKED")
    print(BLANK)
    print("  A2ASentinel enforces two independent trust checks on every")
    print("  incoming A2A request. Both checks must pass for a request")
    print("  to reach the agent. Blocked requests return a JSON-RPC")
    print("  error (-32403) and never touch Agent B's logic.")
    print(BLANK)
    print(WIDE)
    print(BLANK)


if __name__ == "__main__":
    main()
