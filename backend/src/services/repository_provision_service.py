import hashlib
import re
import subprocess
from pathlib import Path

from src.config.settings import settings


class RepositoryProvisionService:
    """
    Resolve which repository a ticket should be implemented
    against.

    When no `repository_url` is given, behavior is unchanged:
    the fixed `settings.repository_path` is used, exactly like
    before this feature existed.

    When a `repository_url` is given, it is cloned (or fast-
    forwarded, if already cloned once) into a deterministic
    local directory keyed by the URL, and every downstream
    service (indexing, workspace, git, code graph, PR) is
    pointed at that clone instead of the fixed setting.
    """

    BASE_DIRECTORY = Path(
        "data/repos"
    )

    def resolve(
        self,
        repository_url: str | None,
        branch: str | None = None,
    ) -> dict:

        if not repository_url:

            repository_path = str(
                Path(
                    settings.repository_path
                ).resolve()
            )

            return {
                "repository_path": repository_path,
                "repository_url": None,
                "owner": settings.github_owner,
                "repo_name": settings.github_repository,
                "base_branch": (
                    branch
                    or settings.github_base_branch
                ),
                "index_key": self._path_key(
                    repository_path
                ),
                # Preserve the pre-existing fixed
                # location so the default/settings
                # based repo keeps using its current
                # index file, unchanged.
                "index_directory": (
                    "data/repository_index"
                ),
            }

        owner, repo_name = (
            self._parse_owner_repo(
                repository_url
            )
        )

        repo_key = self._url_key(
            repository_url
        )

        local_path = (
            self.BASE_DIRECTORY
            / repo_key
        ).resolve()

        if (
            local_path / ".git"
        ).exists():

            self._update_existing_clone(
                local_path,
                branch,
            )

        else:

            self._clone_repository(
                repository_url,
                local_path,
                branch,
            )

        return {
            "repository_path": str(
                local_path
            ),
            "repository_url": repository_url,
            "owner": owner,
            "repo_name": repo_name,
            "base_branch": (
                branch
                or settings.github_base_branch
            ),
            "index_key": repo_key,
            "index_directory": str(
                Path("data/repository_index")
                / repo_key
            ),
        }

    def _parse_owner_repo(
        self,
        url: str,
    ) -> tuple[str, str]:

        match = re.search(
            r"github\.com[:/]+"
            r"([^/]+)/"
            r"([^/.]+?)"
            r"(?:\.git)?/?$",
            url,
        )

        if not match:
            raise ValueError(
                "Could not parse owner/repo "
                f"from URL: {url}"
            )

        return (
            match.group(1),
            match.group(2),
        )

    def _url_key(
        self,
        url: str,
    ) -> str:

        return hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()[:16]

    def _path_key(
        self,
        path: str,
    ) -> str:

        return hashlib.sha256(
            path.encode("utf-8")
        ).hexdigest()[:16]

    def _authenticated_url(
        self,
        url: str,
    ) -> str:
        """
        Inject the configured GitHub token into the clone
        URL so private repositories can be cloned/fetched
        non-interactively. No-op for SSH URLs.
        """

        if (
            not settings.github_token
            or not url.startswith("https://")
        ):
            return url

        return url.replace(
            "https://",
            f"https://{settings.github_token}@",
            1,
        )

    def _clone_repository(
        self,
        url: str,
        destination: Path,
        branch: str | None,
    ) -> None:

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        command = [
            "git",
            "clone",
        ]

        if branch:
            command += [
                "--branch",
                branch,
            ]

        command += [
            self._authenticated_url(url),
            str(destination),
        ]

        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )

    def _update_existing_clone(
        self,
        repository_path: Path,
        branch: str | None,
    ) -> None:

        subprocess.run(
            [
                "git",
                "fetch",
                "origin",
            ],
            cwd=repository_path,
            capture_output=True,
            text=True,
            check=True,
        )

        target_branch = (
            branch
            or self._default_remote_branch(
                repository_path
            )
        )

        subprocess.run(
            [
                "git",
                "checkout",
                target_branch,
            ],
            cwd=repository_path,
            capture_output=True,
            text=True,
            check=True,
        )

        # Reset to a clean, up-to-date state.
        # This directory is agent-managed (under
        # data/repos), never the user's own working
        # copy, so discarding local drift here is safe.
        subprocess.run(
            [
                "git",
                "reset",
                "--hard",
                f"origin/{target_branch}",
            ],
            cwd=repository_path,
            capture_output=True,
            text=True,
            check=True,
        )

    def _default_remote_branch(
        self,
        repository_path: Path,
    ) -> str:

        result = subprocess.run(
            [
                "git",
                "symbolic-ref",
                "refs/remotes/origin/HEAD",
            ],
            cwd=repository_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return (
                result.stdout.strip()
                .rsplit("/", 1)[-1]
            )

        return settings.github_base_branch
