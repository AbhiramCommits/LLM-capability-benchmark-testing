# API Reference

> Base URL: `http://127.0.0.1:8000`  
> All endpoints are prefixed with `/api/v1`.

## Table of Contents

1. [Upload Document](#1-upload-document)
2. [List Documents](#2-list-documents)
3. [Get Document by ID](#3-get-document-by-id)
4. [Delete Document](#4-delete-document)
5. [Search Documents by Tag](#5-search-documents-by-tag)

---

## 1. Upload Document

Upload a new document file along with metadata. The file is stored in-memory
and assigned a unique identifier.

### Request

```
POST /api/v1/documents/upload
Content-Type: multipart/form-data
```

| Field         | Type     | Required | Description                                               |
|---------------|----------|----------|-----------------------------------------------------------|
| `file`        | binary   | Yes      | The document file to upload.                              |
| `filename`    | string   | Yes      | Original filename including extension (e.g. `report.pdf`).|
| `tags`        | string   | No       | Comma-separated tag list (e.g. `"finance,report"`).       |
| `description` | string   | No       | Human-readable summary of the document content.           |

### Response

**Status:** `201 Created`

```json
{
  "document": {
    "id": "a1b2c3d4e5f6",
    "filename": "report.pdf",
    "tags": ["finance", "report"],
    "description": "Q2 financial report",
    "size_bytes": 1048576,
    "uploaded_at": "2025-06-15T12:00:00.000000+00:00"
  },
  "message": "Document uploaded successfully."
}
```

| Field                    | Type      | Description                                   |
|--------------------------|-----------|-----------------------------------------------|
| `document.id`            | string    | Unique hex identifier assigned by the server. |
| `document.filename`      | string    | Stored filename.                              |
| `document.tags`          | string[]  | List of categorization tags.                  |
| `document.description`   | string \| null | Optional document description.           |
| `document.size_bytes`    | integer   | File size in bytes.                           |
| `document.uploaded_at`   | string    | ISO-8601 UTC upload timestamp.                |
| `message`                | string    | Human-readable confirmation.                  |

---

## 2. List Documents

Retrieve a paginated list of all stored documents, ordered by upload time
(newest first).

### Request

```
GET /api/v1/documents?page=1&page_size=20
```

| Parameter    | Type    | Required | Default | Description                             |
|--------------|---------|----------|---------|-----------------------------------------|
| `page`       | integer | No       | `1`     | Page number (1-indexed).                |
| `page_size`  | integer | No       | `20`    | Documents per page (max 100).           |

### Response

**Status:** `200 OK`

```json
{
  "documents": [
    {
      "id": "a1b2c3d4e5f6",
      "filename": "report.pdf",
      "tags": ["finance", "report"],
      "description": "Q2 financial report",
      "size_bytes": 1048576,
      "uploaded_at": "2025-06-15T12:00:00.000000+00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

| Field            | Type     | Description                                   |
|------------------|----------|-----------------------------------------------|
| `documents`      | array    | List of StoredDocument records.               |
| `total`          | integer  | Total documents in the store.                 |
| `page`           | integer  | Current page number.                          |
| `page_size`      | integer  | Max records per page.                         |

---

## 3. Get Document by ID

Retrieve a single document's full record by its unique identifier.

### Request

```
GET /api/v1/documents/{document_id}
```

| Parameter       | Type   | Required | Description                |
|-----------------|--------|----------|----------------------------|
| `document_id`   | string | Yes      | Hex ID from upload response.|

### Response

**Status:** `200 OK`

```json
{
  "document": {
    "id": "a1b2c3d4e5f6",
    "filename": "report.pdf",
    "tags": ["finance", "report"],
    "description": "Q2 financial report",
    "size_bytes": 1048576,
    "uploaded_at": "2025-06-15T12:00:00.000000+00:00"
  }
}
```

**Status:** `404 Not Found` — when no document matches the given `document_id`.

```json
{
  "detail": "No document found with id 'unknown'."
}
```

---

## 4. Delete Document

Permanently remove a document and its metadata from the system.

### Request

```
DELETE /api/v1/documents/{document_id}
```

| Parameter       | Type   | Required | Description                |
|-----------------|--------|----------|----------------------------|
| `document_id`   | string | Yes      | Hex ID from upload response.|

### Response

**Status:** `200 OK`

```json
{
  "message": "Document 'a1b2c3d4e5f6' deleted successfully.",
  "deleted_id": "a1b2c3d4e5f6"
}
```

**Status:** `404 Not Found` — when no document matches the given `document_id`.

```json
{
  "detail": "No document found with id 'unknown'."
}
```

---

## 5. Search Documents by Tag

Search for documents whose tags contain the given substring. Matching is
case-insensitive.

### Request

```
GET /api/v1/documents/search?tag=finance
```

| Parameter | Type   | Required | Description                                |
|-----------|--------|----------|--------------------------------------------|
| `tag`     | string | Yes      | Substring matched against each document's tags.|

### Response

**Status:** `200 OK`

```json
{
  "documents": [
    {
      "id": "a1b2c3d4e5f6",
      "filename": "report.pdf",
      "tags": ["finance", "report"],
      "description": "Q2 financial report",
      "size_bytes": 1048576,
      "uploaded_at": "2025-06-15T12:00:00.000000+00:00"
    }
  ],
  "query": "finance",
  "total_matches": 1
}
```

**Status:** `400 Bad Request` — when no `tag` parameter is supplied or it is empty.

```json
{
  "detail": "The 'tag' query parameter must be a non-empty string."
}
```
