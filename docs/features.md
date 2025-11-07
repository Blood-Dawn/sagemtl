# SageMTL Features

This guide covers the enhanced features available in SageMTL.

## Compose Workspace

The Compose workspace is a unified interface for text processing that combines cleaning, translation, and glossary management in one place.

### Key Features

- **Drag & Drop File Loading**: Drop .txt, .md, .html, or .jsonl files directly onto the source text area
- **Language Pickers**: Select from 15+ languages including Chinese, Japanese, Korean, and European languages
- **Real-time Diff View**: See before/after comparisons using Monaco Editor
- **Pipeline Execution**: Run complete Clean → Translate → Glossary workflow with one click

### Usage

1. **Load Text**:
   - Type or paste text into the source editor
   - Drag and drop a file onto the text area
   - Open from an existing dataset

2. **Configure Processing**:
   - **Clean Tab**: Enable text normalization options (smart quotes, whitespace, NFKC, etc.)
   - **Translate Tab**: Select source and target languages, choose provider
   - **Glossary Tab**: Manage term replacements (CSV or JSON format)
   - **Pipeline Tab**: Run the complete workflow

3. **View Results**:
   - The diff editor shows changes in real-time
   - Switch between side-by-side and inline views
   - Export results or save to datasets

## Novel Crawler

The novel crawler automatically detects chapter patterns and crawls multi-chapter novels from websites.

### Supported URL Patterns

The crawler automatically detects these common chapter URL patterns:

- `/chapter-1`, `/chapter-2`, ... (dash-separated)
- `/1/`, `/2/`, ... (numeric path segments)
- `/ch1/`, `/ch2/`, ... (prefixed numbers)
- `/1.html`, `/2.html`, ... (numbered HTML files)

### Features

- **Automatic Pattern Detection**: No manual configuration needed
- **Chapter Title Extraction**: Automatically finds chapter titles
- **CSS Selector Filtering**: Customize content extraction with allow/block selectors
- **Dataset Creation**: Saves chapters as organized datasets
- **Metadata Tracking**: Captures novel title, author, cover, and word counts

### API Usage

```python
import httpx

# Start a novel crawl job
response = httpx.post("http://localhost:8000/api/crawl/novel", json={
    "start_url": "https://example.com/novel/chapter-1",
    "start_chapter": 1,
    "end_chapter": 50,
    "allow_selectors": ["article", ".chapter-content"],
    "block_selectors": ["nav", "footer", ".ads"],
    "dataset_name": "my-novel",
    "max_concurrent": 3
})

job_id = response.json()["job_id"]

# Track progress via WebSocket
import websocket
ws = websocket.create_connection(f"ws://localhost:8000/api/jobs/ws/{job_id}")
while True:
    msg = ws.recv()
    data = json.loads(msg)
    if data["type"] == "complete":
        break
    print(f"Progress: {data.get('progress', 0) * 100}%")
```

### Dataset Structure

Crawled novels are saved with this structure:

```
~/.sagemtl/data/novel-name/
├── meta.json              # Novel metadata
└── files/
    ├── chapter-0001.txt
    ├── chapter-0002.txt
    └── ...
```

The `meta.json` includes:

```json
{
  "type": "novel",
  "title": "Novel Title",
  "author": "Author Name",
  "cover_url": "https://example.com/cover.jpg",
  "chapter_count": 50,
  "total_words": 125000,
  "chapters": [
    {
      "number": 1,
      "title": "Chapter 1: Beginning",
      "url": "https://example.com/ch1",
      "word_count": 2500
    }
  ]
}
```

## Job Tracking and Logs

Enhanced job tracking provides comprehensive metrics and logs for all background operations.

### Tracked Metrics

- **Runtime**: Execution time in milliseconds
- **Input Size**: Input text size in bytes
- **Output Size**: Output text size in bytes
- **Provider**: Translation provider used
- **Languages**: Source and target language codes

### Log Viewing

Jobs automatically log key events:

```
[1] Novel crawl job queued
[2] Starting novel crawl from https://example.com/ch1
[3] Detecting chapter pattern and crawling chapters 1-10
[4] ✓ Crawled 10 chapters (25,432 words)
[5] ✓ Saved to dataset: my-novel
[6] ✓ Completed in 12534ms
```

### Real-time Updates

Connect to a job's WebSocket endpoint for live progress:

```javascript
const ws = new WebSocket(`ws://localhost:8000/api/jobs/ws/${jobId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'progress') {
    console.log(`Progress: ${data.progress * 100}%`);
  } else if (data.type === 'complete') {
    console.log('Job completed!', data.result);
  } else if (data.type === 'error') {
    console.error('Job failed:', data.error);
  }
};
```

### Job Detail Modal

The UI provides a comprehensive job detail view with:

- **Job Metrics**: Runtime, input/output sizes, provider info
- **Live Status**: Real-time progress bar and status badge
- **Complete Logs**: Full log output with line numbers
- **Result Data**: Structured result data (JSON)
- **Error Details**: Full error messages and stack traces
- **Actions**: Cancel running jobs or retry failed ones

## Settings Management

Application settings are now managed through a REST API and persisted to `~/.sagemtl/config.toml`.

### Available Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `newline_mode` | string | `"lf"` | Newline style: `lf`, `crlf`, `system`, or `preserve` |
| `clean_input_path` | string | `"-"` | Default input path for clean command |
| `clean_output_path` | string? | `null` | Default output path (null = stdout) |
| `crawl_glob` | string | `"*.html"` | Glob pattern for batch crawling |
| `crawl_outdir` | string | `"out"` | Default crawl output directory |
| `crawl_jsonl` | boolean | `false` | Output crawl results as JSONL |
| `thread_count` | integer | auto | CPU-heavy task thread count |

### API Endpoints

**GET /api/settings**

Get current settings:

```bash
curl http://localhost:8000/api/settings
```

**PUT /api/settings**

Update settings (partial updates supported):

```bash
curl -X PUT http://localhost:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"thread_count": 8, "newline_mode": "crlf"}'
```

**POST /api/settings/reset**

Reset all settings to defaults:

```bash
curl -X POST http://localhost:8000/api/settings/reset
```

### UI Settings Page

The Settings page (`/settings`) provides a user-friendly interface for managing configuration:

1. **Application Settings Tab**: Edit all config values with proper controls
2. **Glossaries Tab**: Manage translation glossaries
3. **Real-time Validation**: Input validation before saving
4. **Persistence**: Changes are immediately written to `config.toml`
5. **Reset Button**: Restore all defaults with one click

## Dataset Management

### Import and Export

Import files into datasets:

```bash
# Via API
curl -X POST http://localhost:8000/api/datasets/import \
  -F "files=@chapter1.txt" \
  -F "files=@chapter2.txt" \
  -F "dataset_name=my-novel" \
  -F "dataset_type=novel"
```

### Dataset Types

SageMTL supports three dataset types:

1. **text**: General text files
2. **novel**: Multi-chapter novels with metadata
3. **translation**: Parallel text for training

### Novel Datasets

Novel datasets include enhanced metadata:

- Cover image URL
- Chapter count
- Author information
- Last processed job ID
- Total word count

### Opening in Compose

Click "Open in Compose" on any dataset to:

1. Load the first file's content into the source editor
2. Auto-populate the dataset ID for saving results
3. Preserve dataset context throughout the workflow

## Glossary Management

Glossaries enable consistent terminology across translations.

### Glossary Format

**CSV Format:**

```csv
source,target,case_sensitive,word_boundary,notes
角色,character,true,true,General term for character
主角,protagonist,true,true,Main character
```

**JSON Format:**

```json
[
  {
    "source": "角色",
    "target": "character",
    "case_sensitive": true,
    "word_boundary": true,
    "notes": "General term for character"
  }
]
```

### Pre-translation vs Post-translation

- **Pre-translation**: Apply glossary to source text before translation
- **Post-translation**: Apply glossary to translated output (recommended)

### Glossary Editor

The Settings page includes a built-in glossary editor:

1. Create new glossaries
2. Add/edit/delete entries
3. Import from CSV or JSON
4. Export glossaries
5. Case-sensitive and word-boundary matching options

## Advanced Features

### CSS Selector Filtering

Both the crawler and novel crawler support CSS selector filtering:

**Allow Selectors**: Include only matching elements

```css
article, .chapter-content, main, .post-body
```

**Block Selectors**: Exclude matching elements

```css
nav, footer, .sidebar, .ads, .comments, .navigation
```

### Concurrent Processing

Control concurrency for crawling operations:

- Novel crawler: 1-10 concurrent requests
- Batch processing: Thread count from settings
- Translation queue: Sequential processing (one at a time)

### Error Handling

All background jobs include comprehensive error handling:

- Detailed error messages in job logs
- Stack traces for debugging
- Automatic retry support for failed jobs
- Toast notifications on completion/failure
