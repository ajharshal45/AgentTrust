"""Human-in-the-loop alert queue for AgentTrust."""

from datetime import datetime, timezone
import json
from pathlib import Path

QUEUE_FILE_PATH = Path(__file__).parent / "alert_queue.json"


def load_queue(queue_path: Path = QUEUE_FILE_PATH) -> list[dict]:
    """Load all alerts from the alert queue JSON file."""
    if not queue_path.exists():
        return []
    try:
        with open(queue_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_queue(alerts: list[dict], queue_path: Path = QUEUE_FILE_PATH) -> None:
    """Save all alerts to the alert queue JSON file."""
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2)


def enqueue_for_review(
    agent_name: str,
    requested_task: str,
    reason: str,
    queue_path: Path = QUEUE_FILE_PATH,
) -> dict:
    """Enqueue a new request for human review.

    If an alert for this agent_name and requested_task already exists, returns it.
    Otherwise, creates a new pending alert entry.
    """
    alerts = load_queue(queue_path)

    # Check if a pending or decisioned alert already exists for this pair
    for item in reversed(alerts):
        if item.get("agent_name") == agent_name and item.get("requested_task") == requested_task:
            if item.get("status") == "pending":
                return item

    next_id = len(alerts) + 1
    new_alert = {
        "alert_id": next_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_name": agent_name,
        "requested_task": requested_task,
        "reason": reason,
        "status": "pending",
    }
    alerts.append(new_alert)
    save_queue(alerts, queue_path)
    return new_alert


def get_alert_status(
    agent_name: str,
    requested_task: str,
    queue_path: Path = QUEUE_FILE_PATH,
) -> str | None:
    """Get the latest review status ('pending', 'approved', 'rejected') for an agent + task pair."""
    alerts = load_queue(queue_path)
    for item in reversed(alerts):
        if item.get("agent_name") == agent_name and item.get("requested_task") == requested_task:
            return item.get("status")
    return None


def get_alert(alert_id: int, queue_path: Path = QUEUE_FILE_PATH) -> dict | None:
    """Get a specific alert by ID."""
    alerts = load_queue(queue_path)
    for item in alerts:
        if item.get("alert_id") == alert_id:
            return item
    return None


def update_alert_status(
    alert_id: int,
    new_status: str,
    queue_path: Path = QUEUE_FILE_PATH,
) -> bool:
    """Update the status of an alert to 'approved' or 'rejected'."""
    if new_status not in ("approved", "rejected", "pending"):
        return False

    alerts = load_queue(queue_path)
    updated = False
    for item in alerts:
        if item.get("alert_id") == alert_id:
            item["status"] = new_status
            item["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            updated = True
            break

    if updated:
        save_queue(alerts, queue_path)
    return updated


def list_alerts(
    status_filter: str | None = None,
    queue_path: Path = QUEUE_FILE_PATH,
) -> list[dict]:
    """List all alerts, optionally filtered by status."""
    alerts = load_queue(queue_path)
    if status_filter:
        return [a for a in alerts if a.get("status") == status_filter]
    return alerts
