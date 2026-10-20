import { useCallback, useEffect, useState } from 'react';
import { mlTargets, mlTrain } from '../api/client';
import type { MlTargetsResponse, MlTrainResponse } from '../api/types';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import ErrorAlert from '../components/ErrorAlert';
import Spinner from '../components/Spinner';
import StatCard from '../components/StatCard';
import { useDataset } from '../context/DatasetContext';
import { formatNumber } from '../utils/validation';

const METRIC_HELP: Record<string, string> = {
  mae: 'Mean absolute error — average prediction error (lower is better).',
  rmse: 'Root mean squared error — penalises large errors (lower is better).',
  r2: 'R² — share of target variance explained (1 is perfect, 0 is the mean baseline).',
  accuracy: 'Share of correct predictions.',
  precision: 'Weighted precision across classes.',
  recall: 'Weighted recall across classes.',
  f1: 'Weighted F1 — harmonic mean of precision and recall (primary metric).',
};

export default function MlPage() {
  const { file, recordResult } = useDataset();
  const [targets, setTargets] = useState<MlTargetsResponse | null>(null);
  const [target, setTarget] = useState('');
  const [features, setFeatures] = useState<string[]>([]);
  const [testSize, setTestSize] = useState(0.2);
  const [result, setResult] = useState<MlTrainResponse | null>(null);
  const [loadingTargets, setLoadingTargets] = useState(false);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTargets = useCallback(async () => {
    if (!file) return;
    setLoadingTargets(true);
    setError(null);
    setResult(null);
    try {
      const response = await mlTargets(file);
      setTargets(response);
      const firstEligible = response.targets.find((t) => t.eligible);
      setTarget(firstEligible?.column ?? '');
      setFeatures(
        response.columns.filter((c) => c !== firstEligible?.column),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load targets.');
    } finally {
      setLoadingTargets(false);
    }
  }, [file]);

  useEffect(() => {
    setTargets(null);
    setResult(null);
    setError(null);
  }, [file]);

  const selected = targets?.targets.find((t) => t.column === target);
  const eligibleTargets = targets?.targets.filter((t) => t.eligible) ?? [];

  const train = useCallback(async () => {
    if (!file || !target) return;
    setTraining(true);
    setError(null);
    try {
      const response = await mlTrain(
        file,
        target,
        features,
        selected?.task ?? '',
        testSize,
      );
      setResult(response);
      recordResult('ml', { ...response });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Training failed.');
    } finally {
      setTraining(false);
    }
  }, [file, target, features, selected, testSize, recordResult]);

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
        onClick={() => void loadTargets()}
        disabled={loadingTargets}
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {loadingTargets ? 'Inspecting…' : 'Inspect ML targets'}
      </button>

      {loadingTargets && <Spinner label="Inspecting columns…" />}
      {error && (
        <ErrorAlert
          title="Machine learning error"
          message={error}
          onRetry={() => void loadTargets()}
        />
      )}

      {targets && eligibleTargets.length === 0 && (
        <EmptyState
          title="No eligible target column"
          hint="This dataset has no numeric or categorical column suitable for training."
        />
      )}

      {targets && eligibleTargets.length > 0 && (
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-end gap-3">
            <label className="text-sm font-medium text-slate-700">
              Prediction target
              <select
                value={target}
                onChange={(event) => {
                  setTarget(event.target.value);
                  setFeatures(
                    targets.columns.filter((c) => c !== event.target.value),
                  );
                  setResult(null);
                }}
                className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                {eligibleTargets.map((item) => (
                  <option key={item.column} value={item.column}>
                    {item.column} ({item.task})
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium text-slate-700">
              Test fraction
              <select
                value={testSize}
                onChange={(event) =>
                  setTestSize(Number(event.target.value))
                }
                className="ml-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                {[0.1, 0.2, 0.3, 0.4].map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
            <button
              onClick={() => void train()}
              disabled={training || !target}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {training ? 'Training…' : 'Train & compare models'}
            </button>
          </div>

          {selected && (
            <p className="text-sm text-slate-500">
              Task: <b>{selected.task}</b>. Target <b>{target}</b> is
              automatically excluded from the features.
            </p>
          )}

          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-slate-700">
              Feature columns ({features.length} selected)
            </legend>
            <div className="flex flex-wrap gap-3">
              {targets.columns
                .filter((c) => c !== target)
                .map((column) => (
                  <label
                    key={column}
                    className="flex items-center gap-2 text-sm text-slate-600"
                  >
                    <input
                      type="checkbox"
                      checked={features.includes(column)}
                      onChange={(event) =>
                        setFeatures((previous) =>
                          event.target.checked
                            ? [...previous, column]
                            : previous.filter((c) => c !== column),
                        )
                      }
                    />
                    {column}
                  </label>
                ))}
            </div>
          </fieldset>
        </div>
      )}

      {training && <Spinner label="Training and evaluating models…" />}

      {result && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Task" value={result.task} accent />
            <StatCard label="Best model" value={result.best_model} />
            <StatCard
              label="Train rows"
              value={String(result.train_rows)}
            />
            <StatCard
              label="Test rows"
              value={String(result.test_rows)}
            />
          </div>

          <p className="text-sm text-slate-500">{result.notes}</p>

          <DataTable
            headers={[
              'Model',
              'Status',
              ...(result.models[0]?.metrics
                ? Object.keys(result.models[0].metrics)
                : []),
            ]}
            rows={result.models.map((model) => [
              model.model +
                (model.model === result.best_model ? '  ★ best' : ''),
              model.status,
              ...(model.metrics
                ? Object.values(model.metrics).map((value) =>
                    formatNumber(value),
                  )
                : ['—']),
            ])}
          />

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            <p className="mb-2 font-semibold text-slate-700">
              Metric meanings
            </p>
            <ul className="list-disc space-y-1 pl-5">
              {(result.models[0]?.metrics
                ? Object.keys(result.models[0].metrics)
                : []
              ).map((metric) => (
                <li key={metric}>
                  <b>{metric}</b>: {METRIC_HELP[metric] ?? ''}
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-slate-400">
              Metrics are computed on held-out test data (seed{' '}
              {result.random_seed}).
            </p>
          </div>
        </>
      )}
    </div>
  );
}
