from pathlib import Path

from src.config.settings import settings
from src.services.code_graph_service import (
    CodeGraphService,
    CodeGraphUnavailableError,
)
from src.services.repository_search_service import (
    RepositorySearchService,
)


def find_relevant_files(
    ticket: dict,
    repository_path: str | Path | None = None,
    index_directory: str | Path | None = None,
    max_results: int = 10,
) -> list[dict]:
    """
    Find existing files that may be relevant
    to the ticket.

    Primary source: code-review-graph (structural +
    semantic/FTS node search). It is cheaper and more
    precise than substring search because it matches
    function/class names and falls back to FTS5 itself
    when no embeddings have been built.

    The keyword index (repository.json) is used as a
    fallback/supplement so results never regress if the
    graph server is unavailable or returns partial
    coverage.
    """

    title = ticket.get(
        "title",
        "",
    )

    description = ticket.get(
        "description",
        "",
    )

    acceptance_criteria = ticket.get(
        "acceptance_criteria",
        [],
    )

    query = " ".join([
        title,
        description,
        " ".join(acceptance_criteria),
    ])

    relevant_files = _search_via_graph(
        query=query,
        repository_path=repository_path,
        max_results=max_results,
    )

    if len(relevant_files) >= max_results:
        return relevant_files[:max_results]

    relevant_files = _supplement_with_keyword_search(
        query=query,
        existing=relevant_files,
        repository_path=repository_path,
        index_directory=index_directory,
        max_results=max_results,
    )

    return relevant_files[:max_results]


def _search_via_graph(
    query: str,
    repository_path: str | Path | None,
    max_results: int,
) -> list[dict]:

    repo_root = str(
        Path(
            repository_path
            or settings.repository_path
        ).resolve()
    )

    try:
        nodes = (
            CodeGraphService.instance()
            .semantic_search_nodes(
                query=query,
                limit=max_results * 2,
                repo_root=repo_root,
            )
        )

    except CodeGraphUnavailableError as error:

        print(
            "code-review-graph unavailable, "
            f"falling back to keyword search: {error}"
        )

        return []

    return _map_graph_nodes_to_files(
        nodes,
        repository_path=repo_root,
    )


def _map_graph_nodes_to_files(
    nodes: list[dict],
    repository_path: str | Path,
) -> list[dict]:
    """
    Graph nodes carry an absolute `file_path`. The rest
    of the pipeline (repository index, workspace service)
    works with paths relative to the repository root, so
    every node must be normalized before it can flow into
    `read_relevant_files`.
    """

    repository_root = (
        Path(
            repository_path
        ).resolve()
    )

    files_by_path: dict[str, dict] = {}

    for node in nodes:

        file_path = node.get("file_path")

        if not file_path:
            continue

        try:
            relative_path = (
                Path(file_path)
                .resolve()
                .relative_to(repository_root)
            )

        except ValueError:
            # Node lives outside the repository root.
            continue

        normalized_path = str(
            relative_path
        ).replace(
            "\\",
            "/",
        )

        score = node.get(
            "score",
            0,
        )

        existing = files_by_path.get(
            normalized_path
        )

        if (
            existing is None
            or score > existing["score"]
        ):
            files_by_path[normalized_path] = {
                "path": normalized_path,
                "source": "graph",
                "matched_symbol": node.get(
                    "name"
                ),
                "kind": node.get("kind"),
                "score": score,
            }

    return sorted(
        files_by_path.values(),
        key=lambda file: file["score"],
        reverse=True,
    )


def _supplement_with_keyword_search(
    query: str,
    existing: list[dict],
    repository_path: str | Path | None,
    index_directory: str | Path | None,
    max_results: int,
) -> list[dict]:

    search_service = (
        RepositorySearchService(
            repository_path=repository_path,
            index_directory=index_directory,
        )
    )

    existing_paths = {
        _normalize_path(file["path"])
        for file in existing
    }

    keyword_results = search_service.search(
        query=query,
        max_results=max_results,
    )

    combined = list(existing)

    for file in keyword_results:

        if len(combined) >= max_results:
            break

        dumped = file.model_dump(
            exclude={"content"}
        )

        normalized_path = _normalize_path(
            dumped["path"]
        )

        if normalized_path in existing_paths:
            continue

        dumped["path"] = normalized_path
        dumped["source"] = "keyword"

        combined.append(dumped)

        existing_paths.add(
            normalized_path
        )

    return combined


def _normalize_path(
    path: str,
) -> str:
    """
    Normalize Windows/Linux path separators so graph
    results (always forward-slash) and keyword-index
    results (native OS separator) can be deduplicated
    against each other.
    """

    return path.replace(
        "\\",
        "/",
    )


def read_relevant_files(
    relevant_files: list[dict],
    repository_path: str | Path | None = None,
    index_directory: str | Path | None = None,
) -> list[dict]:
    """
    Read the contents of the files selected
    by repository search.
    """

    search_service = (
        RepositorySearchService(
            repository_path=repository_path,
            index_directory=index_directory,
        )
    )

    paths = [
        file["path"]
        for file in relevant_files
    ]

    files = (
        search_service.get_files_by_paths(
            paths
        )
    )

    return [
        file.model_dump()
        for file in files
    ]


def get_repository_structure(
    repository_path: str | Path | None = None,
    index_directory: str | Path | None = None,
) -> list[str]:
    """
    Get repository structure from the
    existing repository index.
    """

    search_service = (
        RepositorySearchService(
            repository_path=repository_path,
            index_directory=index_directory,
        )
    )

    return (
        search_service
        .get_repository_structure()
    )