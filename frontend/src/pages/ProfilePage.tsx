import { useCallback, useEffect, useState } from 'react';
import { profileDataset } from '../api/client';
import type { ProfileResponse } from '../api/types';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import ErrorAlert from '../components/ErrorAlert';
import Spinner from '../components/Spinner';
import StatCard from '../components/StatCard';
import { useDataset } from '../context/DatasetContext';
import { formatBytes, formatNumber } from '../utils/validation';

export default function ProfilePage() {
  const { file } = useDataset();
  const [result, setResult] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await profileDataset(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Profiling failed.');
    } finally {
      setLoading(false);
    }
  }, [file]);

  useEffect(() => {
    setResult(null);
    setError(null);
  }, [file]);

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
      <button
        onClick={() => void run()}
        disabled={loading}
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Profiling…' : 'Run profiling'}
      </button>

      {loading && <Spinner label="Profiling dataset…" />}
      {error && (
        <ErrorAlert
          title="Profiling failed"
          message={error}
          onRetry={() => void run()}
        />
      )}

      {result && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <StatCard label="Rows" value={String(result.overview.rows)} accent />
            <StatCard
              label="Columns"
              value={String(result.overview.columns)}
            />
            <StatCard
              label="Duplicate rows"
              value={String(result.overview.duplicate_rows)}
            />
            <StatCard
              label="Missing values"
              value={String(result.overview.total_missing_values)}
            />
            <StatCard
              label="Memory"
              value={formatBytes(result.overview.memory_usage_bytes)}
            />
          </div>

          <section className="space-y-3">
            <h3 className="font-semibold text-slate-700">Columns</h3>
            <DataTable
              headers={[
                'Name',
                'Type',
                'Kind',
                'Missing',
                'Missing %',
                'Unique',
                'Constant',
              ]}
              rows={result.columns.map((column) => [
                column.name,
                column.data_type,
                column.column_type,
                column.missing_values,
                `${column.missing_percentage}%`,
                column.unique_values,
                column.is_constant ? 'yes' : 'no',
              ])}
            />
          </section>

          <section className="space-y-3">
            <h3 className="font-semibold text-slate-700">
              Numeric statistics
            </h3>
            <DataTable
              headers={[
                'Column',
                'Mean',
                'Median',
                'Std dev',
                'Min',
                'Max',
              ]}
              rows={Object.entries(result.numeric_statistics).map(
                ([name, stats]) => [
                  name,
                  formatNumber(stats.mean),
                  formatNumber(stats.median),
                  formatNumber(stats.standard_deviation),
                  formatNumber(stats.minimum),
                  formatNumber(stats.maximum),
                ],
              )}
              emptyMessage="No numeric columns in this dataset."
            />
          </section>
        </>
      )}
    </div>
  );
}
