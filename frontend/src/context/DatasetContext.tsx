import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { uploadDataset } from '../api/client';
import type { UploadResponse } from '../api/types';
import { validateCsvFile } from '../utils/validation';

interface DatasetState {
  file: File | null;
  preview: UploadResponse | null;
  uploading: boolean;
  error: string | null;
  upload: (file: File) => Promise<boolean>;
  clear: () => void;
}

const DatasetContext = createContext<DatasetState | null>(null);

export function DatasetProvider({ children }: { children: ReactNode }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<UploadResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = useCallback(async (candidate: File) => {
    const validation = validateCsvFile(candidate);
    if (!validation.ok) {
      setError(validation.error ?? 'Invalid file.');
      return false;
    }

    setUploading(true);
    setError(null);
    try {
      const result = await uploadDataset(candidate);
      setFile(candidate);
      setPreview(result);
      return true;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Upload failed.',
      );
      return false;
    } finally {
      setUploading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setFile(null);
    setPreview(null);
    setError(null);
  }, []);

  const value = useMemo(
    () => ({ file, preview, uploading, error, upload, clear }),
    [file, preview, uploading, error, upload, clear],
  );

  return (
    <DatasetContext.Provider value={value}>
      {children}
    </DatasetContext.Provider>
  );
}

export function useDataset(): DatasetState {
  const context = useContext(DatasetContext);
  if (!context) {
    throw new Error('useDataset must be used within DatasetProvider');
  }
  return context;
}
