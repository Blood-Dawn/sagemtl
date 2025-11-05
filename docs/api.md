# REST API Reference

SageMTL provides a FastAPI-based REST API that exposes all core functionality over HTTP.

## Starting the Server

```bash
# Using the CLI
sagemtl serve --host 127.0.0.1 --port 8000

# Or using uvicorn directly
uvicorn sagemtl.serve.api:app --host 127.0.0.1 --port 8000
```

The API server will start on `http://127.0.0.1:8000` with automatic OpenAPI documentation at `/docs`.

## Endpoints

### Text Cleaning

**POST /clean**

Clean and normalize text with configurable options.

Request body:
```json
{
  "text": "Hello    World",
  "options": {
    "smart_quotes": true,
    "em_dash": true,
    "minus_sign": true,
    "nbsp_to_space": true,
    "zero_width": true,
    "collapse_blank_lines": true,
    "ensure_trailing_lf": true
  }
}
```

Response:
```json
{
  "text": "Hello World\n",
  "meta": {
    "original_length": 13,
    "cleaned_length": 12
  }
}
```

### HTML Crawling

**POST /crawl**

Extract structured text from HTML.

Request body:
```json
{
  "html": "<html><body><p>Content</p></body></html>",
  "url": null,
  "allow_selectors": ["article", "main"],
  "block_selectors": [".sidebar", ".footer"],
  "options": {
    "ensure_trailing_lf": false
  }
}
```

Or fetch from a URL:
```json
{
  "url": "https://example.com",
  "allow_selectors": [],
  "block_selectors": []
}
```

Response:
```json
{
  "source": "inline",
  "meta": {
    "blocks_count": 1
  },
  "blocks": [
    {
      "order": 0,
      "text": "Content",
      "css_path": "body > p",
      "xpath": "/html/body/p",
      "lang": null
    }
  ]
}
```

### Translation

**POST /translate**

Queue a translation job.

Request body:
```json
{
  "text": "Hello world",
  "src_lang": "en",
  "tgt_lang": "fr",
  "provider": "echo",
  "glossary": null,
  "meta": {}
}
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "result": null,
  "error": null
}
```

### Job Management

**GET /jobs**

List all translation jobs.

Response:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "translate",
    "status": "done",
    "created_at": "2025-11-05T12:00:00.000000Z",
    "updated_at": "2025-11-05T12:00:01.000000Z",
    "result": {
      "text": "Hello world"
    },
    "error": null
  }
]
```

**GET /jobs/{job_id}**

Get a specific job by ID.

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "translate",
  "status": "done",
  "result": {
    "text": "Hello world"
  }
}
```

**DELETE /jobs/{job_id}**

Cancel a job (only works for queued/running jobs).

Response:
```json
{
  "status": "cancelled",
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Dataset Management

**GET /datasets**

List all registered datasets.

Response:
```json
[
  {
    "name": "my-dataset",
    "format": "jsonl",
    "filename": "dataset.jsonl",
    "created_at": "2025-11-05T12:00:00.000000Z"
  }
]
```

## CORS Configuration

The API is configured to allow cross-origin requests from `http://localhost:5173` for development purposes. This enables the React UI to communicate with the API during local development.

## Error Handling

The API uses standard HTTP status codes:

- `200 OK` - Successful request
- `400 Bad Request` - Invalid input
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

Error responses include a detail message:

```json
{
  "detail": "Job 123 not found"
}
```

## Interactive Documentation

Visit `http://localhost:8000/docs` when the server is running to access the interactive Swagger UI documentation, where you can test all endpoints directly from your browser.
