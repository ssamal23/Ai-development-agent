import asyncio
import json
import threading
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.config.settings import settings


class CodeGraphUnavailableError(Exception):
    """
    Raised when the code-review-graph MCP server cannot be
    reached or a tool call fails.

    Callers MUST catch this and fall back to keyword search.
    The graph is an enhancement, not a hard dependency.
    """


class CodeGraphService:
    """
    Sync wrapper around the code-review-graph MCP server
    (``uvx code-review-graph serve``).

    The server is a long-lived stdio subprocess. Starting it
    and loading the graph is expensive, so the subprocess and
    MCP session are started once on a background event loop
    and reused for every call, instead of per-request.
    """

    _instance: "CodeGraphService | None" = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

        self._start_lock = threading.Lock()
        self._started = False
        self._start_error: Exception | None = None

    @classmethod
    def instance(cls) -> "CodeGraphService":

        with cls._instance_lock:

            if cls._instance is None:
                cls._instance = cls()

        return cls._instance

    def _ensure_started(self) -> None:

        if self._started:

            if self._start_error:
                raise CodeGraphUnavailableError(
                    str(self._start_error)
                )

            return

        with self._start_lock:

            if self._started:

                if self._start_error:
                    raise CodeGraphUnavailableError(
                        str(self._start_error)
                    )

                return

            self._loop = asyncio.new_event_loop()

            self._thread = threading.Thread(
                target=self._loop.run_forever,
                daemon=True,
            )

            self._thread.start()

            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._connect(),
                    self._loop,
                )

                future.result(timeout=45)

            except Exception as error:

                self._start_error = error
                self._started = True

                raise CodeGraphUnavailableError(
                    "code-review-graph MCP server "
                    f"unavailable: {error}"
                ) from error

            self._started = True

    async def _connect(self) -> None:

        server_params = StdioServerParameters(
            command="uvx",
            args=[
                "--from",
                "code-review-graph[embeddings]",
                "code-review-graph",
                "serve",
            ],
            cwd=str(
                Path(
                    settings.repository_path
                ).resolve()
            ),
        )

        self._exit_stack = AsyncExitStack()

        read, write = (
            await self._exit_stack
            .enter_async_context(
                stdio_client(server_params)
            )
        )

        session = (
            await self._exit_stack
            .enter_async_context(
                ClientSession(read, write)
            )
        )

        await session.initialize()

        self._session = session

    def _call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> dict | list:

        self._ensure_started()

        assert self._session is not None
        assert self._loop is not None

        future = asyncio.run_coroutine_threadsafe(
            self._session.call_tool(
                name,
                arguments=arguments,
            ),
            self._loop,
        )

        try:
            result = future.result(timeout=60)

        except Exception as error:
            raise CodeGraphUnavailableError(
                f"code-review-graph tool call "
                f"'{name}' failed: {error}"
            ) from error

        if result.isError:
            raise CodeGraphUnavailableError(
                f"code-review-graph tool '{name}' "
                f"returned an error: "
                f"{self._extract_text(result.content)}"
            )

        if result.structuredContent is not None:
            return result.structuredContent

        return self._parse_text_content(
            result.content
        )

    def _extract_text(
        self,
        content: list,
    ) -> str:

        texts = [
            block.text
            for block in content
            if getattr(block, "text", None)
        ]

        return "\n".join(texts)

    def _parse_text_content(
        self,
        content: list,
    ) -> dict | list:

        combined = self._extract_text(content)

        if not combined:
            return {}

        try:
            return json.loads(combined)

        except json.JSONDecodeError:
            return {"raw": combined}

    def _repo_root(
        self,
        repo_root: str | Path | None = None,
    ) -> str:

        return str(
            Path(
                repo_root
                or settings.repository_path
            ).resolve()
        )

    def ensure_graph_built(
        self,
        repo_root: str | Path | None = None,
        full_rebuild: bool = False,
    ) -> dict:
        """
        Build the graph for the target repository if it
        has never been indexed, otherwise incrementally
        update it for whatever changed since the last
        build. Then (re)embed any nodes that don't have
        embeddings yet so semantic_search_nodes_tool can
        use vector similarity instead of exact-name FTS.

        Cheap to call on every ticket: an up-to-date graph
        and embedding set do effectively no work, mirroring
        how RepositoryIndexService.update_index() is a
        no-op when nothing changed.
        """

        resolved_root = self._repo_root(
            repo_root
        )

        build_result = self._call_tool(
            "build_or_update_graph_tool",
            {
                "repo_root": resolved_root,
                "full_rebuild": full_rebuild,
                "postprocess": "minimal",
            },
        )

        try:
            embed_result = self._call_tool(
                "embed_graph_tool",
                {
                    "repo_root": resolved_root,
                    "provider": "local",
                },
            )

        except CodeGraphUnavailableError as error:
            # Embeddings are an enhancement on top of FTS,
            # not a hard requirement. If the embeddings
            # extra isn't installed or inference fails,
            # semantic_search_nodes_tool still works in
            # FTS/keyword mode.
            embed_result = {
                "status": "unavailable",
                "error": str(error),
            }

        return {
            "build": build_result,
            "embed": embed_result,
        }

    def semantic_search_nodes(
        self,
        query: str,
        limit: int = 15,
        kind: str | None = None,
        repo_root: str | Path | None = None,
    ) -> list[dict]:
        """
        Search the graph for functions/classes/files
        relevant to `query`.

        Falls back to FTS/keyword matching server-side
        when no embeddings have been built for the graph
        (no `embed_graph_tool` run). Either way, this is
        cheaper and more structural than substring search
        over full file contents.
        """

        resolved_root = self._repo_root(
            repo_root
        )

        arguments: dict = {
            "query": query,
            "limit": limit,
            "repo_root": resolved_root,
        }

        if kind:
            arguments["kind"] = kind

        data = self._call_tool(
            "semantic_search_nodes_tool",
            arguments,
        )

        if isinstance(data, dict):

            if data.get("search_mode") == "none":
                # Graph has never been built for this
                # repository. Build it once and retry
                # instead of silently returning nothing.
                self.ensure_graph_built(
                    resolved_root
                )

                data = self._call_tool(
                    "semantic_search_nodes_tool",
                    arguments,
                )

            if isinstance(data, dict):
                return data.get("results") or []

        if isinstance(data, list):
            return data

        return []

    def is_available(self) -> bool:

        try:
            self._ensure_started()
            return True

        except CodeGraphUnavailableError:
            return False

    def close(self) -> None:

        if self._loop is None:
            return

        if self._exit_stack is not None:

            async def _shutdown():
                await self._exit_stack.aclose()

            try:
                future = (
                    asyncio
                    .run_coroutine_threadsafe(
                        _shutdown(),
                        self._loop,
                    )
                )

                future.result(timeout=10)

            except Exception:
                pass

        self._loop.call_soon_threadsafe(
            self._loop.stop
        )

        self._started = False
        self._session = None
