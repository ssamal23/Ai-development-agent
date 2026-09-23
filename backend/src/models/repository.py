from typing import Optional

from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    path: str
    hash: str
    size: int
    extension: str
    language: Optional[str] = None
    content: Optional[str] = None


class RepositoryIndex(BaseModel):
    repository_path: str
    last_commit: Optional[str] = None
    files: list[FileMetadata] = Field(
        default_factory=list
    )