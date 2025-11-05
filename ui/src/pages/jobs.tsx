import { useCallback, useEffect, useState } from 'react';
import type { ColumnDef } from '@tanstack/react-table';
import { RefreshCw, Play, X, Eye, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { DataTable } from '@/components/data-table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/toaster';
import { apiClient } from '@/api/client-v2';
import type { JobRecord } from '@/api/client-v2';
import { useJobWebSocket } from '@/hooks/use-job-websocket';

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

  return (
    <div className="space-y-6 p-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Jobs ({jobs.length})</CardTitle>
          <div className="flex gap-2">
            <Button
              variant={autoRefresh ? 'default' : 'outline'}
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
              {autoRefresh ? 'Auto-refresh' : 'Manual'}
            </Button>
            <Button variant="outline" size="sm" onClick={loadJobs}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <DataTable columns={jobColumns} data={jobs} />
        </CardContent>
      </Card>

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

        <div className="space-y-4">
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
          {liveJob.metadata && Object.keys(liveJob.metadata).length > 0 && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Metadata</p>
              <ScrollArea className="max-h-32 rounded-lg border border-border/50 bg-muted/20 p-3">
                <pre className="text-xs font-mono">
                  {JSON.stringify(liveJob.metadata, null, 2)}
                </pre>
              </ScrollArea>
            </div>
          )}

          {/* Result (if completed) */}
          {liveJob.result && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Result</p>
              <ScrollArea className="max-h-48 rounded-lg border border-border/50 bg-muted/20 p-3">
                <pre className="text-xs font-mono">
                  {JSON.stringify(liveJob.result, null, 2)}
                </pre>
              </ScrollArea>
            </div>
          )}

          {/* Error (if failed) */}
          {liveJob.error && (
            <div>
              <p className="text-sm font-medium text-destructive mb-2">Error</p>
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3">
                <p className="text-xs font-mono text-destructive">{liveJob.error}</p>
              </div>
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

          {/* Actions */}
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
        </div>
      </DialogContent>
    </Dialog>
  );
}
