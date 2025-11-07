import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { ChevronRight, Menu, Moon, Search as SearchIcon, SunMedium, Terminal, Play } from 'lucide-react';
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels';
import { navSections } from '@/config/navigation';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTheme } from '@/components/theme-provider';
import { useLayoutStore } from '@/state/layout-store';
import { LogConsole } from '@/components/log-console';
import { mockLogs } from '@/mocks/logs';

const breadcrumbs: Record<string, string[]> = {
  '/compose': ['Workflow', 'Compose'],
  '/crawl': ['Workflow', 'Crawl'],
  '/clean': ['Workflow', 'Clean'],
  '/translate': ['Workflow', 'Translate'],
  '/datasets': ['Data', 'Datasets'],
  '/jobs': ['Data', 'Jobs'],
  '/settings': ['Settings'],
};

export function AppShell() {
  const location = useLocation();
  const path = location.pathname === '/' ? '/compose' : location.pathname;
  const crumb = breadcrumbs[path] ?? ['Workflow'];
  const { theme, toggleTheme } = useTheme();
  const { inspectorOpen, toggleInspector, consoleCollapsed, toggleConsole } = useLayoutStore();
  const [logs, setLogs] = useState<string[]>(mockLogs.slice(0, 2));

  useEffect(() => {
    const queue = [...mockLogs];
    let mounted = true;
    const interval = setInterval(() => {
      if (!mounted) return;
      setLogs((prev) => {
        const next = queue[prev.length % queue.length];
        if (!next) return prev;
        return [...prev, next];
      });
    }, 2000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="hidden w-64 flex-shrink-0 border-r border-border/60 bg-card/40 px-4 py-8 lg:flex">
        <div className="flex w-full flex-col gap-8">
          <div>
            <div className="text-sm font-semibold uppercase tracking-[0.3em] text-primary">SageMTL</div>
            <p className="mt-2 text-xs text-muted-foreground">Cognitive data operations suite</p>
          </div>
          <nav className="flex flex-col gap-6">
            {navSections.map((section) => (
              <div key={section.label} className="space-y-3">
                <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{section.label}</p>
                <div className="space-y-1">
                  {section.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-muted-foreground transition hover:bg-secondary/60 hover:text-foreground',
                          (isActive || path === item.to) && 'bg-secondary/80 text-foreground shadow-inner',
                        )
                      }
                    >
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              </div>
            ))}
          </nav>
        </div>
      </aside>
      <div className="flex flex-1 flex-col">
        <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 px-4 py-4 backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Button variant="ghost" size="icon" className="lg:hidden">
                <Menu className="h-5 w-5" />
              </Button>
              {crumb.map((segment, index) => (
                <div key={segment} className="flex items-center gap-2">
                  <span className={cn('font-medium', index === crumb.length - 1 ? 'text-foreground' : 'text-muted-foreground')}>
                    {segment}
                  </span>
                  {index < crumb.length - 1 ? <ChevronRight className="h-3 w-3" /> : null}
                </div>
              ))}
            </div>
            <div className="flex flex-1 flex-col gap-3 lg:flex-row lg:items-center lg:justify-end">
              <div className="relative w-full max-w-sm">
                <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input placeholder="Quick search" className="pl-10" />
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleTheme}
                  className="h-10 w-10 rounded-full border border-border/60"
                >
                  {theme === 'dark' ? <SunMedium className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                </Button>
                <Button className="gap-2 rounded-full px-6">
                  <Play className="h-4 w-4" />
                  Run
                </Button>
              </div>
            </div>
          </div>
        </header>
        <PanelGroup direction="horizontal" className="flex flex-1">
          <Panel defaultSize={70} minSize={50} className="flex flex-col">
            <main className="flex-1 space-y-6 p-6">
              <Outlet />
            </main>
          </Panel>
          {inspectorOpen ? (
            <>
              <PanelResizeHandle className="hidden w-px bg-border/60 lg:block" />
              <Panel defaultSize={30} minSize={20} className="hidden border-l border-border/60 bg-card/40 lg:flex">
                <aside className="flex h-full w-full flex-col">
                  <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
                    <div>
                      <h3 className="text-sm font-semibold">Inspector</h3>
                      <p className="text-xs text-muted-foreground">Selection, job status & diffs</p>
                    </div>
                    <Button variant="ghost" size="icon" onClick={toggleInspector}>
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                  <ScrollArea className="flex-1 px-4 py-4">
                    <InspectorContent />
                  </ScrollArea>
                </aside>
              </Panel>
            </>
          ) : null}
        </PanelGroup>
        {!inspectorOpen ? (
          <div className="hidden items-center justify-end border-t border-border/60 bg-card/40 px-2 py-1 lg:flex">
            <Button variant="ghost" size="sm" onClick={toggleInspector} className="flex items-center gap-2">
              <ChevronRight className="h-4 w-4 rotate-180" />
              Open Inspector
            </Button>
          </div>
        ) : null}
        <footer className="border-t border-border/60 bg-background/80 px-4">
          <LogConsole logs={logs} isCollapsed={consoleCollapsed} onToggle={toggleConsole} />
        </footer>
      </div>
    </div>
  );
}

function InspectorContent() {
  const { selection } = useLayoutStore();
  if (!selection) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
        <Terminal className="h-6 w-6" />
        <p>No selection yet. Explore a table row to see more context.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 text-sm">
      {Object.entries(selection).map(([key, value]) => (
        <div key={key} className="rounded-xl border border-border/40 bg-secondary/30 p-3">
          <p className="text-xs uppercase tracking-widest text-muted-foreground">{key}</p>
          <p className="font-medium text-foreground">{String(value)}</p>
        </div>
      ))}
    </div>
  );
}
