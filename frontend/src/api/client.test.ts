import { describe, expect, it } from 'vitest';
import { ApiError, messageForStatus } from './client';

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
