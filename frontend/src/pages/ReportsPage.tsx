import { useCallback, useMemo, useState } from 'react';
import {
  generateReport,
  type ReportFormat,
  type ReportSection,
} from '../api/client';
import EmptyState from '../components/EmptyState';
import ErrorAlert from '../components/ErrorAlert';
import Spinner from '../components/Spinner';
import { useDataset } from '../context/DatasetContext';

const SECTION_LABELS: Record<ReportSection['type'], string> = {
  profile: 'Dataset profile',
  descriptive: 'Descriptive statistics',
  group: 'Group analysis',
  correlations: 'Correlations',
  outliers: 'Outlier detection',
  ml: 'Machine learning evaluation',
};

const FORMATS: { value: ReportFormat; label: string }[] = [
  { value: 'json', label: 'JSON (structured data)' },
  { value: 'csv', label: 'CSV (tabular)' },
  { value: 'html', label: 'HTML (view / print)' },
];

export default function ReportsPage() {
  const { file, preview, results } = useDataset();
  const [format, setFormat] = useState<ReportFormat>('html');
  const [selected, setSelected] = useState<
    Partial<Record<ReportSection['type'], boolean>>
  >({});
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const available = useMemo(
    () =>
      (Object.keys(SECTION_LABELS) as ReportSection['type'][]).filter(
        (type) => type in results,
      ),
    [results],
  );

  const toggle = (type: ReportSection['type']) => {
    setSelected((previous) => ({
      ...previous,
      [type]: !previous[type],
    }));
  };

  const generate = useCallback(async () => {
    if (!file) return;
    setError(null);
    setSuccess(null);

    const chosen = available.filter(
      (type) => selected[type] !== false,
    );

    if (available.length > 0 && chosen.length === 0) {
      setError('Select at least one analysis section to include.');
      return;
    }

    const sections: ReportSection[] = chosen.map((type) => ({
      type,
      data: results[type] as Record<string, unknown>,
    }));

    setGenerating(true);
    try {
      const { blob, filename } = await generateReport(
        {
          filename: file.name,
          rows: preview?.rows ?? null,
          columns: preview?.columns_count ?? null,
          sections,
        },
        format,
      );

      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);

      setSuccess(`Generated ${filename}.`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Report generation failed.',
      );
    } finally {
      setGenerating(false);
    }
  }, [file, preview, results, available, selected, format]);

  if (!file) {
    return (
      <EmptyState
        title="No dataset loaded"
        hint="Upload a CSV on the Dataset page first."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h2 className="text-base font-semibold text-slate-800">
          Report contents
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Select which analysis results to include. Only sections you
          have actually run are listed.
        </p>

        {available.length === 0 ? (
          <p className="mt-4 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
            No analysis results available yet. Run profiling,
            descriptive, group, correlation, outlier, or ML analyses
            first.
          </p>
        ) : (
          <ul className="mt-4 space-y-2">
            {available.map((type) => (
              <li key={type}>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={selected[type] !== false}
                    onChange={() => toggle(type)}
                    className="h-4 w-4 rounded border-slate-300"
                  />
                  {SECTION_LABELS[type]}
                </label>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm font-medium text-slate-700">
          Format
          <select
            value={format}
            onChange={(event) =>
              setFormat(event.target.value as ReportFormat)
            }
            className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            {FORMATS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={() => void generate()}
          disabled={generating}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {generating ? 'Generating…' : 'Generate report'}
        </button>
      </div>

      {generating && <Spinner label="Building report…" />}
      {error && (
        <ErrorAlert
          title="Could not generate report"
          message={error}
          onRetry={() => void generate()}
        />
      )}
      {success && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          {success}
        </div>
      )}
    </div>
  );
}
