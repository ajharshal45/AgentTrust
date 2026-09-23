# A2ASentinel

**Runtime Trust Verification Layer for Google's A2A (Agent-to-Agent) Protocol**

Mid-Semester EDI Project | Python 3.14 | `a2a-sdk` v1.1.4

---

## What is A2ASentinel?

A2ASentinel is a security middleware that sits between two A2A agents and enforces trust verification on every incoming request — **before** the request reaches the target agent.

It runs two checks in order, short-circuiting on the first failure:

| Check | What it verifies | Failure reason |
|---|---|---|
| **1. Signature** | Caller's AgentCard carries a valid JWS signature | `invalid signature: ...` |
| **2. Capability-match** | The requested task matches a skill declared in the caller's card | `capability mismatch: ...` |

If both checks pass → request is forwarded to Agent B.  
If either check fails → JSON-RPC error `-32403` is returned; Agent B never sees the request.

---

## Project Structure

```
A2ASentinel/
├── agent_b/              # Target agent (task-executing A2A server)
│   ├── card.py           # AgentCard with summarize_text + translate_text skills
│   ├── executor.py       # AgentExecutor with canned responses
│   └── server.py         # FastAPI + uvicorn on port 8001
│
├── agent_a/              # Requesting client with 4 personas
│   ├── card.py           # 4 AgentCard definitions (legitimate + 3 attackers)
│   ├── client.py         # httpx-based JSON-RPC request sender
│   └── run.py            # CLI runner: python -m agent_a.run <persona>
│
├── sentinel/             # Trust verification middleware
│   ├── keys.py           # HMAC-SHA256 JWS signing/verification
│   ├── checks.py         # check_signature() + check_capability_match()
│   ├── middleware.py     # A2ASentinelMiddleware (Starlette BaseHTTPMiddleware)
│   └── server.py         # Protected server: Agent B + sentinel wired together
│
├── demo/                 # Demo runner
│   ├── run_demo.py       # 3-scenario projector-ready demo script
│   └── README.md         # Demo-specific instructions
│
└── tests/
    └── test_agent_b.py   # Agent B verification (3/3 pass)
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install "a2a-sdk[fastapi]" uvicorn httpx
```

### 2. Run the demo (two terminals)

**Terminal 1 — start the protected server:**
```bash
python -m sentinel.server
```

**Terminal 2 — run the demo:**
```bash
python -m demo.run_demo
```

---

## Demo Scenarios

```
======================================================================
  SCENARIO 1: Legitimate Agent (AgentA)
======================================================================
  SENTINEL DECISION : ALLOWED
  AGENT B RESPONSE  : [Agent B] Executed summarize_text on: ...

======================================================================
  SCENARIO 2: Attacker with Forged Signature (AttackerBot)
======================================================================
  SENTINEL DECISION : BLOCKED by A2ASentinel: invalid signature:
                      all signatures failed cryptographic verification

======================================================================
  SCENARIO 3: Attacker with Valid Signature, Wrong Skills (ConfusedBot)
======================================================================
  SENTINEL DECISION : BLOCKED by A2ASentinel: capability mismatch:
                      requested skill 'translate_text' not in
                      caller's declared skills ['data_export']
```

---

## Agent A Personas

```bash
python -m agent_a.run legitimate          # valid card + real signature
python -m agent_a.run attacker-signature  # forged JWS signature
python -m agent_a.run attacker-capability # valid sig, wrong declared skills
python -m agent_a.run attacker-skill      # no signature at all
python -m agent_a.run all                 # run all four
```

---

## Architecture

```
Agent A (client)
    |
    |  POST / {method: "SendMessage", params: {message, metadata: {caller_agent_card}}}
    |
    v
+----------------------------+
|   A2ASentinel Middleware   |   <-- sentinel/middleware.py
|                            |
|  [1] Signature Check       |   BLOCKED -> JSON-RPC -32403 error
|  [2] Capability-Match      |   BLOCKED -> JSON-RPC -32403 error
|                            |
+----------------------------+
    |
    |  (only if both checks pass)
    v
Agent B (server)             <-- agent_b/ (unmodified)
    |
    v
Canned response
```

---

## Security Checks — Design Notes

### Signature Verification
Uses **HMAC-SHA256** with a shared demo key as a simplified JWS scheme (RFC 7515 envelope structure: `base64url(header).base64url(payload).base64url(signature)`). In production, this would be replaced with **ES256 (ECDSA P-256)** asymmetric keys — the verification flow is identical, only the key type changes.

### Capability-Match
Infers the requested skill from the message text using keyword matching (same keywords as Agent B's executor), then checks that skill ID exists in the caller's AgentCard `skills` list. Agents that request tasks outside their declared capabilities are blocked.

---

## Before / After A2ASentinel

| Persona | Without Sentinel | With Sentinel | Check that fires |
|---|---|---|---|
| AgentA (legitimate) | SUCCEEDED | **ALLOWED** + Agent B responds | — (both pass) |
| AttackerBot (forged sig) | SUCCEEDED | **BLOCKED** | Check 1: signature |
| ConfusedBot (valid sig, wrong skills) | SUCCEEDED | **BLOCKED** | Check 2: capability-match |
| SneakyBot (no signature) | SUCCEEDED | **BLOCKED** | Check 1: no signatures field |

---

## Tech Stack

- **[a2a-sdk](https://pypi.org/project/a2a-sdk/) v1.1.4** — Google's Agent-to-Agent protocol SDK
- **FastAPI + Starlette** — web framework and middleware layer
- **uvicorn** — ASGI server
- **httpx** — async HTTP client
- **Python stdlib** — `hmac`, `hashlib`, `base64` for cryptography (no extra deps)
