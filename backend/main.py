import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.services.repository_index_service import (
    RepositoryIndexService,
)

from src.services.repository_service import (
    RepositoryService,
)

from src.services import session_tracker
from src.services import retry_memory
from src.services import observability
from src.services.token_usage import (
    TokenUsageHandler,
    current_ticket_id,
)

from src.workflows.ticket_workflow import (
    create_workflow,
)

app = FastAPI(
    title="AI Development Agent",
    version="0.9.0",
)

app.add_middleware(
    CORSMiddleware,
    # Vite falls back to the next free port (5174, 5175, ...)
    # whenever 5173 is already taken, so a fixed origin list
    # breaks the moment that happens. Allow any local dev
    # server port instead of chasing the actual port number.
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TicketRequest(BaseModel):
    ticket: dict
    repository_url: str | None = None
    branch: str | None = None


@app.get("/")
def root():
    return {"message": ("AI Development Agent is running")}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/repository/scan")
def scan_repository():

    service = RepositoryService()

    files = service.scan_repository()

    return {
        "total_files": len(files),
        "files": [file.model_dump() for file in files],
    }


@app.post("/repository/index")
def create_repository_index():

    service = RepositoryIndexService()

    index = service.index_repository()

    return {
        "message": ("Repository indexed successfully"),
        "repository": (index.repository_path),
        "commit": index.last_commit,
        "total_files": len(index.files),
    }


@app.post("/repository/update-index")
def update_repository_index():

    service = RepositoryIndexService()

    result = service.update_index()

    index = result["index"]

    changes = result["changes"]

    return {
        "message": ("Repository index updated"),
        "repository": (index.repository_path),
        "commit": index.last_commit,
        "total_files": len(index.files),
        "changes": changes,
    }


# Placeholder ticket source. Shaped like what a real
# Azure Boards / Jira integration would return, so the
# frontend and /api/agent/analyze can be built against a
# stable contract now and swapped to a real board later
# without changing either side.
MOCK_TICKETS = [
    {
        "id": "FRONT_DEV-001",
        "title": "Create Login Page",
        "description": (
            "Add a login page with email and password "
            "fields, following the existing app's layout "
            "and styling conventions."
        ),
        "acceptance_criteria": [
            "Login form has an email field and a password field",
            "Both fields are required",
            "Login button submits the form",
        ],
        "state": "Done",
        "priority": "High",
        "assignee": "Unassigned",
    },
    {
        "id": "ENH_FRONT_DEV-002",
        "title": "Redirect to home page on successful login with validation",
        "description": "The existing login page needs to authenticate the entered email and password. On a successful match, the user should be redirected to the home page. On a mismatch, the form should show an inline error message instead of redirecting, and the user should remain on the login page. NOTE: This is mock/demo authentication only — validate against a hardcoded email and password client-side. Do not build real backend authentication, hashing, or session/token handling as part of this ticket.",
        "acceptance_criteria": [
            "Login succeeds only when email is ssamal1@evoketechnologies.com and password is soumya@123",
            "Credential check is a simple client-side comparison (mock auth for demo purposes, not real security)",
            "On successful login, the user is redirected to the home page",
            "On incorrect email or password, an inline error message is shown (e.g. 'Invalid email or password')",
            "On failure, the user stays on the login page and the form retains the entered email (password field is cleared)",
            "Existing required-field validation (empty email/password) continues to work as before",
            "Error message clears once the user starts editing the fields again",
        ],
        "state": "Done",
        "priority": "High",
        "assignee": "Unassigned",
    },
    {
        "id": "FRONT_DEV-003",
        "title": "Create Home page component",
        "description": "Create a new Home page component matching the design in the linked Figma file. Follow the existing project's design system (colors, fonts, spacing, components) instead of the raw styling in the Figma file.",
        "acceptance_criteria": [
            "A Home page component is created matching the layout and content shown in the Figma design",
            "Styling reuses the existing project's design system rather than introducing new colors, fonts, or spacing",
        ],
        "state": "Done",
        "priority": "High",
        "assignee": "Unassigned",
        "design_reference": "https://www.figma.com/design/zYLrG4iGIyGCe4VdTjbAz0/Audit-test?node-id=0-1&t=2jLtKW7ozxX9Ow5Z-1",
    },
    {
        "id": "ENH_FRONT_DEV-007",
        "title": "Enhance Home page design to match Figma (full screen, Figma colors)",
        "description": "Enhance the existing Home page so its design matches the linked Figma frame. The page must fill the full browser window (full width and full height, no centered narrow container or outer gutters, and no unused blank space around the layout). Use the exact colors from the Figma design (backgrounds, text, borders, accents, active states) as well as its fonts, font sizes and corner radii, instead of the project's current theme colors. Keep the existing functionality and routing unchanged; this is a visual enhancement only.",
        "acceptance_criteria": [
            "The Home page layout fills the full screen: full viewport width and height, with no centered max-width container, outer margins or blank side gutters.",
            "Every color on the Home page (backgrounds, text, borders, buttons, active/selected states, icons) uses the exact hex values from the Figma design.",
            "Fonts, font sizes, font weights and corner radii match the Figma design.",
            "The layout, structure and content of the page match the Figma frame.",
            "Existing Home page functionality, navigation and logout continue to work as before.",
        ],
        "state": "New",
        "priority": "High",
        "assignee": "Unassigned",
        "design_reference": "https://www.figma.com/design/zYLrG4iGIyGCe4VdTjbAz0/Audit-test?node-id=9-17",
    },
    {
        "id": "BACK_DEV-002",
        "title": "Add product search API",
        "description": (
            "Add a backend endpoint that searches products " "by name or category."
        ),
        "acceptance_criteria": [
            "GET endpoint accepts a query parameter",
            "Returns matching products as JSON",
            "Returns an empty list when nothing matches",
        ],
        "state": "Done",
        "priority": "Medium",
        "assignee": "Unassigned",
    },
    {
        "id": "ENH_FRONT_DEV-005",
        "title": "Persist login session across page reloads and logout",
        "description": "Enhance the existing login functionality so that after a successful login, the user remains authenticated when the page is refreshed or the browser reloads. Currently, after a successful login the user is redirected to the home page, but refreshing the page sends the user back to the login page. The application should persist the mock login state on the client side and restore the authenticated state when the application starts. The user should be redirected to the login page only after explicitly clicking the Logout button. NOTE: This is mock/demo authentication only. Do not implement real backend authentication, JWT, session management, token refresh, or server-side authentication as part of this ticket.",
        "acceptance_criteria": [
            "After a successful login with the existing valid mock credentials, the user is redirected to the home page.",
            "The authenticated/mock login state is persisted on the client side so that it survives a browser page reload.",
            "When an authenticated user refreshes or reloads the home page, the user remains on the home page and is not redirected to the login page.",
            "When the application starts and a valid persisted mock login state exists, the user is treated as already logged in.",
            "If no authenticated login state exists, accessing the protected home page redirects the user to the login page.",
            "The Logout button clears the persisted login state.",
            "After logout, the user is redirected to the login page.",
            "After logout, refreshing the browser must not automatically authenticate the user again.",
            "After logout, accessing the home page directly must redirect the user to the login page.",
            "The existing login validation and mock credential check continue to work as before.",
            "The existing login page should not be shown again simply because the browser page was refreshed after a successful login.",
            "Do not introduce backend authentication, JWT tokens, password hashing, refresh tokens, or server-side session management.",
        ],
        "state": "New",
        "priority": "High",
        "assignee": "Unassigned",
    },
    {
        "id": "TEST-004",
        "title": "Add tests for checkout flow",
        "description": (
            "Add automated test coverage for the existing " "checkout flow."
        ),
        "acceptance_criteria": [
            "Covers the happy path checkout",
            "Covers empty cart checkout attempt",
        ],
        "state": "New",
        "priority": "Medium",
        "assignee": "Unassigned",
    },
    {
        "id": "BACK_DEV-005",
        "title": "Add order history endpoint",
        "description": ("Add a backend endpoint that returns a user's " "past orders."),
        "acceptance_criteria": [
            "GET endpoint returns orders for the current user",
            "Orders are sorted by most recent first",
        ],
        "state": "Done",
        "priority": "Medium",
        "assignee": "Unassigned",
    },
    {
        "id": "ENH_BACK_DEV-006",
        "title": "Add pagination to product listing API",
        "description": (
            "Extend the existing product listing endpoint "
            "with page/limit query parameters."
        ),
        "acceptance_criteria": [
            "Accepts page and limit query parameters",
            "Response includes total count",
        ],
        "state": "Done",
        "priority": "Low",
        "assignee": "Unassigned",
    },
]

# Placeholder current sprint. A real board integration
# would report this itself; there's no sprint concept yet
# without one.
CURRENT_SPRINT_NO = 12


@app.get("/api/tickets")
def list_tickets():
    """
    Return the ticket backlog plus sprint-level summary
    counts (completed / in progress / sprint number).

    Stands in for a real Azure Boards / Jira / GitHub
    Issues integration for now. The response shape is the
    same either way, so swapping in a real provider later
    only changes this function's implementation, not any
    caller.
    """

    completed_tickets_count = sum(
        1 for ticket in MOCK_TICKETS if ticket["state"] == "Done"
    )

    in_progress_tickets_count = sum(
        1 for ticket in MOCK_TICKETS if ticket["state"] == "In Progress"
    )

    return {
        "total_tickets": len(MOCK_TICKETS),
        "completed_tickets_count": completed_tickets_count,
        "in_progress_tickets_count": in_progress_tickets_count,
        "sprint_no": CURRENT_SPRINT_NO,
        "tickets": MOCK_TICKETS,
    }


def _build_analysis_response(state: dict) -> dict:
    return {
        "ticket": state["ticket"],
        "repo_config": state["repo_config"],
        "ticket_category": state["ticket_category"],
        "analysis": state["analysis"],
        "repository_structure": state["repository_structure"],
        "relevant_files": state["relevant_files"],
        "implementation_plan": state["implementation_plan"],
        "code_changes": state["code_changes"],
        "verification_result": state["verification_result"],
        "verification_attempts": state["verification_attempts"],
        "coding_attempts": state["coding_attempts"],
        "changed_files": state["changed_files"],
        "test_result": state["test_result"],
        "test_attempts": state["test_attempts"],
        "design_review": state.get("design_review_result"),
        "workspace_path": state["workspace_path"],
        "git_branch": state["git_branch"],
        "git_result": state["git_result"],
        "pull_request": state["pull_request"],
    }


def _run_ticket_workflow(
    ticket_id: str,
    initial_state: dict,
) -> None:

    current_ticket_id.set(ticket_id)

    workflow = create_workflow()

    final_state = dict(initial_state)

    ticket_title = initial_state["ticket"].get(
        "title",
        "",
    )

    try:
        with observability.trace_ticket_run(
            ticket_id,
            ticket_title,
        ) as trace_id:

            for update in workflow.stream(
                initial_state,
                stream_mode="updates",
                config={
                    "callbacks": [
                        *observability.get_langchain_callbacks(),
                        TokenUsageHandler(ticket_id),
                    ],
                },
            ):
                for node_name, delta in update.items():

                    if not isinstance(delta, dict):
                        continue

                    final_state.update(delta)

                    session_tracker.record_node(
                        ticket_id,
                        node_name,
                        delta,
                    )

            observability.update_current_trace_output(
                {
                    "verification_status": (
                        final_state.get(
                            "verification_result",
                            {},
                        ).get("status")
                    ),
                    "test_status": (
                        final_state.get(
                            "test_result",
                            {},
                        ).get("final_status")
                    ),
                    "pull_request_url": (
                        final_state.get(
                            "pull_request",
                            {},
                        ).get("url")
                    ),
                }
            )

        observability.score_ticket_run(
            trace_id,
            final_state,
        )

        if (
            final_state.get(
                "test_result",
                {},
            ).get("final_status")
            == "PASSED"
        ):
            # Verification and tests actually passed this
            # run - any downstream PR failure (e.g. a GitHub
            # token permission issue) isn't something a code
            # retry would fix, so there's nothing to remember.
            retry_memory.clear(ticket_id)
        else:
            retry_memory.remember_failure(
                ticket_id,
                verification_result=final_state.get("verification_result"),
                test_result=final_state.get("test_result"),
            )

        session_tracker.finish_session(
            ticket_id,
            result=_build_analysis_response(final_state),
        )

    except Exception as error:

        session_tracker.fail_session(
            ticket_id,
            error=str(error),
        )


@app.post("/api/agent/analyze")
def analyze_ticket_endpoint(
    request: TicketRequest,
):

    ticket_id = str(
        request.ticket.get(
            "id",
            "ticket",
        )
    )

    session_id = session_tracker.start_session(
        ticket_id=ticket_id,
        title=request.ticket.get(
            "title",
            "",
        ),
    )

    # If a previous run of this exact ticket failed
    # verification or tests, hand the Coding Agent's first
    # attempt this run the same failure feedback a retry
    # would get mid-run, instead of it starting blind and
    # likely re-making the same mistake at the same cost.
    last_failure = retry_memory.get_last_failure(ticket_id)

    initial_state = {
        "ticket": request.ticket,
        "repository_url": request.repository_url,
        "branch": request.branch,
        "repo_config": {},
        "ticket_category": {},
        "analysis": "",
        "design_reference": None,
        "repository_structure": [],
        "relevant_files": [],
        "repository_context": [],
        "workspace_context": [],
        "implementation_plan": {},
        "code_changes": {},
        "previous_code_changes": {},
        "verification_result": (
            last_failure.get(
                "verification_result",
                {},
            )
            if last_failure
            else {}
        ),
        "verification_attempts": 0,
        "coding_attempts": 0,
        "changed_files": [],
        "test_result": (
            last_failure.get(
                "test_result",
                {},
            )
            if last_failure
            else {}
        ),
        "test_attempts": 0,
        "workspace_path": "",
        "git_branch": "",
        "git_result": {},
        "pull_request": {},
    }

    threading.Thread(
        target=_run_ticket_workflow,
        args=(ticket_id, initial_state),
        daemon=True,
    ).start()

    return {
        "session_id": session_id,
        "ticket_id": ticket_id,
        "status": "running",
    }


@app.get("/api/agent/sessions/{ticket_id}")
def get_ticket_session(
    ticket_id: str,
):

    session = session_tracker.get_session(ticket_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=("No session found for this ticket."),
        )

    return session


@app.get("/repository/search")
def search_repository(query: str):

    service = RepositorySearchService()

    results = service.search(query)

    return {
        "query": query,
        "total_results": len(results),
        "files": [file.model_dump() for file in results],
    }
