from github import Github
from github.GithubException import GithubException

from src.config.settings import settings
from src.models.pull_request import PullRequestResult


class GitHubService:

    def __init__(
        self,
        owner: str | None = None,
        repo_name: str | None = None,
    ):
        if not settings.github_token:
            raise ValueError(
                "GITHUB_TOKEN is not configured."
            )

        self.github = Github(
            settings.github_token
        )

        self.owner = (
            owner
            or settings.github_owner
        )

        self.repository_name = (
            f"{self.owner}/"
            f"{repo_name or settings.github_repository}"
        )

    def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str | None = None,
    ) -> PullRequestResult:

        base_branch = (
            base_branch
            or settings.github_base_branch
        )

        try:
            repository = (
                self.github
                .get_repo(
                    self.repository_name
                )
            )

            existing_prs = (
                repository
                .get_pulls(
                    state="open",
                    head=(
                        f"{self.owner}:"
                        f"{head_branch}"
                    ),
                    base=base_branch,
                )
            )

            for existing_pr in existing_prs:
                return PullRequestResult(
                    success=True,
                    title=existing_pr.title,
                    branch=head_branch,
                    base_branch=base_branch,
                    url=existing_pr.html_url,
                    number=existing_pr.number,
                    message=(
                        "An open pull request "
                        "already exists for this branch."
                    ),
                )

            pull_request = (
                repository
                .create_pull(
                    title=title,
                    body=body,
                    head=head_branch,
                    base=base_branch,
                )
            )

            return PullRequestResult(
                success=True,
                title=pull_request.title,
                branch=head_branch,
                base_branch=base_branch,
                url=pull_request.html_url,
                number=pull_request.number,
                message=(
                    "Pull request created "
                    "successfully."
                ),
            )

        except GithubException as error:
            return PullRequestResult(
                success=False,
                title=title,
                branch=head_branch,
                base_branch=base_branch,
                url=None,
                number=None,
                message=(
                    "GitHub API error: "
                    f"{error}"
                ),
            )