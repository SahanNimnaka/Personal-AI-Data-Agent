import { useRef, useState } from 'react';
import { useDataset } from '../context/DatasetContext';
import { formatBytes, validateCsvFile } from '../utils/validation';

export default function FileUpload() {
  const { file, preview, uploading, error, upload, clear } =
    useDataset();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleFile(candidate: File) {
    setLocalError(null);
    const validation = validateCsvFile(candidate);
    if (!validation.ok) {
      setLocalError(validation.error ?? 'Invalid file.');
      return;
    }
    await upload(candidate);
  }

  function onDrop(event: React.DragEvent) {
    event.preventDefault();
    setDragActive(false);
    const dropped = event.dataTransfer.files[0];
    if (dropped) {
      void handleFile(dropped);
    }
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        className={`rounded-xl border-2 border-dashed p-10 text-center transition ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-slate-300 bg-white'
        }`}
      >
        <p className="text-lg font-semibold text-slate-700">
          Upload a CSV dataset
        </p>
        <p className="mt-1 text-sm text-slate-500">
          Drag and drop a file here, or browse. Maximum size 10 MB.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(event) => {
            const selected = event.target.files?.[0];
            if (selected) {
              void handleFile(selected);
            }
            event.target.value = '';
          }}
        />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {uploading ? 'Uploading…' : 'Choose CSV file'}
        </button>
      </div>

      {(localError || error) && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {localError ?? error}
        </div>
      )}

      {preview && file && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
          <div className="text-sm text-emerald-800">
            <span className="font-semibold">{preview.filename}</span> loaded —{' '}
            {preview.rows} rows, {preview.columns_count} columns (
            {formatBytes(file.size)}).
          </div>
          <button
            onClick={clear}
            className="rounded-md border border-emerald-300 px-3 py-1 text-sm text-emerald-800 hover:bg-emerald-100"
          >
            Clear dataset
          </button>
        </div>
      )}
    </div>
  );
}
