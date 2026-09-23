# A2ASentinel: 3-Tier Trust Model & Human-in-the-Loop Review Walkthrough

This walkthrough documents the upgrade of **A2ASentinel** from a binary (Allowed/Blocked) model to a **3-Tier Trust Model** (`PASS`, `ALERT`, `BLOCK`), introducing a human-in-the-loop review queue ([`sentinel/alert_queue.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/alert_queue.py)), a reviewer CLI tool ([`sentinel/review.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/review.py)), and new partial-match alert personas.

---

## 1. Architectural Overview

```
                                  ┌───────────────────────────┐
                                  │      A2ASentinel Stage    │
                                  └─────────────┬─────────────┘
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 │                              │                              │
                 v                              v                              v
           verdict: "pass"               verdict: "alert"               verdict: "block"
                 │                              │                              │
                 v                              v                              v
            ALLOWED                      PENDING_REVIEW                     BLOCKED
    (Forward to Agent B)             (Enqueue to alert_queue)          (JSON-RPC -32403)
                                                │
                                                │  python -m sentinel.review approve/reject <id>
                                                v
                                 ┌─────────────────────────────┐
                                 │   Human Reviewer Action     │
                                 └──────────────┬──────────────┘
                                                │
                       ┌────────────────────────┴────────────────────────┐
                       │                                                 │
                       v                                                 v
                   APPROVED                                          REJECTED
         (Next request: ALLOWED)                           (Next request: BLOCKED)
```

---

## 2. Key Changes Made

### 1. 3-Tier Stage Result Interface ([`sentinel/stages/base.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/stages/base.py))
- Replaced boolean `passed` with `verdict: Literal["pass", "alert", "block"]`.

### 2. Partial Match Logic ([`sentinel/stages/rbac.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/stages/rbac.py))
- Evaluates `alert_queue` status first:
  - If reviewer previously `approved` $\rightarrow$ `verdict="pass"`
  - If reviewer previously `rejected` $\rightarrow$ `verdict="block"`
- Exact skill match $\rightarrow$ `verdict="pass"`
- Partial / Fuzzy keyword stem match (e.g., requested `summarize_text` vs. declared `summarize_draft`) $\rightarrow$ `verdict="alert"`
- Completely disjoint capability $\rightarrow$ `verdict="block"`

### 3. Human Review Queue & CLI Tool ([`sentinel/alert_queue.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/alert_queue.py) & [`sentinel/review.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/sentinel/review.py))
- Stores alerts in `sentinel/alert_queue.json`.
- `python -m sentinel.review`: Lists pending review items.
- `python -m sentinel.review approve <id>`: Approves item `<id>`.
- `python -m sentinel.review reject <id>`: Rejects item `<id>`.

### 4. Alert Personas ([`agent_a/card.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/agent_a/card.py) & [`agent_a/run.py`](file:///c:/college/EDI%20Project/3rd%20sem-1/agent_a/run.py))
- **`alert-persona` (`AlertBot`)**: Declares `summarize_draft`, requests `summarize_text` (Approval demo).
- **`alert-reject` (`RiskyBot`)**: Declares `translate_draft`, requests `translate_text` (Rejection demo).

---

## 3. Live Verification Workflows

### Workflow A: Human Approval Flow (`AlertBot`)

1. **Trigger Alert**:
   ```bash
   python -m agent_a.run alert-persona
   ```
   **Output**:
   ```text
   ERROR: {
     "code": -32403,
     "message": "BLOCKED by A2ASentinel: PENDING_REVIEW: partial capability match: requested 'summarize_text' requires human review against declared skills ['summarize_draft'] (Enqueued in Alert Queue #1)"
   }
   [ALERT / PENDING_REVIEW] Enqueued for human review in sentinel/review.py
   ```

2. **Inspect Queue**:
   ```bash
   python -m sentinel.review
   ```
   **Output**:
   ```text
   =================================================================
     A2ASentinel Human Review Queue [PENDING]
   =================================================================
     ID #1 | Agent: AlertBot | Task: summarize_text
       Reason   : partial capability match: requested 'summarize_text' requires human review against declared skills ['summarize_draft']
       Status   : PENDING
   ```

3. **Approve Alert**:
   ```bash
   python -m sentinel.review approve 1
   ```
   **Output**:
   ```text
   =================================================================
     [HUMAN REVIEWER ACTION] Alert #1 -> APPROVED
     Agent   : AlertBot
     Task    : summarize_text
     Status  : APPROVED
   =================================================================
   ```

4. **Re-run Request**:
   ```bash
   python -m agent_a.run alert-persona
   ```
   **Output**:
   ```text
   Response: '[Agent B] Executed summarize_text on: Please provide a summarize_brief for this draft document.'
   [ALLOWED] Request passed human review and Agent B executed
   ```

---

### Workflow B: Human Rejection Flow (`RiskyBot`)

1. **Trigger Alert**:
   ```bash
   python -m agent_a.run alert-reject
   ```
   **Output**:
   ```text
   ERROR: {
     "code": -32403,
     "message": "BLOCKED by A2ASentinel: PENDING_REVIEW: partial capability match: requested 'translate_text' requires human review against declared skills ['translate_draft'] (Enqueued in Alert Queue #2)"
   }
   [ALERT / PENDING_REVIEW] Enqueued for human review
   ```

2. **Reject Alert**:
   ```bash
   python -m sentinel.review reject 2
   ```
   **Output**:
   ```text
   =================================================================
     [HUMAN REVIEWER ACTION] Alert #2 -> REJECTED
     Agent   : RiskyBot
     Task    : translate_text
     Status  : REJECTED
   =================================================================
   ```

3. **Re-run Request**:
   ```bash
   python -m agent_a.run alert-reject
   ```
   **Output**:
   ```text
   ERROR: {
     "code": -32403,
     "message": "BLOCKED by A2ASentinel: capability mismatch: human reviewer rejected request for 'translate_text'"
   }
   [BLOCKED] Request rejected by human reviewer or policy
   ```

---

### 4. Cryptographic Audit Ledger Verification
```bash
python -m sentinel.verify_ledger
```
**Output**:
```text
--- Audit Ledger Verification ---
Verification Result: VALID LEDGER
```
