// Kept below Vercel's hard 4.5 MB request-body limit, which rejects
// larger uploads before they reach the backend.
export const MAX_FILE_SIZE_BYTES = 4 * 1024 * 1024;
export const MAX_QUESTION_LENGTH = 2000;

export interface FileValidationResult {
  ok: boolean;
  error?: string;
}

export function validateCsvFile(file: File): FileValidationResult {
  if (!file.name.toLowerCase().endsWith('.csv')) {
    return { ok: false, error: 'Only .csv files are supported.' };
  }

  if (file.size === 0) {
    return { ok: false, error: 'The selected file is empty.' };
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      ok: false,
      error: 'File exceeds the 4 MB size limit.',
    };
  }

  return { ok: true };
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  return Number.isInteger(value)
    ? value.toLocaleString()
    : value.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

export function validateQuestion(question: string): FileValidationResult {
  if (question.trim().length === 0) {
    return { ok: false, error: 'Please enter a question.' };
  }
  if (question.length > MAX_QUESTION_LENGTH) {
    return {
      ok: false,
      error: `Questions are limited to ${MAX_QUESTION_LENGTH} characters.`,
    };
  }
  return { ok: true };
}

export function validateTestSize(testSize: number): FileValidationResult {
  if (Number.isNaN(testSize) || testSize < 0.1 || testSize > 0.5) {
    return {
      ok: false,
      error: 'The test fraction must be between 0.1 and 0.5.',
    };
  }
  return { ok: true };
}

export function parseReportFilename(
  disposition: string | null,
  format: string,
): string {
  const match = disposition?.match(/filename="([^"]+)"/);
  return match?.[1] ?? `report.${format}`;
}
