/**
 * SageMTL API v2 Client
 *
 * Client for interacting with the SageMTL v2 API endpoints.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Types
export interface CleanOptions {
  smart_quotes?: boolean;
  em_dash?: boolean;
  minus_sign?: boolean;
  nbsp_to_space?: boolean;
  zero_width?: boolean;
  collapse_blank_lines?: boolean;
  ensure_trailing_lf?: boolean;
  trim_trailing_spaces?: boolean;
  unicode_nfkc?: boolean;
  normalize_eol?: string;
  apply_glossary?: boolean;
  glossary_path?: string;
}

export interface ComposeCleanRequest {
  text: string;
  options?: CleanOptions;
}

export interface ComposeCleanResponse {
  text: string;
  meta: Record<string, unknown>;
  glossary_applied: boolean;
}

export interface ComposeTranslateRequest {
  text: string;
  src_lang?: string;
  tgt_lang?: string;
  provider?: string;
  glossary_path?: string;
  apply_glossary_pre?: boolean;
  apply_glossary_post?: boolean;
  dataset_id?: string;
  save_to_dataset?: boolean;
}

export interface ComposeTranslateResponse {
  job_id: string;
  status: string;
}

export interface ComposePipelineRequest {
  source_text: string;
  dataset_id?: string;
  clean_options?: CleanOptions;
  src_lang?: string;
  tgt_lang?: string;
  provider?: string;
  glossary_path?: string;
  save_to_dataset?: boolean;
}

export interface ComposePipelineResponse {
  clean_job_id?: string;
  translate_job_id: string;
  status: string;
  message: string;
}

export interface DatasetRecord {
  id: string;
  name: string;
  type: string;
  format: string;
  size_bytes: number;
  items_count: number;
  created_at: string;
  updated_at: string;
  meta: Record<string, unknown>;
  cover_path?: string;
  chapter_count?: number;
}

export interface ImportResponse {
  dataset_id: string;
  name: string;
  files_imported: number;
  total_bytes: number;
  items: Array<Record<string, unknown>>;
}

export interface NovelDataset {
  id: string;
  name: string;
  cover_url?: string;
  chapter_count: number;
  last_processed_job?: string;
  created_at: string;
  meta: Record<string, unknown>;
}

export interface CrawlChapterRequest {
  start_url: string;
  depth?: number;
  max_chapters?: number;
  allow_selectors?: string[];
  block_selectors?: string[];
  render_js?: boolean;
  dataset_name?: string;
  novel_title?: string;
}

export interface CrawlResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface JobResponse {
  id: string;
  type: string;
  status: string;
  created_at: string;
  updated_at: string;
  meta: Record<string, unknown>;
  result?: Record<string, unknown>;
  error?: string;
  log: string[];
  log_path?: string;
  progress?: number;
}

// Alias for backward compatibility
export type JobRecord = JobResponse;

export interface AppSettings {
  newline_mode: string;
  clean_input_path: string;
  clean_output_path: string | null;
  crawl_glob: string;
  crawl_outdir: string;
  crawl_jsonl: boolean;
  thread_count: number;
}

export interface GlossaryEntry {
  source: string;
  target: string;
  case_sensitive?: boolean;
  word_boundary?: boolean;
  notes?: string;
}

// API Client Class
export class SageMTLClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  // Compose endpoints
  async composeClean(request: ComposeCleanRequest): Promise<ComposeCleanResponse> {
    const response = await fetch(`${this.baseUrl}/api/compose/clean`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Clean failed: ${response.statusText}`);
    }

    return response.json();
  }

  async composeTranslate(request: ComposeTranslateRequest): Promise<ComposeTranslateResponse> {
    const response = await fetch(`${this.baseUrl}/api/compose/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Translate failed: ${response.statusText}`);
    }

    return response.json();
  }

  async composePipeline(request: ComposePipelineRequest): Promise<ComposePipelineResponse> {
    const response = await fetch(`${this.baseUrl}/api/compose/pipeline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Pipeline failed: ${response.statusText}`);
    }

    return response.json();
  }

  // Dataset endpoints
  async listDatasets(): Promise<DatasetRecord[]> {
    const response = await fetch(`${this.baseUrl}/api/datasets`);

    if (!response.ok) {
      throw new Error(`List datasets failed: ${response.statusText}`);
    }

    return response.json();
  }

  async importDataset(files: File[], datasetName?: string, datasetType: string = 'text'): Promise<ImportResponse> {
    const formData = new FormData();

    files.forEach((file) => {
      formData.append('files', file);
    });

    if (datasetName) {
      formData.append('dataset_name', datasetName);
    }
    formData.append('dataset_type', datasetType);

    const response = await fetch(`${this.baseUrl}/api/datasets/import`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Import failed: ${response.statusText}`);
    }

    return response.json();
  }

  async listNovels(): Promise<NovelDataset[]> {
    const response = await fetch(`${this.baseUrl}/api/datasets/novels`);

    if (!response.ok) {
      throw new Error(`List novels failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getDataset(datasetId: string): Promise<DatasetRecord> {
    const response = await fetch(`${this.baseUrl}/api/datasets/${datasetId}`);

    if (!response.ok) {
      throw new Error(`Get dataset failed: ${response.statusText}`);
    }

    return response.json();
  }

  async deleteDataset(datasetId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/datasets/${datasetId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Delete dataset failed: ${response.statusText}`);
    }
  }

  async listDatasetFiles(datasetId: string): Promise<Array<Record<string, unknown>>> {
    const response = await fetch(`${this.baseUrl}/api/datasets/${datasetId}/files`);

    if (!response.ok) {
      throw new Error(`List files failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getDatasetFile(datasetId: string, filePath: string): Promise<{ path: string; content: string; size_bytes: number }> {
    const response = await fetch(`${this.baseUrl}/api/datasets/${datasetId}/files/${filePath}`);

    if (!response.ok) {
      throw new Error(`Get file failed: ${response.statusText}`);
    }

    return response.json();
  }

  // Crawl endpoints
  async crawlChapters(request: CrawlChapterRequest): Promise<CrawlResponse> {
    const response = await fetch(`${this.baseUrl}/api/crawl/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Crawl failed: ${response.statusText}`);
    }

    return response.json();
  }

  // Job endpoints
  async listJobs(): Promise<JobResponse[]> {
    const response = await fetch(`${this.baseUrl}/api/jobs`);

    if (!response.ok) {
      throw new Error(`List jobs failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getJob(jobId: string): Promise<JobResponse> {
    const response = await fetch(`${this.baseUrl}/api/jobs/${jobId}`);

    if (!response.ok) {
      throw new Error(`Get job failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getJobLog(jobId: string): Promise<{ log: string; source: string; path?: string }> {
    const response = await fetch(`${this.baseUrl}/api/jobs/${jobId}/log`);

    if (!response.ok) {
      throw new Error(`Get job log failed: ${response.statusText}`);
    }

    return response.json();
  }

  async cancelJob(jobId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/jobs/${jobId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Cancel job failed: ${response.statusText}`);
    }
  }

  async retryJob(jobId: string): Promise<{ status: string; new_job_id: string }> {
    const response = await fetch(`${this.baseUrl}/api/jobs/${jobId}/retry`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Retry job failed: ${response.statusText}`);
    }

    return response.json();
  }

  async purgeJobs(keepRunning: boolean = true): Promise<{ purged: number }> {
    const url = new URL(`${this.baseUrl}/api/jobs`);
    url.searchParams.set('keep_running', keepRunning.toString());

    const response = await fetch(url.toString(), {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Purge jobs failed: ${response.statusText}`);
    }

    return response.json();
  }

  // WebSocket for job progress
  createJobWebSocket(jobId: string): WebSocket {
    const wsUrl = this.baseUrl.replace('http', 'ws');
    return new WebSocket(`${wsUrl}/api/jobs/ws/${jobId}`);
  }

  // Settings endpoints
  async getSettings(): Promise<AppSettings> {
    const response = await fetch(`${this.baseUrl}/api/settings`);

    if (!response.ok) {
      throw new Error(`Get settings failed: ${response.statusText}`);
    }

    return response.json();
  }

  async updateSettings(settings: Partial<AppSettings>): Promise<AppSettings> {
    const response = await fetch(`${this.baseUrl}/api/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });

    if (!response.ok) {
      throw new Error(`Update settings failed: ${response.statusText}`);
    }

    return response.json();
  }

  async resetSettings(): Promise<{ status: string; message: string }> {
    const response = await fetch(`${this.baseUrl}/api/settings/reset`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`Reset settings failed: ${response.statusText}`);
    }

    return response.json();
  }

  // Glossary endpoints
  async listGlossaries(): Promise<{ glossaries: string[] }> {
    const response = await fetch(`${this.baseUrl}/api/compose/glossaries`);

    if (!response.ok) {
      throw new Error(`List glossaries failed: ${response.statusText}`);
    }

    return response.json();
  }

  async getGlossary(path: string): Promise<{ entries: GlossaryEntry[] }> {
    const response = await fetch(`${this.baseUrl}/api/compose/glossaries/${encodeURIComponent(path)}`);

    if (!response.ok) {
      throw new Error(`Get glossary failed: ${response.statusText}`);
    }

    return response.json();
  }

  async createGlossary(name: string): Promise<{ path: string; message: string }> {
    const response = await fetch(`${this.baseUrl}/api/compose/glossaries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });

    if (!response.ok) {
      throw new Error(`Create glossary failed: ${response.statusText}`);
    }

    return response.json();
  }

  async updateGlossary(path: string, data: { entries: GlossaryEntry[] }): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/api/compose/glossaries/${encodeURIComponent(path)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`Update glossary failed: ${response.statusText}`);
    }

    return response.json();
  }

  async deleteGlossary(path: string): Promise<{ status: string }> {
    const response = await fetch(`${this.baseUrl}/api/compose/glossaries/${encodeURIComponent(path)}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Delete glossary failed: ${response.statusText}`);
    }

    return response.json();
  }
}

// Export singleton instance
export const apiClient = new SageMTLClient();
