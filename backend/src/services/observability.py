"""
Langfuse tracing for the ticket workflow.

Every agent call in this codebase goes through get_llm(), so Langfuse's
LangChain CallbackHandler gives us automatic `generation` observations
(model, tokens, cost, latency) for free. What it doesn't give us is
which of OUR agents each call belongs to - for that, agent entry
points are wrapped in @observe(as_type=...) so the trace tree shows
Ticket Agent -> Planning Agent -> Coding Agent etc. as named steps,
each with its LLM call(s) nested underneath.

Tracing is entirely optional: with no LANGFUSE_PUBLIC_KEY/SECRET_KEY
configured, every function here is a no-op and the app behaves exactly
as it did before this module existed.
"""

import os
from contextlib import contextmanager

from src.config.settings import settings

# Langfuse's get_client() reads credentials from the process
# environment, not from our pydantic Settings object - and it must
# see them before the first get_client()/CallbackHandler() call
# anywhere in the app. This pushes .env's values into os.environ once,
# early, so import order elsewhere doesn't matter.
if settings.langfuse_public_key:
    os.environ.setdefault(
        "LANGFUSE_PUBLIC_KEY",
        settings.langfuse_public_key,
    )

if settings.langfuse_secret_key:
    os.environ.setdefault(
        "LANGFUSE_SECRET_KEY",
        settings.langfuse_secret_key,
    )

if settings.langfuse_host:
    os.environ.setdefault(
        "LANGFUSE_HOST",
        settings.langfuse_host,
    )

TRACING_ENABLED = bool(
    settings.langfuse_public_key
    and settings.langfuse_secret_key
)


def get_langchain_callbacks() -> list:
    """
    Callbacks to pass as config={"callbacks": ...} to any
    llm.invoke() / workflow.stream() call so it's captured as a
    Langfuse generation, nested under whatever @observe span or
    start_as_current_observation is currently active.

    Returns an empty list when tracing isn't configured, so every
    call site works unchanged either way.
    """

    from src.services.token_usage import TokenUsageHandler

    # Token usage is always tracked, independent of Langfuse.
    callbacks: list = [TokenUsageHandler()]

    if TRACING_ENABLED:
        from langfuse.langchain import CallbackHandler

        callbacks.append(CallbackHandler())

    return callbacks


@contextmanager
def trace_ticket_run(
    ticket_id: str,
    ticket_title: str,
):
    """
    Wraps one ticket workflow execution (Plan -> Code -> Verify
    -> Test -> Build -> PR, including every internal retry) in a
    single Langfuse trace.

    Grouped into a session by ticket_id, so if the same ticket
    is retried later (a brand new trace, since it's a separate
    graph run), both attempts show up together in the Sessions
    view instead of looking unrelated.

    Yields the trace_id (None when tracing isn't configured) so
    the caller can attach scores to this exact trace afterward.
    """

    if not TRACING_ENABLED:
        yield None
        return

    from langfuse import (
        Langfuse,
        get_client,
        propagate_attributes,
    )

    langfuse = get_client()
    trace_id = Langfuse.create_trace_id()

    with propagate_attributes(
        trace_name="ticket-workflow",
        session_id=ticket_id,
        tags=["ticket-workflow"],
        metadata={
            "ticket_id": ticket_id,
            "ticket_title": ticket_title,
        },
    ):
        with langfuse.start_as_current_observation(
            as_type="agent",
            name="ticket-workflow",
            trace_context={
                "trace_id": trace_id,
            },
        ) as root_span:
            root_span.update(
                input={
                    "ticket_id": ticket_id,
                    "ticket_title": ticket_title,
                }
            )

            yield trace_id


def update_current_trace_output(
    output: dict,
) -> None:
    """
    Set the output of the currently active root span (call this
    from inside the `with trace_ticket_run(...)` block, before
    it exits) to a curated summary of how the run ended -
    verification/test outcome, PR link - rather than leaving it
    empty or defaulting to the raw final graph state.
    """

    if not TRACING_ENABLED:
        return

    from langfuse import get_client

    get_client().update_current_span(
        output=output
    )


def score_ticket_run(
    trace_id: str | None,
    final_state: dict,
) -> None:
    """
    Attach the verification score and test pass/fail as scores
    on the completed trace, so trends across tickets/time (is
    the agent's success rate improving?) show up in Langfuse's
    Scores views without needing to parse trace output by hand.
    """

    if not TRACING_ENABLED or not trace_id:
        return

    from langfuse import get_client

    langfuse = get_client()

    verification_result = (
        final_state.get("verification_result")
        or {}
    )
    test_result = (
        final_state.get("test_result")
        or {}
    )

    score = verification_result.get("score")

    if isinstance(score, (int, float)):
        langfuse.create_score(
            trace_id=trace_id,
            name="verification-score",
            value=score,
            data_type="NUMERIC",
        )

    if "success" in test_result:
        langfuse.create_score(
            trace_id=trace_id,
            name="tests-passed",
            value=bool(
                test_result["success"]
            ),
            data_type="BOOLEAN",
        )

    langfuse.flush()
