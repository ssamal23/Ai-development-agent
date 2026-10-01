import threading
from contextvars import ContextVar
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from src.services import session_tracker


# The ticket whose workflow is running in this context. LangGraph
# copies the context into every node, so agents that build their
# own callbacks (get_langchain_callbacks()) can still report usage
# without being handed the ticket id.
current_ticket_id: ContextVar[str | None] = ContextVar(
    "current_ticket_id",
    default=None,
)

_seen_lock = threading.Lock()
_seen_runs: set[UUID] = set()


def _first_report(run_id: UUID) -> bool:
    """
    The handler can be attached twice to one call (once inherited
    from workflow.stream(), once from an agent's own callbacks);
    count each LLM run once.
    """

    with _seen_lock:
        if run_id in _seen_runs:
            return False

        if len(_seen_runs) > 5000:
            _seen_runs.clear()

        _seen_runs.add(run_id)
        return True


def _current_node(metadata: dict | None) -> str:
    node = (metadata or {}).get("langgraph_node")

    if node:
        return node

    try:
        from langgraph.config import get_config

        return (
            get_config().get("metadata", {}).get("langgraph_node")
            or "unknown"
        )

    except Exception:
        return "unknown"


class TokenUsageHandler(BaseCallbackHandler):
    """
    Reports every LLM call's token usage to the session tracker,
    attributed to the LangGraph node that made it.

    Passed once as a callback on workflow.stream(); LangChain
    propagates it to every nested llm.invoke() inside the nodes,
    and each call's metadata carries `langgraph_node`.
    """

    def __init__(self, ticket_id: str | None = None) -> None:
        self.ticket_id = ticket_id
        self._run_node: dict[UUID, str] = {}

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list,
        *,
        run_id: UUID,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self._run_node[run_id] = _current_node(metadata)

    def on_llm_end(
        self,
        response,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        node = self._run_node.pop(run_id, "unknown")

        input_tokens = output_tokens = cache_read = 0
        model = None

        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                meta = getattr(message, "response_metadata", None) or {}
                model = model or meta.get("model_name") or meta.get("model")

                usage = getattr(message, "usage_metadata", None)

                if not usage:
                    continue

                input_tokens += usage.get("input_tokens", 0)
                output_tokens += usage.get("output_tokens", 0)
                cache_read += (
                    usage.get("input_token_details") or {}
                ).get("cache_read", 0)

        if not (input_tokens or output_tokens):
            return

        ticket_id = self.ticket_id or current_ticket_id.get()

        if not ticket_id or not _first_report(run_id):
            return

        session_tracker.add_usage(
            ticket_id,
            node,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read,
            model=model
            or (response.llm_output or {}).get("model_name"),
        )

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._run_node.pop(run_id, None)
