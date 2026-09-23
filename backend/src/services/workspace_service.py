import hashlib
import shutil
import tempfile
from pathlib import Path

from src.config.settings import settings
from src.models.repository import FileMetadata


class WorkspaceService:

    def __init__(
        self,
        repository_path: str | Path | None = None,
    ):
        self.repository_path = (
            Path(
                repository_path
                or settings.repository_path
            )
            .resolve()
        )

        self.workspace_path: Path | None = None

    def create_workspace(self) -> Path:
        """
        Create a temporary working copy of the repository.

        The original repository is never modified while
        the agent is developing and testing.
        """

        self._validate_repository()

        self.workspace_path = Path(
            tempfile.mkdtemp(
                prefix="ai-agent-workspace-"
            )
        )

        self._copy_repository(
            self.repository_path,
            self.workspace_path,
        )

        return self.workspace_path

    def cleanup(self) -> None:
        """
        Remove the temporary workspace.
        """

        if (
            self.workspace_path
            and self.workspace_path.exists()
        ):
            shutil.rmtree(
                self.workspace_path,
                ignore_errors=True,
            )

        self.workspace_path = None

    def apply_workspace_to_repository(
        self,
    ) -> None:
        """
        Copy the successfully tested workspace
        changes back to the real repository.

        This should only be called after:

        1. Story verification passes
        2. Tests pass
        """

        self._validate_workspace()

        self._sync_directory(
            self.workspace_path,
            self.repository_path,
        )

    def read_file(
        self,
        relative_path: str,
    ) -> str:
        """
        Read a file from the current workspace.
        """

        self._validate_workspace()

        file_path = (
            self.workspace_path
            / relative_path
        ).resolve()

        self._validate_path(
            file_path,
            self.workspace_path,
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"File does not exist in workspace: "
                f"{relative_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"Path is not a file: "
                f"{relative_path}"
            )

        try:
            return file_path.read_text(
                encoding="utf-8"
            )

        except UnicodeDecodeError:
            raise ValueError(
                f"Unable to read file as UTF-8: "
                f"{relative_path}"
            )

    def get_file_metadata(
        self,
        relative_path: str,
    ) -> FileMetadata:
        """
        Get metadata for a file from the
        current workspace.
        """

        self._validate_workspace()

        file_path = (
            self.workspace_path
            / relative_path
        ).resolve()

        self._validate_path(
            file_path,
            self.workspace_path,
        )

        if not file_path.exists():
            raise FileNotFoundError(
                f"File does not exist in workspace: "
                f"{relative_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"Path is not a file: "
                f"{relative_path}"
            )

        extension = (
            file_path.suffix.lower()
        )

        content = self.read_file(
            relative_path
        )

        return FileMetadata(
            path=relative_path.replace(
                "\\",
                "/",
            ),
            hash=self._calculate_hash(
                file_path
            ),
            size=file_path.stat().st_size,
            extension=extension,
            language=self._detect_language(
                extension
            ),
            content=content,
        )

    def get_files_context(
        self,
        paths: list[str],
    ) -> list[dict]:
        """
        Read the latest versions of requested
        files from the temporary workspace.

        This is used during verification/test
        retries so the Coding Agent receives
        the current workspace state instead
        of stale repository-index content.
        """

        self._validate_workspace()

        context = []

        unique_paths = list(
            dict.fromkeys(paths)
        )

        for relative_path in unique_paths:

            try:
                metadata = (
                    self.get_file_metadata(
                        relative_path
                    )
                )

                context.append(
                    metadata.model_dump()
                )

            except (
                OSError,
                PermissionError,
                UnicodeDecodeError,
                ValueError,
                FileNotFoundError,
            ) as error:

                print(
                    f"Could not read workspace "
                    f"file {relative_path}: "
                    f"{error}"
                )

        return context

    def get_changed_workspace_files(
        self,
        paths: list[str],
    ) -> list[dict]:
        """
        Return the latest workspace contents
        for the supplied paths.
        """

        return self.get_files_context(
            paths
        )

    def _validate_repository(self) -> None:

        if not self.repository_path.exists():
            raise FileNotFoundError(
                f"Repository does not exist: "
                f"{self.repository_path}"
            )

        if not self.repository_path.is_dir():
            raise ValueError(
                f"Repository path is not a directory: "
                f"{self.repository_path}"
            )

        if not (
            self.repository_path / ".git"
        ).exists():
            raise ValueError(
                f"Not a Git repository: "
                f"{self.repository_path}"
            )

    def _validate_workspace(self) -> None:

        if self.workspace_path is None:
            raise ValueError(
                "Workspace has not been created."
            )

        if not self.workspace_path.exists():
            raise FileNotFoundError(
                "Workspace does not exist."
            )

    def _validate_path(
        self,
        file_path: Path,
        root_path: Path | None = None,
    ) -> None:

        root = (
            root_path
            or self.repository_path
        ).resolve()

        if not file_path.is_relative_to(
            root
        ):
            raise ValueError(
                "Invalid file path."
            )

    def _copy_repository(
        self,
        source: Path,
        destination: Path,
    ) -> None:

        ignored_directories = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            "dist",
            "build",
            ".next",
            ".nuxt",
            "coverage",
            ".idea",
            ".vscode",
        }

        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        for item in source.iterdir():

            if (
                item.is_dir()
                and item.name
                in ignored_directories
            ):
                continue

            target = (
                destination / item.name
            )

            if item.is_dir():

                shutil.copytree(
                    item,
                    target,
                    dirs_exist_ok=True,
                )

            else:

                shutil.copy2(
                    item,
                    target,
                )

    def _sync_directory(
        self,
        source: Path,
        destination: Path,
    ) -> None:

        ignored_directories = {
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            "dist",
            "build",
            ".next",
            ".nuxt",
            "coverage",
            ".idea",
            ".vscode",
        }

        source_files: set[Path] = set()

        for source_item in source.rglob("*"):

            relative_path = (
                source_item.relative_to(
                    source
                )
            )

            if any(
                part in ignored_directories
                for part in relative_path.parts
            ):
                continue

            destination_item = (
                destination / relative_path
            )

            if source_item.is_dir():

                destination_item.mkdir(
                    parents=True,
                    exist_ok=True,
                )

            else:

                source_files.add(
                    relative_path
                )

                destination_item.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                shutil.copy2(
                    source_item,
                    destination_item,
                )

        destination_files: set[Path] = set()

        for destination_item in destination.rglob("*"):

            relative_path = (
                destination_item.relative_to(
                    destination
                )
            )

            if any(
                part in ignored_directories
                for part in relative_path.parts
            ):
                continue

            if destination_item.is_file():
                destination_files.add(
                    relative_path
                )

        files_to_delete = (
            destination_files
            - source_files
        )

        for relative_path in files_to_delete:

            destination_item = (
                destination / relative_path
            )

            if destination_item.exists():
                destination_item.unlink()

        directories = [
            item
            for item in destination.rglob("*")
            if item.is_dir()
        ]

        for directory in sorted(
            directories,
            key=lambda path: len(
                path.parts
            ),
            reverse=True,
        ):

            relative_path = (
                directory.relative_to(
                    destination
                )
            )

            if any(
                part in ignored_directories
                for part in relative_path.parts
            ):
                continue

            try:
                directory.rmdir()
            except OSError:
                pass

    def _calculate_hash(
        self,
        file_path: Path,
    ) -> str:

        sha256 = hashlib.sha256()

        with file_path.open("rb") as file:

            for chunk in iter(
                lambda: file.read(8192),
                b"",
            ):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _detect_language(
        self,
        extension: str,
    ) -> str | None:

        languages = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sass": "scss",
            ".less": "less",
            ".json": "json",
            ".xml": "xml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sql": "sql",
            ".sh": "shell",
            ".bat": "batch",
            ".ps1": "powershell",
        }

        return languages.get(extension)