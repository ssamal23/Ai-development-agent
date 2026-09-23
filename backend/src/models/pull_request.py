from pydantic import BaseModel


class PullRequestResult(BaseModel):
    success: bool
    title: str
    branch: str
    base_branch: str
    url: str | None = None
    number: int | None = None
    message: str