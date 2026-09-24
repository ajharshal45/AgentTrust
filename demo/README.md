# AgentTrust Demo

## What this demonstrates

AgentTrust is a runtime trust verification layer for Google's A2A (Agent-to-Agent)
protocol. It sits as FastAPI middleware in front of a target agent (Agent B) and
enforces two independent security checks on every incoming request:

1. **Signature check** — the caller's AgentCard must carry a cryptographically valid
   JWS signature. Cards with missing, forged, or tampered signatures are rejected
   before the request ever reaches Agent B.
2. **Capability-match check** — the task being requested must correspond to a skill
   the calling agent has declared in its own AgentCard. An agent that declares only
   "web_search" but requests "translate_text" is blocked, even if its signature is valid.

Both checks must pass for a request to be forwarded to Agent B. Blocked requests
receive a JSON-RPC error response (`-32403`) and are never seen by Agent B's logic.

---

## Commands to run the full demo

**Terminal 1 — start the protected server (keep this running):**
```
cd "c:\Engineering (b-tech)\EDI\5th sem\Agenttrust"
python -m sentinel.server
```

**Terminal 2 — run the demo:**
```
cd "c:\Engineering (b-tech)\EDI\5th sem\Agenttrust"
python -m demo.run_demo
```

---

## Scenario summary

| Scenario | Agent | What it does | Expected outcome |
|---|---|---|---|
| **1 — Legitimate** | AgentA | Valid signed card, requests a declared skill | `ALLOWED` — Agent B responds with canned result |
| **2 — Forged Signature** | AttackerBot | Card has a tampered JWS signature | `BLOCKED` — Check 1 (signature) fails |
| **3 — Capability Mismatch** | ConfusedBot | Valid signature, but declared skill ≠ requested skill | `BLOCKED` — Check 2 (capability-match) fails |

---

## Individual persona commands (for testing/debugging)

```
python -m agent_a.run legitimate          # Scenario 1
python -m agent_a.run attacker-signature  # Scenario 2
python -m agent_a.run attacker-capability # Scenario 3
python -m agent_a.run attacker-skill      # Extra: no signature at all
python -m agent_a.run all                 # All four in sequence
```
