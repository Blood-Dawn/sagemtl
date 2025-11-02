import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export type MetricCardProps = {
  title: string;
  value: string;
  description?: string;
  icon?: React.ReactNode;
  className?: string;
};

export function MetricCard({ title, value, description, icon, className }: MetricCardProps) {
  return (
    <Card className={cn('relative overflow-hidden', className)}>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-lg font-semibold text-foreground/90">{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </div>
        {icon ? <div className="rounded-xl bg-primary/15 p-3 text-primary">{icon}</div> : null}
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-semibold tracking-tight text-foreground">{value}</p>
      </CardContent>
      <div className="pointer-events-none absolute inset-0 rounded-2xl border border-white/5 opacity-40" />
    </Card>
  );
}
