import { formatBytes } from '@/lib/utils';

export type Dataset = {
  id: string;
  name: string;
  language: string;
  size: number;
  documents: number;
  updatedAt: string;
};

const languages = ['en', 'fr', 'de', 'es', 'ja'];

export const datasets: Dataset[] = Array.from({ length: 14 }).map((_, index) => ({
  id: `DATASET-${index + 1}`,
  name: `Knowledge Pack ${index + 1}`,
  language: languages[index % languages.length],
  size: 10_485_760 + index * 512_000,
  documents: 1000 + index * 120,
  updatedAt: new Date(Date.now() - index * 3_600_000).toISOString(),
}));

export function datasetSizeLabel(dataset: Dataset) {
  return formatBytes(dataset.size);
}
