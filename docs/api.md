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

## Settings API

### GET /api/settings

Get current application settings.

**Response:**
```json
{
  "newline_mode": "lf",
  "clean_input_path": "-",
  "clean_output_path": null,
  "crawl_glob": "*.html",
  "crawl_outdir": "out",
  "crawl_jsonl": false,
  "thread_count": 8
}
```

### PUT /api/settings

Update application settings (partial updates supported).

**Request:**
```json
{
  "thread_count": 16,
  "newline_mode": "crlf"
}
```

**Response:**
```json
{
  "newline_mode": "crlf",
  "clean_input_path": "-",
  "clean_output_path": null,
  "crawl_glob": "*.html",
  "crawl_outdir": "out",
  "crawl_jsonl": false,
  "thread_count": 16
}
```

### POST /api/settings/reset

Reset all settings to defaults.

**Response:**
```json
{
  "status": "reset",
  "message": "Settings reset to defaults"
}
```

## Novel Crawler API

### POST /api/crawl/novel

Crawl a novel with automatic chapter pattern detection.

**Request:**
```json
{
  "start_url": "https://example.com/novel/chapter-1",
  "start_chapter": 1,
  "end_chapter": 50,
  "allow_selectors": ["article", ".chapter-content"],
  "block_selectors": ["nav", "footer", ".ads"],
  "dataset_name": "my-novel",
  "max_concurrent": 3
}
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "status": "queued",
  "message": "Novel crawl job queued. Expected to crawl 50 chapters. Track at /api/jobs/a1b2c3d4-5678-90ab-cdef-1234567890ab"
}
```

**Supported URL Patterns:**
- `/chapter-1`, `/chapter-2`, ... (dash-separated)
- `/1/`, `/2/`, ... (numeric path segments)
- `/ch1/`, `/ch2/`, ... (prefixed numbers)
- `/1.html`, `/2.html`, ... (numbered HTML files)

## Compose API

### POST /api/compose/clean

Clean text with enhanced options including glossary support.

**Request:**
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
    "ensure_trailing_lf": true,
    "trim_trailing_spaces": true,
    "unicode_nfkc": true,
    "normalize_eol": "lf",
    "apply_glossary": false,
    "glossary_path": null
  }
}
```

**Response:**
```json
{
  "text": "Hello World\n",
  "meta": {
    "original_length": 13,
    "cleaned_length": 12
  },
  "glossary_applied": false
}
```

### POST /api/compose/translate

Queue a translation job with optional glossary processing.

**Request:**
```json
{
  "text": "你好世界",
  "src_lang": "zh",
  "tgt_lang": "en",
  "provider": "echo",
  "glossary_path": "~/.sagemtl/glossaries/terms.csv",
  "apply_glossary_pre": false,
  "apply_glossary_post": true,
  "dataset_id": "my-dataset",
  "save_to_dataset": false
}
```

**Response:**
```json
{
  "job_id": "translation-job-id",
  "status": "queued"
}
```

### POST /api/compose/pipeline

Execute the full Compose pipeline: Clean → Translate → Glossary → Save.

**Request:**
```json
{
  "source_text": "你好世界",
  "dataset_id": null,
  "clean_options": {
    "smart_quotes": true,
    "unicode_nfkc": true
  },
  "src_lang": "zh",
  "tgt_lang": "en",
  "provider": "echo",
  "glossary_path": null,
  "save_to_dataset": false
}
```

**Response:**
```json
{
  "clean_job_id": null,
  "translate_job_id": "pipeline-job-id",
  "status": "queued",
  "message": "Pipeline queued successfully. Track via /api/jobs/pipeline-job-id"
}
```

## Job Tracking API

### GET /api/jobs

List all jobs with full details.

**Response:**
```json
[
  {
    "id": "job-id",
    "type": "translate",
    "status": "done",
    "created_at": "2025-11-07T10:00:00.000Z",
    "updated_at": "2025-11-07T10:00:05.123Z",
    "meta": {
      "runtime_ms": 5123.45,
      "input_bytes": 1024,
      "output_bytes": 1536,
      "provider": "echo",
      "src_lang": "zh",
      "tgt_lang": "en"
    },
    "result": {
      "text": "translated text"
    },
    "error": null,
    "log": [
      "Translation completed in 5123.45ms",
      "Input: 1024 bytes → Output: 1536 bytes"
    ],
    "progress": 1.0
  }
]
```

### GET /api/jobs/{job_id}

Get detailed information about a specific job.

### DELETE /api/jobs/{job_id}

Cancel a running or queued job.

**Response:**
```json
{
  "status": "cancelled",
  "job_id": "job-id"
}
```

### WebSocket /api/jobs/ws/{job_id}

Real-time job progress updates via WebSocket.

**Messages:**

Progress update:
```json
{
  "type": "progress",
  "job_id": "job-id",
  "status": "running",
  "progress": 0.5,
  "message": "Processing...",
  "updated_at": "2025-11-07T10:00:02.000Z"
}
```

Completion:
```json
{
  "type": "complete",
  "job_id": "job-id",
  "status": "done",
  "result": {
    "text": "output"
  },
  "updated_at": "2025-11-07T10:00:05.000Z"
}
```

Error:
```json
{
  "type": "error",
  "job_id": "job-id",
  "message": "Error description"
}
```

## Dataset Management API

### GET /api/datasets

List all datasets with enhanced metadata.

**Response:**
```json
[
  {
    "id": "my-novel",
    "name": "my-novel",
    "type": "novel",
    "format": "txt",
    "size_bytes": 1048576,
    "items_count": 50,
    "created_at": "2025-11-07T10:00:00.000Z",
    "updated_at": "2025-11-07T10:00:00.000Z",
    "meta": {
      "title": "My Novel",
      "author": "Author Name",
      "chapter_count": 50
    },
    "cover_path": "https://example.com/cover.jpg",
    "chapter_count": 50
  }
]
```

### POST /api/datasets/import

Import files as a new dataset.

**Form Data:**
- `files`: One or more files (.txt, .md, .html, .jsonl, .epub)
- `dataset_name`: Optional dataset name
- `dataset_type`: Dataset type (text, novel, translation)

**Response:**
```json
{
  "dataset_id": "dataset-abc123",
  "name": "dataset-abc123",
  "files_imported": 3,
  "total_bytes": 102400,
  "items": [
    {
      "filename": "chapter1.txt",
      "path": "files/chapter1.txt",
      "size_bytes": 34100,
      "type": "txt"
    }
  ]
}
```

### GET /api/datasets/novels

List all novel-type datasets.

**Response:**
```json
[
  {
    "id": "my-novel",
    "name": "My Novel",
    "cover_url": "https://example.com/cover.jpg",
    "chapter_count": 50,
    "last_processed_job": "job-id",
    "created_at": "2025-11-07T10:00:00.000Z",
    "meta": {}
  }
]
```

### GET /api/datasets/{dataset_id}

Get detailed information about a specific dataset.

### DELETE /api/datasets/{dataset_id}

Delete a dataset and its files.

### GET /api/datasets/{dataset_id}/files

List all files in a dataset.

### GET /api/datasets/{dataset_id}/files/{file_path}

Get content of a specific file from a dataset.

**Response:**
```json
{
  "path": "files/chapter1.txt",
  "content": "Chapter 1 content...",
  "size_bytes": 34100
}
```

## Interactive API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation with:

- Try-it-now functionality
- Request/response examples
- Schema definitions
- Authentication (if enabled)

Alternative ReDoc documentation available at `http://localhost:8000/redoc`.
