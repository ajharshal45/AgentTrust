"""Human-in-the-loop CLI reviewer for AgentTrust.

Usage:
    python -m sentinel.review               (lists pending review items)
    python -m sentinel.review approve <id>   (approves alert item <id>)
    python -m sentinel.review reject <id>    (rejects alert item <id>)
"""

import sys

from sentinel import alert_queue


def print_alerts(status: str = "pending") -> None:
    alerts = alert_queue.list_alerts(status_filter=status)
    print("=" * 65)
    print(f"  AgentTrust Human Review Queue [{status.upper()}]")
    print("=" * 65)
    if not alerts:
        print(f"  No {status} alerts in queue.")
    else:
        for a in alerts:
            print(f"  ID #{a['alert_id']} | Agent: {a['agent_name']} | Task: {a['requested_task']}")
            print(f"    Reason   : {a['reason']}")
            print(f"    Enqueued : {a['timestamp']}")
            print(f"    Status   : {a['status'].upper()}")
            print("-" * 65)
    print()


def main():
    args = sys.argv[1:]

    if not args:
        print_alerts("pending")
        print("Commands:")
        print("  python -m sentinel.review approve <id>")
        print("  python -m sentinel.review reject <id>")
        return

    command = args[0].lower()

    if command in ("approve", "reject"):
        if len(args) < 2:
            print(f"Error: Missing alert ID. Usage: python -m sentinel.review {command} <id>")
            sys.exit(1)

        try:
            alert_id = int(args[1])
        except ValueError:
            print(f"Error: Invalid alert ID '{args[1]}'. Must be an integer.")
            sys.exit(1)

        alert = alert_queue.get_alert(alert_id)
        if not alert:
            print(f"Error: Alert #{alert_id} not found.")
            sys.exit(1)

        new_status = "approved" if command == "approve" else "rejected"
        success = alert_queue.update_alert_status(alert_id, new_status)

        if success:
            action_label = "APPROVED" if command == "approve" else "REJECTED"
            print("=" * 65)
            print(f"  [HUMAN REVIEWER ACTION] Alert #{alert_id} -> {action_label}")
            print(f"  Agent   : {alert['agent_name']}")
            print(f"  Task    : {alert['requested_task']}")
            print(f"  Status  : {new_status.upper()}")
            print("=" * 65)
            print()
            print(f"Future requests for {alert['agent_name']} -> {alert['requested_task']} will now resolve to:")
            if command == "approve":
                print("  >> ALLOWED (Forwarded to Agent B)")
            else:
                print("  >> BLOCKED (Human Reviewer Rejected)")
            print()
        else:
            print(f"Error: Failed to update alert #{alert_id}.")
            sys.exit(1)
    else:
        print(f"Unknown command '{command}'.")
        print("Usage:")
        print("  python -m sentinel.review")
        print("  python -m sentinel.review approve <id>")
        print("  python -m sentinel.review reject <id>")
        sys.exit(1)


if __name__ == "__main__":
    main()
