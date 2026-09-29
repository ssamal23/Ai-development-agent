import hashlib
import subprocess
from pathlib import Path

from src.config.settings import settings
from src.models.repository import FileMetadata


class RepositoryService:
    def __init__(
        self,
        repository_path: str | Path | None = None,
    ):
        self.repository_path = Path(
            repository_path
            or settings.repository_path
        )

    def validate_repository(self, require_git: bool = True) -> None:
        """
        Validate that the configured path exists and is a directory.

        Set require_git=False to allow scanning a plain folder that
        is not (yet) a Git repository.
        """

        if not self.repository_path.exists():
            raise FileNotFoundError(
                f"Repository does not exist: {self.repository_path}"
            )

        if not self.repository_path.is_dir():
            raise ValueError(
                f"Repository path is not a directory: {self.repository_path}"
            )

        if require_git and not (self.repository_path / ".git").exists():
            raise ValueError(
                f"Not a Git repository: {self.repository_path}"
            )

    def get_current_commit(self) -> str:
        """
        Get the current Git commit SHA.
        """

        self.validate_repository(require_git=True)

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repository_path,
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip()

    def get_all_files(self) -> list[Path]:
        """
        Get all files from the repository.

        We ignore directories that should not be analyzed,
        such as node_modules, .git, build folders, etc.
        """

        self.validate_repository(require_git=False)

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

        files: list[Path] = []

        for path in self.repository_path.rglob("*"):

            if not path.is_file():
                continue

            relative_path = path.relative_to(
                self.repository_path
            )

            # Skip files inside ignored directories
            if any(
                part in ignored_directories
                for part in relative_path.parts
            ):
                continue

            files.append(path)

        return files

    def read_file(self, relative_path: str) -> str:
        """
        Read a file's text content from the repository.
        """

        file_path = self.repository_path / relative_path

        resolved_file = file_path.resolve()
        resolved_repo = self.repository_path.resolve()

        if not resolved_file.is_relative_to(resolved_repo):
            raise ValueError("Invalid file path.")

        if not resolved_file.exists():
            raise FileNotFoundError(
                f"File does not exist: {relative_path}"
            )

        return resolved_file.read_text(encoding="utf-8")

    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash for a file.

        This hash helps us determine whether a file
        has changed since the previous indexing.
        """

        sha256 = hashlib.sha256()

        with file_path.open("rb") as file:

            for chunk in iter(
                lambda: file.read(8192),
                b"",
            ):
                sha256.update(chunk)

        return sha256.hexdigest()

    def detect_language(
        self,
        extension: str,
    ) -> str | None:
        """
        Detect programming language from file extension.
        """

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

    def get_file_metadata(
        self,
        file_path: Path,
    ) -> FileMetadata:
        """
        Create metadata for a single file.
        """

        relative_path = file_path.relative_to(
            self.repository_path
        )

        extension = file_path.suffix.lower()

        language = self.detect_language(extension)

        return FileMetadata(
            path=str(relative_path),
            hash=self.calculate_file_hash(file_path),
            size=file_path.stat().st_size,
            extension=extension,
            language=language,
        )

    def scan_repository(self) -> list[FileMetadata]:
        """
        Scan the entire repository and create
        metadata for every supported file.
        """

        files = self.get_all_files()

        metadata: list[FileMetadata] = []

        for file_path in files:

            try:
                file_metadata = self.get_file_metadata(
                    file_path
                )

                metadata.append(file_metadata)

            except (OSError, PermissionError) as error:

                print(
                    f"Skipping file {file_path}: {error}"
                )

        return metadata

    def get_changed_files(self,previous_commit: str) -> dict[str, list[str] | str]:
        """
        Compare the previous indexed commit with
        the current Git commit.

        Returns:
            added
            modified
            deleted
            previous_commit
            current_commit
        """

        self.validate_repository()

        current_commit = self.get_current_commit()

        # Nothing changed
        if previous_commit == current_commit:
            return {
                "previous_commit": previous_commit,
                "current_commit": current_commit,
                "added": [],
                "modified": [],
                "deleted": [],
            }

        result = subprocess.run(
            [
                "git",
                "diff",
                "--name-status",
                previous_commit,
                current_commit,
            ],
            cwd=self.repository_path,
            capture_output=True,
            text=True,
            check=True,
        )

        added: list[str] = []
        modified: list[str] = []
        deleted: list[str] = []

        for line in result.stdout.splitlines():

            if not line.strip():
                continue

            parts = line.split(
                "\t",
                maxsplit=1,
            )

            if len(parts) != 2:
                continue

            status = parts[0]
            path = parts[1]

            if status == "A":
                added.append(path)

            elif status == "M":
                modified.append(path)

            elif status == "D":
                deleted.append(path)

            # Git can return statuses such as:
            # R100 old.py new.py
            #
            # We will handle renamed files separately later.
            elif status.startswith("R"):
                renamed_paths = path.split("\t")

                if len(renamed_paths) == 2:
                    deleted.append(
                        renamed_paths[0]
                    )

                    added.append(
                        renamed_paths[1]
                    )

        return {
            "previous_commit": previous_commit,
            "current_commit": current_commit,
            "added": added,
            "modified": modified,
            "deleted": deleted,
        }
