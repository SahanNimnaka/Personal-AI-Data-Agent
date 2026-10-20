import { useCallback, useEffect, useState } from 'react';
import { detectOutliers } from '../api/client';
import type { OutliersResponse } from '../api/types';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import ErrorAlert from '../components/ErrorAlert';
import Spinner from '../components/Spinner';
import StatCard from '../components/StatCard';
import { useDataset } from '../context/DatasetContext';
import { useNumericColumns } from '../hooks/useColumns';
import { formatNumber } from '../utils/validation';

export default function OutliersPage() {
  const { file } = useDataset();
  const numericColumns = useNumericColumns();
  const [column, setColumn] = useState('');
  const [result, setResult] = useState<OutliersResponse | null>(null);
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
      setResult(await detectOutliers(file, column));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Detection failed.',
      );
    } finally {
      setLoading(false);
    }
  }, [file, column]);

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
        hint="Outlier detection requires a numeric column."
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
          {loading ? 'Detecting…' : 'Detect outliers (IQR)'}
        </button>
      </div>

      {loading && <Spinner label="Detecting outliers…" />}
      {error && (
        <ErrorAlert
          title="Outlier detection failed"
          message={error}
          onRetry={() => void run()}
        />
      )}

      {result && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <StatCard label="Q1" value={formatNumber(result.q1)} />
            <StatCard label="Q3" value={formatNumber(result.q3)} />
            <StatCard label="IQR" value={formatNumber(result.iqr)} />
            <StatCard
              label="Lower bound"
              value={formatNumber(result.lower_bound)}
            />
            <StatCard
              label="Upper bound"
              value={formatNumber(result.upper_bound)}
            />
            <StatCard
              label="Outliers found"
              value={String(result.outlier_count)}
              accent
            />
          </div>

          <p className="text-sm text-slate-500">
            {result.interpretation_note}
          </p>

          {result.outlier_count > 0 ? (
            <DataTable
              headers={['Row index', 'Value']}
              rows={result.outliers.map((item) => [
                item.row_index,
                formatNumber(item.value),
              ])}
            />
          ) : (
            <EmptyState
              title="No outliers detected"
              hint={`All values of '${result.column}' fall within the IQR fences.`}
            />
          )}
        </>
      )}
    </div>
  );
}
