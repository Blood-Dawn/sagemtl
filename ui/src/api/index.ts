import { delay } from '@/lib/utils';
import { normalizeText } from '@/mocks/text';
import { jobs } from '@/mocks/jobs';
import { datasets } from '@/mocks/datasets';

export type CleanPayload = {
  text: string;
  options: {
    smartQuotes: boolean;
    dashes: boolean;
    zeroWidth: boolean;
    linewrap: boolean;
  };
};

export async function postClean(payload: CleanPayload) {
  const normalized = normalizeText(payload.text, payload.options);
  return delay({
    preview: normalized,
    saved: true,
  }, 700);
}

export type CrawlPayload = {
  url: string;
  depth: number;
  renderJs: boolean;
};

export async function postCrawl(payload: CrawlPayload) {
  const blocks = Array.from({ length: 5 }).map((_, index) => ({
    id: `block-${index + 1}`,
    url: `${payload.url}/page-${index + 1}`,
    type: index % 2 === 0 ? 'article' : 'link',
    tokens: 120 + index * 35,
    preview: `Lorem ipsum dolor sit amet ${index}`,
  }));
  return delay({ blocks }, 800);
}

export type TranslatePayload = {
  text: string;
  model: string;
  glossary?: File | null;
};

export async function postTranslate(payload: TranslatePayload) {
  // Mock translation: Just reverse the text as a simple demo
  const mockTranslated = payload.text.split(' ').reverse().join(' ');

  return delay({
    id: `JOB-${Math.floor(Math.random() * 10000)}`,
    source: payload.text,
    target: mockTranslated,
  }, 900);
}

export async function getJobs() {
  return delay(jobs, 500);
}

export async function getDatasets() {
  return delay(datasets, 500);
}
