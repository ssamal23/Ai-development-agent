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

from src.agents.escalation_agent import (
    generate_escalation_pr,
    create_failure_report,
)

from src.agents.quality_gate_agent import (
    run_quality_gates,
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

from src.services.git_service import (
    GitService,
)

from src.services.code_graph_service import (
    CodeGraphService,
    CodeGraphUnavailableError,
)

from src.services.repository_provision_service import (
    RepositoryProvisionService,
)

from src.services.repository_index_service import (
    RepositoryIndexService,
)

from src.utils.ticket_category import (
    parse_ticket_category,
)


class TicketState(TypedDict):
    ticket: dict

    ticket_category: dict

    repository_url: str | None

    branch: str | None

    repo_config: dict

    analysis: str

    repository_structure: list[str]

    code_graph_status: dict

    relevant_files: list[dict]

    repository_context: list[dict]

    workspace_context: list[dict]

    implementation_plan: dict

    code_changes: dict

    previous_code_changes: dict

    quality_gate_result: dict

    verification_result: dict

    verification_attempts: int

    coding_attempts: int

    changed_files: list[str]

    code_apply_error: dict | None

    code_apply_attempts: int

    agent_created_files: list[str]

    test_result: dict

    test_attempts: int

    workspace_path: str

    git_branch: str

    git_result: dict

    pull_request: dict

    failure_report: dict

    escalation_pr: dict


def prepare_repository_node(
    state: TicketState,
):
    """
    Resolve which repository this ticket targets.

    When `repository_url` is provided, clone it (or
    fast-forward an existing clone) into a dedicated
    local directory and use that for every downstream
    step. When it is omitted, behavior is unchanged:
    the fixed `settings.repository_path` is used.
    """

    repo_config = (
        RepositoryProvisionService()
        .resolve(
            repository_url=state.get(
                "repository_url"
            ),
            branch=state.get("branch"),
        )
    )

    return {
        "repo_config": repo_config
    }


def analyze_ticket_node(
    state: TicketState,
):
    analysis = analyze_ticket(
        state["ticket"]
    )

    category = parse_ticket_category(
        state["ticket"].get("id")
    )

    return {
        "analysis": analysis,
        "ticket_category": category,
    }


def prepare_index_node(
    state: TicketState,
):
    """
    Keep the keyword repository index up to date for the
    resolved repository before anything searches it.

    Builds a full index on first run for this repository,
    incrementally updates it afterwards. Mirrors the
    behavior ensure_code_graph_node provides for the
    structural graph.
    """

    repo_config = state["repo_config"]

    index_service = RepositoryIndexService(
        repository_path=repo_config[
            "repository_path"
        ],
        index_directory=repo_config[
            "index_directory"
        ],
    )

    index_service.update_index()

    return {}


def repository_structure_node(
    state: TicketState,
):
    repo_config = state["repo_config"]

    structure = get_repository_structure(
        repository_path=repo_config[
            "repository_path"
        ],
        index_directory=repo_config[
            "index_directory"
        ],
    )

    return {
        "repository_structure": structure
    }


def ensure_code_graph_node(
    state: TicketState,
):
    """
    Keep the code-review-graph for the target repository
    up to date before searching it.

    Builds the graph on first run, incrementally updates
    it on every run after that. Failures are non-fatal:
    find_relevant_files falls back to keyword search when
    the graph is unavailable.
    """

    repo_config = state["repo_config"]

    try:
        status = (
            CodeGraphService.instance()
            .ensure_graph_built(
                repo_root=repo_config[
                    "repository_path"
                ]
            )
        )

    except CodeGraphUnavailableError as error:

        print(
            "code-review-graph unavailable, "
            f"continuing without it: {error}"
        )

        status = {
            "status": "unavailable",
            "error": str(error),
        }

    return {
        "code_graph_status": status
    }


def find_files_node(
    state: TicketState,
):
    repo_config = state["repo_config"]

    relevant_files = (
        find_relevant_files(
            state["ticket"],
            repository_path=repo_config[
                "repository_path"
            ],
            index_directory=repo_config[
                "index_directory"
            ],
        )
    )

    return {
        "relevant_files": relevant_files
    }


def read_files_node(
    state: TicketState,
):
    repo_config = state["repo_config"]

    repository_context = (
        read_relevant_files(
            state["relevant_files"],
            repository_path=repo_config[
                "repository_path"
            ],
            index_directory=repo_config[
                "index_directory"
            ],
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
        apply_error=state.get(
            "code_apply_error"
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


def quality_gate_node(
    state: TicketState,
):
    """
    Run quality gates (linting, security, type checks)
    before verification.

    Issues are flagged but don't block workflow.
    """

    workspace_path = state["workspace_path"]

    result = run_quality_gates(
        workspace_path=workspace_path
    )

    return {
        "quality_gate_result": (
            result.to_dict()
        )
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
        return "escalate_verification_failure"

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

    previously_created = set(
        state.get(
            "agent_created_files",
            [],
        )
    )

    try:
        changed_files = (
            service.apply_changes(
                changes,
                allow_recreate=(
                    previously_created
                ),
            )
        )

    except (
        FileExistsError,
        FileNotFoundError,
        ValueError,
    ) as error:

        return {
            "code_apply_error": {
                "error": str(error),
                "error_type": (
                    type(error).__name__
                ),
            },
            "code_apply_attempts": (
                state.get(
                    "code_apply_attempts",
                    0,
                ) + 1
            ),
        }

    newly_created = {
        change.file.replace(
            "\\",
            "/",
        )
        for change in changes
        if change.action == "create"
    }

    return {
        "changed_files": changed_files,
        "code_apply_error": None,
        "agent_created_files": sorted(
            previously_created
            | newly_created
        ),
    }


def apply_code_changes_router(
    state: TicketState,
):
    if not state.get("code_apply_error"):
        return "refresh_workspace_after_code"

    attempts = state.get(
        "code_apply_attempts",
        0,
    )

    if attempts >= 3:
        return "escalate_apply_failure"

    return "refresh_workspace_for_apply_retry"


def refresh_workspace_for_apply_retry_node(
    state: TicketState,
):
    """
    Refresh the workspace state after a failed
    apply attempt (e.g. create/modify mismatch),
    before sending the error back to the Coding
    Agent for another try.
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


def escalate_apply_failure_node(
    state: TicketState,
):
    """
    Escalate a persistent apply failure:
    the Coding Agent kept generating changes
    that CodeEditService cannot safely apply
    (e.g. wrong create/modify action) after
    3 attempts.
    """

    escalation_pr = generate_escalation_pr(
        ticket=state["ticket"],
        failure_type="apply",
        code_changes=state.get(
            "code_changes"
        ),
        attempts=state.get(
            "code_apply_attempts",
            0,
        ),
    )

    failure_report = create_failure_report(
        ticket=state["ticket"],
        failure_type="apply",
        coding_attempts=state.get(
            "coding_attempts",
            0,
        ),
        verification_attempts=state.get(
            "verification_attempts",
            0,
        ),
        test_attempts=state.get(
            "test_attempts",
            0,
        ),
    )

    return {
        "escalation_pr": escalation_pr,
        "failure_report": failure_report,
        "test_result": {
            "success": False,
            "final_status": "APPLY_ESCALATED",
            "message": (
                "Code changes could not be applied "
                "after 3 attempts. Escalation PR "
                "created for review."
            ),
            "apply_error": state.get(
                "code_apply_error"
            ),
        },
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
        return "escalate_test_failure"

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


def escalate_verification_failure_node(
    state: TicketState,
):
    """
    Escalate verification failure:
    - Generate failure report
    - Create draft PR with analysis
    """

    escalation_pr = generate_escalation_pr(
        ticket=state["ticket"],
        failure_type="verification",
        verification_result=state.get(
            "verification_result"
        ),
        code_changes=state.get(
            "code_changes"
        ),
        attempts=state.get(
            "verification_attempts",
            0,
        ),
    )

    failure_report = create_failure_report(
        ticket=state["ticket"],
        failure_type="verification",
        verification_result=state.get(
            "verification_result"
        ),
        coding_attempts=state.get(
            "coding_attempts",
            0,
        ),
        verification_attempts=state.get(
            "verification_attempts",
            0,
        ),
        test_attempts=state.get(
            "test_attempts",
            0,
        ),
    )

    return {
        "escalation_pr": escalation_pr,
        "failure_report": failure_report,
        "test_result": {
            "success": False,
            "final_status": (
                "VERIFICATION_ESCALATED"
            ),
            "message": (
                "Implementation failed verification "
                "after 3 attempts. "
                "Escalation PR created for review."
            ),
            "verification": (
                state[
                    "verification_result"
                ]
            ),
        }
    }


def escalate_test_failure_node(
    state: TicketState,
):
    """
    Escalate test failure:
    - Generate failure report
    - Create draft PR with analysis
    """

    escalation_pr = generate_escalation_pr(
        ticket=state["ticket"],
        failure_type="tests",
        test_result=state.get(
            "test_result"
        ),
        code_changes=state.get(
            "code_changes"
        ),
        attempts=state.get(
            "test_attempts",
            0,
        ),
    )

    failure_report = create_failure_report(
        ticket=state["ticket"],
        failure_type="tests",
        test_result=state.get(
            "test_result"
        ),
        coding_attempts=state.get(
            "coding_attempts",
            0,
        ),
        verification_attempts=state.get(
            "verification_attempts",
            0,
        ),
        test_attempts=state.get(
            "test_attempts",
            0,
        ),
    )

    return {
        "escalation_pr": escalation_pr,
        "failure_report": failure_report,
        "test_result": {
            **state["test_result"],
            "final_status": "TESTS_ESCALATED",
            "message": (
                "Tests failed after 3 attempts. "
                "Escalation PR created for review."
            ),
        }
    }


def conflict_resolution_node(
    state: TicketState,
):
    """
    Detect and handle merge conflicts
    before pushing to remote.

    Runs after apply_workspace_node, which has already
    synced changes into the real repository AND deleted
    the temporary workspace. Conflicts (against the
    remote) can only occur in the real repository - the
    scratch workspace no longer exists at this point.
    """

    repo_config = state["repo_config"]

    git_service = GitService(
        repository_path=repo_config[
            "repository_path"
        ]
    )

    # Check for conflicts
    conflicts = (
        git_service.detect_conflicts()
    )

    if not conflicts:
        return {
            "git_result": {
                "conflict_detection": "PASS",
                "conflicts": [],
                "message": "No conflicts detected",
            }
        }

    # Try to auto-resolve with "ours" strategy
    # (keep ai-agent changes)
    resolution = (
        git_service
        .resolve_conflicts_auto(
            strategy="ours"
        )
    )

    if resolution["success"]:
        return {
            "git_result": {
                "conflict_detection": "RESOLVED",
                "conflicts": conflicts,
                "message": (
                    f"Resolved {len(conflicts)} "
                    "conflicts using ours strategy"
                ),
                "resolution_strategy": "ours",
            }
        }

    else:
        return {
            "git_result": {
                "conflict_detection": "FAILED",
                "conflicts": conflicts,
                "message": (
                    f"Failed to resolve {len(conflicts)} "
                    "conflicts"
                ),
                "error": resolution.get("error"),
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
    repo_config = state["repo_config"]

    workspace_service = (
        WorkspaceService(
            repository_path=repo_config[
                "repository_path"
            ]
        )
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
    repo_config = state["repo_config"]

    branch = create_git_branch(
        ticket=state["ticket"],
        repository_path=repo_config[
            "repository_path"
        ],
    )

    return {
        "git_branch": branch
    }


def apply_workspace_node(
    state: TicketState,
):
    repo_config = state["repo_config"]

    workspace_service = (
        WorkspaceService(
            repository_path=repo_config[
                "repository_path"
            ]
        )
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
    repo_config = state["repo_config"]

    result = commit_and_push(
        ticket=state["ticket"],
        branch_name=state[
            "git_branch"
        ],
        repository_path=repo_config[
            "repository_path"
        ],
    )

    return {
        "git_result": result
    }


def create_pull_request_node(
    state: TicketState,
):
    repo_config = state["repo_config"]

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
        repository_path=repo_config[
            "repository_path"
        ],
        owner=repo_config["owner"],
        repo_name=repo_config[
            "repo_name"
        ],
        base_branch=repo_config[
            "base_branch"
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
        "prepare_repository",
        prepare_repository_node,
    )

    graph.add_node(
        "prepare_index",
        prepare_index_node,
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
        "ensure_code_graph",
        ensure_code_graph_node,
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
        "quality_gate",
        quality_gate_node,
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
        "refresh_workspace_for_apply_retry",
        refresh_workspace_for_apply_retry_node,
    )

    graph.add_node(
        "escalate_apply_failure",
        escalate_apply_failure_node,
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
        "escalate_verification_failure",
        escalate_verification_failure_node,
    )

    graph.add_node(
        "escalate_test_failure",
        escalate_test_failure_node,
    )

    graph.add_node(
        "conflict_resolution",
        conflict_resolution_node,
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
        "prepare_repository",
    )

    graph.add_edge(
        "prepare_repository",
        "prepare_index",
    )

    graph.add_edge(
        "prepare_index",
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
        "ensure_code_graph",
    )

    graph.add_edge(
        "ensure_code_graph",
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
        "quality_gate",
    )

    graph.add_edge(
        "quality_gate",
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
            "escalate_verification_failure": (
                "escalate_verification_failure"
            ),
        },
    )

    graph.add_edge(
        "refresh_workspace_for_retry",
        "generate_code",
    )

    graph.add_conditional_edges(
        "apply_code_changes",
        apply_code_changes_router,
        {
            "refresh_workspace_after_code": (
                "refresh_workspace_after_code"
            ),
            "refresh_workspace_for_apply_retry": (
                "refresh_workspace_for_apply_retry"
            ),
            "escalate_apply_failure": (
                "escalate_apply_failure"
            ),
        },
    )

    graph.add_edge(
        "refresh_workspace_for_apply_retry",
        "generate_code",
    )

    graph.add_edge(
        "escalate_apply_failure",
        END,
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
            "escalate_test_failure": (
                "escalate_test_failure"
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
        "conflict_resolution",
    )

    graph.add_edge(
        "conflict_resolution",
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

    graph.add_edge(
        "escalate_verification_failure",
        END,
    )

    graph.add_edge(
        "escalate_test_failure",
        END,
    )

    return graph.compile()