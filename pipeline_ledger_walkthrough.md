# AgentTrust: Pipeline Restructuring & Hash-Chained Audit Ledger Walkthrough

This walkthrough documents the restructuring of **AgentTrust** from a single middleware with hardcoded checks into a modular **PIPELINE** of independent stages (`signature_check`, `rbac`), and the addition of an append-only, **HMAC-SHA256 hash-chained audit ledger** (`ledger.py`).

---

## Key Changes Made

### 1. Modular Stage Architecture (`sentinel/stages/`)
- **[base.py](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/stages/base.py)**: Defined `StageResult` dataclass (`passed: bool`, `reason: str | None`, `stage_name: str`).
- **[signature_check.py](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/stages/signature_check.py)**: Encapsulates Check 1 (JWS HMAC-SHA256 signature verification).
- **[rbac.py](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/stages/rbac.py)**: Encapsulates Check 2 (Capability-match / RBAC declared skill validation).

### 2. Sequential Pipeline Executor ([sentinel/pipeline.py](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/pipeline.py))
- Manages an ordered list of security stages (`[signature_check, rbac]`).
- Short-circuits immediately on the first stage returning `passed=False`.
- Automatically calls `ledger.log_decision()` for every request (both `ALLOWED` and `BLOCKED`).

### 3. Hash-Chained Audit Ledger ([sentinel/ledger.py](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/ledger.py))
- Stores append-only audit entries in `sentinel/audit_ledger.jsonl`.
- Computes `entry_hash = HMAC-SHA256(DEMO_SECRET_KEY, canonical_entry_data + previous_entry_hash)` reusing the key from `sentinel/keys.py`.
- Provides `verify_chain()` to recompute every hash from entry 1 and verify chain integrity.

### 4. Middleware Integration ([sentinel/middleware.py](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/middleware.py))
- Updated `AgentTrustMiddleware` to invoke `pipeline.run(request_context)` while preserving existing JSON-RPC `-32403` error formats.

### 5. Verification Tool ([sentinel/verify_ledger.py](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/verify_ledger.py))
- CLI script to verify ledger integrity (`python -m sentinel.verify_ledger`).
- Includes `--tamper` flag to corrupt an entry and verify cryptographic tamper detection.

---

## Verification Results

### 1. Full Demo Run Output (`python -m demo.run_demo`)

```text
======================================================================
  AgentTrust -- Runtime Trust Verification for A2A Protocol
  Mid-Semester Demo | EDI Project
======================================================================

  Checking connection to protected server (localhost:8001)...
  Connected. Starting demo.

======================================================================
  SCENARIO 1: Legitimate Agent (AgentA)
======================================================================
  SENTINEL DECISION : ALLOWED
  AGENT B RESPONSE  : [Agent B] Executed summarize_text on: Please summarize the following research on quantum computing.

  >> RESULT: ALLOWED -- request reached Agent B and got a real response.

======================================================================
  SCENARIO 2: Attacker with Forged Signature (AttackerBot)
======================================================================
  SENTINEL DECISION : BLOCKED by AgentTrust: invalid signature: all signatures failed cryptographic verification

  >> RESULT: BLOCKED at Check 1 (signature verification).

======================================================================
  SCENARIO 3: Attacker with Valid Signature, Wrong Skills (ConfusedBot)
======================================================================
  SENTINEL DECISION : BLOCKED by AgentTrust: capability mismatch: requested skill 'translate_text' not in caller's declared skills ['data_export']

  >> RESULT: BLOCKED at Check 2 (capability-match).

======================================================================
  DEMO SUMMARY
======================================================================
  Scenario 1: AgentA       | ALLOWED + response
  Scenario 2: AttackerBot  | BLOCKED (Check 1: signature)
  Scenario 3: ConfusedBot  | BLOCKED (Check 2: capability)
======================================================================
```

---

### 2. Audit Ledger File Output (`sentinel/audit_ledger.jsonl`)

```json
{"timestamp":"2026-09-23T14:13:11.960140+00:00","agent_name":"AgentA","requested_task":"summarize_text","decision":"ALLOWED","reason":"","entry_hash":"21edea29f3ddb8e8d0d89a4e9589a5658e4ea646ad8c2dafd4c241d57eb65ee8"}
{"timestamp":"2026-09-23T14:13:12.533701+00:00","agent_name":"AttackerBot","requested_task":"summarize_text","decision":"BLOCKED","reason":"invalid signature: all signatures failed cryptographic verification","entry_hash":"8e371ac81abe80f93128aae2612019649c19d07c12f47d7b5bc08b893452f32e"}
{"timestamp":"2026-09-23T14:13:13.079504+00:00","agent_name":"ConfusedBot","requested_task":"translate_text","decision":"BLOCKED","reason":"capability mismatch: requested skill 'translate_text' not in caller's declared skills ['data_export']","entry_hash":"d5596c58ed0afde419555f0006bfcdef4fe7bfdc1f7e5126be09a50af66eb14f"}
```

---

### 3. Ledger Verification (`python -m sentinel.verify_ledger`)

```text
--- Audit Ledger Verification ---
Verification Result: VALID LEDGER
```

---

### 4. Tamper Detection Test (`python -m sentinel.verify_ledger --tamper`)

```text
--- Audit Ledger Verification (with --tamper demo) ---
[DEMO] Manually corrupted entry #3 in audit_ledger.jsonl
Verification Result: TAMPER DETECTED at entry 3
>> SUCCESS: Audit ledger correctly detected cryptographic tampering!
```
