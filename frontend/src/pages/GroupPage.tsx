import { useCallback, useEffect, useState } from 'react';
import { groupAnalysis } from '../api/client';
import type { GroupResponse } from '../api/types';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import ErrorAlert from '../components/ErrorAlert';
import Spinner from '../components/Spinner';
import { useDataset } from '../context/DatasetContext';
import { useAllColumns, useNumericColumns } from '../hooks/useColumns';
import { formatNumber } from '../utils/validation';

export default function GroupPage() {
  const { file } = useDataset();
  const allColumns = useAllColumns();
  const numericColumns = useNumericColumns();
  const [groupColumn, setGroupColumn] = useState('');
  const [valueColumn, setValueColumn] = useState('');
  const [result, setResult] = useState<GroupResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setGroupColumn(allColumns.find((c) => !numericColumns.includes(c)) ?? allColumns[0] ?? '');
    setValueColumn(numericColumns[0] ?? '');
    setResult(null);
    setError(null);
  }, [file, allColumns, numericColumns]);

  const run = useCallback(async () => {
    if (!file || !groupColumn || !valueColumn) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await groupAnalysis(file, groupColumn, valueColumn));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Grouping failed.');
    } finally {
      setLoading(false);
    }
  }, [file, groupColumn, valueColumn]);

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
          Group by
          <select
            value={groupColumn}
            onChange={(event) => setGroupColumn(event.target.value)}
            className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            {allColumns.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium text-slate-700">
          Value column
          <select
            value={valueColumn}
            onChange={(event) => setValueColumn(event.target.value)}
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
          disabled={loading || !groupColumn || !valueColumn}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Grouping…' : 'Run group analysis'}
        </button>
      </div>

      {numericColumns.length === 0 && (
        <EmptyState
          title="No numeric columns"
          hint="Group analysis needs a numeric value column."
        />
      )}

      {loading && <Spinner label="Grouping data…" />}
      {error && (
        <ErrorAlert
          title="Group analysis failed"
          message={error}
          onRetry={() => void run()}
        />
      )}

      {result && (
        <DataTable
          headers={[
            result.group_column,
            'count',
            'sum',
            'mean',
          ]}
          rows={result.groups.map((row) => [
            String(row[result.group_column]),
            formatNumber(Number(row.count)),
            formatNumber(Number(row.sum)),
            formatNumber(Number(row.mean)),
          ])}
          emptyMessage="No groups found."
        />
      )}
    </div>
  );
}
