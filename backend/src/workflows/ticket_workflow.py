from pathlib import Path
from typing import TypedDict

from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from src.agents.ticket_agent import (
    analyze_ticket,
)

from src.agents.repository_agent import (
    find_relevant_files,
    read_relevant_files,
    get_repository_structure,
)

from src.agents.planning_agent import (
    create_implementation_plan,
)

from src.agents.coding_agent import (
    generate_code_changes,
)

from src.agents.verification_agent import (
    verify_implementation,
)

from src.agents.test_agent import (
    run_tests,
)

from src.agents.git_agent import (
    create_git_branch,
    commit_and_push,
)

from src.agents.pr_agent import (
    create_pull_request,
)

from src.models.code_change import (
    CodeChange,
)

from src.services.code_edit_service import (
    CodeEditService,
)

from src.services.workspace_service import (
    WorkspaceService,
)


class TicketState(TypedDict):
    ticket: dict

    analysis: str

    repository_structure: list[str]

    relevant_files: list[dict]

    repository_context: list[dict]

    workspace_context: list[dict]

    implementation_plan: dict

    code_changes: dict

    previous_code_changes: dict

    verification_result: dict

    verification_attempts: int

    coding_attempts: int

    changed_files: list[str]

    test_result: dict

    test_attempts: int

    workspace_path: str

    git_branch: str

    git_result: dict

    pull_request: dict


def analyze_ticket_node(
    state: TicketState,
):
    analysis = analyze_ticket(
        state["ticket"]
    )

    return {
        "analysis": analysis
    }


def repository_structure_node(
    state: TicketState,
):
    structure = (
        get_repository_structure()
    )

    return {
        "repository_structure": structure
    }


def find_files_node(
    state: TicketState,
):
    relevant_files = (
        find_relevant_files(
            state["ticket"]
        )
    )

    return {
        "relevant_files": relevant_files
    }


def read_files_node(
    state: TicketState,
):
    repository_context = (
        read_relevant_files(
            state["relevant_files"]
        )
    )

    return {
        "repository_context": (
            repository_context
        ),
        "workspace_context": (
            repository_context
        ),
    }


def planning_node(
    state: TicketState,
):
    plan = create_implementation_plan(
        ticket=state["ticket"],
        repository_structure=state[
            "repository_structure"
        ],
        relevant_files=state[
            "repository_context"
        ],
    )

    return {
        "implementation_plan": plan
    }


def coding_node(
    state: TicketState,
):
    workspace_context = state.get(
        "workspace_context",
        [],
    )

    previous_code_changes = state.get(
        "previous_code_changes",
        {},
    )

    result = generate_code_changes(
        ticket=state["ticket"],
        implementation_plan=state[
            "implementation_plan"
        ],
        repository_context=state[
            "repository_context"
        ],
        verification_result=state.get(
            "verification_result"
        ),
        test_result=state.get(
            "test_result"
        ),
        workspace_context=workspace_context,
        previous_code_changes=(
            previous_code_changes
        ),
    )

    code_changes = (
        result.model_dump()
    )

    return {
        "code_changes": code_changes,

        "previous_code_changes": (
            code_changes
        ),

        "coding_attempts": (
            state.get(
                "coding_attempts",
                0,
            ) + 1
        ),
    }


def verification_node(
    state: TicketState,
):
    result = verify_implementation(
        ticket=state["ticket"],
        implementation_plan=state[
            "implementation_plan"
        ],
        code_changes=state[
            "code_changes"
        ],
    )

    return {
        "verification_result": result
    }


def verification_router(
    state: TicketState,
):
    result = state[
        "verification_result"
    ]

    if result["status"] == "PASS":
        return "apply_code_changes"

    attempts = state.get(
        "verification_attempts",
        0,
    )

    if attempts >= 3:
        return "verification_failed"

    return "refresh_workspace_for_retry"


def refresh_workspace_for_retry_node(
    state: TicketState,
):
    """
    Refresh the latest workspace state before
    sending another implementation attempt to
    the Coding Agent.
    """

    workspace_service = (
        WorkspaceService()
    )

    workspace_service.workspace_path = (
        Path(
            state["workspace_path"]
        )
    )

    current_paths = set()

    for file in state.get(
        "relevant_files",
        [],
    ):
        path = file.get("path")

        if path:
            current_paths.add(path)

    for change in state.get(
        "code_changes",
        {},
    ).get(
        "changes",
        [],
    ):
        path = change.get("file")

        if path:
            current_paths.add(path)

    workspace_context = (
        workspace_service
        .get_files_context(
            list(current_paths)
        )
    )

    return {
        "workspace_context": (
            workspace_context
        ),
        "verification_attempts": (
            state.get(
                "verification_attempts",
                0,
            ) + 1
        ),
    }


def apply_code_changes_node(
    state: TicketState,
):
    workspace_path = state[
        "workspace_path"
    ]

    changes = [
        CodeChange(**change)
        for change in state[
            "code_changes"
        ]["changes"]
    ]

    service = CodeEditService(
        repository_path=workspace_path
    )

    changed_files = (
        service.apply_changes(
            changes
        )
    )

    return {
        "changed_files": changed_files
    }


def refresh_workspace_after_code_node(
    state: TicketState,
):
    """
    Refresh the latest implementation from
    the workspace after Coding Agent changes
    have been applied.

    This state is then used by the Test retry
    path and subsequent Coding Agent attempts.
    """

    workspace_service = (
        WorkspaceService()
    )

    workspace_service.workspace_path = (
        Path(
            state["workspace_path"]
        )
    )

    paths = set()

    for file in state.get(
        "relevant_files",
        [],
    ):
        path = file.get("path")

        if path:
            paths.add(path)

    for change in state.get(
        "code_changes",
        {},
    ).get(
        "changes",
        [],
    ):
        path = change.get("file")

        if path:
            paths.add(path)

    workspace_context = (
        workspace_service
        .get_files_context(
            list(paths)
        )
    )

    return {
        "workspace_context": (
            workspace_context
        )
    }


def test_node(
    state: TicketState,
):
    workspace_path = state[
        "workspace_path"
    ]

    result = run_tests(
        repository_path=workspace_path
    )

    return {
        "test_result": result,

        "test_attempts": (
            state.get(
                "test_attempts",
                0,
            ) + 1
        ),
    }


def test_router(
    state: TicketState,
):
    result = state[
        "test_result"
    ]

    if result["success"]:
        return "tests_passed"

    attempts = state.get(
        "test_attempts",
        0,
    )

    if attempts >= 3:
        return "tests_failed"

    return "refresh_workspace_after_test_failure"


def refresh_workspace_after_test_failure_node(
    state: TicketState,
):
    """
    Refresh the exact latest workspace state
    after a test failure.

    The next Coding Agent attempt receives
    the current implementation instead of
    stale repository-index content.
    """

    workspace_service = (
        WorkspaceService()
    )

    workspace_service.workspace_path = (
        Path(
            state["workspace_path"]
        )
    )

    paths = set()

    for file in state.get(
        "relevant_files",
        [],
    ):
        path = file.get("path")

        if path:
            paths.add(path)

    for change in state.get(
        "code_changes",
        {},
    ).get(
        "changes",
        [],
    ):
        path = change.get("file")

        if path:
            paths.add(path)

    workspace_context = (
        workspace_service
        .get_files_context(
            list(paths)
        )
    )

    return {
        "workspace_context": (
            workspace_context
        )
    }


def tests_passed_node(
    state: TicketState,
):
    return {
        "test_result": {
            **state["test_result"],
            "final_status": "PASSED",
        }
    }


def tests_failed_node(
    state: TicketState,
):
    return {
        "test_result": {
            **state["test_result"],
            "final_status": "FAILED",
            "message": (
                "Tests failed after "
                "3 attempts."
            ),
        }
    }


def verification_failed_node(
    state: TicketState,
):
    return {
        "test_result": {
            "success": False,
            "final_status": (
                "VERIFICATION_FAILED"
            ),
            "message": (
                "Implementation failed story "
                "verification after 3 attempts."
            ),
            "verification": (
                state[
                    "verification_result"
                ]
            ),
        }
    }


def create_workspace_node(
    state: TicketState,
):
    workspace_service = (
        WorkspaceService()
    )

    workspace_path = (
        workspace_service
        .create_workspace()
    )

    return {
        "workspace_path": str(
            workspace_path
        )
    }


def create_git_branch_node(
    state: TicketState,
):
    branch = create_git_branch(
        ticket=state["ticket"],
    )

    return {
        "git_branch": branch
    }


def apply_workspace_node(
    state: TicketState,
):
    workspace_service = (
        WorkspaceService()
    )

    workspace_service.workspace_path = (
        Path(
            state["workspace_path"]
        )
    )

    workspace_service.apply_workspace_to_repository()

    workspace_service.cleanup()

    return {}


def git_commit_push_node(
    state: TicketState,
):
    result = commit_and_push(
        ticket=state["ticket"],
        branch_name=state[
            "git_branch"
        ],
    )

    return {
        "git_result": result
    }


def create_pull_request_node(
    state: TicketState,
):
    result = create_pull_request(
        ticket=state["ticket"],
        branch_name=state[
            "git_branch"
        ],
        changed_files=state[
            "changed_files"
        ],
        verification_result=state[
            "verification_result"
        ],
        test_result=state[
            "test_result"
        ],
    )

    return {
        "pull_request": result
    }


def create_workflow():

    graph = StateGraph(
        TicketState
    )

    graph.add_node(
        "create_workspace",
        create_workspace_node,
    )

    graph.add_node(
        "analyze_ticket",
        analyze_ticket_node,
    )

    graph.add_node(
        "repository_structure",
        repository_structure_node,
    )

    graph.add_node(
        "find_relevant_files",
        find_files_node,
    )

    graph.add_node(
        "read_relevant_files",
        read_files_node,
    )

    graph.add_node(
        "create_plan",
        planning_node,
    )

    graph.add_node(
        "generate_code",
        coding_node,
    )

    graph.add_node(
        "verify_code",
        verification_node,
    )

    graph.add_node(
        "refresh_workspace_for_retry",
        refresh_workspace_for_retry_node,
    )

    graph.add_node(
        "apply_code_changes",
        apply_code_changes_node,
    )

    graph.add_node(
        "refresh_workspace_after_code",
        refresh_workspace_after_code_node,
    )

    graph.add_node(
        "run_tests",
        test_node,
    )

    graph.add_node(
        "refresh_workspace_after_test_failure",
        refresh_workspace_after_test_failure_node,
    )

    graph.add_node(
        "tests_passed",
        tests_passed_node,
    )

    graph.add_node(
        "tests_failed",
        tests_failed_node,
    )

    graph.add_node(
        "verification_failed",
        verification_failed_node,
    )

    graph.add_node(
        "apply_workspace",
        apply_workspace_node,
    )

    graph.add_node(
        "create_git_branch",
        create_git_branch_node,
    )

    graph.add_node(
        "git_commit_push",
        git_commit_push_node,
    )

    graph.add_node(
        "create_pull_request",
        create_pull_request_node,
    )

    graph.add_edge(
        START,
        "create_workspace",
    )

    graph.add_edge(
        "create_workspace",
        "analyze_ticket",
    )

    graph.add_edge(
        "analyze_ticket",
        "repository_structure",
    )

    graph.add_edge(
        "repository_structure",
        "find_relevant_files",
    )

    graph.add_edge(
        "find_relevant_files",
        "read_relevant_files",
    )

    graph.add_edge(
        "read_relevant_files",
        "create_plan",
    )

    graph.add_edge(
        "create_plan",
        "generate_code",
    )

    graph.add_edge(
        "generate_code",
        "verify_code",
    )

    graph.add_conditional_edges(
        "verify_code",
        verification_router,
        {
            "generate_code": (
                "generate_code"
            ),
            "apply_code_changes": (
                "apply_code_changes"
            ),
            "refresh_workspace_for_retry": (
                "refresh_workspace_for_retry"
            ),
            "verification_failed": (
                "verification_failed"
            ),
        },
    )

    graph.add_edge(
        "refresh_workspace_for_retry",
        "generate_code",
    )

    graph.add_edge(
        "apply_code_changes",
        "refresh_workspace_after_code",
    )

    graph.add_edge(
        "refresh_workspace_after_code",
        "run_tests",
    )

    graph.add_conditional_edges(
        "run_tests",
        test_router,
        {
            "refresh_workspace_after_test_failure": (
                "refresh_workspace_after_test_failure"
            ),
            "tests_passed": (
                "tests_passed"
            ),
            "tests_failed": (
                "tests_failed"
            ),
        },
    )

    graph.add_edge(
        "refresh_workspace_after_test_failure",
        "generate_code",
    )

    graph.add_edge(
        "tests_passed",
        "create_git_branch",
    )

    graph.add_edge(
        "create_git_branch",
        "apply_workspace",
    )

    graph.add_edge(
        "apply_workspace",
        "git_commit_push",
    )

    graph.add_edge(
        "git_commit_push",
        "create_pull_request",
    )

    graph.add_edge(
        "create_pull_request",
        END,
    )

    graph.add_edge(
        "tests_failed",
        END,
    )

    graph.add_edge(
        "verification_failed",
        END,
    )

    return graph.compile()