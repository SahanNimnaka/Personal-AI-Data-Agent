import { useCallback, useEffect, useState } from 'react';
import { createChart } from '../api/client';
import type { ChartResponse, ChartType } from '../api/types';
import EmptyState from '../components/EmptyState';
import ErrorAlert from '../components/ErrorAlert';
import PlotChart from '../components/PlotChart';
import Spinner from '../components/Spinner';
import { useDataset } from '../context/DatasetContext';
import { useAllColumns, useNumericColumns } from '../hooks/useColumns';

const CHART_TYPES: ChartType[] = [
  'bar',
  'line',
  'scatter',
  'histogram',
  'box',
];

const NEEDS_Y: ChartType[] = ['bar', 'line', 'scatter'];

export default function ChartsPage() {
  const { file } = useDataset();
  const allColumns = useAllColumns();
  const numericColumns = useNumericColumns();
  const [chartType, setChartType] = useState<ChartType>('bar');
  const [xColumn, setXColumn] = useState('');
  const [yColumn, setYColumn] = useState('');
  const [result, setResult] = useState<ChartResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setXColumn(allColumns[0] ?? '');
    setYColumn(numericColumns[0] ?? '');
    setResult(null);
    setError(null);
  }, [file, allColumns, numericColumns]);

  const needsY = NEEDS_Y.includes(chartType);

  const run = useCallback(async () => {
    if (!file || !xColumn || (needsY && !yColumn)) return;
    setLoading(true);
    setError(null);
    try {
      setResult(
        await createChart(file, chartType, xColumn, needsY ? yColumn : null),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chart failed.');
    } finally {
      setLoading(false);
    }
  }, [file, chartType, xColumn, yColumn, needsY]);

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
          Chart type
          <select
            value={chartType}
            onChange={(event) =>
              setChartType(event.target.value as ChartType)
            }
            className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            {CHART_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium text-slate-700">
          X column
          <select
            value={xColumn}
            onChange={(event) => setXColumn(event.target.value)}
            className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            {allColumns.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        {(chartType === 'box' || needsY) && (
          <label className="text-sm font-medium text-slate-700">
            Y column{chartType === 'box' ? ' (optional)' : ''}
            <select
              value={yColumn}
              onChange={(event) => setYColumn(event.target.value)}
              className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              {chartType === 'box' && (
                <option value="">(none)</option>
              )}
              {numericColumns.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        )}
        <button
          onClick={() => void run()}
          disabled={loading || !xColumn || (needsY && !yColumn)}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Rendering…' : 'Render chart'}
        </button>
      </div>

      {loading && <Spinner label="Rendering chart…" />}
      {error && (
        <ErrorAlert
          title="Chart failed"
          message={error}
          onRetry={() => void run()}
        />
      )}

      {result && (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <PlotChart
            data={result.chart.data}
            layout={result.chart.layout}
          />
        </div>
      )}

      {!result && !loading && !error && (
        <EmptyState
          title="No chart yet"
          hint="Choose columns and render a chart."
        />
      )}
    </div>
  );
}
