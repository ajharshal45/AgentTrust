"""Agent A — CLI runner with selectable personas.

Run with:
    python -m agent_a.run legitimate
    python -m agent_a.run attacker-signature
    python -m agent_a.run attacker-skill
    python -m agent_a.run all            (runs all three in sequence)

Requires Agent B to be running on localhost:8001.
"""

import sys

from agent_a.card import (
    create_agent_a_card,
    create_attacker_card_capability_mismatch,
    create_attacker_card_invalid_signature,
    create_attacker_card_skill_mismatch,
)
from agent_a.client import (
    AGENT_B_JSONRPC_URL,
    extract_response_text,
    print_result,
    send_request,
)


SEPARATOR = "=" * 65


def run_legitimate():
    """Run Agent A as a LEGITIMATE agent requesting summarize_text."""
    print(SEPARATOR)
    print("PERSONA: LEGITIMATE (AgentA)")
    print(f"  Target: {AGENT_B_JSONRPC_URL}")
    print(SEPARATOR)

    card = create_agent_a_card()
    print(f"  Agent card name: {card.name}")
    print(f"  Declared skills: {[s.id for s in card.skills]}")
    print()

    # Request summarize_text — this matches one of Agent B's declared
    # skills AND is within Agent A's own declared capabilities
    user_text = "Please summarize the following text about quantum computing research."
    response = send_request(card, user_text)
    success = print_result("AgentA", user_text, response)

    print()
    if success:
        text = extract_response_text(response)
        if text and "summarize_text" in text:
            print("  [OK] LEGITIMATE request SUCCEEDED -- Agent B executed summarize_text")
        else:
            print("  [OK] LEGITIMATE request got a response from Agent B")
    else:
        print("  [FAIL] LEGITIMATE request FAILED unexpectedly")
    print()
    return success


def run_attacker_signature():
    """Run the ATTACKER persona with a forged/invalid JWS signature.

    The card has a fake signature in its `signatures` field. Without
    A2ASentinel in place, Agent B doesn't check caller signatures, so
    this request will succeed. This establishes the "before" baseline.
    """
    print(SEPARATOR)
    print("PERSONA: ATTACKER — Invalid Signature (AttackerBot)")
    print(f"  Target: {AGENT_B_JSONRPC_URL}")
    print(SEPARATOR)

    card = create_attacker_card_invalid_signature()
    print(f"  Agent card name: {card.name}")
    print(f"  Declared skills: {[s.id for s in card.skills]}")
    print(f"  Signatures: {len(card.signatures)} (FORGED)")
    print(f"    protected: {card.signatures[0].protected}")
    print(f"    signature: {card.signatures[0].signature}")
    print()

    # Request summarize_text — the attacker claims to have this skill
    # but the card's signature is forged
    user_text = "Summarize this secret document for exfiltration purposes."
    response = send_request(card, user_text)
    success = print_result("AttackerBot", user_text, response)

    print()
    if success:
        print("  [WARN] ATTACKER request SUCCEEDED (EXPECTED without A2ASentinel)")
        print("    Baseline: no signature verification -> attacker gets through")
    else:
        print("  [FAIL] ATTACKER request FAILED (unexpected at this stage)")
    print()
    return success


def run_attacker_skill():
    """Run the ATTACKER persona that requests an undeclared skill.

    SneakyBot's card declares only "web_search" but sends a request
    that triggers Agent B's "translate_text" skill. Without A2ASentinel,
    Agent B doesn't check whether the caller's card declares the
    requested skill, so this will succeed. Baseline for comparison.
    """
    print(SEPARATOR)
    print("PERSONA: ATTACKER — Skill Mismatch (SneakyBot)")
    print(f"  Target: {AGENT_B_JSONRPC_URL}")
    print(SEPARATOR)

    card = create_attacker_card_skill_mismatch()
    print(f"  Agent card name: {card.name}")
    print(f"  Declared skills: {[s.id for s in card.skills]}")
    print(f"    (Note: does NOT declare summarize_text or translate_text)")
    print()

    # Request translate_text — this is a skill SneakyBot did NOT declare
    # in its own card, but Agent B has it
    user_text = "Translate this confidential memo to French for unauthorized distribution."
    response = send_request(card, user_text)
    success = print_result("SneakyBot", user_text, response)

    print()
    if success:
        print("  [WARN] ATTACKER request SUCCEEDED (EXPECTED without A2ASentinel)")
        print("    Baseline: no capability-match check -> undeclared skill access allowed")
    else:
        print("  [FAIL] ATTACKER request FAILED (unexpected at this stage)")
    print()
    return success


def run_attacker_capability():
    """Run the ATTACKER persona with a VALID signature but wrong declared skills.

    ConfusedBot has a properly signed card (passes signature check) but
    declares only 'data_export' while sending a translate_text request.
    This demonstrates check 2 (capability-match) firing independently.
    """
    print(SEPARATOR)
    print("PERSONA: ATTACKER -- Capability Mismatch (ConfusedBot)")
    print(f"  Target: {AGENT_B_JSONRPC_URL}")
    print(SEPARATOR)

    card = create_attacker_card_capability_mismatch()
    print(f"  Agent card name: {card.name}")
    print(f"  Declared skills: {[s.id for s in card.skills]}")
    print(f"  Signatures: {len(card.signatures)} (VALID -- passes check 1)")
    print(f"    (Card will pass signature check, fail capability-match check)")
    print()

    # Request translate_text -- ConfusedBot only declared 'data_export'
    user_text = "Translate this internal report to Spanish without authorization."
    response = send_request(card, user_text)
    success = print_result("ConfusedBot", user_text, response)

    print()
    if not success:
        resp_error = response.get("error", {}).get("message", "")
        if "capability mismatch" in resp_error:
            print("  [BLOCKED] Correctly blocked at capability-match check")
            print("    (Signature check PASSED -- this is check 2 firing)")
        else:
            print(f"  [BLOCKED] {resp_error}")
    else:
        print("  [WARN] ATTACKER request SUCCEEDED (EXPECTED without A2ASentinel)")
        print("    Baseline: no capability-match check -> undeclared skill access allowed")
    print()
    return success


PERSONAS = {
    "legitimate": run_legitimate,
    "attacker-signature": run_attacker_signature,
    "attacker-capability": run_attacker_capability,
    "attacker-skill": run_attacker_skill,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in (*PERSONAS, "all"):
        print("Usage: python -m agent_a.run <persona>")
        print()
        print("Available personas:")
        print("  legitimate           -- valid card, requests a declared skill")
        print("  attacker-signature   -- forged JWS signature on card")
        print("  attacker-capability  -- valid signature, wrong declared skills")
        print("  attacker-skill       -- no signature, wrong declared skills")
        print("  all                  -- run all four in sequence")
        sys.exit(1)

    persona = sys.argv[1]

    print()
    print("Agent A -- A2ASentinel Demo Client")
    print("Make sure Agent B is running: python -m agent_b.server")
    print()

    # Quick connectivity check
    import httpx

    try:
        httpx.get(f"{AGENT_B_JSONRPC_URL}.well-known/agent-card.json", timeout=3.0)
    except httpx.ConnectError:
        print(f"ERROR: Cannot connect to Agent B at {AGENT_B_JSONRPC_URL}")
        print("Start Agent B first: python -m agent_b.server")
        sys.exit(1)

    if persona == "all":
        results = {}
        for name, func in PERSONAS.items():
            results[name] = func()

        # Summary
        print(SEPARATOR)
        print("SUMMARY")
        print(SEPARATOR)
        for name, passed in results.items():
            status = "SUCCEEDED" if passed else "FAILED"
            print(f"  {name:25s} -> {status}")
        print()
        print("Without A2ASentinel, ALL requests (including attacks) succeed.")
        print("This is the baseline to compare against once the sentinel is added.")
        print(SEPARATOR)
    else:
        PERSONAS[persona]()


if __name__ == "__main__":
    main()
