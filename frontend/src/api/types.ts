export interface UploadColumn {
  name: string;
  data_type: string;
  missing_values: number;
}

export interface UploadResponse {
  filename: string;
  rows: number;
  columns_count: number;
  columns: UploadColumn[];
  preview: Record<string, unknown>[];
}

export interface ProfileColumn {
  name: string;
  data_type: string;
  column_type: string;
  missing_values: number;
  missing_percentage: number;
  unique_values: number;
  is_constant: boolean;
}

export interface NumericStatistics {
  mean: number | null;
  median: number | null;
  standard_deviation: number | null;
  minimum: number | null;
  maximum: number | null;
}

export interface ProfileResponse {
  filename: string;
  overview: {
    rows: number;
    columns: number;
    duplicate_rows: number;
    total_missing_values: number;
    memory_usage_bytes: number;
  };
  columns: ProfileColumn[];
  numeric_statistics: Record<string, NumericStatistics>;
}

export interface DescriptiveResponse {
  column: string;
  count: number;
  mean: number;
  median: number;
  standard_deviation: number | null;
  minimum: number;
  maximum: number;
}

export interface GroupRow {
  [key: string]: string | number;
}

export interface GroupResponse {
  group_column: string;
  value_column: string;
  groups: GroupRow[];
}

export type ChartType = 'bar' | 'line' | 'scatter' | 'histogram' | 'box';

export interface PlotlyTrace {
  type: string;
  x?: unknown[];
  y?: unknown[];
  [key: string]: unknown;
}

export interface ChartResponse {
  chart_type: string;
  chart: {
    data: PlotlyTrace[];
    layout: Record<string, unknown>;
  };
}

export interface CorrelationPair {
  column_a: string;
  column_b: string;
  correlation: number | null;
}

export interface CorrelationsResponse {
  filename: string;
  method: string;
  numeric_columns: string[];
  correlations: CorrelationPair[];
  interpretation_note: string;
}

export interface OutlierValue {
  row_index: number;
  value: number;
}

export interface OutliersResponse {
  filename: string;
  column: string;
  method: string;
  q1: number;
  q3: number;
  iqr: number;
  lower_bound: number;
  upper_bound: number;
  outlier_count: number;
  outliers: OutlierValue[];
  interpretation_note: string;
}

export interface AgentToolExecution {
  tool: string;
  arguments: Record<string, unknown>;
  status: 'ok' | 'error';
  result: Record<string, unknown>;
}

export interface AgentResponse {
  question: string;
  answer: string;
  source: 'llm' | 'fallback';
  provider: string;
  tools_executed: AgentToolExecution[];
  notes: string;
}
