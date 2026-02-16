"""Provider file DTOs."""

from uuid import UUID

from pydantic import BaseModel


class ProviderFileResponse(BaseModel):
    """Provider file response."""

    id: UUID
    provider_id: UUID
    filename: str
    original_name: str
    file_type: str
    file_size: int
    description: str | None
    category: str | None
    created_at: str
    viewable: bool

    class Config:
        from_attributes = True


class ProviderFilesListResponse(BaseModel):
    """Provider files list response."""

    items: list[ProviderFileResponse]
    total: int
