import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/toaster';

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
  const { push } = useToast();

  const handleSave = () => {
    push({ title: 'Settings saved', description: 'Runtime configuration persisted (mock)' });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Runtime configuration</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {Object.entries(settings).map(([key, value]) => (
          <div key={key} className="grid gap-2 md:grid-cols-[220px_1fr] md:items-center">
            <label className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{key}</label>
            <Input
              value={value}
              onChange={(event) => setSettings((prev) => ({ ...prev, [key]: event.target.value }))}
            />
          </div>
        ))}
        <div className="flex justify-end">
          <Button onClick={handleSave} className="px-6">
            Save changes
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
