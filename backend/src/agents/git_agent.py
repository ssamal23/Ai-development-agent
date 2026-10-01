from pathlib import Path

from langfuse import observe

from src.config.settings import settings
from src.models.git import GitResult
from src.services.git_service import GitService


class GitAgent:

    def __init__(
        self,
        repository_path: str | Path | None = None,
    ):
        if repository_path:
            self.repository_path = (
                Path(repository_path)
                .resolve()
            )
        else:
            self.repository_path = (
                Path(
                    settings.repository_path
                ).resolve()
            )

        self.git_service = GitService(
            self.repository_path
        )

    def create_branch(
        self,
        ticket: dict,
    ) -> str:

        ticket_id = str(
            ticket.get(
                "id",
                "ticket",
            )
        )

        title = ticket.get(
            "title",
            "implementation",
        )

        slug = self._slugify(title)

        branch_name = (
            f"ai-agent/"
            f"{ticket_id}-"
            f"{slug}"
        )

        return self.git_service.create_branch(
            branch_name
        )

    def commit_and_push(
        self,
        ticket: dict,
        branch_name: str,
    ) -> GitResult:

        changed_files = (
            self.git_service
            .get_changed_files()
        )

        if not changed_files:

            return GitResult(
                success=False,
                branch=branch_name,
                commit=None,
                remote=(
                    self.git_service
                    .get_remote_url()
                ),
                pushed=False,
                message=(
                    "No changes were found "
                    "to commit."
                ),
                changed_files=[],
            )

        ticket_id = str(
            ticket.get(
                "id",
                "ticket",
            )
        )

        title = ticket.get(
            "title",
            "implementation",
        )

        commit_message = (
            f"feat: "
            f"{self._clean_commit_title(title)} "
            f"({ticket_id})"
        )

        commit = (
            self.git_service.commit(
                commit_message
            )
        )

        push_result = (
            self.git_service.push(
                branch_name
            )
        )

        if not push_result.get("success"):
            return GitResult(
                success=False,
                branch=branch_name,
                commit=commit,
                remote=(
                    self.git_service
                    .get_remote_url()
                ),
                pushed=False,
                message=(
                    push_result.get(
                        "message",
                        "Push failed"
                    )
                ),
                changed_files=changed_files,
                conflicts=(
                    push_result.get(
                        "conflicts",
                        []
                    )
                ),
            )

        return GitResult(
            success=True,
            branch=branch_name,
            commit=commit,
            remote=(
                self.git_service
                .get_remote_url()
            ),
            pushed=True,
            message=(
                "Changes committed and "
                "pushed successfully."
            ),
            changed_files=changed_files,
        )

    def _slugify(
        self,
        value: str,
    ) -> str:

        value = value.lower()

        characters = []

        for char in value:

            if char.isalnum():
                characters.append(char)

            else:
                characters.append("-")

        slug = "".join(
            characters
        )

        while "--" in slug:
            slug = slug.replace(
                "--",
                "-",
            )

        return slug.strip("-")[:60]

    def _clean_commit_title(
        self,
        value: str,
    ) -> str:

        value = value.strip()

        value = " ".join(
            value.split()
        )

        if len(value) > 60:
            value = value[:60].rstrip()

        return value


@observe(as_type="tool", name="create-git-branch")
def create_git_branch(
    ticket: dict,
    repository_path: str | Path | None = None,
) -> str:

    agent = GitAgent(
        repository_path=repository_path
    )

    return agent.create_branch(
        ticket
    )


@observe(as_type="tool", name="commit-and-push")
def commit_and_push(
    ticket: dict,
    branch_name: str,
    repository_path: str | Path | None = None,
) -> dict:

    agent = GitAgent(
        repository_path=repository_path
    )

    result = agent.commit_and_push(
        ticket=ticket,
        branch_name=branch_name,
    )

    return result.model_dump()