from typing import Literal

from pydantic import BaseModel


class CodeChange(BaseModel):
    action: Literal["create", "modify", "delete"]
    file: str
    reason: str
    content: str | None = None


class CodeChangeResponse(BaseModel):
    changes: list[CodeChange]