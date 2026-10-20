import type {
  AgentResponse,
  ChartResponse,
  ChartType,
  CorrelationsResponse,
  DescriptiveResponse,
  GroupResponse,
  MlTargetsResponse,
  MlTrainResponse,
  OutliersResponse,
  ProfileResponse,
  UploadResponse,
} from './types';
import { parseReportFilename } from '../utils/validation';

// In production the frontend and backend are served from the same origin
// (Vercel Services), and all API traffic is routed under /api. During
// local development VITE_API_BASE_URL points at the local backend, which
// serves the same /api-prefixed paths.
const BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const API_PREFIX = '/api';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function extractError(response: Response): Promise<string> {
  const fallback = messageForStatus(response.status);
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string' && body.detail.trim()) {
      return body.detail;
    }
    return fallback;
  } catch {
    return fallback;
  }
}

export function messageForStatus(status: number): string {
  if (status === 0) {
    return 'Cannot reach the API server. Is the backend running?';
  }
  if (status === 413) {
    return 'The file is too large for the server.';
  }
  if (status >= 500) {
    return 'The server encountered an error. Please try again.';
  }
  if (status === 404) {
    return 'The requested resource was not found.';
  }
  return `Request failed with status ${status}`;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${API_PREFIX}${path}`, init);
  } catch {
    throw new ApiError(0, messageForStatus(0));
  }

  if (!response.ok) {
    throw new ApiError(response.status, await extractError(response));
  }

  return (await response.json()) as T;
}

function fileForm(file: File): FormData {
  const form = new FormData();
  form.append('file', file);
  return form;
}

export async function uploadDataset(
  file: File,
): Promise<UploadResponse> {
  return request<UploadResponse>('/datasets/upload', {
    method: 'POST',
    body: fileForm(file),
  });
}

export async function profileDataset(
  file: File,
): Promise<ProfileResponse> {
  return request<ProfileResponse>('/datasets/profile', {
    method: 'POST',
    body: fileForm(file),
  });
}

export async function descriptiveStatistics(
  file: File,
  column: string,
): Promise<DescriptiveResponse> {
  const params = new URLSearchParams({ column });
  return request<DescriptiveResponse>(
    `/analysis/descriptive?${params.toString()}`,
    { method: 'POST', body: fileForm(file) },
  );
}

export async function groupAnalysis(
  file: File,
  groupColumn: string,
  valueColumn: string,
): Promise<GroupResponse> {
  const params = new URLSearchParams({
    group_column: groupColumn,
    value_column: valueColumn,
  });
  return request<GroupResponse>(
    `/analysis/group?${params.toString()}`,
    { method: 'POST', body: fileForm(file) },
  );
}

export async function createChart(
  file: File,
  chartType: ChartType,
  xColumn: string,
  yColumn: string | null,
): Promise<ChartResponse> {
  const params = new URLSearchParams({
    chart_type: chartType,
    x_column: xColumn,
  });
  if (yColumn) {
    params.set('y_column', yColumn);
  }
  return request<ChartResponse>(
    `/visualizations/chart?${params.toString()}`,
    { method: 'POST', body: fileForm(file) },
  );
}

export async function correlations(
  file: File,
  method: 'pearson' | 'spearman' | 'kendall',
): Promise<CorrelationsResponse> {
  const params = new URLSearchParams({ method });
  return request<CorrelationsResponse>(
    `/analysis/correlations?${params.toString()}`,
    { method: 'POST', body: fileForm(file) },
  );
}

export async function detectOutliers(
  file: File,
  column: string,
): Promise<OutliersResponse> {
  // The backend declares `column` as a FastAPI Form field, so it must
  // be sent inside the multipart body, not as a query parameter.
  const form = fileForm(file);
  form.append('column', column);
  return request<OutliersResponse>('/analysis/outliers', {
    method: 'POST',
    body: form,
  });
}

export async function askAgent(
  file: File,
  question: string,
): Promise<AgentResponse> {
  const form = fileForm(file);
  form.append('question', question);
  return request<AgentResponse>('/agent/chat', {
    method: 'POST',
    body: form,
  });
}

export async function mlTargets(file: File): Promise<MlTargetsResponse> {
  return request<MlTargetsResponse>('/ml/targets', {
    method: 'POST',
    body: fileForm(file),
  });
}

export async function mlTrain(
  file: File,
  targetColumn: string,
  featureColumns: string[],
  task: string,
  testSize: number,
): Promise<MlTrainResponse> {
  const form = fileForm(file);
  form.append('target_column', targetColumn);
  form.append('feature_columns', featureColumns.join(','));
  if (task) {
    form.append('task', task);
  }
  form.append('test_size', String(testSize));
  return request<MlTrainResponse>('/ml/train', {
    method: 'POST',
    body: form,
  });
}

export type ReportFormat = 'json' | 'csv' | 'html';

export interface ReportSection {
  type:
    | 'profile'
    | 'descriptive'
    | 'group'
    | 'correlations'
    | 'outliers'
    | 'ml';
  data: Record<string, unknown>;
}

export interface ReportPayload {
  filename: string;
  rows: number | null;
  columns: number | null;
  sections: ReportSection[];
}

export interface DownloadedReport {
  blob: Blob;
  filename: string;
}

export async function generateReport(
  payload: ReportPayload,
  format: ReportFormat,
): Promise<DownloadedReport> {
  let response: Response;
  try {
    response = await fetch(
      `${BASE_URL}${API_PREFIX}/reports/generate?format=${format}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
    );
  } catch {
    throw new ApiError(0, messageForStatus(0));
  }

  if (!response.ok) {
    throw new ApiError(response.status, await extractError(response));
  }

  const disposition = response.headers.get('content-disposition');
  const filename = parseReportFilename(disposition, format);

  return { blob: await response.blob(), filename };
}

export { BASE_URL };

