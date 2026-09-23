# A2ASentinel: Rate Limiter & Cycle Overflow Mitigation Walkthrough

This walkthrough documents the implementation of the **Rate Limiter & Cycle Overflow Mitigation Stage** ([`sentinel/stages/rate_limiter.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/stages/rate_limiter.py)) to defend against flooding and recursive delegation/loop attacks from the A2ASecBench attack categories.

---

## 1. Architectural Design & Pipeline Stage Order

Rate limiting is registered **FIRST** (Stage 0) in the **A2ASentinel** pipeline before signature verification or RBAC checks. This ensures flooding requests are dropped cheaply before spending CPU time on cryptographic JWS signature validation or payload decoding.

```text
                         ┌─────────────────────────────────────┐
                         │       Incoming A2A Request          │
                         └──────────────────┬──────────────────┘
                                            │
                                            v
                         ┌─────────────────────────────────────┐
                         │   Stage 0: Rate Limiter & Cycle     │  <-- RUNS FIRST (Cheap check)
                         │   Overflow Detection                │
                         └──────────────────┬──────────────────┘
                                            │
                       ┌────────────────────┴────────────────────┐
                       │                                         │
                       v (Passed)                                v (Exceeded)
         ┌───────────────────────────┐                    ❌ BLOCKED
         │ Stage 1: Signature Check  │                (Rate limit / Cycle overflow)
         └─────────────┬─────────────┘
                       │
                       v
         ┌───────────────────────────┐
         │ Stage 2: RBAC Check       │
         └─────────────┬─────────────┘
```

---

## 2. Mitigation Heuristics & Rules

1. **Token-Bucket Sliding-Window Rate Limiting (Per Agent)**:
   - **Rule**: Max `RATE_LIMIT_BURST = 5` requests per `RATE_LIMIT_WINDOW = 10.0` seconds per `agent_name`.
   - **Action**: Exceeding burst limit returns `verdict="block", reason="rate limit exceeded: N requests in 10s"`.

2. **Cycle Overflow / Recursive Task Loop Detection**:
   - **Rule**: Max `CYCLE_REPEAT_THRESHOLD = 3` repeat requests for the exact same `(agent_name, requested_task)` pair in `CYCLE_REPEAT_WINDOW = 5.0` seconds.
   - **Action**: Repeated task loops return `verdict="block", reason="cycle overflow detected: agent 'AgentA' repeated task 'summarize_text' N times in 5s"`.

---

## 3. Key Files Created / Modified

- **[`sentinel/stages/rate_limiter.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/stages/rate_limiter.py)**: Implements sliding window rate limiter and cycle overflow checks.
- **[`sentinel/pipeline.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/pipeline.py)**: Registers `rate_limiter.run` as the first stage (`[rate_limiter.run, signature_check.run, rbac.run]`).
- **[`agent_a/run.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/agent_a/run.py)**: Added `run_flooder()` CLI test runner (`python -m agent_a.run flooder`).

---

## 4. Live Verification Results

### 1. Normal-Pace Requests (`python -m demo.run_demo`)
```text
  Scenario | Agent        | Check Failed          | Outcome
  ------------------------------------------------------------------
  1        | AgentA       | none (both pass)      | ALLOWED + response
  2        | AttackerBot  | Check 1: signature    | BLOCKED
  3        | ConfusedBot  | Check 2: capability   | BLOCKED
```
*Normal-pace requests remain 100% unaffected.*

---

### 2. Rapid-Fire Flood Test (`python -m agent_a.run flooder`)
```text
=================================================================
FLOOD TEST: Rapid-Fire Requests (10 Requests in Loop)
  Target Agent: AgentA | Target URL: http://localhost:8001/
  Rate Limit Policy: Max 5 requests per 10s window | Cycle Overflow: Max 3 repeat tasks
=================================================================

  Request # 1 -> ALLOWED (Agent B executed summarize_text)
  Request # 2 -> ALLOWED (Agent B executed summarize_text)
  Request # 3 -> ALLOWED (Agent B executed summarize_text)
  Request # 4 -> BLOCKED (Reason: BLOCKED by A2ASentinel: cycle overflow detected: agent 'AgentA' repeated task 'summarize_text' 4 times in 5s)
  Request # 5 -> BLOCKED (Reason: BLOCKED by A2ASentinel: cycle overflow detected: agent 'AgentA' repeated task 'summarize_text' 4 times in 5s)
  Request # 6 -> BLOCKED (Reason: BLOCKED by A2ASentinel: cycle overflow detected: agent 'AgentA' repeated task 'summarize_text' 4 times in 5s)
  Request # 7 -> BLOCKED (Reason: BLOCKED by A2ASentinel: cycle overflow detected: agent 'AgentA' repeated task 'summarize_text' 4 times in 5s)
  Request # 8 -> BLOCKED (Reason: BLOCKED by A2ASentinel: cycle overflow detected: agent 'AgentA' repeated task 'summarize_text' 4 times in 5s)
  Request # 9 -> BLOCKED (Reason: BLOCKED by A2ASentinel: cycle overflow detected: agent 'AgentA' repeated task 'summarize_text' 4 times in 5s)
  Request #10 -> BLOCKED (Reason: BLOCKED by A2ASentinel: cycle overflow detected: agent 'AgentA' repeated task 'summarize_text' 4 times in 5s)

=================================================================
FLOOD TEST RESULTS: 3 ALLOWED, 7 BLOCKED
Rate Limiter Stage 0 correctly intercepted rapid-fire requests before cryptographic checks.
=================================================================
```

---

### 3. Cryptographic Audit Ledger Verification (`python -m sentinel.verify_ledger`)
```text
--- Audit Ledger Verification ---
Verification Result: VALID LEDGER
```
