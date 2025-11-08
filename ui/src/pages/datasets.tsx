import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import type { ColumnDef } from '@tanstack/react-table';
import { Upload, FolderOpen, Plus, Download, FileText, BookOpen } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table';
import { useToast } from '@/components/toaster';
import { apiClient } from '@/api/client-v2';
import type { DatasetRecord, NovelDataset } from '@/api/client-v2';

export function DatasetsPage() {
  const [search, setSearch] = useState('');
  const [datasets, setDatasets] = useState<DatasetRecord[]>([]);
  const [novels, setNovels] = useState<NovelDataset[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const { push } = useToast();
  const navigate = useNavigate();

  // Fetch datasets and novels
  const loadData = useCallback(async () => {
    try {
      const [datasetsData, novelsData] = await Promise.all([
        apiClient.listDatasets(),
        apiClient.listNovels(),
      ]);
      setDatasets(datasetsData);
      setNovels(novelsData);
    } catch (error) {
      push({
        title: 'Failed to load data',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  }, [push]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Drag-drop file import
  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      setIsUploading(true);
      try {
        const result = await apiClient.importDataset(acceptedFiles);
        push({
          title: 'Import successful',
          description: `Imported ${result.files_imported} file(s) to dataset "${result.name}"`,
        });
        await loadData(); // Refresh datasets
      } catch (error) {
        push({
          title: 'Import failed',
          description: error instanceof Error ? error.message : 'Unknown error',
          variant: 'destructive',
        });
      } finally {
        setIsUploading(false);
      }
    },
    [push, loadData]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/html': ['.html'],
      'application/json': ['.json', '.jsonl'],
      'application/epub+zip': ['.epub'],
    },
    disabled: isUploading,
  });

  // Filter datasets
  const filteredDatasets = useMemo(() => {
    return datasets.filter((dataset) => {
      if (!search) return true;
      const searchLower = search.toLowerCase();
      return (
        dataset.name.toLowerCase().includes(searchLower) ||
        dataset.id.toLowerCase().includes(searchLower)
      );
    });
  }, [datasets, search]);

  // Dataset table columns
  const datasetColumns: ColumnDef<DatasetRecord>[] = [
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => (
        <div>
          <p className="font-medium">{row.original.name}</p>
          <p className="text-xs text-muted-foreground">{row.original.id}</p>
        </div>
      ),
    },
    {
      accessorKey: 'size_bytes',
      header: 'Size',
      cell: ({ row }) => {
        const bytes = row.original.size_bytes;
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
        return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
      },
    },
    {
      accessorKey: 'type',
      header: 'Type',
      cell: ({ row }) => (
        <Badge variant="secondary" className="capitalize">
          {row.original.type}
        </Badge>
      ),
    },
    {
      accessorKey: 'created_at',
      header: 'Added',
      cell: ({ row }) => {
        const date = new Date(row.original.created_at);
        return date.toLocaleDateString();
      },
    },
    {
      accessorKey: 'items_count',
      header: 'Items',
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              try {
                // Load the first file from the dataset
                const files = await apiClient.listDatasetFiles(row.original.id);
                if (files.length > 0) {
                  const filePath = (files[0].path || files[0].name) as string;
                  const fileContent = await apiClient.getDatasetFile(row.original.id, filePath);
                  navigate('/compose', { state: { text: fileContent.content, datasetId: row.original.id } });
                } else {
                  push({
                    title: 'No files',
                    description: 'This dataset has no files to open',
                    variant: 'destructive',
                  });
                }
              } catch (error) {
                push({
                  title: 'Failed to open',
                  description: error instanceof Error ? error.message : 'Unknown error',
                  variant: 'destructive',
                });
              }
            }}
          >
            Open
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              try {
                await apiClient.deleteDataset(row.original.id);
                push({
                  title: 'Dataset deleted',
                  description: `Deleted dataset: ${row.original.name}`,
                });
                await loadData();
              } catch (error) {
                push({
                  title: 'Delete failed',
                  description: error instanceof Error ? error.message : 'Unknown error',
                  variant: 'destructive',
                });
              }
            }}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6 p-6">
      {/* Import Toolbar */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Import Datasets
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Drag-drop zone */}
          <div
            {...getRootProps()}
            className={`
              flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors
              ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
              ${isUploading ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:border-primary hover:bg-accent/50'}
            `}
          >
            <input {...getInputProps()} />
            <Upload className="h-12 w-12 text-muted-foreground" />
            <p className="text-sm font-medium">
              {isDragActive ? 'Drop files here...' : 'Drag & drop files here, or click to browse'}
            </p>
            <p className="text-xs text-muted-foreground">
              Supported: .txt, .md, .html, .json, .jsonl, .epub
            </p>
            {isUploading && <p className="text-sm text-primary">Uploading...</p>}
          </div>

          {/* Import buttons */}
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => getRootProps().onClick?.({} as any)}>
              <FileText className="mr-2 h-4 w-4" />
              Import Files
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                push({
                  title: 'Folder import',
                  description: 'This feature requires desktop file system access',
                });
              }}
            >
              <FolderOpen className="mr-2 h-4 w-4" />
              Import Folder
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                push({
                  title: 'New dataset',
                  description: 'Creating empty dataset...',
                });
              }}
            >
              <Plus className="mr-2 h-4 w-4" />
              New Dataset
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Novels Section */}
      {novels.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              Novels ({novels.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {novels.map((novel) => (
                <Card key={novel.id} className="overflow-hidden">
                  {novel.cover_url && (
                    <div className="aspect-[3/4] overflow-hidden bg-muted">
                      <img
                        src={novel.cover_url}
                        alt={novel.name}
                        className="h-full w-full object-cover"
                      />
                    </div>
                  )}
                  <CardContent className="p-4">
                    <h3 className="font-medium line-clamp-2">{novel.name}</h3>
                    {typeof novel.meta?.author === 'string' && (
                      <p className="text-xs text-muted-foreground">by {novel.meta.author}</p>
                    )}
                    <div className="mt-2 flex items-center justify-between">
                      <Badge variant="secondary">{novel.chapter_count} chapters</Badge>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          navigate('/compose', { state: { datasetId: novel.id, isNovel: true } });
                        }}
                      >
                        Open
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Datasets Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>All Datasets ({filteredDatasets.length})</CardTitle>
          <div className="flex gap-2">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search datasets..."
              className="w-64"
            />
            <Button
              variant="secondary"
              onClick={() => {
                push({
                  title: 'Export datasets',
                  description: 'Preparing export...',
                });
              }}
            >
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <DataTable columns={datasetColumns} data={filteredDatasets} />
        </CardContent>
      </Card>
    </div>
  );
}
