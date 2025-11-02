import { useEffect, useMemo, useRef } from 'react';
import { AnsiUp } from 'ansi_up';
import { cn } from '@/lib/utils';

export type LogConsoleProps = {
  logs: string[];
  isCollapsed?: boolean;
  onToggle?: () => void;
};

const ansi = new AnsiUp();
ansi.use_classes = true;

export function LogConsole({ logs, isCollapsed, onToggle }: LogConsoleProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const content = useMemo(
    () =>
      logs.map((line, index) => (
        <div
          dangerouslySetInnerHTML={{ __html: ansi.ansi_to_html(line) }}
          key={`${line}-${index}`}
          className="font-mono text-xs"
        />
      )),
    [logs],
  );

  return (
    <div className={cn('flex h-full flex-col overflow-hidden rounded-t-3xl border-t border-border/60 bg-card/80 shadow-lg transition-all', isCollapsed ? 'h-12' : 'h-64')}>
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center justify-between px-4 py-3 text-xs font-medium uppercase tracking-widest text-muted-foreground hover:text-foreground"
      >
        Console
        <span>{isCollapsed ? 'Expand' : 'Collapse'}</span>
      </button>
      <div className={cn('flex-1 overflow-y-auto px-4 pb-4', isCollapsed ? 'hidden' : 'block')}>
        <div className="space-y-1">
          {content}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
