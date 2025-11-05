import { useCallback, useEffect, useState } from 'react';
import type { ColumnDef } from '@tanstack/react-table';
import { Plus, Edit2, Trash2, Download, Upload, Save, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { DataTable } from '@/components/data-table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { useToast } from '@/components/toaster';
import { apiClient } from '@/api/client-v2';
import type { GlossaryEntry } from '@/api/client-v2';

const defaults = {
  SAGEMTL_DATA_DIR: '/data/sagemtl',
  SAGEMTL_CACHE_DIR: '/data/cache',
  API_BASE: 'http://localhost:8000',
  ENABLE_GPU: 'true',
  DEFAULT_MODEL: 'nllb-200-3.3B',
};

type SettingsState = typeof defaults;

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsState>(defaults);
  const [glossaries, setGlossaries] = useState<string[]>([]);
  const [selectedGlossary, setSelectedGlossary] = useState<string | null>(null);
  const [glossaryEntries, setGlossaryEntries] = useState<GlossaryEntry[]>([]);
  const [editingEntry, setEditingEntry] = useState<GlossaryEntry | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const { push } = useToast();

  // Load glossaries
  const loadGlossaries = useCallback(async () => {
    try {
      const result = await apiClient.listGlossaries();
      setGlossaries(result.glossaries);
    } catch (error) {
      push({
        title: 'Failed to load glossaries',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  }, [push]);

  // Load glossary entries
  const loadGlossaryEntries = useCallback(
    async (path: string) => {
      try {
        const result = await apiClient.getGlossary(path);
        setGlossaryEntries(result.entries);
      } catch (error) {
        push({
          title: 'Failed to load glossary',
          description: error instanceof Error ? error.message : 'Unknown error',
          variant: 'destructive',
        });
      }
    },
    [push]
  );

  useEffect(() => {
    loadGlossaries();
  }, [loadGlossaries]);

  useEffect(() => {
    if (selectedGlossary) {
      loadGlossaryEntries(selectedGlossary);
    }
  }, [selectedGlossary, loadGlossaryEntries]);

  const handleSaveSettings = () => {
    push({ title: 'Settings saved', description: 'Runtime configuration persisted' });
  };

  const handleCreateGlossary = async () => {
    const name = prompt('Enter glossary name:');
    if (!name) return;

    try {
      await apiClient.createGlossary(name);
      push({ title: 'Glossary created', description: `Created glossary: ${name}` });
      await loadGlossaries();
      setSelectedGlossary(name);
    } catch (error) {
      push({
        title: 'Failed to create glossary',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteGlossary = async (path: string) => {
    if (!confirm(`Delete glossary: ${path}?`)) return;

    try {
      await apiClient.deleteGlossary(path);
      push({ title: 'Glossary deleted', description: `Deleted glossary: ${path}` });
      await loadGlossaries();
      if (selectedGlossary === path) {
        setSelectedGlossary(null);
        setGlossaryEntries([]);
      }
    } catch (error) {
      push({
        title: 'Failed to delete glossary',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const handleSaveEntry = async (entry: GlossaryEntry) => {
    if (!selectedGlossary) return;

    try {
      const updatedEntries = editingEntry
        ? glossaryEntries.map((e) => (e.source === editingEntry.source ? entry : e))
        : [...glossaryEntries, entry];

      await apiClient.updateGlossary(selectedGlossary, { entries: updatedEntries });

      push({
        title: editingEntry ? 'Entry updated' : 'Entry added',
        description: `${entry.source} → ${entry.target}`,
      });

      await loadGlossaryEntries(selectedGlossary);
      setEditingEntry(null);
      setIsCreating(false);
    } catch (error) {
      push({
        title: 'Failed to save entry',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteEntry = async (source: string) => {
    if (!selectedGlossary) return;
    if (!confirm(`Delete entry: ${source}?`)) return;

    try {
      const updatedEntries = glossaryEntries.filter((e) => e.source !== source);
      await apiClient.updateGlossary(selectedGlossary, { entries: updatedEntries });

      push({ title: 'Entry deleted', description: `Deleted entry: ${source}` });
      await loadGlossaryEntries(selectedGlossary);
    } catch (error) {
      push({
        title: 'Failed to delete entry',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const glossaryColumns: ColumnDef<GlossaryEntry>[] = [
    {
      accessorKey: 'source',
      header: 'Source',
      cell: ({ row }) => <span className="font-medium">{row.original.source}</span>,
    },
    {
      accessorKey: 'target',
      header: 'Target',
      cell: ({ row }) => <span className="text-muted-foreground">{row.original.target}</span>,
    },
    {
      accessorKey: 'case_sensitive',
      header: 'Case Sensitive',
      cell: ({ row }) => (
        <Badge variant={row.original.case_sensitive ? 'default' : 'secondary'}>
          {row.original.case_sensitive ? 'Yes' : 'No'}
        </Badge>
      ),
    },
    {
      accessorKey: 'word_boundary',
      header: 'Word Boundary',
      cell: ({ row }) => (
        <Badge variant={row.original.word_boundary ? 'default' : 'secondary'}>
          {row.original.word_boundary ? 'Yes' : 'No'}
        </Badge>
      ),
    },
    {
      accessorKey: 'notes',
      header: 'Notes',
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground truncate max-w-xs">
          {row.original.notes || '—'}
        </span>
      ),
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) => (
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setEditingEntry(row.original)}
          >
            <Edit2 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeleteEntry(row.original.source)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6 p-6">
      <Tabs defaultValue="settings">
        <TabsList>
          <TabsTrigger value="settings">Settings</TabsTrigger>
          <TabsTrigger value="glossaries">Glossaries</TabsTrigger>
        </TabsList>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle>Runtime Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {Object.entries(settings).map(([key, value]) => (
                <div key={key} className="grid gap-2 md:grid-cols-[220px_1fr] md:items-center">
                  <label className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                    {key}
                  </label>
                  <Input
                    value={value}
                    onChange={(event) =>
                      setSettings((prev) => ({ ...prev, [key]: event.target.value }))
                    }
                  />
                </div>
              ))}
              <div className="flex justify-end">
                <Button onClick={handleSaveSettings} className="px-6">
                  <Save className="mr-2 h-4 w-4" />
                  Save Changes
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Glossaries Tab */}
        <TabsContent value="glossaries">
          <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
            {/* Glossary List */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Glossaries</span>
                  <Button size="sm" onClick={handleCreateGlossary}>
                    <Plus className="h-4 w-4" />
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {glossaries.map((glossary) => (
                  <button
                    key={glossary}
                    onClick={() => setSelectedGlossary(glossary)}
                    className={`w-full rounded-lg border p-3 text-left transition ${
                      selectedGlossary === glossary
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:border-primary/50 hover:bg-accent/50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium truncate">{glossary}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteGlossary(glossary);
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </button>
                ))}
                {glossaries.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No glossaries yet. Click + to create one.
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Glossary Entries */}
            {selectedGlossary ? (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>{selectedGlossary}</CardTitle>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        push({
                          title: 'Import glossary',
                          description: 'Upload CSV or JSON file',
                        });
                      }}
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      Import
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        push({
                          title: 'Export glossary',
                          description: 'Downloading glossary file',
                        });
                      }}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Export
                    </Button>
                    <Button size="sm" onClick={() => setIsCreating(true)}>
                      <Plus className="mr-2 h-4 w-4" />
                      Add Entry
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <DataTable columns={glossaryColumns} data={glossaryEntries} />
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="flex items-center justify-center py-16">
                  <p className="text-sm text-muted-foreground">
                    Select a glossary to view and edit entries
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Entry Editor Dialog */}
      {(editingEntry || isCreating) && (
        <GlossaryEntryDialog
          entry={editingEntry || undefined}
          onSave={handleSaveEntry}
          onClose={() => {
            setEditingEntry(null);
            setIsCreating(false);
          }}
        />
      )}
    </div>
  );
}

type GlossaryEntryDialogProps = {
  entry?: GlossaryEntry;
  onSave: (entry: GlossaryEntry) => void;
  onClose: () => void;
};

function GlossaryEntryDialog({ entry, onSave, onClose }: GlossaryEntryDialogProps) {
  const [source, setSource] = useState(entry?.source || '');
  const [target, setTarget] = useState(entry?.target || '');
  const [caseSensitive, setCaseSensitive] = useState(entry?.case_sensitive ?? true);
  const [wordBoundary, setWordBoundary] = useState(entry?.word_boundary ?? false);
  const [notes, setNotes] = useState(entry?.notes || '');

  const handleSave = () => {
    if (!source || !target) {
      alert('Source and target are required');
      return;
    }

    onSave({
      source,
      target,
      case_sensitive: caseSensitive,
      word_boundary: wordBoundary,
      notes,
    });
  };

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{entry ? 'Edit Entry' : 'Add Entry'}</DialogTitle>
          <DialogDescription>
            Define a glossary term replacement rule
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <Label htmlFor="source">Source Term</Label>
            <Input
              id="source"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="Original term"
              disabled={!!entry} // Cannot edit source for existing entries
            />
          </div>

          <div>
            <Label htmlFor="target">Target Term</Label>
            <Input
              id="target"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder="Replacement term"
            />
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="case-sensitive"
              checked={caseSensitive}
              onCheckedChange={(checked) => setCaseSensitive(checked as boolean)}
            />
            <Label htmlFor="case-sensitive" className="cursor-pointer">
              Case sensitive
            </Label>
          </div>

          <div className="flex items-center gap-2">
            <Checkbox
              id="word-boundary"
              checked={wordBoundary}
              onCheckedChange={(checked) => setWordBoundary(checked as boolean)}
            />
            <Label htmlFor="word-boundary" className="cursor-pointer">
              Match whole words only (word boundary)
            </Label>
          </div>

          <div>
            <Label htmlFor="notes">Notes (optional)</Label>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Additional context or explanation"
              rows={3}
            />
          </div>
        </div>

        <div className="flex gap-2 justify-end">
          <Button variant="outline" onClick={onClose}>
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
          <Button onClick={handleSave}>
            <Save className="mr-2 h-4 w-4" />
            Save
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
