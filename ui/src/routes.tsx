import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from '@/components/app-shell';
import { ComposePage } from '@/pages/compose';
import { CleanPage } from '@/pages/clean';
import { CrawlPage } from '@/pages/crawl';
import { TranslatePage } from '@/pages/translate';
import { DatasetsPage } from '@/pages/datasets';
import { JobsPage } from '@/pages/jobs';
import { SettingsPage } from '@/pages/settings';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/compose" replace /> },
      { path: 'compose', element: <ComposePage /> },
      { path: 'clean', element: <CleanPage /> },
      { path: 'crawl', element: <CrawlPage /> },
      { path: 'translate', element: <TranslatePage /> },
      { path: 'datasets', element: <DatasetsPage /> },
      { path: 'jobs', element: <JobsPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
]);
