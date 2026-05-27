"""Document CRUD routes for the Document Management System.

This module exposes five endpoints covering the full lifecycle of a
document: upload, list, retrieve, delete, and tag-based search.
"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app import database, models, schemas

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=schemas.UploadResponse,
    status_code=201,
    summary="Upload a new document",
)
async def upload_document(
    file: UploadFile = File(description="The document file to upload."),
    filename: str = Form(
        description="Original filename to store (overrides the multipart filename)."
    ),
    tags: str = Form(
        default="",
        description="Comma-separated list of tags for categorization and search.",
    ),
    description: str | None = Form(
        default=None, description="Optional description of the document content."
    ),
) -> schemas.UploadResponse:
    """Upload a new document into the system.

    Accepts a multipart form with the binary file and metadata fields.
    The file content is read into memory, hashed into a unique ID, and
    stored alongside the supplied tags and description.

    Returns the newly created document record on success.
    """
    content = await file.read()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    doc = database.insert_document(
        filename=filename,
        content=content,
        tags=tag_list,
        description=description,
    )
    return schemas.UploadResponse(document=doc)


@router.get(
    "",
    response_model=schemas.ListDocumentsResponse,
    summary="List all documents",
)
async def list_documents(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Number of documents per page (max 100)."
    ),
) -> schemas.ListDocumentsResponse:
    """Retrieve a paginated list of all stored documents.

    Documents are sorted by upload time with the most recently uploaded
    appearing first. Pagination is controlled through the `page` and
    `page_size` query parameters.
    """
    docs = database.list_documents(page=page, page_size=page_size)
    total = database.count_documents()
    return schemas.ListDocumentsResponse(
        documents=docs, total=total, page=page, page_size=page_size
    )


@router.get(
    "/{document_id}",
    response_model=schemas.GetDocumentResponse,
    summary="Get a document by ID",
)
async def get_document(
    document_id: str,
) -> schemas.GetDocumentResponse:
    """Retrieve a single document by its unique identifier.

    Returns the full document record including metadata and timestamps.
    If no document matches the given ID, a 404 response is returned.
    """
    doc = database.get_document(document_id)
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=f"No document found with id '{document_id}'.",
        )
    return schemas.GetDocumentResponse(document=doc)


@router.delete(
    "/{document_id}",
    response_model=schemas.DeleteDocumentResponse,
    summary="Delete a document",
)
async def delete_document(
    document_id: str,
) -> schemas.DeleteDocumentResponse:
    """Permanently delete a document from the system.

    Once deleted the document and its metadata cannot be recovered.
    Returns a 404 if the document does not exist.
    """
    deleted = database.delete_document(document_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No document found with id '{document_id}'.",
        )
    return schemas.DeleteDocumentResponse(
        message=f"Document '{document_id}' deleted successfully.",
        deleted_id=document_id,
    )


@router.get(
    "/search",
    response_model=schemas.SearchDocumentsResponse,
    summary="Search documents by tag",
)
async def search_documents(
    tag: str = Query(
        description="Substring to match against document tags (case-insensitive)."
    ),
) -> schemas.SearchDocumentsResponse:
    """Search for documents whose tags contain the given substring.

    Performs a case-insensitive substring match across all tags on all
    documents. Results are ordered by upload time (newest first).

    If no documents match, an empty list is returned with `total_matches: 0`.
    """
    if not tag.strip():
        raise HTTPException(
            status_code=400,
            detail="The 'tag' query parameter must be a non-empty string.",
        )
    results = database.search_by_tag(tag)
    return schemas.SearchDocumentsResponse(
        documents=results, query=tag, total_matches=len(results)
    )
