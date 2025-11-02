import { useMemo, useState } from 'react';
import type { ColumnDef } from '@tanstack/react-table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table';
import { datasets, datasetSizeLabel } from '@/mocks/datasets';
import type { Dataset } from '@/mocks/datasets';
import { useToast } from '@/components/toaster';
import { useLayoutStore } from '@/state/layout-store';
import { WizardModal } from '@/components/wizard-modal';

export function DatasetsPage() {
  const [search, setSearch] = useState('');
  const [language, setLanguage] = useState('');
  const [format, setFormat] = useState<'csv' | 'jsonl'>('csv');
  const { push } = useToast();
  const select = useLayoutStore((state) => state.select);

  const filtered = useMemo(() => {
    return datasets.filter((dataset) => {
      const matchesSearch = search
        ? dataset.name.toLowerCase().includes(search.toLowerCase()) || dataset.id.toLowerCase().includes(search.toLowerCase())
        : true;
      const matchesLang = language ? dataset.language === language : true;
      return matchesSearch && matchesLang;
    });
  }, [language, search]);

  const columns: ColumnDef<Dataset>[] = [
    {
      accessorKey: 'name',
      header: 'Dataset',
      cell: ({ row }) => (
        <div>
          <p className="font-medium">{row.original.name}</p>
          <p className="text-xs text-muted-foreground">{row.original.id}</p>
        </div>
      ),
    },
    {
      accessorKey: 'language',
      header: 'Language',
      cell: ({ row }) => <Badge variant="secondary" className="uppercase">{row.original.language}</Badge>,
    },
    {
      accessorKey: 'size',
      header: 'Size',
      cell: ({ row }) => datasetSizeLabel(row.original),
    },
    {
      accessorKey: 'documents',
      header: 'Documents',
    },
    {
      id: 'inspect',
      header: '',
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => select({ dataset: row.original.name, language: row.original.language, documents: row.original.documents })}
        >
          Inspect
        </Button>
      ),
    },
  ];

  const exportData = (targetFormat: 'csv' | 'jsonl') => {
    push({
      title: 'Export started',
      description: `Preparing ${filtered.length} datasets as ${targetFormat.toUpperCase()}`,
    });
  };

  const wizardSteps = [
    {
      title: 'Choose format',
      description: 'Select the export schema for your dataset bundle.',
      content: (
        <div className="space-y-2 text-sm">
          <Button
            variant={format === 'csv' ? 'default' : 'secondary'}
            className="w-full justify-start"
            onClick={() => setFormat('csv')}
          >
            CSV (comma separated)
          </Button>
          <Button
            variant={format === 'jsonl' ? 'default' : 'secondary'}
            className="w-full justify-start"
            onClick={() => setFormat('jsonl')}
          >
            JSONL (one doc per line)
          </Button>
        </div>
      ),
    },
    {
      title: 'Confirm recipients',
      description: 'Mock step for future integrations.',
      content: <p className="text-sm text-muted-foreground">Exports will be delivered to engineering@sagemtl.ai</p>,
    },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>Filters</CardTitle>
          </div>
          <WizardModal
            trigger={<Button variant="secondary">Bulk export wizard</Button>}
            steps={wizardSteps}
            onFinish={() => {
              exportData(format);
              push({ title: 'Export queued', description: 'Datasets will be packaged shortly.' });
            }}
          />
        </CardHeader>
        <CardContent className="flex flex-col gap-4 md:flex-row md:items-end">
          <div className="flex-1 space-y-2">
            <label className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Search</label>
            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Dataset name" />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Language</label>
            <Input value={language} onChange={(event) => setLanguage(event.target.value)} placeholder="en" className="w-24" />
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => exportData('csv')}>
              Export CSV
            </Button>
            <Button variant="secondary" onClick={() => exportData('jsonl')}>
              Export JSONL
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Datasets</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable columns={columns} data={filtered} searchPlaceholder="Search datasets" />
        </CardContent>
      </Card>
    </div>
  );
}
