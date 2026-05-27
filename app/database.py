from __future__ import annotations

import hashlib
import threading
import time
import uuid
from datetime import datetime, timezone

from app.models import StoredDocument

# ---------------------------------------------------------------------------
# In-memory document store
# ---------------------------------------------------------------------------
# Uses a dict keyed by hex document ID, guarded by a re-entrant lock to
# support concurrent readers without data races.
# ---------------------------------------------------------------------------

_store: dict[str, StoredDocument] = {}
_lock = threading.RLock()


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def generate_id() -> str:
    """Produce a short unique hex identifier from a UUID4 hash."""
    raw = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    return raw[:12]


def insert_document(
    filename: str,
    content: bytes,
    tags: list[str] | None = None,
    description: str | None = None,
) -> StoredDocument:
    """Persist a new document and return its full record.

    Args:
        filename: Original filename including extension.
        content: Raw file bytes uploaded by the client.
        tags: Optional list of categorization tags.
        description: Optional human-readable summary.

    Returns:
        The newly created StoredDocument record.
    """
    doc_id = generate_id()
    now = _now_iso()
    doc = StoredDocument(
        id=doc_id,
        filename=filename,
        size_bytes=len(content),
        uploaded_at=now,
        tags=tags or [],
        description=description,
    )
    with _lock:
        _store[doc_id] = doc
    return doc


def get_document(document_id: str) -> StoredDocument | None:
    """Retrieve a document by its unique identifier.

    Args:
        document_id: The hex string ID assigned during upload.

    Returns:
        The StoredDocument if found, otherwise None.
    """
    with _lock:
        return _store.get(document_id)


def list_documents(page: int = 1, page_size: int = 20) -> list[StoredDocument]:
    """Return a paginated list of all stored documents.

    Args:
        page: 1-indexed page number.
        page_size: Maximum records to include per page.

    Returns:
        A slice of the full document list for the requested page.
    """
    with _lock:
        all_docs = sorted(_store.values(), key=lambda d: d.uploaded_at, reverse=True)
    start = (page - 1) * page_size
    return all_docs[start : start + page_size]


def count_documents() -> int:
    """Return the total number of stored documents."""
    with _lock:
        return len(_store)


def delete_document(document_id: str) -> bool:
    """Remove a document from the store by ID.

    Args:
        document_id: The document to delete.

    Returns:
        True if the document was found and removed, False otherwise.
    """
    with _lock:
        if document_id in _store:
            del _store[document_id]
            return True
    return False


def search_by_tag(query: str) -> list[StoredDocument]:
    """Find documents whose tags contain the query substring (case-insensitive).

    Args:
        query: Substring to match against each document's tags.

    Returns:
        Documents with at least one matching tag, most-recent first.
    """
    lowered = query.lower()
    with _lock:
        all_docs = _store.values()
    results = [
        d for d in all_docs if any(lowered in tag.lower() for tag in d.tags)
    ]
    results.sort(key=lambda d: d.uploaded_at, reverse=True)
    return results
