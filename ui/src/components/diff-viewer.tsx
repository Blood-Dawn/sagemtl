import diff_match_patch from 'diff-match-patch';
import { useMemo } from 'react';
import { cn } from '@/lib/utils';

type DiffTuple = [number, string];

export type DiffViewerProps = {
  original: string;
  modified: string;
  split?: boolean;
};

const dmp = new diff_match_patch();

export function DiffViewer({ original, modified, split = false }: DiffViewerProps) {
  const diffs = useMemo<DiffTuple[]>(() => {
    const result = dmp.diff_main(original, modified);
    dmp.diff_cleanupSemantic(result);
    return result as DiffTuple[];
  }, [original, modified]);

  if (split) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <DiffBlock title="Source" diffs={diffs} type="original" />
        <DiffBlock title="Preview" diffs={diffs} type="modified" />
      </div>
    );
  }

  return <DiffBlock title="Diff" diffs={diffs} />;
}

type DiffBlockProps = {
  title: string;
  diffs: DiffTuple[];
  type?: 'original' | 'modified';
};

function DiffBlock({ title, diffs, type }: DiffBlockProps) {
  return (
    <div className="rounded-2xl border border-border/60 bg-secondary/40 p-4">
      <div className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wider">{title}</div>
      <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words text-sm leading-relaxed">
        {diffs.map(([operation, text], index) => {
          if (type === 'original' && operation === diff_match_patch.DIFF_INSERT) return null;
          if (type === 'modified' && operation === diff_match_patch.DIFF_DELETE) return null;
          const highlight =
            operation === diff_match_patch.DIFF_INSERT
              ? 'bg-emerald-500/20 text-emerald-100'
              : operation === diff_match_patch.DIFF_DELETE
                ? 'bg-rose-500/20 text-rose-100 line-through'
                : 'text-foreground';
          return (
            <span key={`${operation}-${index}`} className={cn('rounded px-1 py-0.5', highlight)}>
              {text}
            </span>
          );
        })}
      </pre>
    </div>
  );
}
