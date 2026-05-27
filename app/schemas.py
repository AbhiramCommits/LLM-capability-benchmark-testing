from __future__ import annotations

from pydantic import BaseModel, Field

from app.models import DocumentMetadata, StoredDocument


# ── Upload ────────────────────────────────────────────────────────────────────

class UploadRequest(BaseModel):
    """Expected JSON metadata body accompanying the uploaded file."""

    metadata: DocumentMetadata = Field(description="Metadata for the new document.")


class UploadResponse(BaseModel):
    """Returned after a successful upload."""

    document: StoredDocument = Field(description="The newly created document record.")
    message: str = Field(default="Document uploaded successfully.")


# ── List ──────────────────────────────────────────────────────────────────────

class ListDocumentsResponse(BaseModel):
    """Paginated listing of stored documents."""

    documents: list[StoredDocument] = Field(
        description="List of document records for the current page."
    )
    total: int = Field(description="Total number of documents in the store.")
    page: int = Field(description="Current page number (1-indexed).")
    page_size: int = Field(description="Maximum records per page.")


# ── Get by ID ─────────────────────────────────────────────────────────────────

class GetDocumentResponse(BaseModel):
    """Returned when a single document is requested by ID."""

    document: StoredDocument = Field(description="The matching document record.")


# ── Delete ────────────────────────────────────────────────────────────────────

class DeleteDocumentResponse(BaseModel):
    """Returned after a successful deletion."""

    message: str = Field(description="Confirmation message.")
    deleted_id: str = Field(description="ID of the document that was removed.")


# ── Search by Tag ─────────────────────────────────────────────────────────────

class SearchDocumentsResponse(BaseModel):
    """Results from a tag-based search query."""

    documents: list[StoredDocument] = Field(
        description="Documents whose tags match the query."
    )
    query: str = Field(description="The search substring that was used.")
    total_matches: int = Field(description="Number of matching documents found.")
