/**
 * Compose Page - Unified Clean + Translate + Glossary Pipeline
 *
 * Layout:
 * - Left: Source Editor + Dataset Picker
 * - Center: Tabs (Clean, Translate, Glossary, Pipeline)
 * - Right: Monaco Diff Editor (Before/After/Side-by-Side)
 */

import { useState } from 'react';
import { DiffEditor } from '@monaco-editor/react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Loader2, FileText, Languages, BookText, Workflow } from 'lucide-react';
import { apiClient, CleanOptions } from '@/api/client-v2';
import { useToast } from '@/hooks/use-toast';
import { useJobWebSocket } from '@/hooks/use-job-websocket';

export function ComposePage() {
  const [sourceText, setSourceText] = useState('');
  const [cleanedText, setCleanedText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [diffMode, setDiffMode] = useState<'inline' | 'side-by-side'>('side-by-side');

  const { toast } = useToast();

  // Clean options state
  const [cleanOptions, setCleanOptions] = useState<CleanOptions>({
    smart_quotes: true,
    em_dash: true,
    minus_sign: true,
    nbsp_to_space: true,
    zero_width: true,
    collapse_blank_lines: true,
    ensure_trailing_lf: true,
    trim_trailing_spaces: true,
    unicode_nfkc: true,
    normalize_eol: 'lf',
    apply_glossary: false,
  });

  // Translate options state
  const [translateOptions, setTranslateOptions] = useState({
    src_lang: 'auto',
    tgt_lang: 'en',
    provider: 'echo',
    glossary_path: '',
    apply_glossary_pre: false,
    apply_glossary_post: true,
    save_to_dataset: false,
  });

  // WebSocket for job tracking
  useJobWebSocket({
    jobId: currentJobId || '',
    enabled: !!currentJobId,
    onProgress: (message) => {
      console.log('Job progress:', message);
    },
    onComplete: (message) => {
      console.log('Job complete:', message);
      setIsLoading(false);

      if (message.result?.text) {
        setTranslatedText(message.result.text as string);
      }

      toast({
        title: 'Translation Complete',
        description: 'Your translation job has finished successfully.',
      });

      setCurrentJobId(null);
    },
    onError: (message) => {
      console.error('Job error:', message);
      setIsLoading(false);

      toast({
        title: 'Translation Failed',
        description: message.error || 'An error occurred during translation.',
        variant: 'destructive',
      });

      setCurrentJobId(null);
    },
  });

  const handleClean = async () => {
    if (!sourceText.trim()) {
      toast({
        title: 'No text',
        description: 'Please enter some text to clean.',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);

    try {
      const response = await apiClient.composeClean({
        text: sourceText,
        options: cleanOptions,
      });

      setCleanedText(response.text);

      toast({
        title: 'Text Cleaned',
        description: response.glossary_applied
          ? 'Text cleaned and glossary applied.'
          : 'Text cleaned successfully.',
      });
    } catch (error) {
      console.error('Clean error:', error);
      toast({
        title: 'Clean Failed',
        description: error instanceof Error ? error.message : 'Failed to clean text',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTranslate = async () => {
    const textToTranslate = cleanedText || sourceText;

    if (!textToTranslate.trim()) {
      toast({
        title: 'No text',
        description: 'Please enter some text to translate.',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);

    try {
      const response = await apiClient.composeTranslate({
        text: textToTranslate,
        ...translateOptions,
      });

      setCurrentJobId(response.job_id);

      toast({
        title: 'Translation Queued',
        description: `Job ${response.job_id} is now processing...`,
      });
    } catch (error) {
      console.error('Translate error:', error);
      setIsLoading(false);
      toast({
        title: 'Translation Failed',
        description: error instanceof Error ? error.message : 'Failed to queue translation',
        variant: 'destructive',
      });
    }
  };

  const handleRunPipeline = async () => {
    if (!sourceText.trim()) {
      toast({
        title: 'No text',
        description: 'Please enter some text to process.',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);

    try {
      const response = await apiClient.composePipeline({
        source_text: sourceText,
        clean_options: cleanOptions,
        ...translateOptions,
      });

      setCurrentJobId(response.translate_job_id);

      toast({
        title: 'Pipeline Started',
        description: response.message,
      });
    } catch (error) {
      console.error('Pipeline error:', error);
      setIsLoading(false);
      toast({
        title: 'Pipeline Failed',
        description: error instanceof Error ? error.message : 'Failed to start pipeline',
        variant: 'destructive',
      });
    }
  };

  const updateCleanOption = (key: keyof CleanOptions, value: boolean | string) => {
    setCleanOptions((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="h-full flex gap-4 p-6">
      {/* Left Panel - Source Editor */}
      <div className="flex-1 flex flex-col gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Source Text
            </CardTitle>
            <CardDescription>Enter or paste your source text here</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              placeholder="Enter text to process..."
              className="min-h-[400px] font-mono"
            />
          </CardContent>
        </Card>
      </div>

      {/* Center Panel - Options Tabs */}
      <div className="flex-1 flex flex-col">
        <Tabs defaultValue="clean" className="flex-1">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="clean">Clean</TabsTrigger>
            <TabsTrigger value="translate">Translate</TabsTrigger>
            <TabsTrigger value="glossary">Glossary</TabsTrigger>
            <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
          </TabsList>

          {/* Clean Tab */}
          <TabsContent value="clean" className="flex-1">
            <Card>
              <CardHeader>
                <CardTitle>Clean Options</CardTitle>
                <CardDescription>Configure text normalization settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="smart-quotes"
                      checked={cleanOptions.smart_quotes}
                      onCheckedChange={(checked) => updateCleanOption('smart_quotes', !!checked)}
                    />
                    <Label htmlFor="smart-quotes">Smart Quotes → Straight</Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="em-dash"
                      checked={cleanOptions.em_dash}
                      onCheckedChange={(checked) => updateCleanOption('em_dash', !!checked)}
                    />
                    <Label htmlFor="em-dash">Em-dash → Hyphen</Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="zero-width"
                      checked={cleanOptions.zero_width}
                      onCheckedChange={(checked) => updateCleanOption('zero_width', !!checked)}
                    />
                    <Label htmlFor="zero-width">Remove Zero-width</Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="nbsp"
                      checked={cleanOptions.nbsp_to_space}
                      onCheckedChange={(checked) => updateCleanOption('nbsp_to_space', !!checked)}
                    />
                    <Label htmlFor="nbsp">NBSP → Space</Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="collapse-blank"
                      checked={cleanOptions.collapse_blank_lines}
                      onCheckedChange={(checked) => updateCleanOption('collapse_blank_lines', !!checked)}
                    />
                    <Label htmlFor="collapse-blank">Collapse Blank Lines</Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="trim-trailing"
                      checked={cleanOptions.trim_trailing_spaces}
                      onCheckedChange={(checked) => updateCleanOption('trim_trailing_spaces', !!checked)}
                    />
                    <Label htmlFor="trim-trailing">Trim Trailing Spaces</Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="unicode-nfkc"
                      checked={cleanOptions.unicode_nfkc}
                      onCheckedChange={(checked) => updateCleanOption('unicode_nfkc', !!checked)}
                    />
                    <Label htmlFor="unicode-nfkc">Unicode NFKC</Label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="apply-glossary"
                      checked={cleanOptions.apply_glossary}
                      onCheckedChange={(checked) => updateCleanOption('apply_glossary', !!checked)}
                    />
                    <Label htmlFor="apply-glossary">Apply Glossary</Label>
                  </div>
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label htmlFor="normalize-eol">Normalize EOL</Label>
                  <Select
                    value={cleanOptions.normalize_eol as string}
                    onValueChange={(value) => updateCleanOption('normalize_eol', value)}
                  >
                    <SelectTrigger id="normalize-eol">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="lf">LF (Unix)</SelectItem>
                      <SelectItem value="crlf">CRLF (Windows)</SelectItem>
                      <SelectItem value="preserve">Preserve</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {cleanOptions.apply_glossary && (
                  <div className="space-y-2">
                    <Label htmlFor="glossary-path">Glossary Path</Label>
                    <Input
                      id="glossary-path"
                      value={cleanOptions.glossary_path || ''}
                      onChange={(e) => updateCleanOption('glossary_path', e.target.value)}
                      placeholder="~/.sagemtl/glossaries/terms.csv"
                    />
                  </div>
                )}

                <Button onClick={handleClean} disabled={isLoading} className="w-full">
                  {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Clean Text
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Translate Tab */}
          <TabsContent value="translate" className="flex-1">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Languages className="h-5 w-5" />
                  Translation Settings
                </CardTitle>
                <CardDescription>Configure translation options</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="src-lang">Source Language</Label>
                    <Input
                      id="src-lang"
                      value={translateOptions.src_lang}
                      onChange={(e) => setTranslateOptions((prev) => ({ ...prev, src_lang: e.target.value }))}
                      placeholder="auto"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="tgt-lang">Target Language</Label>
                    <Input
                      id="tgt-lang"
                      value={translateOptions.tgt_lang}
                      onChange={(e) => setTranslateOptions((prev) => ({ ...prev, tgt_lang: e.target.value }))}
                      placeholder="en"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="provider">Provider</Label>
                  <Select
                    value={translateOptions.provider}
                    onValueChange={(value) => setTranslateOptions((prev) => ({ ...prev, provider: value }))}
                  >
                    <SelectTrigger id="provider">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="echo">Echo (Test)</SelectItem>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="anthropic">Anthropic</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="glossary-path-translate">Glossary Path (Optional)</Label>
                  <Input
                    id="glossary-path-translate"
                    value={translateOptions.glossary_path}
                    onChange={(e) => setTranslateOptions((prev) => ({ ...prev, glossary_path: e.target.value }))}
                    placeholder="~/.sagemtl/glossaries/names.csv"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="apply-glossary-post"
                    checked={translateOptions.apply_glossary_post}
                    onCheckedChange={(checked) =>
                      setTranslateOptions((prev) => ({ ...prev, apply_glossary_post: !!checked }))
                    }
                  />
                  <Label htmlFor="apply-glossary-post">Apply Glossary After Translation</Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="save-to-dataset"
                    checked={translateOptions.save_to_dataset}
                    onCheckedChange={(checked) =>
                      setTranslateOptions((prev) => ({ ...prev, save_to_dataset: !!checked }))
                    }
                  />
                  <Label htmlFor="save-to-dataset">Save to Dataset</Label>
                </div>

                <Button onClick={handleTranslate} disabled={isLoading} className="w-full">
                  {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Translate
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Glossary Tab */}
          <TabsContent value="glossary" className="flex-1">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BookText className="h-5 w-5" />
                  Glossary Management
                </CardTitle>
                <CardDescription>Manage translation glossaries</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Glossary management UI coming soon. For now, create CSV or JSON files in ~/.sagemtl/glossaries/
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Pipeline Tab */}
          <TabsContent value="pipeline" className="flex-1">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Workflow className="h-5 w-5" />
                  Full Pipeline
                </CardTitle>
                <CardDescription>Run the complete workflow: Clean → Translate → Save</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <h4 className="font-medium">Pipeline Steps:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-muted-foreground">
                    <li>Clean source text with selected options</li>
                    <li>Apply pre-translation glossary (if enabled)</li>
                    <li>Queue translation job</li>
                    <li>Apply post-translation glossary (if enabled)</li>
                    <li>Save result to dataset (if enabled)</li>
                  </ol>
                </div>

                <Separator />

                <div className="space-y-2">
                  <p className="text-sm">
                    <strong>Clean Options:</strong> {Object.entries(cleanOptions).filter(([_, v]) => v === true).length}{' '}
                    enabled
                  </p>
                  <p className="text-sm">
                    <strong>Translation:</strong> {translateOptions.src_lang} → {translateOptions.tgt_lang}
                  </p>
                  <p className="text-sm">
                    <strong>Provider:</strong> {translateOptions.provider}
                  </p>
                </div>

                <Button onClick={handleRunPipeline} disabled={isLoading} className="w-full" size="lg">
                  {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Run Complete Pipeline
                </Button>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Right Panel - Diff Viewer */}
      <div className="flex-1 flex flex-col gap-4">
        <Card className="flex-1">
          <CardHeader>
            <CardTitle>Preview</CardTitle>
            <CardDescription className="flex items-center justify-between">
              <span>Before vs After comparison</span>
              <Select value={diffMode} onValueChange={(value: any) => setDiffMode(value)}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="side-by-side">Side-by-Side</SelectItem>
                  <SelectItem value="inline">Inline</SelectItem>
                </SelectContent>
              </Select>
            </CardDescription>
          </CardHeader>
          <CardContent className="flex-1">
            <div className="h-[600px]">
              <DiffEditor
                original={sourceText}
                modified={translatedText || cleanedText || sourceText}
                language="plaintext"
                theme="vs-dark"
                options={{
                  readOnly: true,
                  renderSideBySide: diffMode === 'side-by-side',
                  minimap: { enabled: false },
                }}
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
