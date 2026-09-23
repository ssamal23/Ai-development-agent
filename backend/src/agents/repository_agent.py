from src.services.repository_search_service import (
    RepositorySearchService,
)


def find_relevant_files(
    ticket: dict,
) -> list[dict]:
    """
    Find existing files that may be relevant
    to the ticket.
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

    search_service = (
        RepositorySearchService()
    )

    results = search_service.search(
        query=query,
        max_results=10,
    )

    return [
        file.model_dump(
            exclude={"content"}
        )
        for file in results
    ]


def read_relevant_files(
    relevant_files: list[dict],
) -> list[dict]:
    """
    Read the contents of the files selected
    by repository search.
    """

    search_service = (
        RepositorySearchService()
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


def get_repository_structure() -> list[str]:
    """
    Get repository structure from the
    existing repository index.
    """

    search_service = (
        RepositorySearchService()
    )

    return (
        search_service
        .get_repository_structure()
    )