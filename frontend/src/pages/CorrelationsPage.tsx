import { useCallback, useEffect, useState } from 'react';
import { correlations } from '../api/client';
import type { CorrelationsResponse } from '../api/types';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import ErrorAlert from '../components/ErrorAlert';
import Spinner from '../components/Spinner';
import { useDataset } from '../context/DatasetContext';

type Method = 'pearson' | 'spearman' | 'kendall';

const METHODS: Method[] = ['pearson', 'spearman', 'kendall'];

export default function CorrelationsPage() {
  const { file, recordResult } = useDataset();
  const [method, setMethod] = useState<Method>('pearson');
  const [result, setResult] = useState<CorrelationsResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setResult(null);
    setError(null);
  }, [file]);

  const run = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const response = await correlations(file, method);
      setResult(response);
      recordResult('correlations', { ...response });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Correlation failed.',
      );
    } finally {
      setLoading(false);
    }
  }, [file, method, recordResult]);

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
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm font-medium text-slate-700">
          Method
          <select
            value={method}
            onChange={(event) =>
              setMethod(event.target.value as Method)
            }
            className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            {METHODS.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={() => void run()}
          disabled={loading}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Computing…' : 'Compute correlations'}
        </button>
      </div>

      {loading && <Spinner label="Computing correlations…" />}
      {error && (
        <ErrorAlert
          title="Correlation analysis failed"
          message={error}
          onRetry={() => void run()}
        />
      )}

      {result && (
        <>
          <p className="text-sm text-slate-500">
            {result.interpretation_note}
          </p>
          <DataTable
            headers={['Column A', 'Column B', 'Correlation']}
            rows={result.correlations.map((pair) => [
              pair.column_a,
              pair.column_b,
              pair.correlation === null
                ? '—'
                : pair.correlation.toFixed(4),
            ])}
            emptyMessage="No column pairs to correlate."
          />
        </>
      )}
    </div>
  );
}
