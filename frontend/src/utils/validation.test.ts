import { describe, expect, it } from 'vitest';
import {
  formatBytes,
  formatNumber,
  MAX_FILE_SIZE_BYTES,
  parseReportFilename,
  validateCsvFile,
  validateQuestion,
  validateTestSize,
} from './validation';

function fakeFile(name: string, size: number): File {
  return new File([new Uint8Array(size)], name);
}

describe('validateCsvFile', () => {
  it('accepts a small csv file', () => {
    expect(validateCsvFile(fakeFile('data.csv', 100)).ok).toBe(true);
  });

  it('rejects non-csv files', () => {
    const result = validateCsvFile(fakeFile('data.txt', 100));
    expect(result.ok).toBe(false);
    expect(result.error).toContain('.csv');
  });

  it('rejects empty files', () => {
    expect(validateCsvFile(fakeFile('data.csv', 0)).ok).toBe(false);
  });

  it('rejects oversized files', () => {
    const result = validateCsvFile(
      fakeFile('big.csv', MAX_FILE_SIZE_BYTES + 1),
    );
    expect(result.ok).toBe(false);
    expect(result.error).toContain('10 MB');
  });
});

describe('formatBytes', () => {
  it('formats bytes, kilobytes and megabytes', () => {
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(2048)).toBe('2.0 KB');
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.00 MB');
  });
});

describe('formatNumber', () => {
  it('handles null and floats', () => {
    expect(formatNumber(null)).toBe('—');
    expect(formatNumber(2.5)).toBe('2.5');
    expect(formatNumber(1000)).toBe('1,000');
  });
});

describe('validateQuestion', () => {
  it('rejects empty questions', () => {
    expect(validateQuestion('   ').ok).toBe(false);
  });

  it('rejects overly long questions', () => {
    expect(validateQuestion('x'.repeat(2001)).ok).toBe(false);
  });

  it('accepts a normal question', () => {
    expect(validateQuestion('What is the mean sales?').ok).toBe(true);
  });
});

describe('validateTestSize', () => {
  it('rejects out-of-range fractions', () => {
    expect(validateTestSize(0.05).ok).toBe(false);
    expect(validateTestSize(0.9).ok).toBe(false);
  });

  it('accepts valid fractions', () => {
    expect(validateTestSize(0.2).ok).toBe(true);
    expect(validateTestSize(0.5).ok).toBe(true);
  });
});

describe('parseReportFilename', () => {
  it('extracts the filename from a content-disposition header', () => {
    expect(
      parseReportFilename(
        'attachment; filename="data-report.html"',
        'html',
      ),
    ).toBe('data-report.html');
  });

  it('falls back to a format-based name when absent', () => {
    expect(parseReportFilename(null, 'csv')).toBe('report.csv');
    expect(parseReportFilename('', 'json')).toBe('report.json');
  });
});
