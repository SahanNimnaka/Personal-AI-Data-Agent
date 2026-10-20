import { useMemo } from 'react';
import { useDataset } from '../context/DatasetContext';

const NUMERIC_DTYPE = /^(int|uint|float|double|decimal|number)/i;

export function useNumericColumns(): string[] {
  const { preview } = useDataset();
  return useMemo(
    () =>
      preview
        ? preview.columns
            .filter((column) => NUMERIC_DTYPE.test(column.data_type))
            .map((column) => column.name)
        : [],
    [preview],
  );
}

export function useCategoricalColumns(): string[] {
  const { preview } = useDataset();
  return useMemo(
    () =>
      preview
        ? preview.columns
            .filter((column) => !NUMERIC_DTYPE.test(column.data_type))
            .map((column) => column.name)
        : [],
    [preview],
  );
}

export function useAllColumns(): string[] {
  const { preview } = useDataset();
  return useMemo(
    () => (preview ? preview.columns.map((column) => column.name) : []),
    [preview],
  );
}
