from pathlib import Path

from src.config.settings import settings
from src.models.repository import FileMetadata
from src.services.repository_index_service import (
    RepositoryIndexService,
)


class RepositorySearchService:

    def __init__(
        self,
        repository_path: str | Path | None = None,
        index_directory: str | Path | None = None,
    ):
        self.repository_path = Path(
            repository_path
            or settings.repository_path
        )

        self.index_service = (
            RepositoryIndexService(
                repository_path=repository_path,
                index_directory=index_directory,
            )
        )

    def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[FileMetadata]:
        """
        Search repository using the existing repository index.

        Search priority:
        1. File name
        2. File path
        3. File content
        """

        index = self.index_service.load_index()

        if index is None:
            raise ValueError(
                "Repository has not been indexed. "
                "Run /repository/index first."
            )

        query_terms = self._extract_terms(query)

        if not query_terms:
            return []

        results = []

        for file in index.files:

            score = self._calculate_score(
                file,
                query_terms,
            )

            if score > 0:
                results.append(
                    (score, file)
                )

        results.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            file
            for _, file in results[:max_results]
        ]

    def get_repository_structure(
        self,
    ) -> list[str]:
        """
        Get the repository structure from the
        existing repository index.

        No repository rescan is performed.
        """

        index = self.index_service.load_index()

        if index is None:
            raise ValueError(
                "Repository has not been indexed. "
                "Run /repository/index first."
            )

        return sorted(
            file.path
            for file in index.files
        )

    def get_files_by_paths(
        self,
        paths: list[str],
    ) -> list[FileMetadata]:
        """
        Retrieve files from the existing index
        using their paths.
        """

        index = self.index_service.load_index()

        if index is None:
            raise ValueError(
                "Repository has not been indexed. "
                "Run /repository/index first."
            )

        requested_paths = {
            self._normalize_path(path)
            for path in paths
        }

        results = []

        for file in index.files:

            indexed_path = self._normalize_path(
                file.path
            )

            if indexed_path in requested_paths:
                results.append(file)

        return results

    def read_file(
        self,
        relative_path: str,
    ) -> str:
        """
        Read a file directly from the repository.
        """

        file_path = (
            self.repository_path
            / relative_path
        )

        resolved_file = file_path.resolve()

        resolved_repo = (
            self.repository_path.resolve()
        )

        if not resolved_file.is_relative_to(
            resolved_repo
        ):
            raise ValueError(
                "Invalid file path."
            )

        if not resolved_file.exists():
            raise FileNotFoundError(
                f"File does not exist: "
                f"{relative_path}"
            )

        if not resolved_file.is_file():
            raise ValueError(
                f"Path is not a file: "
                f"{relative_path}"
            )

        try:
            return resolved_file.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:
            raise ValueError(
                f"Unable to read file as UTF-8: "
                f"{relative_path}"
            )

    def _extract_terms(
        self,
        query: str,
    ) -> list[str]:

        stop_words = {
            "the",
            "a",
            "an",
            "to",
            "of",
            "and",
            "or",
            "in",
            "on",
            "for",
            "with",
            "add",
            "new",
            "create",
            "implement",
            "update",
            "user",
            "should",
            "can",
            "have",
            "has",
            "that",
            "this",
            "page",
            "system",
            "application",
        }

        words = (
            query
            .lower()
            .replace("-", " ")
            .replace("_", " ")
            .split()
        )

        terms = []

        for word in words:

            word = word.strip(
                ".,!?()[]{}:;\"'"
            )

            if (
                len(word) >= 3
                and word not in stop_words
            ):
                terms.append(word)

        return list(
            dict.fromkeys(terms)
        )

    def _calculate_score(
        self,
        file: FileMetadata,
        query_terms: list[str],
    ) -> int:
        """
        Calculate relevance score.

        File name/path matches receive
        higher scores than content matches.
        """

        path = self._normalize_path(
            file.path
        ).lower()

        file_name = (
            Path(file.path)
            .name
            .lower()
        )

        content = (
            file.content or ""
        ).lower()

        score = 0

        for term in query_terms:

            if term in file_name:
                score += 20

            if term in path:
                score += 10

            content_matches = content.count(
                term
            )

            score += min(
                content_matches,
                10,
            )

        return score

    def _normalize_path(
        self,
        path: str,
    ) -> str:
        """
        Normalize Windows/Linux path separators.
        """

        return path.replace(
            "\\",
            "/",
        )