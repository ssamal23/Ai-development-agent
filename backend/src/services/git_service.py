import re
import subprocess
from pathlib import Path


class GitService:

    def __init__(
        self,
        repository_path: str | Path,
    ):
        self.repository_path = (
            Path(repository_path).resolve()
        )

    def _run(
        self,
        command: list[str],
    ) -> str:

        result = subprocess.run(
            command,
            cwd=self.repository_path,
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip()

    def validate_repository(self) -> None:

        if not self.repository_path.exists():
            raise FileNotFoundError(
                f"Repository does not exist: "
                f"{self.repository_path}"
            )

        if not (
            self.repository_path / ".git"
        ).exists():
            raise ValueError(
                f"Not a Git repository: "
                f"{self.repository_path}"
            )

    def get_current_branch(self) -> str:

        self.validate_repository()

        return self._run([
            "git",
            "branch",
            "--show-current",
        ])

    def get_current_commit(self) -> str:

        self.validate_repository()

        return self._run([
            "git",
            "rev-parse",
            "HEAD",
        ])

    def get_remote_url(
        self,
        remote: str = "origin",
    ) -> str | None:

        self.validate_repository()

        try:
            result = subprocess.run(
                [
                    "git",
                    "remote",
                    "get-url",
                    remote,
                ],
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                check=True,
            )

            return result.stdout.strip()

        except subprocess.CalledProcessError:
            return None

    def get_status(
        self,
    ) -> list[str]:

        self.validate_repository()

        output = self._run([
            "git",
            "status",
            "--porcelain",
        ])

        if not output:
            return []

        return output.splitlines()

    def get_changed_files(
        self,
    ) -> list[str]:

        self.validate_repository()

        output = self._run([
            "git",
            "status",
            "--porcelain",
        ])

        if not output:
            return []

        files = []

        for line in output.splitlines():

            if len(line) < 4:
                continue

            file_path = line[3:]

            # Handle renamed files:
            # old -> new
            if " -> " in file_path:
                file_path = file_path.split(
                    " -> "
                )[-1]

            files.append(file_path)

        return files

    def create_branch(
        self,
        branch_name: str,
    ) -> str:

        self.validate_repository()

        branch_name = self._sanitize_branch_name(
            branch_name
        )

        if not branch_name:
            raise ValueError(
                "Branch name cannot be empty."
            )

        existing_branch = subprocess.run(
            [
                "git",
                "rev-parse",
                "--verify",
                f"refs/heads/{branch_name}",
            ],
            cwd=self.repository_path,
            capture_output=True,
            text=True,
        )

        if existing_branch.returncode == 0:
            raise ValueError(
                f"Branch already exists: "
                f"{branch_name}"
            )

        self._run([
            "git",
            "checkout",
            "-b",
            branch_name,
        ])

        return branch_name

    def stage_files(
        self,
    ) -> None:

        self.validate_repository()

        self._run([
            "git",
            "add",
            "-A",
        ])

    def commit(
        self,
        message: str,
    ) -> str:

        self.validate_repository()

        if not message.strip():
            raise ValueError(
                "Commit message cannot be empty."
            )

        status = self.get_status()

        if not status:
            raise ValueError(
                "No changes available to commit."
            )

        self.stage_files()

        self._run([
            "git",
            "commit",
            "-m",
            message,
        ])

        return self.get_current_commit()

    def push(
        self,
        branch_name: str,
        remote: str = "origin",
    ) -> None:

        self.validate_repository()

        remote_url = self.get_remote_url(
            remote
        )

        if not remote_url:
            raise ValueError(
                f"Git remote '{remote}' "
                "does not exist."
            )

        self._run([
            "git",
            "push",
            "-u",
            remote,
            branch_name,
        ])

    def _sanitize_branch_name(
        self,
        branch_name: str,
    ) -> str:

        value = branch_name.strip()

        value = value.lower()

        value = re.sub(
            r"[^a-z0-9/_-]+",
            "-",
            value,
        )

        value = re.sub(
            r"-+",
            "-",
            value,
        )

        value = value.strip(
            "-/"
        )

        return value