import { useState } from 'react';
import { Upload } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DiffViewer } from '@/components/diff-viewer';
import { useLayoutStore } from '@/state/layout-store';
import { useToast } from '@/components/toaster';
import { postTranslate } from '@/api';

const models = ['nllb-200-3.3B', 'mistral-translate', 'gemini-pro-lingua'];

export function TranslatePage() {
  const [source, setSource] = useState('Montreal is a hub for applied AI research.');
  const [model, setModel] = useState(models[0]);
  const [glossaryName, setGlossaryName] = useState<string | null>(null);
  const [result, setResult] = useState<{ id: string; source: string; target: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const select = useLayoutStore((state) => state.select);
  const { push } = useToast();

  const handleUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setGlossaryName(file.name);
    }
  };

  const handleTranslate = async () => {
    setLoading(true);
    const payload = await postTranslate({ text: source, model });
    setResult(payload);
    push({ title: 'Translation queued', description: `Job ${payload.id} enqueued`, variant: 'success' });
    select({ job: payload.id, model });
    setLoading(false);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <Card>
        <CardHeader>
          <CardTitle>Source content</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea value={source} onChange={(event) => setSource(event.target.value)} className="min-h-[200px]" />
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Model</Label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger>
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  {models.map((name) => (
                    <SelectItem key={name} value={name}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="glossary">Glossary</Label>
              <Button variant="secondary" className="w-full" asChild>
                <label className="flex cursor-pointer items-center justify-center gap-2">
                  <Upload className="h-4 w-4" />
                  {glossaryName ?? 'Upload CSV/TMX'}
                  <input id="glossary" type="file" accept=".csv,.tmx" className="hidden" onChange={handleUpload} />
                </label>
              </Button>
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleTranslate} disabled={loading} className="px-6">
              {loading ? 'Queuing…' : 'Queue translation'}
            </Button>
            {result ? (
              <Button variant="ghost" onClick={() => select({ job: result.id, preview: result.target.slice(0, 80) })}>
                View in Inspector
              </Button>
            ) : null}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Preview</CardTitle>
        </CardHeader>
        <CardContent>
          {result ? (
            <DiffViewer original={result.source} modified={result.target} split />
          ) : (
            <div className="flex h-72 flex-col items-center justify-center rounded-2xl border border-dashed border-border/60 text-sm text-muted-foreground">
              Queue a translation to review side-by-side diff.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
