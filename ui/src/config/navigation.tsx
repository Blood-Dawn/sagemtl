import { Search, Sparkles, Globe2, Database, Workflow, Settings, Layers } from 'lucide-react';

export type NavItem = {
  label: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  to: string;
};

export type NavSection = {
  label: string;
  items: NavItem[];
};

export const navSections: NavSection[] = [
  {
    label: 'Workflow',
    items: [
      { label: 'Compose', icon: Layers, to: '/compose' },
    ],
  },
  {
    label: 'Core',
    items: [
      { label: 'Clean', icon: Sparkles, to: '/clean' },
      { label: 'Crawl', icon: Search, to: '/crawl' },
      { label: 'Translate', icon: Globe2, to: '/translate' },
    ],
  },
  {
    label: 'Data',
    items: [
      { label: 'Datasets', icon: Database, to: '/datasets' },
      { label: 'Jobs', icon: Workflow, to: '/jobs' },
    ],
  },
  {
    label: 'Settings',
    items: [{ label: 'Settings', icon: Settings, to: '/settings' }],
  },
];
