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
            # A rerun of the same ticket always generates this
            # exact branch name. Reuse it (mirrors how PR
            # creation already reuses an existing open PR)
            # instead of permanently blocking every future
            # retry once one run has gotten this far.
            self._run([
                "git",
                "checkout",
                branch_name,
            ])

            return branch_name

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
    ) -> dict:
        """
        Push branch to remote with conflict detection.

        Returns a result dict with:
        - success: bool
        - message: str
        - conflicts: list of conflicting files (if any)
        """

        self.validate_repository()

        remote_url = self.get_remote_url(
            remote
        )

        if not remote_url:
            raise ValueError(
                f"Git remote '{remote}' "
                "does not exist."
            )

        try:
            self._run([
                "git",
                "push",
                "-u",
                remote,
                branch_name,
            ])

            return {
                "success": True,
                "message": (
                    f"Branch {branch_name} "
                    "pushed successfully"
                ),
                "conflicts": [],
            }

        except subprocess.CalledProcessError as e:

            # Check if failure is due to conflicts
            conflicts = (
                self._detect_conflicts(
                    e.stderr
                )
            )

            if conflicts:
                return {
                    "success": False,
                    "message": (
                        "Push failed: merge conflicts detected"
                    ),
                    "conflicts": conflicts,
                    "error": e.stderr,
                }

            return {
                "success": False,
                "message": (
                    f"Push failed: {e.stderr}"
                ),
                "conflicts": [],
                "error": e.stderr,
            }

    def detect_conflicts(self) -> list[str]:
        """
        Detect if there are merge conflicts
        in the current repository state.

        Returns list of conflicted files.
        """

        self.validate_repository()

        # Check for merge conflict markers
        conflict_files = []

        try:
            status = self.get_status()

            for line in status:
                # UU = both modified, AA = both added, DD = both deleted
                if line.startswith(("UU", "AA", "DD")):
                    file_path = line[3:].strip()
                    conflict_files.append(file_path)

            return conflict_files

        except Exception:
            return []

    def has_merge_conflicts(self) -> bool:
        """Check if repository has merge conflicts"""

        conflicts = self.detect_conflicts()
        return len(conflicts) > 0

    def resolve_conflicts_auto(
        self,
        strategy: str = "ours",
    ) -> dict:
        """
        Attempt auto-resolution of conflicts.

        Strategies:
        - 'ours': Keep our changes (ai-agent branch)
        - 'theirs': Keep their changes (main branch)
        - 'abort': Abort the merge

        Returns result with success status and message.
        """

        self.validate_repository()

        if strategy not in (
            "ours",
            "theirs",
            "abort",
        ):
            raise ValueError(
                f"Invalid strategy: {strategy}"
            )

        try:
            if strategy == "abort":
                self._run([
                    "git",
                    "merge",
                    "--abort",
                ])

                return {
                    "success": True,
                    "message": "Merge aborted",
                    "strategy": "abort",
                }

            else:
                # Stage all files with conflict resolution
                self._run([
                    "git",
                    "checkout",
                    f"--{strategy}",
                    ".",
                ])

                self.stage_files()

                return {
                    "success": True,
                    "message": (
                        f"Conflicts resolved using "
                        f"{strategy} strategy"
                    ),
                    "strategy": strategy,
                }

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "message": (
                    f"Failed to resolve conflicts: "
                    f"{e.stderr}"
                ),
                "strategy": strategy,
                "error": e.stderr,
            }

    def _detect_conflicts(
        self,
        error_output: str,
    ) -> list[str]:
        """
        Parse git error output to detect
        which files have conflicts.
        """

        conflicts = []

        for line in error_output.split("\n"):

            if "CONFLICT" in line:
                # Extract file path from conflict message
                # e.g., "CONFLICT (content): Merge conflict in src/file.ts"
                if "in " in line:
                    file_path = (
                        line.split("in ", 1)[-1].strip()
                    )
                    if file_path:
                        conflicts.append(file_path)

        return conflicts

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