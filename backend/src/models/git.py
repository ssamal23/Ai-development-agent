from pydantic import BaseModel


class GitResult(BaseModel):
    success: bool
    branch: str
    commit: str | None = None
    remote: str | None = None
    pushed: bool = False
    message: str
    changed_files: list[str] = []