# Changelog

All notable changes to the Document Management System will be documented
in this file. This project adheres to
[Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2025-06-15

### Added

- `POST /api/v1/documents/upload` — upload a new document with metadata.
- `GET /api/v1/documents` — list all stored documents with pagination.
- `GET /api/v1/documents/{document_id}` — retrieve a single document by ID.
- `DELETE /api/v1/documents/{document_id}` — permanently delete a document.
- `GET /api/v1/documents/search` — search documents by tag substring.
- In-memory document store with thread-safe locking.
- Human-written API reference at `docs/api-reference.md`.
- OpenAPI 3.1 specification at `docs/openapi.yaml`.
- Interactive Swagger UI at `/docs`.
- FastAPI application entry point in `app/main.py`.
- Full set of Pydantic request/response schemas.
