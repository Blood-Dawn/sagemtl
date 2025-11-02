import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

type JobStatus = 'queued' | 'running' | 'done' | 'failed';

const STATUS_VARIANTS: Record<JobStatus, { label: string; variant: React.ComponentProps<typeof Badge>['variant'] }> = {
  queued: { label: 'Queued', variant: 'secondary' },
  running: { label: 'Running', variant: 'warning' },
  done: { label: 'Done', variant: 'success' },
  failed: { label: 'Failed', variant: 'danger' },
};

export function JobStatusBadge({ status, className }: { status: JobStatus; className?: string }) {
  const config = STATUS_VARIANTS[status];
  return <Badge variant={config.variant} className={cn('capitalize', className)}>{config.label}</Badge>;
}

export type { JobStatus };
