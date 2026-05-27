from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """User-supplied metadata attached to every uploaded document."""

    filename: str = Field(
        description="Original filename including extension, e.g. 'report.pdf'."
    )
    tags: list[str] = Field(
        default_factory=list,
        description="A list of free-form tags for categorization and search.",
    )
    description: str | None = Field(
        default=None,
        description="Optional human-readable description of the document content.",
    )


class StoredDocument(DocumentMetadata):
    """A document record as persisted in the backend store."""

    id: str = Field(description="Unique hex identifier assigned by the server.")
    size_bytes: int = Field(description="Size of the uploaded file content in bytes.")
    uploaded_at: str = Field(description="ISO-8601 UTC timestamp of upload time.")
