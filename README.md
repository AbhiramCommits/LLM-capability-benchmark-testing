# Document Management System

A RESTful API service for uploading, storing, searching, and managing
documents with metadata tagging. Built with FastAPI and designed to run
standalone or behind a reverse proxy.

## Features

- **Upload** documents with multipart form data and JSON metadata
- **List** all stored documents with optional pagination
- **Retrieve** a single document by its unique identifier
- **Delete** documents permanently by ID
- **Search** documents by tag with substring matching

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## API Documentation

- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Hand-written reference**: [docs/api-reference.md](docs/api-reference.md)
- **OpenAPI spec**: [docs/openapi.yaml](docs/openapi.yaml)

## Endpoints

| Method   | Path                                 | Description            |
|----------|--------------------------------------|------------------------|
| `POST`   | `/api/v1/documents/upload`           | Upload a new document  |
| `GET`    | `/api/v1/documents`                  | List all documents     |
| `GET`    | `/api/v1/documents/{document_id}`    | Get document by ID     |
| `DELETE` | `/api/v1/documents/{document_id}`    | Delete a document      |
| `GET`    | `/api/v1/documents/search`           | Search by tag          |

Full request/response schemas are documented in
[docs/api-reference.md](docs/api-reference.md).

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # Pydantic data models
│   ├── schemas.py           # Request/response schemas
│   ├── database.py          # In-memory storage layer
│   └── routers/
│       ├── __init__.py
│       └── documents.py     # Document CRUD routes
├── docs/
│   ├── api-reference.md     # Human-written API documentation
│   └── openapi.yaml         # OpenAPI 3.1 specification
├── CHANGELOG.md
├── requirements.txt
└── README.md
```

## Contributing

1. Follow the existing patterns for route handlers, schemas, and docstrings.
2. Update [docs/api-reference.md](docs/api-reference.md) for any new or
   changed endpoints.
3. Keep [docs/openapi.yaml](docs/openapi.yaml) in sync with the route
   definitions.
4. Add an entry to [CHANGELOG.md](CHANGELOG.md) under an `[Unreleased]`
   section for each user-facing change.

## License

MIT
