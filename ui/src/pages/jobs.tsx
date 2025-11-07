import { useCallback, useEffect, useState, useMemo } from 'react';
import type { ColumnDef } from '@tanstack/react-table';
import { RefreshCw, Play, X, Eye, Clock, CheckCircle2, XCircle, Loader2, BarChart3, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { DataTable } from '@/components/data-table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/components/toaster';
import { apiClient } from '@/api/client-v2';
import type { JobRecord } from '@/api/client-v2';
import { useJobWebSocket } from '@/hooks/use-job-websocket';
import { LayoutManager, Widget } from '@/components/layout-manager';

type JobWithProgress = JobRecord & {
  progress?: number;
  isConnected?: boolean;
};

export function JobsPage() {
  const [jobs, setJobs] = useState<JobWithProgress[]>([]);
  const [selectedJob, setSelectedJob] = useState<JobWithProgress | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const { push } = useToast();

  // Load all jobs
  const loadJobs = useCallback(async () => {
    try {
      const result = await apiClient.listJobs();
      setJobs(result.jobs);
    } catch (error) {
      push({
        title: 'Failed to load jobs',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  }, [push]);

  // Initial load
  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadJobs]);

  // Cancel job
  const handleCancel = async (jobId: string) => {
    try {
      await apiClient.cancelJob(jobId);
      push({ title: 'Job cancelled', description: `Job ${jobId} has been cancelled` });
      await loadJobs();
    } catch (error) {
      push({
        title: 'Failed to cancel job',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  // Retry job
  const handleRetry = async (jobId: string) => {
    try {
      await apiClient.retryJob(jobId);
      push({ title: 'Job retried', description: `Job ${jobId} has been queued again` });
      await loadJobs();
    } catch (error) {
      push({
        title: 'Failed to retry job',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const jobColumns: ColumnDef<JobWithProgress>[] = [
    {
      accessorKey: 'id',
      header: 'Job ID',
      cell: ({ row }) => (
        <div className="font-mono text-xs">
          {row.original.id.substring(0, 8)}
        </div>
      ),
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
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const status = row.original.status;
        const Icon =
          status === 'done'
            ? CheckCircle2
            : status === 'failed'
            ? XCircle
            : status === 'running'
            ? Loader2
            : Clock;

        const variant =
          status === 'done'
            ? 'default'
            : status === 'failed'
            ? 'destructive'
            : status === 'running'
            ? 'default'
            : 'secondary';

        return (
          <Badge variant={variant} className="gap-1">
            <Icon className={`h-3 w-3 ${status === 'running' ? 'animate-spin' : ''}`} />
            {status}
          </Badge>
        );
      },
    },
    {
      accessorKey: 'progress',
      header: 'Progress',
      cell: ({ row }) => {
        const job = row.original;
        const progress = job.progress !== undefined ? job.progress * 100 : 0;

        return (
          <div className="flex items-center gap-2">
            <Progress value={progress} className="w-24" />
            <span className="text-xs text-muted-foreground">{Math.round(progress)}%</span>
          </div>
        );
      },
    },
    {
      accessorKey: 'created_at',
      header: 'Created',
      cell: ({ row }) => {
        const date = new Date(row.original.created_at);
        return (
          <div className="text-xs text-muted-foreground">
            {date.toLocaleString()}
          </div>
        );
      },
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const job = row.original;
        return (
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedJob(job)}
            >
              <Eye className="h-4 w-4" />
            </Button>
            {(job.status === 'running' || job.status === 'queued') && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleCancel(job.id)}
              >
                <X className="h-4 w-4" />
              </Button>
            )}
            {job.status === 'failed' && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleRetry(job.id)}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  // Calculate job statistics
  const jobStats = useMemo(() => {
    const total = jobs.length;
    const done = jobs.filter((j) => j.status === 'done').length;
    const failed = jobs.filter((j) => j.status === 'failed').length;
    const running = jobs.filter((j) => j.status === 'running').length;
    const queued = jobs.filter((j) => j.status === 'queued').length;
    const successRate = total > 0 ? ((done / total) * 100).toFixed(1) : '0';

    return { total, done, failed, running, queued, successRate };
  }, [jobs]);

  // Default layout for the Jobs page
  const defaultLayout = [
    { i: 'stats', x: 0, y: 0, w: 12, h: 2, minH: 2, minW: 6 },
    { i: 'controls', x: 0, y: 2, w: 12, h: 1, minH: 1, minW: 6 },
    { i: 'jobs-table', x: 0, y: 3, w: 12, h: 6, minH: 4, minW: 8 },
  ];

  return (
    <div className="h-full p-6">
      <LayoutManager layoutKey="jobsPage" defaultLayout={defaultLayout} rowHeight={80}>
        {/* Statistics Widget */}
        <Widget key="stats" id="stats" title="Job Statistics">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="space-y-1">
              <p className="text-2xl font-bold text-foreground">{jobStats.total}</p>
              <p className="text-xs text-muted-foreground">Total Jobs</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <p className="text-2xl font-bold text-foreground">{jobStats.done}</p>
              </div>
              <p className="text-xs text-muted-foreground">Completed</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <XCircle className="h-4 w-4 text-destructive" />
                <p className="text-2xl font-bold text-foreground">{jobStats.failed}</p>
              </div>
              <p className="text-xs text-muted-foreground">Failed</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 text-primary animate-spin" />
                <p className="text-2xl font-bold text-foreground">{jobStats.running}</p>
              </div>
              <p className="text-xs text-muted-foreground">Running</p>
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" />
                <p className="text-2xl font-bold text-foreground">{jobStats.successRate}%</p>
              </div>
              <p className="text-xs text-muted-foreground">Success Rate</p>
            </div>
          </div>
        </Widget>

        {/* Controls Widget */}
        <Widget key="controls" id="controls" title="Actions">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Manage and monitor your jobs. Drag widgets to rearrange the layout.
            </p>
            <div className="flex gap-2">
              <Button
                variant={autoRefresh ? 'default' : 'outline'}
                size="sm"
                onClick={() => setAutoRefresh(!autoRefresh)}
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
                {autoRefresh ? 'Auto' : 'Manual'}
              </Button>
              <Button variant="outline" size="sm" onClick={loadJobs}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </div>
          </div>
        </Widget>

        {/* Jobs Table Widget */}
        <Widget key="jobs-table" id="jobs-table" title={`All Jobs (${jobs.length})`}>
          <DataTable columns={jobColumns} data={jobs} />
        </Widget>
      </LayoutManager>

      {/* Job Detail Dialog */}
      {selectedJob && (
        <JobDetailDialog
          job={selectedJob}
          onClose={() => setSelectedJob(null)}
          onCancel={handleCancel}
          onRetry={handleRetry}
        />
      )}
    </div>
  );
}

type JobDetailDialogProps = {
  job: JobWithProgress;
  onClose: () => void;
  onCancel: (jobId: string) => void;
  onRetry: (jobId: string) => void;
};

function JobDetailDialog({ job, onClose, onCancel, onRetry }: JobDetailDialogProps) {
  const [liveJob, setLiveJob] = useState<JobWithProgress>(job);
  const [fullLog, setFullLog] = useState<string | null>(null);
  const [isLoadingLog, setIsLoadingLog] = useState(false);
  const { push } = useToast();

  // WebSocket connection for real-time updates
  const { lastMessage, isConnected } = useJobWebSocket({
    jobId: job.id,
    enabled: job.status === 'running' || job.status === 'queued',
    onProgress: (message) => {
      setLiveJob((prev) => ({
        ...prev,
        progress: message.progress,
        status: message.status,
      }));
    },
    onComplete: (message) => {
      setLiveJob((prev) => ({
        ...prev,
        status: message.status,
        progress: 1,
        result: message.result,
      }));
      push({
        title: 'Job completed',
        description: `Job ${job.id.substring(0, 8)} has finished`,
      });
    },
    onError: (message) => {
      setLiveJob((prev) => ({
        ...prev,
        status: 'failed',
        error: message.error,
      }));
      push({
        title: 'Job failed',
        description: message.error || 'Unknown error',
        variant: 'destructive',
      });
    },
  });

  // Load full log file
  const loadFullLog = async () => {
    if (!liveJob.log_path && liveJob.status !== 'failed') {
      return;
    }

    setIsLoadingLog(true);
    try {
      const logData = await apiClient.getJobLog(liveJob.id);
      setFullLog(logData.log);
    } catch (error) {
      console.error('Failed to load job log:', error);
      push({
        title: 'Failed to load log',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setIsLoadingLog(false);
    }
  };

  const progress = liveJob.progress !== undefined ? liveJob.progress * 100 : 0;

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Job Details
            {isConnected && (
              <Badge variant="outline" className="gap-1">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                Live
              </Badge>
            )}
          </DialogTitle>
          <DialogDescription className="font-mono text-xs">
            {liveJob.id}
          </DialogDescription>
        </DialogHeader>

        <Separator />

        <Tabs defaultValue="general" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="logs">
              Logs {liveJob.log_path && <Badge variant="secondary" className="ml-2 h-4 text-[10px]">File</Badge>}
            </TabsTrigger>
            <TabsTrigger value="result">Result</TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="space-y-4 mt-4">
            {/* Job Info */}
            <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Type</p>
              <Badge variant="secondary" className="mt-1 capitalize">
                {liveJob.type}
              </Badge>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Status</p>
              <Badge
                variant={
                  liveJob.status === 'done'
                    ? 'default'
                    : liveJob.status === 'failed'
                    ? 'destructive'
                    : 'secondary'
                }
                className="mt-1 capitalize"
              >
                {liveJob.status}
              </Badge>
            </div>
          </div>

          {/* Progress */}
          <div>
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="font-medium text-muted-foreground">Progress</span>
              <span className="font-medium">{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} />
          </div>

          {/* Metadata */}
          {liveJob.meta && Object.keys(liveJob.meta).length > 0 && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Job Metrics</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {liveJob.meta.runtime_ms && (
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground">Runtime</p>
                    <p className="text-sm font-medium">{liveJob.meta.runtime_ms} ms</p>
                  </div>
                )}
                {liveJob.meta.input_bytes !== undefined && (
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground">Input Size</p>
                    <p className="text-sm font-medium">{(liveJob.meta.input_bytes as number / 1024).toFixed(1)} KB</p>
                  </div>
                )}
                {liveJob.meta.output_bytes !== undefined && (
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground">Output Size</p>
                    <p className="text-sm font-medium">{(liveJob.meta.output_bytes as number / 1024).toFixed(1)} KB</p>
                  </div>
                )}
                {liveJob.meta.provider && (
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground">Provider</p>
                    <p className="text-sm font-medium capitalize">{liveJob.meta.provider as string}</p>
                  </div>
                )}
              </div>
              {Object.keys(liveJob.meta).length > 4 && (
                <details className="mt-2">
                  <summary className="text-xs text-muted-foreground cursor-pointer hover:underline">
                    Show all metadata
                  </summary>
                  <ScrollArea className="max-h-32 mt-2 rounded-lg border border-border/50 bg-muted/20 p-3">
                    <pre className="text-xs font-mono">
                      {JSON.stringify(liveJob.meta, null, 2)}
                    </pre>
                  </ScrollArea>
                </details>
              )}
            </div>
          )}

          {/* Error (if failed) - shown in General tab */}
          {liveJob.error && (
            <div>
              <p className="text-sm font-medium text-destructive mb-2">Error</p>
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
                <p className="text-xs font-mono text-destructive whitespace-pre-wrap">{liveJob.error.split('\n\n')[0]}</p>
              </div>
              {liveJob.log_path && (
                <Button variant="outline" size="sm" className="mt-2" onClick={loadFullLog}>
                  View Full Log File
                </Button>
              )}
            </div>
          )}

          {/* Live Updates */}
          {lastMessage && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Live Updates</p>
              <ScrollArea className="max-h-32 rounded-lg border border-border/50 bg-muted/20 p-3">
                <div className="space-y-1 text-xs font-mono">
                  <div className="text-muted-foreground">
                    [{new Date().toLocaleTimeString()}] {lastMessage.type} - {lastMessage.status}
                  </div>
                </div>
              </ScrollArea>
            </div>
          )}
          </TabsContent>

          {/* Logs Tab */}
          <TabsContent value="logs" className="space-y-4 mt-4">
            {/* In-Memory Logs */}
            {liveJob.log && liveJob.log.length > 0 && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">In-Memory Logs ({liveJob.log.length})</p>
                <ScrollArea className="max-h-64 rounded-lg border border-border/50 bg-muted/20 p-3">
                  <div className="space-y-1">
                    {liveJob.log.map((line, idx) => (
                      <div key={idx} className="text-xs font-mono text-muted-foreground">
                        <span className="text-primary/70">[{idx + 1}]</span> {line}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            )}

            {/* Full Log File */}
            {liveJob.log_path && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-muted-foreground">
                    Log File {liveJob.status === 'failed' && <Badge variant="destructive" className="ml-2">Failed</Badge>}
                  </p>
                  {!fullLog && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={loadFullLog}
                      disabled={isLoadingLog}
                    >
                      {isLoadingLog ? (
                        <>
                          <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                          Loading...
                        </>
                      ) : (
                        'Load Full Log'
                      )}
                    </Button>
                  )}
                </div>
                {fullLog && (
                  <ScrollArea className="max-h-96 rounded-lg border border-border/50 bg-muted/20 p-3">
                    <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap">{fullLog}</pre>
                  </ScrollArea>
                )}
                {!fullLog && !isLoadingLog && (
                  <div className="rounded-lg border border-border/50 bg-muted/20 p-4 text-center text-sm text-muted-foreground">
                    Click "Load Full Log" to view the complete log file with stack traces
                  </div>
                )}
              </div>
            )}

            {!liveJob.log_path && (!liveJob.log || liveJob.log.length === 0) && (
              <div className="rounded-lg border border-border/50 bg-muted/20 p-4 text-center text-sm text-muted-foreground">
                No logs available for this job
              </div>
            )}
          </TabsContent>

          {/* Result Tab */}
          <TabsContent value="result" className="space-y-4 mt-4">
            {liveJob.result ? (
              <ScrollArea className="max-h-96 rounded-lg border border-border/50 bg-muted/20 p-3">
                <pre className="text-xs font-mono">
                  {JSON.stringify(liveJob.result, null, 2)}
                </pre>
              </ScrollArea>
            ) : (
              <div className="rounded-lg border border-border/50 bg-muted/20 p-4 text-center text-sm text-muted-foreground">
                {liveJob.status === 'done' ? 'No result data available' : 'Job has not completed yet'}
              </div>
            )}
          </TabsContent>
        </Tabs>

        {/* Actions */}
        <Separator />
        <div className="flex gap-2 justify-end">
            {(liveJob.status === 'running' || liveJob.status === 'queued') && (
              <Button
                variant="destructive"
                onClick={() => {
                  onCancel(liveJob.id);
                  onClose();
                }}
              >
                <X className="mr-2 h-4 w-4" />
                Cancel Job
              </Button>
            )}
            {liveJob.status === 'failed' && (
              <Button
                variant="default"
                onClick={() => {
                  onRetry(liveJob.id);
                  onClose();
                }}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry Job
              </Button>
            )}
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
