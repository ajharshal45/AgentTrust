"""Append-only, HMAC-SHA256 hash-chained audit logger for AgentTrust."""

from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path

from sentinel.keys import DEMO_SECRET_KEY

LEDGER_FILE_PATH = Path(__file__).parent / "audit_ledger.jsonl"


def _canonical_data_string(
    timestamp: str,
    agent_name: str,
    requested_task: str,
    decision: str,
    reason: str,
) -> str:
    """Create a deterministic JSON string representing entry fields."""
    entry_dict = {
        "agent_name": agent_name,
        "decision": decision,
        "reason": reason,
        "requested_task": requested_task,
        "timestamp": timestamp,
    }
    return json.dumps(entry_dict, separators=(",", ":"), sort_keys=True)


def compute_entry_hash(
    timestamp: str,
    agent_name: str,
    requested_task: str,
    decision: str,
    reason: str,
    previous_entry_hash: str,
) -> str:
    """Compute HMAC-SHA256: HMAC-SHA256(secret_key, canonical_data + previous_entry_hash)."""
    canonical_data = _canonical_data_string(
        timestamp, agent_name, requested_task, decision, reason
    )
    payload = f"{canonical_data}:{previous_entry_hash}".encode("utf-8")
    return hmac.new(DEMO_SECRET_KEY, payload, hashlib.sha256).hexdigest()


def get_last_entry_hash(ledger_path: Path = LEDGER_FILE_PATH) -> str:
    """Get the entry_hash of the last line in the ledger file, or empty string if empty/nonexistent."""
    if not ledger_path.exists():
        return ""

    last_line = ""
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last_line = line

    if not last_line:
        return ""

    try:
        data = json.loads(last_line)
        return data.get("entry_hash", "")
    except Exception:
        return ""


def log_decision(
    agent_name: str,
    requested_task: str,
    decision: str,
    reason: str = "",
    ledger_path: Path = LEDGER_FILE_PATH,
) -> dict:
    """Append a new hash-chained decision record to the audit ledger.

    Returns the logged entry dictionary.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    previous_entry_hash = get_last_entry_hash(ledger_path)

    entry_hash = compute_entry_hash(
        timestamp=timestamp,
        agent_name=agent_name,
        requested_task=requested_task,
        decision=decision,
        reason=reason,
        previous_entry_hash=previous_entry_hash,
    )

    entry = {
        "timestamp": timestamp,
        "agent_name": agent_name,
        "requested_task": requested_task,
        "decision": decision,
        "reason": reason,
        "entry_hash": entry_hash,
    }

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")

    return entry


def verify_chain(ledger_path: Path = LEDGER_FILE_PATH) -> tuple[bool, str]:
    """Verify the cryptographic integrity of the audit ledger hash chain.

    Walks every entry from line 1 (1-indexed), recomputes each hash from scratch,
    confirms it matches the stored entry_hash AND correctly chains to the previous entry hash.

    Returns:
        (True, "VALID LEDGER") if the entire chain is cryptographically intact.
        (False, "TAMPER DETECTED at entry N") if verification fails at entry N.
    """
    if not ledger_path.exists():
        return True, "VALID LEDGER"

    previous_entry_hash = ""
    entry_number = 0

    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            entry_number += 1
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return False, f"TAMPER DETECTED at entry {entry_number}"

            required_fields = [
                "timestamp",
                "agent_name",
                "requested_task",
                "decision",
                "reason",
                "entry_hash",
            ]
            if not all(field in entry for field in required_fields):
                return False, f"TAMPER DETECTED at entry {entry_number}"

            stored_hash = entry["entry_hash"]
            expected_hash = compute_entry_hash(
                timestamp=entry["timestamp"],
                agent_name=entry["agent_name"],
                requested_task=entry["requested_task"],
                decision=entry["decision"],
                reason=entry["reason"],
                previous_entry_hash=previous_entry_hash,
            )

            if not hmac.compare_digest(stored_hash, expected_hash):
                return False, f"TAMPER DETECTED at entry {entry_number}"

            previous_entry_hash = stored_hash

    return True, "VALID LEDGER"
