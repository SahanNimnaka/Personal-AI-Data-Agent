import { useCallback, useRef, useState } from 'react';
import { askAgent } from '../api/client';
import type { AgentResponse } from '../api/types';
import EmptyState from '../components/EmptyState';
import ErrorAlert from '../components/ErrorAlert';
import Spinner from '../components/Spinner';
import ToolActivity from '../components/ToolActivity';
import { useDataset } from '../context/DatasetContext';
import { validateQuestion } from '../utils/validation';

interface Message {
  id: number;
  question: string;
  response: AgentResponse;
}

const SUGGESTIONS = [
  'Give me an overview of the dataset',
  'What is the mean of the sales column?',
  'Show correlations',
  'Are there any outliers in the sales column?',
];

export default function AgentPage() {
  const { file } = useDataset();
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(
    null,
  );
  const nextId = useRef(1);

  const ask = useCallback(
    async (text: string) => {
      if (!file) return;

      const validation = validateQuestion(text);
      if (!validation.ok) {
        setValidationError(validation.error ?? 'Invalid question.');
        return;
      }

      setValidationError(null);
      setError(null);
      setLoading(true);
      try {
        const response = await askAgent(file, text.trim());
        setMessages((previous) => [
          ...previous,
          { id: nextId.current++, question: text.trim(), response },
        ]);
        setQuestion('');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Request failed.');
      } finally {
        setLoading(false);
      }
    },
    [file],
  );

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
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void ask(question);
          }}
          className="space-y-3"
        >
          <label className="block text-sm font-medium text-slate-700">
            Ask a question about your dataset
          </label>
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={2}
            maxLength={2000}
            placeholder="e.g. Which category has the highest total sales?"
            className="w-full resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">
              {question.length}/2000
            </span>
            <button
              type="submit"
              disabled={loading || question.trim().length === 0}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Asking…' : 'Ask'}
            </button>
          </div>
        </form>

        {validationError && (
          <p className="mt-2 text-sm text-red-600">{validationError}</p>
        )}

        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => void ask(suggestion)}
              disabled={loading}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600 hover:bg-slate-100 disabled:opacity-50"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      {loading && <Spinner label="Analyzing your question…" />}
      {error && (
        <ErrorAlert
          title="Agent request failed"
          message={error}
          onRetry={() => void ask(question || 'Give me an overview')}
        />
      )}

      {messages.length === 0 && !loading && (
        <EmptyState
          title="No conversation yet"
          hint="Ask a question above or try a suggestion."
        />
      )}

      <div className="space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className="rounded-xl border border-slate-200 bg-white p-4"
          >
            <p className="text-sm font-semibold text-slate-500">
              You asked
            </p>
            <p className="mb-3 text-slate-800">{message.question}</p>

            <div
              className={`mb-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                message.response.source === 'llm'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-amber-100 text-amber-800'
              }`}
            >
              {message.response.source === 'llm'
                ? `LLM (${message.response.provider})`
                : 'Deterministic fallback'}
            </div>

            <p className="whitespace-pre-wrap text-slate-800">
              {message.response.answer}
            </p>

            {message.response.source === 'fallback' && (
              <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
                {message.response.notes}
              </p>
            )}

            <div className="mt-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Tools executed
              </p>
              <ToolActivity tools={message.response.tools_executed} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
