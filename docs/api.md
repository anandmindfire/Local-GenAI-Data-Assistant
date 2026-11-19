# REST API Documentation

The **Local GenAI Data Assistant** exposes RESTful endpoints with OpenAPI 3.1 documentation available interactively at `/docs` (Swagger UI) and `/redoc` (ReDoc).

Base URL: `http://localhost:8000/api/v1`

---

## Headers

| Header | Description | Default |
|---|---|---|
| `X-Correlation-ID` | Request tracking UUID. Passed back in response headers. | Auto-generated UUID v4 |

---

## 1. Chat

### `POST /api/v1/chat`

Executes the intelligent assistant workflow. Automatically contextualizes conversational follow-ups, classifies intent (`document`, `sql`, `combined`), and returns grounded answers.

#### Request Body
```json
{
  "message": "What is our leave policy, and how many orders were placed last month?",
  "conversation_id": "conv_a1b2c3d4e5f60718"
}
```

- `message` (string, required): Natural language query (1 to 4000 characters).
- `conversation_id` (string, optional): Conversation session identifier. If omitted, a new UUID session is generated.

#### Response Body (`200 OK`)
```json
{
  "conversation_id": "conv_a1b2c3d4e5f60718",
  "answer": "According to the company leave policy, full-time employees receive 24 paid leaves annually. In the database, 7 completed orders were placed over the requested timeframe.",
  "intent": "combined",
  "sources": [
    {
      "document_id": "doc_8f12a4b9c1d0e234",
      "filename": "leave-policy.md",
      "page_number": 1,
      "chunk_id": "doc_8f12a4b9c1d0e234_chunk_0000",
      "score": 0.8872
    }
  ],
  "sql_results": [
    {
      "order_count": 7
    }
  ],
  "execution_metadata": {
    "rag_confidence": "high",
    "sql_row_count": 1,
    "sql_duration_ms": 14.5
  }
}
```

---

## 2. Documents

### `POST /api/v1/documents/ingest`

Upload and index a document (`.pdf`, `.docx`, `.txt`, `.md`) into the vector knowledge base.

#### Request (Multipart Form-Data)
- `file` (binary, required): Uploaded document file.

#### Response Body (`201 Created`)
```json
{
  "document_id": "doc_9a8b7c6d5e4f3a21",
  "filename": "refund-policy.md",
  "file_type": "md",
  "chunk_count": 2,
  "status": "created",
  "message": "Document successfully created with 2 chunks indexed."
}
```

If the document content matches an existing document's SHA-256 hash:
```json
{
  "document_id": "doc_9a8b7c6d5e4f3a21",
  "filename": "refund-policy.md",
  "file_type": "md",
  "chunk_count": 2,
  "status": "skipped",
  "message": "Document with identical content already indexed."
}
```

---

### `GET /api/v1/documents`

Retrieve paginated metadata of all indexed documents.

#### Query Parameters
- `page` (integer, default: `1`, minimum: `1`): Page number.
- `page_size` (integer, default: `20`, minimum: `1`, maximum: `100`): Results per page.

#### Response Body (`200 OK`)
```json
{
  "items": [
    {
      "document_id": "doc_9a8b7c6d5e4f3a21",
      "filename": "refund-policy.md",
      "file_type": "md",
      "file_size_bytes": 1420,
      "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "chunk_count": 2,
      "created_at": "2026-11-18T12:00:00Z",
      "updated_at": "2026-11-18T12:00:00Z"
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### `DELETE /api/v1/documents/{document_id}`

Delete a document from PostgreSQL and cascade delete all its vector embeddings from Qdrant.

#### Parameters
- `document_id` (string, path parameter, required): Stable document identifier.

#### Response Body (`200 OK`)
```json
{
  "status": "success",
  "message": "Document 'doc_9a8b7c6d5e4f3a21' and all associated vector embeddings successfully deleted."
}
```

#### Response Body (`404 Not Found`)
```json
{
  "success": false,
  "error": {
    "category": "DOCUMENT_NOT_FOUND",
    "message": "Document with ID 'doc_invalid' not found.",
    "details": {
      "document_id": "doc_invalid"
    }
  },
  "correlation_id": "e96f13b2-70b6-4db0-b6f7-a41bf8f61405"
}
```

---

## 3. Health & Readiness

### `GET /api/v1/health`

Comprehensive readiness probe for application, PostgreSQL, Qdrant, Ollama, and local models.

#### Response Body (`200 OK` or `503 Service Unavailable`)
```json
{
  "status": "ok",
  "app_version": "0.1.0",
  "dependencies": {
    "database": true,
    "qdrant": true,
    "ollama": true,
    "chat_model_available": true,
    "embedding_model_available": true
  }
}
```

---

## 4. Standard Error Format

All error responses return consistent JSON structures:

```json
{
  "success": false,
  "error": {
    "category": "SQL_VALIDATION_FAILURE",
    "message": "Disallowed operation detected: Drop. Database is read-only.",
    "details": {
      "sql": "DROP TABLE customers",
      "error": "Disallowed operation detected: Drop. Database is read-only."
    }
  },
  "correlation_id": "4b7b3e15-893f-42e3-bce8-6c84cbeaf311"
}
```
