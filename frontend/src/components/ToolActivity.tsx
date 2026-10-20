import type { AgentResponse } from '../api/types';
import { formatNumber } from '../utils/validation';

const TOOL_LABELS: Record<string, string> = {
  get_overview: 'Dataset overview',
  get_descriptive_statistics: 'Descriptive statistics',
  get_group_analysis: 'Group analysis',
  get_correlations: 'Correlations',
  detect_outliers: 'Outlier detection',
  get_chart_config: 'Chart configuration',
};

function ResultSummary({ tool }: { tool: AgentResponse['tools_executed'][number] }) {
  const { tool: name, status, result } = tool;

  if (status === 'error') {
    return (
      <p className="text-sm text-red-600">
        Error: {String(result.error ?? 'unknown error')}
      </p>
    );
  }

  if (name === 'get_descriptive_statistics') {
    return (
      <p className="text-sm text-slate-600">
        mean <b>{formatNumber(result.mean as number)}</b>, median{' '}
        <b>{formatNumber(result.median as number)}</b>, min{' '}
        <b>{formatNumber(result.minimum as number)}</b>, max{' '}
        <b>{formatNumber(result.maximum as number)}</b>
      </p>
    );
  }

  if (name === 'get_overview') {
    const overview = result.overview as Record<string, number>;
    return (
      <p className="text-sm text-slate-600">
        {overview.rows} rows, {overview.columns} columns,{' '}
        {overview.total_missing_values} missing,{' '}
        {overview.duplicate_rows} duplicates
      </p>
    );
  }

  if (name === 'detect_outliers') {
    return (
      <p className="text-sm text-slate-600">
        {String(result.outlier_count)} outlier(s) in{' '}
        <b>{String(result.column)}</b>
      </p>
    );
  }

  if (name === 'get_correlations') {
    const pairs = result.correlations as unknown[];
    return (
      <p className="text-sm text-slate-600">
        {pairs.length} correlation pair(s), method{' '}
        <b>{String(result.method)}</b>
      </p>
    );
  }

  if (name === 'get_group_analysis') {
    const groups = result.groups as unknown[];
    return (
      <p className="text-sm text-slate-600">
        {groups.length} group(s) of {String(result.value_column)} by{' '}
        <b>{String(result.group_column)}</b>
      </p>
    );
  }

  if (name === 'get_chart_config') {
    return (
      <p className="text-sm text-slate-600">
        {String(result.chart_type)} chart: {String(result.x_column)}
        {result.y_column ? ` vs ${String(result.y_column)}` : ''}
      </p>
    );
  }

  return null;
}

export default function ToolActivity({
  tools,
}: {
  tools: AgentResponse['tools_executed'];
}) {
  if (tools.length === 0) {
    return (
      <p className="text-sm text-slate-400">
        No tools were executed for this answer.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {tools.map((tool, index) => (
        <li
          key={index}
          className="rounded-lg border border-slate-200 bg-slate-50 p-3"
        >
          <div className="flex items-center gap-2">
            <span
              className={`size-2 rounded-full ${
                tool.status === 'ok' ? 'bg-emerald-500' : 'bg-red-500'
              }`}
            />
            <span className="text-sm font-semibold text-slate-700">
              {TOOL_LABELS[tool.tool] ?? tool.tool}
            </span>
            {Object.keys(tool.arguments).length > 0 && (
              <span className="text-xs text-slate-500">
                {Object.entries(tool.arguments)
                  .map(([key, value]) => `${key}=${String(value)}`)
                  .join(', ')}
              </span>
            )}
          </div>
          <ResultSummary tool={tool} />
        </li>
      ))}
    </ul>
  );
}
