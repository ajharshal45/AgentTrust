# AgentTrust

**Runtime Trust Verification Gateway & Modular Pipeline for Google's A2A (Agent-to-Agent) Protocol**

Mid-Semester EDI Project | Python 3.14 | `a2a-sdk` v1.1.4

---

## 🌟 What is AgentTrust?

**AgentTrust** is an extensible, zero-trust security gateway and middleware designed to protect Agent-to-Agent (A2A) communications. Positioned between incoming client agents and target executing agents, AgentTrust intercepts JSON-RPC requests and evaluates them through a **5-Stage Sequential Pipeline** using a **3-Tier Trust Model** (`PASS`, `ALERT`, `BLOCK`).

Every decision—whether allowed, blocked, or sent to Human-in-the-Loop (HITL) review—is immutably logged into an **HMAC-SHA256 Hash-Chained Audit Ledger** for tamper-evident security auditing.

---

## 🏗️ Architecture & 5-Stage Pipeline

```text
                             [ Agent A / Client / Attacker ]
                                           │
                                  ( HTTP POST JSON-RPC )
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 AgentTrust Middleware                                  │
│                             (sentinel/middleware.py)                                   │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                            5-Stage Security Evaluation Pipeline                        │
│                             (sentinel/pipeline.py)                                     │
│                                                                                        │
│  [Stage 0: IP Throttle] ──────► Drop IP flood before reading payload (Identity-agnostic) │
│           │                                                                            │
│           ▼                                                                            │
│  [Stage 1: Signature Check] ──► Verify JWS HMAC-SHA256 against agent public keys        │
│           │                                                                            │
│           ▼                                                                            │
│  [Stage 2: Rate Limiter] ────► Per-Agent Quota & Cycle Overflow Loop Detection         │
│           │                     (Enforced ONLY for cryptographically verified agents)   │
│           ▼                                                                            │
│  [Stage 3: RBAC] ────────────► Exact capability check & partial keyword stem match     │
│           │                     (Returns "alert" on partial/fuzzy stem matches)        │
│           ▼                                                                            │
│  [Stage 4: Injection Filter] ─► Regex scanner for prompt overrides & system leaks      │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              3-Tier Decision Engine                                    │
│                                                                                        │
│     ┌────────────────────────────┼───────────────────────────┐                         │
│     │ PASS                       │ ALERT                     │ BLOCK                   │
│     ▼                            ▼                           ▼                         │
│ [ ALLOWED ]            [ HITL Review Queue ]           [ BLOCKED ]                     │
│  Forward to Agent B    (sentinel/alert_queue.py)       JSON-RPC Error Code -32403      │
│  Execution Server       - Manual Mode (Polled status)                                  │
│                         - Auto Mode (Inline review)                                    │
└─────────┬────────────────────────┬───────────────────────────┬─────────────────────────┘
          │                        │                           │
          ▼                        ▼                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                       HMAC-SHA256 Hash-Chained Audit Ledger                            │
│                             (sentinel/ledger.py)                                       │
│  - Appends entry with Hash = HMAC_SHA256(Secret, PrevHash + EntryData)                 │
│  - Tamper verification via `python -m sentinel.verify_ledger`                          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Pipeline Stages Summary

| Stage | Name | File | Description | Action / Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **0** | **IP Throttle** | `sentinel/stages/ip_throttle.py` | Identity-agnostic IP rate limiter (20 req/10s). | `block` on connection flood |
| **1** | **Signature Check** | `sentinel/stages/signature_check.py` | Validates JWS HMAC-SHA256 signatures against public keys. | `block` on missing/forged sig |
| **2** | **Rate Limiter** | `sentinel/stages/rate_limiter.py` | Post-signature per-agent quota (5 req/10s) and cycle overflow loop detection (3 repeats/5s). | `block` on rate/cycle limit |
| **3** | **RBAC** | `sentinel/stages/rbac.py` | Enforces declared capabilities; triggers `alert` on partial/fuzzy stem keyword matches. | `pass` / `alert` / `block` |
| **4** | **Injection Filter** | `sentinel/stages/injection_filter.py` | Regex pattern scanner for prompt overrides (e.g., `"ignore previous instructions"`). | `block` on injection match |

---

## 🚦 3-Tier Trust Model & Human-in-the-Loop (HITL)

AgentTrust supports three distinct execution outcomes:

1. **`ALLOWED` (`pass`)**: Request satisfied all pipeline checks and is forwarded directly to the downstream execution agent.
2. **`BLOCKED` (`block`)**: Request violated a security check. Returns JSON-RPC error code `-32403` with a concise reason.
3. **`PENDING_REVIEW` (`alert`)**: Request involves ambiguous or partial capability matches. It is routed to the HITL queue (`sentinel/alert_queue.py`).

### Reviewer CLI (`sentinel/review.py`)
Operators can list and inspect pending alerts or approve/reject them interactively:
```bash
# List pending alerts
python -m sentinel.review list

# Approve or reject a specific alert task ID
python -m sentinel.review approve <task_id>
python -m sentinel.review reject <task_id>
```

---

## 🔒 Cryptographic Audit Ledger & Verification

All request events and review resolutions are chained in `sentinel/audit_ledger.jsonl`. Each entry contains an HMAC-SHA256 hash computed over the previous entry's hash plus canonical entry JSON:

$$\text{Hash}_n = \text{HMAC-SHA256}\Big(\text{SecretKey}, \text{Hash}_{n-1} + \text{CanonicalJSON}(\text{Entry}_n)\Big)$$

### Verifying Ledger Integrity
```bash
# Verify ledger HMAC hash chain
python -m sentinel.verify_ledger

# Simulate payload tampering to test detection
python -m sentinel.verify_ledger --tamper
```

---

## 📂 Project Structure

```text
AgentTrust/
├── agent_a/                  # Requesting client with demo personas & attack tests
│   ├── card.py               # 7 AgentCard definitions (legitimate, attackers, alerts)
│   ├── client.py             # httpx-based JSON-RPC client
│   └── run.py                # Test runner: python -m agent_a.run <persona>
│
├── agent_b/                  # Downstream executing A2A agent
│   ├── card.py               # AgentCard with summarize_text + translate_text skills
│   ├── executor.py           # AgentExecutor with task implementations
│   └── server.py             # Target server on port 8001
│
├── sentinel/                 # Security Gateway Engine
│   ├── stages/               # Modular 5-stage pipeline components
│   │   ├── base.py           # StageResult dataclass & stage interface
│   │   ├── ip_throttle.py    # Stage 0: Identity-agnostic IP rate limiter
│   │   ├── signature_check.py# Stage 1: Cryptographic JWS verification
│   │   ├── rate_limiter.py   # Stage 2: Post-signature quota & cycle overflow
│   │   ├── rbac.py           # Stage 3: RBAC & fuzzy keyword stem alert trigger
│   │   └── injection_filter.py# Stage 4: Prompt injection regex filter
│   ├── pipeline.py           # 5-stage pipeline manager & HITL simulation controller
│   ├── middleware.py         # Starlette ASGI middleware & HTTP interceptor
│   ├── ledger.py             # HMAC-SHA256 hash-chained audit logger
│   ├── verify_ledger.py      # Audit ledger cryptographic integrity verification tool
│   ├── alert_queue.py        # HITL review queue persistence manager
│   ├── review.py             # CLI tool for human operators
│   ├── keys.py               # HMAC key registry & signature generator
│   └── server.py             # Combined server: Agent B protected by AgentTrust
│
├── demo/                     # Demonstration scripts
│   ├── run_demo.py           # 3-scenario projector demo
│   └── README.md             # Demo instructions
│
├── tests/                    # Unit tests
│   └── test_agent_b.py       # Basic Agent B verification
│
├── pipeline_ledger_walkthrough.md  # Detailed architecture walkthrough
├── alert_tier_walkthrough.md        # Alert tier & HITL walkthrough
├── rate_limiter_walkthrough.md      # Rate limiter & cycle overflow walkthrough
├── injection_filter_walkthrough.md  # Prompt injection scanner walkthrough
├── bugfix_walkthrough.md            # Security bugfix & deadlock resolution guide
├── README.md                 # Project documentation
└── .gitignore                # Git ignore configuration
```

---

## ⚡ Quick Start Guide

### 1. Install Dependencies

```bash
pip install "a2a-sdk[fastapi]" uvicorn httpx
```

### 2. Start the AgentTrust Server

```bash
python -m sentinel.server
```

### 3. Run Persona & Security Test Suite

In a separate terminal, execute individual personas or run the full test suite:

```bash
# Run legitimate agent request
python -m agent_a.run legitimate

# Run attack personas
python -m agent_a.run attacker-signature  # Forged signature
python -m agent_a.run attacker-capability # Undeclared capability
python -m agent_a.run attacker-skill      # Missing signature
python -m agent_a.run attacker-injection  # Prompt injection attack

# Run alert personas (HITL queue triggers)
python -m agent_a.run alert-persona     # Fuzzy stem match (Approved)
python -m agent_a.run alert-reject      # Fuzzy stem match (Rejected)

# Run rate limit & poisoning attack test runners
python -m agent_a.run flooder           # 10 rapid-fire requests
python -m agent_a.run poison-spoof      # Identity poisoning defense check

# Run all personas sequentially
python -m agent_a.run all
```

---

## 🧪 Security Guarantees & Bug Resolutions

1. **HITL Synchronous Deadlock Resolution**: Evaluates human review decisions cleanly via configurable `HITL_SIMULATION_MODE` (`auto` inline simulation for synchronous HTTP clients vs `manual` HTTP 202 Accepted status polling).
2. **Rate-Limit Identity Poisoning Defense**: Separates Stage 0 identity-agnostic IP rate limiting from Stage 2 agent rate limiting. Stage 2 evaluates rate quotas **only after Stage 1 verifies cryptographic signatures**, preventing unauthenticated attackers from exhausting victim agent quotas.

---

## 📜 License & Credits

Built for Google Agent-to-Agent (A2A) Protocol Research & EDI Mid-Semester Submission.
