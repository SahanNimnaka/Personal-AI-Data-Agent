import { useCallback, useEffect, useState } from 'react';
import { descriptiveStatistics } from '../api/client';
import type { DescriptiveResponse } from '../api/types';
import EmptyState from '../components/EmptyState';
import ErrorAlert from '../components/ErrorAlert';
import Spinner from '../components/Spinner';
import StatCard from '../components/StatCard';
import { useDataset } from '../context/DatasetContext';
import { useNumericColumns } from '../hooks/useColumns';
import { formatNumber } from '../utils/validation';

export default function DescriptivePage() {
  const { file, recordResult } = useDataset();
  const numericColumns = useNumericColumns();
  const [column, setColumn] = useState('');
  const [result, setResult] = useState<DescriptiveResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setColumn(numericColumns[0] ?? '');
    setResult(null);
    setError(null);
  }, [file, numericColumns]);

  const run = useCallback(async () => {
    if (!file || !column) return;
    setLoading(true);
    setError(null);
    try {
      const response = await descriptiveStatistics(file, column);
      setResult(response);
      recordResult('descriptive', { ...response });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Analysis failed.',
      );
    } finally {
      setLoading(false);
    }
  }, [file, column, recordResult]);

  if (!file) {
    return (
      <EmptyState
        title="No dataset loaded"
        hint="Upload a CSV on the Dataset page first."
      />
    );
  }

  if (numericColumns.length === 0) {
    return (
      <EmptyState
        title="No numeric columns"
        hint="Descriptive statistics require at least one numeric column."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm font-medium text-slate-700">
          Numeric column
          <select
            value={column}
            onChange={(event) => setColumn(event.target.value)}
            className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            {numericColumns.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <button
          onClick={() => void run()}
          disabled={loading || !column}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Computing…' : 'Compute statistics'}
        </button>
      </div>

      {loading && <Spinner label="Computing statistics…" />}
      {error && (
        <ErrorAlert
          title="Analysis failed"
          message={error}
          onRetry={() => void run()}
        />
      )}

      {result && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <StatCard label="Count" value={formatNumber(result.count)} accent />
          <StatCard label="Mean" value={formatNumber(result.mean)} />
          <StatCard label="Median" value={formatNumber(result.median)} />
          <StatCard
            label="Std deviation"
            value={formatNumber(result.standard_deviation)}
          />
          <StatCard label="Minimum" value={formatNumber(result.minimum)} />
          <StatCard label="Maximum" value={formatNumber(result.maximum)} />
        </div>
      )}
    </div>
  );
}
