import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { JobStatusBadge } from '@/components/job-status-badge';
import { getJobs } from '@/api';
import type { Job } from '@/mocks/jobs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { useLayoutStore } from '@/state/layout-store';

export function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<Job | null>(null);
  const select = useLayoutStore((state) => state.select);

  useEffect(() => {
    getJobs().then(setJobs);
  }, []);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Jobs</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {jobs.map((job) => (
            <button
              type="button"
              key={job.id}
              onClick={() => {
                setSelected(job);
                select({ job: job.id, status: job.status });
              }}
              className="rounded-2xl border border-border/60 bg-card/70 p-4 text-left shadow-soft transition hover:border-primary/60 hover:shadow-lg"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{job.id}</p>
                  <h3 className="text-lg font-semibold">{job.name}</h3>
                </div>
                <JobStatusBadge status={job.status} />
              </div>
              <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
                <span>{new Date(job.createdAt).toLocaleString()}</span>
                {job.eta ? <span>ETA {job.eta}</span> : null}
              </div>
              {job.gpu ? (
                <Badge variant="secondary" className="mt-4 uppercase">
                  GPU {job.gpu}
                </Badge>
              ) : null}
            </button>
          ))}
        </CardContent>
      </Card>
      <JobDetail job={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

type JobDetailProps = {
  job: Job | null;
  onClose: () => void;
};

function JobDetail({ job, onClose }: JobDetailProps) {
  return (
    <Dialog open={Boolean(job)} onOpenChange={(open) => (!open ? onClose() : null)}>
      <DialogContent className="max-w-3xl">
        {job ? (
          <>
            <DialogHeader>
              <DialogTitle>{job.name}</DialogTitle>
              <DialogDescription className="flex items-center gap-2 text-sm">
                <JobStatusBadge status={job.status} />
                <span>{job.id}</span>
              </DialogDescription>
            </DialogHeader>
            <Separator />
            <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
              <ScrollArea className="max-h-80 rounded-xl border border-border/60 bg-secondary/20 p-4">
                <div className="space-y-4">
                  {job.steps.map((step) => (
                    <div key={step.name} className="rounded-xl bg-card/80 p-3 shadow-sm">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-semibold">{step.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(step.startedAt).toLocaleTimeString()} →{' '}
                            {step.completedAt ? new Date(step.completedAt).toLocaleTimeString() : 'pending'}
                          </p>
                        </div>
                        <JobStatusBadge status={step.status} />
                      </div>
                      <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
                        {step.logs.map((log) => (
                          <li key={log}>• {log}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </ScrollArea>
              <div className="space-y-4">
                <div className="rounded-xl border border-border/60 bg-card/70 p-4">
                  <p className="text-sm font-semibold">Progress</p>
                  <Progress value={job.status === 'done' ? 100 : job.status === 'failed' ? 100 : job.status === 'running' ? 60 : 5} />
                  <p className="mt-2 text-xs text-muted-foreground">
                    Created {new Date(job.createdAt).toLocaleString()}
                  </p>
                </div>
                <div className="rounded-xl border border-border/60 bg-card/70 p-4">
                  <p className="text-sm font-semibold">Live log</p>
                  <div className="mt-2 max-h-40 overflow-auto text-xs text-muted-foreground">
                    {job.steps.flatMap((step) => step.logs).map((line, index) => (
                      <div key={`${line}-${index}`}>{line}</div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
