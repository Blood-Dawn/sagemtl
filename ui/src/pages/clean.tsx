import { useState } from 'react';
import { UploadCloud, Wand2 } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DiffViewer } from '@/components/diff-viewer';
import { messyText } from '@/mocks/text';
import { postClean } from '@/api';
import { useLayoutStore } from '@/state/layout-store';
import { useToast } from '@/components/toaster';
import { MetricCard } from '@/components/metric-card';

const defaultOptions = {
  smartQuotes: true,
  dashes: true,
  zeroWidth: true,
  linewrap: false,
};

export function CleanPage() {
  const [input, setInput] = useState(messyText);
  const [options, setOptions] = useState(defaultOptions);
  const [preview, setPreview] = useState('');
  const [loading, setLoading] = useState(false);
  const { push } = useToast();
  const select = useLayoutStore((state) => state.select);

  const toggleOption = (key: keyof typeof options) => {
    setOptions((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const runPreview = async () => {
    setLoading(true);
    const result = await postClean({ text: input, options });
    setPreview(result.preview);
    push({ title: 'Preview updated', description: 'Mock normalization complete', variant: 'success' });
    select({ action: 'normalize', preview: `${result.preview.slice(0, 80)}…` });
    setLoading(false);
  };

  const handleSave = () => {
    push({ title: 'Saved', description: 'Cleaned text persisted to cache' });
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="Queued jobs" value="12" description="Active normalization tasks" />
        <MetricCard title="Avg latency" value="420 ms" description="Last 24h" />
        <MetricCard title="Artifacts removed" value="98" description="Current document" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Card className="space-y-6">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Wand2 className="h-5 w-5 text-primary" /> Clean input
              </CardTitle>
              <p className="text-sm text-muted-foreground">Drop raw content to normalize artifacts before translation.</p>
            </div>
            <Button variant="secondary" size="sm">
              <UploadCloud className="mr-2 h-4 w-4" /> Drop file
            </Button>
          </CardHeader>
          <CardContent className="space-y-6">
            <Textarea value={input} onChange={(event) => setInput(event.target.value)} className="min-h-[240px]" />
            <div className="grid gap-3 sm:grid-cols-2">
              {(
                [
                  ['smartQuotes', 'Smart quotes'],
                  ['dashes', 'Normalize dashes'],
                  ['zeroWidth', 'Strip zero-width'],
                  ['linewrap', 'Fix line wraps'],
                ] as Array<[keyof typeof options, string]>
              ).map(([key, label]) => (
                <Label key={key} className="flex items-center justify-between rounded-xl border border-border/60 bg-secondary/30 px-4 py-2">
                  <span>{label}</span>
                  <Switch checked={options[key]} onCheckedChange={() => toggleOption(key)} />
                </Label>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={runPreview} disabled={loading} className="gap-2">
                <Wand2 className="h-4 w-4" /> Preview
              </Button>
              <Button variant="secondary" onClick={handleSave}>
                Save
              </Button>
            </div>
          </CardContent>
        </Card>
        <Card className="h-full">
          <CardHeader>
            <CardTitle>Preview</CardTitle>
          </CardHeader>
          <CardContent>
            {preview ? <DiffViewer original={input} modified={preview} split /> : <EmptyPreview />}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function EmptyPreview() {
  return (
    <div className="flex h-72 flex-col items-center justify-center rounded-2xl border border-dashed border-border/60 text-center text-sm text-muted-foreground">
      Run a preview to see normalized output.
    </div>
  );
}
