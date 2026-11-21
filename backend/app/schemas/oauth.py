"""Google ID-token sign-in request contract."""

from pydantic import BaseModel, Field


class GoogleCredentialRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=8192)
