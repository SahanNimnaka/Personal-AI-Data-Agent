import { useState, type ReactNode } from 'react';

export type PageId =
  | 'upload'
  | 'profile'
  | 'descriptive'
  | 'group'
  | 'charts'
  | 'correlations'
  | 'outliers'
  | 'agent'
  | 'ml';

const NAV_ITEMS: { id: PageId; label: string }[] = [
  { id: 'upload', label: 'Dataset' },
  { id: 'profile', label: 'Profiling' },
  { id: 'descriptive', label: 'Descriptive' },
  { id: 'group', label: 'Group analysis' },
  { id: 'charts', label: 'Charts' },
  { id: 'correlations', label: 'Correlations' },
  { id: 'outliers', label: 'Outliers' },
  { id: 'agent', label: 'AI Agent' },
  { id: 'ml', label: 'Machine Learning' },
];

interface Props {
  active: PageId;
  onNavigate: (page: PageId) => void;
  datasetLabel: string | null;
  children: ReactNode;
}

export default function Layout({
  active,
  onNavigate,
  datasetLabel,
  children,
}: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const nav = (
    <nav className="flex flex-col gap-1 p-3">
      {NAV_ITEMS.map((item) => (
        <button
          key={item.id}
          onClick={() => {
            onNavigate(item.id);
            setSidebarOpen(false);
          }}
          className={`rounded-lg px-3 py-2 text-left text-sm font-medium transition ${
            active === item.id
              ? 'bg-blue-600 text-white'
              : 'text-slate-300 hover:bg-slate-800 hover:text-white'
          }`}
        >
          {item.label}
        </button>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col bg-slate-900 lg:flex">
        <div className="border-b border-slate-800 px-5 py-5">
          <h1 className="text-lg font-bold text-white">
            AI Data Agent
          </h1>
          <p className="mt-0.5 text-xs text-slate-400">
            Personal analysis dashboard
          </p>
        </div>
        {nav}
      </aside>

      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setSidebarOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 w-60 bg-slate-900">
            <div className="border-b border-slate-800 px-5 py-5">
              <h1 className="text-lg font-bold text-white">
                AI Data Agent
              </h1>
            </div>
            {nav}
          </aside>
        </div>
      )}

      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-md p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
            aria-label="Open menu"
          >
            <span className="block h-0.5 w-5 bg-current" />
            <span className="mt-1 block h-0.5 w-5 bg-current" />
            <span className="mt-1 block h-0.5 w-5 bg-current" />
          </button>
          <div>
            <h2 className="text-base font-semibold text-slate-800">
              {NAV_ITEMS.find((item) => item.id === active)?.label}
            </h2>
            {datasetLabel && (
              <p className="text-xs text-slate-500">
                Dataset: {datasetLabel}
              </p>
            )}
          </div>
        </header>

        <main className="mx-auto max-w-6xl p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
