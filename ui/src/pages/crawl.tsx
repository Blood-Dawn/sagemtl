import { useState } from 'react';
import type { ColumnDef } from '@tanstack/react-table';
import { Globe, FileText, Settings2, Play, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/data-table';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/components/toaster';
import { apiClient } from '@/api/client-v2';
import type { ChapterResult } from '@/api/client-v2';
import { useJobWebSocket } from '@/hooks/use-job-websocket';

export function CrawlPage() {
  const [mode, setMode] = useState<'url' | 'html'>('url');
  const [url, setUrl] = useState('');
  const [html, setHtml] = useState('');
  const [allowSelectors, setAllowSelectors] = useState('article, .chapter-content, .post-content');
  const [blockSelectors, setBlockSelectors] = useState('nav, footer, .ad, .sidebar');
  const [startChapter, setStartChapter] = useState(1);
  const [endChapter, setEndChapter] = useState(10);
  const [maxConcurrent, setMaxConcurrent] = useState(3);

  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [chapters, setChapters] = useState<ChapterResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  const { push } = useToast();

  // WebSocket for job progress
  const { lastMessage } = useJobWebSocket({
    jobId: currentJobId || '',
    enabled: !!currentJobId && isRunning,
    onProgress: (message) => {
      if (message.progress !== undefined) {
        push({
          title: 'Crawl in progress',
          description: `${Math.round(message.progress * 100)}% complete`,
        });
      }
    },
    onComplete: (message) => {
      setIsRunning(false);
      const result = message.result as { chapters: ChapterResult[] };
      setChapters(result.chapters);
      push({
        title: 'Crawl complete',
        description: `Extracted ${result.chapters.length} chapters`,
      });
    },
    onError: (message) => {
      setIsRunning(false);
      push({
        title: 'Crawl failed',
        description: message.error || 'Unknown error',
        variant: 'destructive',
      });
    },
  });

  // Extract single page
  const handleExtract = async () => {
    try {
      setIsRunning(true);
      const result = await apiClient.extractHTML({
        url: mode === 'url' ? url : undefined,
        html: mode === 'html' ? html : undefined,
        allow_selectors: allowSelectors.split(',').map((s) => s.trim()).filter(Boolean),
        block_selectors: blockSelectors.split(',').map((s) => s.trim()).filter(Boolean),
      });

      setChapters([
        {
          chapter_number: 1,
          title: result.title || 'Extracted Content',
          content: result.text,
          url: url || undefined,
        },
      ]);

      push({
        title: 'Extraction complete',
        description: `Extracted ${result.text.split(' ').length} words`,
      });
    } catch (error) {
      push({
        title: 'Extraction failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setIsRunning(false);
    }
  };

  // Crawl multiple chapters
  const handleCrawlChapters = async () => {
    if (!url) {
      push({
        title: 'URL required',
        description: 'Please enter a base URL for chapter crawling',
        variant: 'destructive',
      });
      return;
    }

    try {
      setIsRunning(true);
      const result = await apiClient.crawlChapters({
        base_url: url,
        start_chapter: startChapter,
        end_chapter: endChapter,
        chapter_url_template: undefined, // Let backend auto-detect
        allow_selectors: allowSelectors.split(',').map((s) => s.trim()).filter(Boolean),
        block_selectors: blockSelectors.split(',').map((s) => s.trim()).filter(Boolean),
        max_concurrent: maxConcurrent,
      });

      setCurrentJobId(result.job_id);

      push({
        title: 'Crawl started',
        description: `Job ${result.job_id} is running`,
      });
    } catch (error) {
      setIsRunning(false);
      push({
        title: 'Crawl failed to start',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const chapterColumns: ColumnDef<ChapterResult>[] = [
    {
      accessorKey: 'chapter_number',
      header: 'Chapter',
      cell: ({ row }) => <Badge variant="outline">Ch. {row.original.chapter_number}</Badge>,
    },
    {
      accessorKey: 'title',
      header: 'Title',
      cell: ({ row }) => (
        <div>
          <p className="font-medium">{row.original.title || 'Untitled'}</p>
          {row.original.url && (
            <p className="text-xs text-muted-foreground truncate max-w-md">{row.original.url}</p>
          )}
        </div>
      ),
    },
    {
      accessorKey: 'content',
      header: 'Words',
      cell: ({ row }) => {
        const wordCount = row.original.content.split(/\s+/).length;
        return <span className="text-muted-foreground">{wordCount.toLocaleString()}</span>;
      },
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            push({
              title: 'Chapter preview',
              description: row.original.content.substring(0, 100) + '...',
            });
          }}
        >
          Preview
        </Button>
      ),
    },
  ];

  const progress = lastMessage?.progress !== undefined ? lastMessage.progress * 100 : 0;

  return (
    <div className="space-y-6 p-6">
      {/* Crawl Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Chapter Extraction
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Input Mode Tabs */}
          <Tabs value={mode} onValueChange={(v) => setMode(v as 'url' | 'html')}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="url">From URL</TabsTrigger>
              <TabsTrigger value="html">From HTML</TabsTrigger>
            </TabsList>

            <TabsContent value="url" className="space-y-4">
              <div>
                <Label htmlFor="url">Base URL</Label>
                <Input
                  id="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/novel/chapter-1"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  The base URL for chapter crawling. The system will auto-detect chapter patterns.
                </p>
              </div>
            </TabsContent>

            <TabsContent value="html" className="space-y-4">
              <div>
                <Label htmlFor="html">HTML Content</Label>
                <Textarea
                  id="html"
                  value={html}
                  onChange={(e) => setHtml(e.target.value)}
                  placeholder="<html>...</html>"
                  rows={8}
                  className="font-mono text-xs"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Paste HTML content to extract chapter text.
                </p>
              </div>
            </TabsContent>
          </Tabs>

          {/* CSS Selectors */}
          <div className="space-y-4 rounded-lg border border-border/50 bg-muted/20 p-4">
            <div className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-muted-foreground" />
              <h3 className="font-medium">CSS Selectors</h3>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label htmlFor="allow-selectors">Allow Selectors</Label>
                <Textarea
                  id="allow-selectors"
                  value={allowSelectors}
                  onChange={(e) => setAllowSelectors(e.target.value)}
                  placeholder="article, .chapter-content"
                  rows={3}
                  className="font-mono text-xs"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Include elements matching these selectors (comma-separated)
                </p>
              </div>

              <div>
                <Label htmlFor="block-selectors">Block Selectors</Label>
                <Textarea
                  id="block-selectors"
                  value={blockSelectors}
                  onChange={(e) => setBlockSelectors(e.target.value)}
                  placeholder="nav, footer, .ad"
                  rows={3}
                  className="font-mono text-xs"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Exclude elements matching these selectors (comma-separated)
                </p>
              </div>
            </div>
          </div>

          {/* Chapter Range (only for URL mode) */}
          {mode === 'url' && (
            <div className="space-y-4 rounded-lg border border-border/50 bg-muted/20 p-4">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <h3 className="font-medium">Chapter Range</h3>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <Label htmlFor="start-chapter">Start Chapter</Label>
                  <Input
                    id="start-chapter"
                    type="number"
                    min={1}
                    value={startChapter}
                    onChange={(e) => setStartChapter(Number(e.target.value))}
                  />
                </div>

                <div>
                  <Label htmlFor="end-chapter">End Chapter</Label>
                  <Input
                    id="end-chapter"
                    type="number"
                    min={1}
                    value={endChapter}
                    onChange={(e) => setEndChapter(Number(e.target.value))}
                  />
                </div>

                <div>
                  <Label htmlFor="max-concurrent">Max Concurrent</Label>
                  <Input
                    id="max-concurrent"
                    type="number"
                    min={1}
                    max={10}
                    value={maxConcurrent}
                    onChange={(e) => setMaxConcurrent(Number(e.target.value))}
                  />
                </div>
              </div>

              <p className="text-xs text-muted-foreground flex items-start gap-1">
                <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                Will crawl chapters {startChapter} to {endChapter} ({endChapter - startChapter + 1} total)
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2">
            {mode === 'url' && (
              <Button onClick={handleCrawlChapters} disabled={isRunning || !url}>
                <Play className="mr-2 h-4 w-4" />
                {isRunning ? 'Crawling...' : 'Crawl Chapters'}
              </Button>
            )}
            <Button
              variant="secondary"
              onClick={handleExtract}
              disabled={isRunning || (mode === 'url' && !url) || (mode === 'html' && !html)}
            >
              <FileText className="mr-2 h-4 w-4" />
              Extract Single Page
            </Button>
          </div>

          {/* Progress Bar */}
          {isRunning && currentJobId && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Progress</span>
                <span className="font-medium">{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} />
              <p className="text-xs text-muted-foreground">Job ID: {currentJobId}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Extracted Chapters */}
      {chapters.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Extracted Chapters ({chapters.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable columns={chapterColumns} data={chapters} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
