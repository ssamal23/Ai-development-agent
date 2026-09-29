import json
from pathlib import Path

from src.config.settings import settings
from src.models.repository import (
    FileMetadata,
    RepositoryIndex,
)
from src.services.repository_service import (
    RepositoryService,
)


class RepositoryIndexService:

    def __init__(
        self,
        repository_path: str | Path | None = None,
        index_directory: str | Path | None = None,
    ):

        self.repository_service = RepositoryService(
            repository_path=repository_path
        )

        self.index_directory = Path(
            index_directory
            or "data/repository_index"
        )

        self.index_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.index_file = (
            self.index_directory
            / "repository.json"
        )

    def index_repository(self) -> RepositoryIndex:
        """
        Perform the initial full repository indexing.

        This scans the repository once and stores
        metadata + source content.
        """

        print(
            "Starting full repository indexing..."
        )

        files = (
            self.repository_service
            .scan_repository()
        )

        indexed_files: list[FileMetadata] = []

        for file in files:

            try:

                content = (
                    self.repository_service
                    .read_file(file.path)
                )

                file.content = content

                indexed_files.append(file)

            except (
                OSError,
                PermissionError,
                UnicodeDecodeError,
                ValueError,
            ) as error:

                print(
                    f"Skipping content for "
                    f"{file.path}: {error}"
                )

                indexed_files.append(file)

        commit = (
            self.repository_service
            .get_current_commit()
        )

        index = RepositoryIndex(
            repository_path=str(
                settings.repository_path
            ),
            last_commit=commit,
            files=indexed_files,
        )

        self._save_index(index)

        print(
            f"Repository indexed successfully."
            f" Files: {len(index.files)}"
        )

        return index

    def load_index(
        self,
    ) -> RepositoryIndex | None:
        """
        Load the existing repository index.
        """

        if not self.index_file.exists():
            return None

        try:

            data = json.loads(
                self.index_file.read_text(
                    encoding="utf-8"
                )
            )

            return RepositoryIndex(**data)

        except (
            json.JSONDecodeError,
            ValueError,
        ) as error:

            print(
                f"Invalid repository index: {error}"
            )

            return None

    def update_index(self):

        """
        Incrementally update the repository index.

        Only added and modified files have their
        content re-read.

        Deleted files are removed from the index.
        """

        index = self.load_index()

        if index is None:

            print(
                "No existing index found."
            )

            new_index = (
                self.index_repository()
            )

            return {
                "type": "full",
                "index": new_index,
                "changes": None,
            }

        changes = (
            self.repository_service
            .get_changed_files(
                index.last_commit
            )
        )

        added_files = changes["added"]
        modified_files = changes["modified"]
        deleted_files = changes["deleted"]

        # Nothing changed
        if (
            not added_files
            and not modified_files
            and not deleted_files
        ):

            print(
                "Repository has no changes."
            )

            return {
                "type": "incremental",
                "index": index,
                "changes": changes,
            }

        files_by_path: dict[str, FileMetadata] = {
            file.path: file
            for file in index.files
        }

        # -----------------------------------------
        # Added + Modified files
        # -----------------------------------------

        changed_files = (
            added_files
            + modified_files
        )

        for relative_path in changed_files:

            full_path = (
                self.repository_service.repository_path
                / relative_path
            )

            if not full_path.exists():
                continue

            try:

                metadata = (
                    self.repository_service
                    .get_file_metadata(
                        full_path
                    )
                )

                # Read source code
                content = (
                    self.repository_service
                    .read_file(
                        relative_path
                    )
                )

                metadata.content = content

                files_by_path[
                    relative_path
                ] = metadata

                print(
                    f"Updated index: "
                    f"{relative_path}"
                )

            except (
                OSError,
                PermissionError,
                UnicodeDecodeError,
                ValueError,
            ) as error:

                print(
                    f"Could not index "
                    f"{relative_path}: {error}"
                )

        # -----------------------------------------
        # Deleted files
        # -----------------------------------------

        for relative_path in deleted_files:

            if relative_path in files_by_path:

                del files_by_path[
                    relative_path
                ]

                print(
                    f"Removed from index: "
                    f"{relative_path}"
                )

        new_commit = (
            self.repository_service
            .get_current_commit()
        )

        updated_index = RepositoryIndex(
            repository_path=index.repository_path,
            last_commit=new_commit,
            files=list(
                files_by_path.values()
            ),
        )

        self._save_index(
            updated_index
        )

        return {
            "type": "incremental",
            "index": updated_index,
            "changes": changes,
        }

    def _save_index(
        self,
        index: RepositoryIndex,
    ) -> None:
        """
        Save the repository index.
        """

        self.index_file.write_text(
            index.model_dump_json(
                indent=2
            ),
            encoding="utf-8",
        )

        print(
            f"Index saved to: "
            f"{self.index_file}"
        )