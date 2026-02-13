from typing import Literal

from pydantic import BaseModel, Field


class ReviewPatchResponse(BaseModel):
    decision: Literal["approved", "rejected"] = Field(description="approved or rejected")
    message: str
    added_lines: int = 0
    removed_lines: int = 0

