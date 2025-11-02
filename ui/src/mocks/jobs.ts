import { addMinutes, formatDistanceToNow } from 'date-fns';
import type { JobStatus } from '@/components/job-status-badge';

export type JobStep = {
  name: string;
  status: JobStatus;
  startedAt: string;
  completedAt?: string;
  logs: string[];
};

export type Job = {
  id: string;
  name: string;
  status: JobStatus;
  createdAt: string;
  eta?: string;
  gpu?: string;
  steps: JobStep[];
};

const now = new Date();

export const jobs: Job[] = Array.from({ length: 8 }).map((_, index) => {
  const statusSequence: JobStatus[] = ['queued', 'running', 'running', 'done', 'failed'];
  const status = statusSequence[index % statusSequence.length];
  const start = addMinutes(now, -index * 12);
  const eta = status === 'running' ? formatDistanceToNow(addMinutes(start, 6), { addSuffix: true }) : undefined;
  const steps: JobStep[] = [
    {
      name: 'Normalize Text',
      status: status === 'queued' ? 'queued' : 'done',
      startedAt: addMinutes(start, -2).toISOString(),
      completedAt: status !== 'queued' ? addMinutes(start, -1).toISOString() : undefined,
      logs: ['Queued for normalization', 'Normalization complete'],
    },
    {
      name: 'Vector Crawl',
      status: status === 'running' ? 'running' : status === 'queued' ? 'queued' : 'done',
      startedAt: start.toISOString(),
      completedAt: status === 'done' ? addMinutes(start, 3).toISOString() : undefined,
      logs: ['Renderer: Playwright (headless)', 'Fetched 23 documents'],
    },
    {
      name: 'Translate',
      status: status === 'failed' ? 'failed' : status === 'done' ? 'done' : 'queued',
      startedAt: addMinutes(start, 4).toISOString(),
      completedAt: status === 'failed' ? addMinutes(start, 5).toISOString() : undefined,
      logs: ['Queued for translation'],
    },
  ];
  return {
    id: `JOB-${8200 + index}`,
    name: `Web Crawl Batch ${index + 1}`,
    status,
    createdAt: start.toISOString(),
    eta,
    gpu: index % 3 === 0 ? 'A100' : undefined,
    steps,
  };
});
