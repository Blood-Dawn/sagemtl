import { useState } from 'react';
import type { ColumnDef } from '@tanstack/react-table';
import { useLayoutStore } from '@/state/layout-store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/components/data-table';
import { postCrawl } from '@/api';
import { useToast } from '@/components/toaster';

interface CrawlBlock {
  id: string;
  url: string;
  type: string;
  tokens: number;
  preview: string;
}

export function CrawlPage() {
  const [url, setUrl] = useState('https://docs.sagemtl.ai');
  const [depth, setDepth] = useState(1);
  const [renderJs, setRenderJs] = useState(true);
  const [blocks, setBlocks] = useState<CrawlBlock[]>([]);
  const [loading, setLoading] = useState(false);
  const select = useLayoutStore((state) => state.select);
  const { push } = useToast();

  const columns: ColumnDef<CrawlBlock>[] = [
    {
      accessorKey: 'url',
      header: 'URL',
      cell: ({ row }) => (
        <div>
          <p className="font-medium text-foreground">{row.original.url}</p>
          <p className="text-xs text-muted-foreground">{row.original.type}</p>
        </div>
      ),
    },
    {
      accessorKey: 'tokens',
      header: 'Tokens',
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => select({ url: row.original.url, tokens: row.original.tokens, preview: row.original.preview })}
        >
          Open in Inspector
        </Button>
      ),
    },
  ];

  const handleCrawl = async () => {
    setLoading(true);
    const result = await postCrawl({ url, depth, renderJs });
    setBlocks(result.blocks);
    push({ title: 'Crawl complete', description: `Extracted ${result.blocks.length} blocks`, variant: 'success' });
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Configure crawl</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <div className="md:col-span-2">
            <Label htmlFor="url">Target URL</Label>
            <Input id="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://" />
          </div>
          <div>
            <Label htmlFor="depth">Depth</Label>
            <Input
              id="depth"
              type="number"
              min={1}
              max={4}
              value={depth}
              onChange={(event) => setDepth(Number.parseInt(event.target.value, 10))}
            />
          </div>
          <div className="flex items-end justify-between gap-2 rounded-xl border border-border/60 bg-secondary/30 px-3 py-2">
            <div>
              <p className="text-sm font-medium">Render JavaScript</p>
              <p className="text-xs text-muted-foreground">Headless Chrome (Playwright)</p>
            </div>
            <Switch checked={renderJs} onCheckedChange={setRenderJs} />
          </div>
          <div className="md:col-span-4 flex justify-end">
            <Button onClick={handleCrawl} disabled={loading} className="px-6">
              {loading ? 'Fetching…' : 'Run crawl'}
            </Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Extracted blocks</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable columns={columns} data={blocks} searchPlaceholder="Filter by URL" />
        </CardContent>
      </Card>
    </div>
  );
}
