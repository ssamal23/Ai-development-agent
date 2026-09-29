import threading
import uuid
from datetime import datetime, timezone
from typing import Any

STAGE_ORDER = ["Plan", "Code", "Test", "Build", "PR"]

# Maps every ticket_workflow.py graph node to one of the
# 5 stages shown in the frontend progress tracker. Several
# nodes bucket into the same stage (e.g. the retry/refresh
# nodes around coding all show as "Code").
NODE_STAGE = {
    "prepare_repository": "Plan",
    "prepare_index": "Plan",
    "create_workspace": "Plan",
    "analyze_ticket": "Plan",
    "repository_structure": "Plan",
    "ensure_code_graph": "Plan",
    "find_relevant_files": "Plan",
    "read_relevant_files": "Plan",
    "create_plan": "Plan",
    "generate_code": "Code",
    "quality_gate": "Code",
    "verify_code": "Code",
    "refresh_workspace_for_retry": "Code",
    "apply_code_changes": "Code",
    "refresh_workspace_for_apply_retry": "Code",
    "refresh_workspace_after_code": "Code",
    "escalate_apply_failure": "Code",
    "escalate_verification_failure": "Code",
    "verification_failed": "Code",
    "run_tests": "Test",
    "refresh_workspace_after_test_failure": "Test",
    "tests_passed": "Test",
    "tests_failed": "Test",
    "escalate_test_failure": "Test",
    "create_git_branch": "Build",
    "apply_workspace": "Build",
    "conflict_resolution": "Build",
    "git_commit_push": "PR",
    "create_pull_request": "PR",
}

# Nodes that mean this stage failed rather than progressed.
FAILURE_NODES = {
    "escalate_apply_failure",
    "escalate_verification_failure",
    "escalate_test_failure",
    "tests_failed",
    "verification_failed",
}

NODE_LABEL = {
    "prepare_repository": "Preparing repository",
    "prepare_index": "Indexing repository",
    "create_workspace": "Setting up workspace",
    "analyze_ticket": "Analyzing ticket",
    "repository_structure": "Scanning repository",
    "ensure_code_graph": "Building code graph",
    "find_relevant_files": "Finding relevant files",
    "read_relevant_files": "Reading files",
    "create_plan": "Planning",
    "generate_code": "Coding",
    "quality_gate": "Running quality checks",
    "verify_code": "Verifying",
    "refresh_workspace_for_retry": "Coding",
    "apply_code_changes": "Applying changes",
    "refresh_workspace_for_apply_retry": "Coding",
    "refresh_workspace_after_code": "Coding",
    "run_tests": "Running tests",
    "refresh_workspace_after_test_failure": "Coding",
    "tests_passed": "Tests passed",
    "tests_failed": "Tests failed",
    "create_git_branch": "Creating branch",
    "apply_workspace": "Building",
    "conflict_resolution": "Resolving conflicts",
    "git_commit_push": "Pushing changes",
    "create_pull_request": "Creating pull request",
    "escalate_apply_failure": "Escalated: changes could not be applied",
    "escalate_verification_failure": "Escalated: verification failed",
    "escalate_test_failure": "Escalated: tests failed",
    "verification_failed": "Verification failed",
}

_lock = threading.Lock()
_sessions: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_session(ticket_id: str, title: str) -> str:
    session_id = f"S-{uuid.uuid4().hex[:8]}"

    with _lock:
        _sessions[ticket_id] = {
            "session_id": session_id,
            "ticket_id": ticket_id,
            "title": title,
            "branch": None,
            "status_label": "Starting",
            "stages": [
                {"name": name, "status": "pending"}
                for name in STAGE_ORDER
            ],
            "updated_at": _now(),
            "done": False,
            "error": None,
            "result": None,
        }

    return session_id


def record_node(ticket_id: str, node_name: str, delta: dict) -> None:
    stage_name = NODE_STAGE.get(node_name)

    if stage_name is None:
        return

    with _lock:
        session = _sessions.get(ticket_id)

        if session is None:
            return

        stage_index = STAGE_ORDER.index(stage_name)
        is_failure = node_name in FAILURE_NODES

        for index, stage in enumerate(session["stages"]):
            if index < stage_index and stage["status"] not in (
                "done",
                "error",
            ):
                stage["status"] = "done"
            elif index == stage_index:
                stage["status"] = (
                    "error" if is_failure else "running"
                )

        branch = delta.get("git_branch")

        if branch:
            session["branch"] = branch

        session["status_label"] = NODE_LABEL.get(
            node_name,
            node_name,
        )
        session["updated_at"] = _now()


def finish_session(ticket_id: str, result: dict) -> None:
    with _lock:
        session = _sessions.get(ticket_id)

        if session is None:
            return

        any_error = any(
            stage["status"] == "error"
            for stage in session["stages"]
        )

        if not any_error:
            for stage in session["stages"]:
                if stage["status"] != "done":
                    stage["status"] = "done"

        session["done"] = True
        session["result"] = result
        session["status_label"] = (
            "Failed" if any_error else "Completed"
        )
        session["updated_at"] = _now()


def fail_session(ticket_id: str, error: str) -> None:
    with _lock:
        session = _sessions.get(ticket_id)

        if session is None:
            return

        stages = session["stages"]

        # An exception raised inside a node happens before that
        # node returns, so its "updates" stream event never
        # fires and record_node() never sees it. The last stage
        # marked "running" is really the last stage that FINISHED
        # successfully (its node returned); the crash happened in
        # whichever stage comes right after it.
        failed_index = next(
            (
                index
                for index, stage in enumerate(stages)
                if stage["status"] == "pending"
            ),
            None,
        )

        if failed_index is not None:
            if (
                failed_index > 0
                and stages[failed_index - 1]["status"] == "running"
            ):
                stages[failed_index - 1]["status"] = "done"

            stages[failed_index]["status"] = "error"

        else:
            for stage in reversed(stages):
                if stage["status"] != "done":
                    stage["status"] = "error"
                    break

        session["done"] = True
        session["error"] = error
        session["status_label"] = "Failed"
        session["updated_at"] = _now()


def get_session(ticket_id: str) -> dict | None:
    with _lock:
        session = _sessions.get(ticket_id)

        return (
            None
            if session is None
            else {
                **session,
                "stages": [
                    dict(stage)
                    for stage in session["stages"]
                ],
            }
        )
