# Requirements: A2ASentinel MVP

## Environment
- Python 3.12
- `a2a-sdk` (confirmed installed version: 1.1.4) — see sdk_reference.md for
  the verified real API surface before writing any code against it.
- FastAPI-based server (the SDK provides FastAPI route integration natively).

## Components to build

### 1. Agent B — the task-executing agent
- A minimal A2A server agent using `AgentExecutor` from the SDK.
- Should expose 1-2 simple declared skills in its Agent Card, e.g.
  "summarize_text" and "translate_text".
- On receiving a valid request, it just returns a canned response
  confirming the task type it executed (no real AI logic needed for
  the demo — this is about the security layer, not the agent's own
  intelligence).

### 2. Agent A — the requesting client
- Uses the SDK's `Client` (from `client_factory.py` / `ClientFactory`)
  to send task requests to Agent B, presenting its own Agent Card.
- Needs two configurable "personas" for the demo:
  - **Legitimate persona:** valid signed card, requests a task matching
    its declared skill.
  - **Attacker persona:** either (a) a tampered/invalid signature, or
    (b) a valid signature but requests a task outside its declared
    skills — needs to support both attack modes if feasible, or pick
    the simpler one first and note the other as a fast follow-up.

### 3. A2ASentinel — the interceptor
- Sits between Agent A and Agent B — do not modify Agent B's own logic
  to do these checks; the checks belong in a separate, clearly isolated
  layer, since the whole point is that the security layer is independent
  of the agents themselves.
- Implementation approach: prefer using the SDK's native interceptor
  hook (`Client.add_interceptor` / `ClientCallInterceptor`) if it fits,
  since this is a real, built-in extension point rather than something
  we're bolting on awkwardly. If that hook only covers the client side
  and doesn't give visibility into the server side, use FastAPI
  middleware in front of `add_a2a_routes_to_fastapi` on Agent B's side
  instead — pick whichever is cleaner given what you find when
  exploring the actual SDK, and explain the choice.
- Checks, run in order, short-circuiting on first failure:
  1. **Signature check** — verify the AgentCard's `signatures` field
     (JWS-based, per RFC 7515) is present and valid. If full real
     cryptographic verification is complex for the demo, implement a
     simplified but real verification using a keypair generated for
     this demo, and clearly comment that this simulates full A2A v1.0
     signature verification.
  2. **Capability-match check** — compare the requested task/skill
     against the AgentCard's declared `skills` list. If the request
     doesn't correspond to a declared skill, this fails.
- Output: for every request, print a clear line:
  `[A2ASentinel] <agent_name> -> <requested_task>: ALLOWED`
  or
  `[A2ASentinel] <agent_name> -> <requested_task>: BLOCKED (reason: ...)`

### 4. Demo runner
- One script (or a couple of clearly labeled scripts) that can run both
  demo scenarios described in demo_scenarios.md, in sequence, with
  clean, readable console output suitable for a live review — this
  will be shown to a panel, so output clarity matters as much as
  correctness.

## Non-functional requirements
- Keep dependencies minimal — no new heavy frameworks beyond what
  `a2a-sdk` already pulls in (FastAPI, pydantic, httpx are fine since
  they're already dependencies).
- Code should be simple enough for a team of 4 second/third-year
  students to read, explain, and extend next — favor clarity over
  cleverness.
- If any part of the described design doesn't match what the installed
  SDK actually supports, say so explicitly and propose the closest
  realistic alternative rather than silently changing the approach.
