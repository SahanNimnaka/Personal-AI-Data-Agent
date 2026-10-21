import { describe, expect, it } from 'vitest';
import {
  ApiError,
  buildApiUrl,
  messageForStatus,
  resolveApiBaseUrl,
} from './client';

describe('resolveApiBaseUrl', () => {
  it('uses same-origin in production when unset (never localhost)', () => {
    const base = resolveApiBaseUrl(undefined, true);
    expect(base).toBe('');
    expect(base).not.toContain('localhost');
  });

  it('treats an empty or whitespace override as unset in production', () => {
    expect(resolveApiBaseUrl('', true)).toBe('');
    expect(resolveApiBaseUrl('   ', true)).toBe('');
  });

  it('uses same-origin in development by default (served via dev proxy)', () => {
    const base = resolveApiBaseUrl(undefined, false);
    expect(base).toBe('');
    expect(base).not.toContain('localhost');
  });

  it('honors an explicit override in production', () => {
    expect(resolveApiBaseUrl('https://api.example.com', true)).toBe(
      'https://api.example.com',
    );
  });

  it('strips trailing slashes from an override', () => {
    expect(resolveApiBaseUrl('https://api.example.com/', true)).toBe(
      'https://api.example.com',
    );
    expect(resolveApiBaseUrl('http://localhost:8000///', false)).toBe(
      'http://localhost:8000',
    );
  });
});

describe('buildApiUrl', () => {
  it('produces a same-origin /api path in production', () => {
    expect(buildApiUrl('/datasets/upload', '')).toBe('/api/datasets/upload');
  });

  it('never targets localhost when the base is same-origin', () => {
    expect(buildApiUrl('/health', '')).not.toContain('localhost');
  });

  it('appends /api exactly once for every route', () => {
    const routes = [
      '/datasets/upload',
      '/datasets/profile',
      '/analysis/descriptive',
      '/analysis/group',
      '/analysis/correlations',
      '/analysis/outliers',
      '/visualizations/chart',
      '/agent/chat',
      '/ml/targets',
      '/ml/train',
      '/reports/generate',
    ];
    for (const route of routes) {
      const url = buildApiUrl(route, '');
      expect(url).toBe(`/api${route}`);
      expect(url.includes('/api/api')).toBe(false);
      expect(url.startsWith('/api/')).toBe(true);
    }
  });

  it('prefixes an explicit cross-origin base correctly', () => {
    expect(buildApiUrl('/health', 'https://api.example.com')).toBe(
      'https://api.example.com/api/health',
    );
  });

  it('rejects a path that already contains the /api prefix', () => {
    expect(() => buildApiUrl('/api/health', '')).toThrow(/must not include/);
  });

  it('rejects a path that does not start with a slash', () => {
    expect(() => buildApiUrl('health', '')).toThrow(/must start with/);
  });
});

describe('messageForStatus', () => {
  it('reports an unreachable server for status 0', () => {
    expect(messageForStatus(0)).toContain('Cannot reach the API server');
  });

  it('maps oversized uploads to a clear message', () => {
    expect(messageForStatus(413)).toContain('too large');
  });

  it('returns a generic message for server errors', () => {
    const message = messageForStatus(500);
    expect(message).toContain('server');
    expect(message).not.toContain('Traceback');
    expect(message).not.toContain('at ');
  });

  it('falls back to a status-based message otherwise', () => {
    expect(messageForStatus(418)).toContain('418');
  });
});

describe('ApiError', () => {
  it('carries the status and message', () => {
    const error = new ApiError(400, 'Bad input');
    expect(error.status).toBe(400);
    expect(error.message).toBe('Bad input');
    expect(error).toBeInstanceOf(Error);
  });
});
