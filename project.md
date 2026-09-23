# Project: A2ASentinel

## What this is
A college mid-semester project MVP demonstrating a runtime trust verification
layer for Google's Agent-to-Agent (A2A) protocol. Full research vision (ML
behavioral analysis, hash-chained tamper-evident logs, multi-instance
consensus) comes later — this build is a scoped-down, working demo for a
review panel in about a week.

## The problem being demonstrated
A2A's signed Agent Cards prove who issued a card, once, at the start. They
do not verify that an agent's ongoing behavior matches what it declared.
A2ASentinel sits between agents and checks both identity (signature) and
behavior (declared vs. requested capability) on every request, not just once.

## Scope for THIS build (MVP only)
Build only:
1. Two A2A agents that can talk to each other via the real `a2a-sdk`.
2. An interceptor layer ("A2ASentinel") sitting between them.
3. Signature verification check.
4. A simple, rule-based capability-match check (declared skills vs.
   requested task) — NOT machine learning yet.
5. A clear ALLOWED / BLOCKED decision output with reason, per request.
6. Two runnable demo scenarios (see demo_scenarios.md).

## Explicitly OUT of scope for this build
- ML-based anomaly detection (Isolation Forest etc.) — future phase
- Hash-chained / tamper-evident logging — future phase
- Multi-instance consensus / redundancy — future phase
- Moving Target Defense (rotating thresholds) — future phase
- Full A2ASecBench benchmark integration — future phase

Do not build ahead into these — keep the MVP lean and demoable.

## Success criteria for this MVP
- A legitimate agent's request passes through and reaches the target agent.
- A request with either (a) an invalid/tampered signature, or (b) a
  capability mismatch, gets blocked by the interceptor, with a printed
  reason, and never reaches the target agent.
- Both scenarios can be run and shown live, with clear console output.
