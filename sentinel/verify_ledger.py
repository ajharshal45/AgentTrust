"""Audit Ledger Verification CLI tool.

Usage:
    python -m sentinel.verify_ledger
    python -m sentinel.verify_ledger --tamper
"""

import json
import sys
from pathlib import Path

from sentinel.ledger import LEDGER_FILE_PATH, verify_chain


def tamper_ledger(ledger_path: Path = LEDGER_FILE_PATH) -> bool:
    """Manually corrupts one entry in the ledger file for demonstration purposes."""
    if not ledger_path.exists():
        print(f"Error: Ledger file {ledger_path} does not exist.")
        return False

    lines = []
    with open(ledger_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        print(f"Error: Ledger file {ledger_path} is empty.")
        return False

    # Tamper with entry (modify requested_task field without recomputing entry_hash)
    idx_to_tamper = len(lines) - 1
    entry = json.loads(lines[idx_to_tamper])

    entry["requested_task"] = entry.get("requested_task", "") + "_TAMPERED"

    lines[idx_to_tamper] = json.dumps(entry, separators=(",", ":"))

    with open(ledger_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"[DEMO] Manually corrupted entry #{idx_to_tamper + 1} in audit_ledger.jsonl")
    return True


def main():
    tamper_mode = "--tamper" in sys.argv

    if tamper_mode:
        print("--- Audit Ledger Verification (with --tamper demo) ---")
        original_content = None
        if LEDGER_FILE_PATH.exists():
            with open(LEDGER_FILE_PATH, "r", encoding="utf-8") as f:
                original_content = f.read()

        if not tamper_ledger():
            sys.exit(1)

        try:
            valid, result_msg = verify_chain()
            print(f"Verification Result: {result_msg}")
            if not valid:
                print(">> SUCCESS: Audit ledger correctly detected cryptographic tampering!")
            else:
                print(">> ERROR: Tamper detection failed.")
                sys.exit(1)
        finally:
            if original_content is not None:
                with open(LEDGER_FILE_PATH, "w", encoding="utf-8") as f:
                    f.write(original_content)
                print("[DEMO] Ledger automatically restored to valid cryptographic state.")
        sys.exit(0)
    else:
        print("--- Audit Ledger Verification ---")
        valid, result_msg = verify_chain()
        print(f"Verification Result: {result_msg}")
        if valid:
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
