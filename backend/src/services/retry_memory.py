import threading
from typing import Any

_lock = threading.Lock()
_last_failure: dict[str, dict[str, Any]] = {}


def remember_failure(
    ticket_id: str,
    verification_result: dict | None,
    test_result: dict | None,
) -> None:
    """
    Record the verification/test failure reasons from a
    ticket run that did not end in a merged PR, so the next
    retry's Coding Agent starts already knowing what to fix
    instead of rediscovering the same mistake from scratch.
    """

    with _lock:
        _last_failure[ticket_id] = {
            "verification_result": verification_result,
            "test_result": test_result,
        }


def get_last_failure(
    ticket_id: str,
) -> dict[str, Any] | None:
    with _lock:
        return _last_failure.get(ticket_id)


def clear(ticket_id: str) -> None:
    with _lock:
        _last_failure.pop(ticket_id, None)
