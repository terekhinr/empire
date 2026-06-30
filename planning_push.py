"""Web Push for Empire Tasks (VAPID + reminder delivery)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv

from planning_db import (
    delete_push_subscription,
    list_due_reminders_for_push,
    list_push_subscriptions,
    mark_reminder_pushed,
    prune_push_subscriptions,
    save_push_subscription,
)

load_dotenv()
logger = logging.getLogger("empire.planning_push")

VAPID_PUBLIC = os.getenv("PLANNING_VAPID_PUBLIC_KEY", "").strip()
VAPID_PRIVATE = os.getenv("PLANNING_VAPID_PRIVATE_KEY", "").strip()
VAPID_CONTACT = os.getenv("PLANNING_VAPID_CONTACT", "mailto:info@neverretire.ru").strip() or "mailto:info@neverretire.ru"


def push_configured() -> bool:
    return bool(VAPID_PUBLIC and VAPID_PRIVATE)


def vapid_public_key() -> str | None:
    return VAPID_PUBLIC or None


def upsert_subscription(sub: dict[str, Any], *, user_agent: str | None = None) -> int:
    endpoint = (sub.get("endpoint") or "").strip()
    keys = sub.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth = (keys.get("auth") or "").strip()
    if not endpoint or not p256dh or not auth:
        raise ValueError("invalid_subscription")
    return save_push_subscription(endpoint, p256dh, auth, user_agent=user_agent)


def remove_subscription(endpoint: str) -> bool:
    return delete_push_subscription(endpoint)


def _subscription_info(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "endpoint": row["endpoint"],
        "keys": {"p256dh": row["p256dh"], "auth": row["auth"]},
    }


def send_push(
    subscription: dict[str, Any],
    *,
    title: str,
    body: str,
    url: str = "/tasks/",
    tag: str | None = None,
    task_id: int | None = None,
    image: str | None = None,
) -> None:
    if not push_configured():
        raise RuntimeError("push_not_configured")
    from pywebpush import WebPushException, webpush

    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "url": url,
            "tag": tag or "empire-task",
            "task_id": task_id,
            "image": image,
        },
        ensure_ascii=False,
    )
    webpush(
        subscription_info=subscription,
        data=payload,
        vapid_private_key=VAPID_PRIVATE,
        vapid_claims={"sub": VAPID_CONTACT},
    )


def broadcast_push(
    *,
    title: str,
    body: str,
    url: str = "/tasks/",
    tag: str | None = None,
    task_id: int | None = None,
    image: str | None = None,
) -> dict[str, int]:
    subs = list_push_subscriptions()
    sent = 0
    gone = 0
    errors = 0
    for row in subs:
        try:
            send_push(
                _subscription_info(row),
                title=title,
                body=body,
                url=url,
                tag=tag,
                task_id=task_id,
                image=image,
            )
            sent += 1
        except Exception as exc:
            from pywebpush import WebPushException

            if isinstance(exc, WebPushException) and getattr(exc, "response", None) is not None:
                code = exc.response.status_code
                if code in (404, 410):
                    delete_push_subscription(row["endpoint"])
                    gone += 1
                    continue
            logger.warning("push failed endpoint=%s: %s", row["endpoint"][:48], exc)
            errors += 1
    prune_push_subscriptions()
    return {"sent": sent, "gone": gone, "errors": errors, "subs": len(subs)}


def process_due_reminder_pushes() -> dict[str, Any]:
    """Send Web Push for tasks with due remind_at (once per reminder)."""
    if not push_configured():
        return {"ok": False, "reason": "push_not_configured", "sent": 0}
    subs = list_push_subscriptions()
    if not subs:
        return {"ok": True, "reason": "no_subscriptions", "sent": 0, "tasks": 0}

    due = list_due_reminders_for_push()
    total_sent = 0
    for task in due:
        tid = int(task["id"])
        title = task.get("title") or "Напоминание"
        body = title
        if task.get("due_date"):
            body = f"{title} · {task['due_date']}"
        url = f"/tasks/?task={tid}"
        image = None
        if task.get("image_url"):
            image = f"https://neverretire.ru{task['image_url']}"
        stats = broadcast_push(
            title="Empire Tasks",
            body=body,
            url=url,
            tag=f"task-{tid}",
            task_id=tid,
            image=image,
        )
        if stats["sent"] > 0:
            mark_reminder_pushed(tid)
            total_sent += stats["sent"]
    return {"ok": True, "tasks": len(due), "sent": total_sent, "subscriptions": len(subs)}
