import DataTable from '../components/DataTable';
import FileUpload from '../components/FileUpload';
import StatCard from '../components/StatCard';
import { useDataset } from '../context/DatasetContext';

export default function UploadPage() {
  const { preview } = useDataset();

  return (
    <div className="space-y-6">
      <FileUpload />

      {preview && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Rows" value={String(preview.rows)} accent />
            <StatCard
              label="Columns"
              value={String(preview.columns_count)}
            />
            <StatCard
              label="Total missing"
              value={String(
                preview.columns.reduce(
                  (sum, column) => sum + column.missing_values,
                  0,
                ),
              )}
            />
            <StatCard label="File" value={preview.filename} />
          </div>

          <section className="space-y-3">
            <h3 className="font-semibold text-slate-700">Columns</h3>
            <DataTable
              headers={['Name', 'Data type', 'Missing values']}
              rows={preview.columns.map((column) => [
                column.name,
                column.data_type,
                column.missing_values,
              ])}
            />
          </section>

          <section className="space-y-3">
            <h3 className="font-semibold text-slate-700">
              Preview (first rows)
            </h3>
            <DataTable
              headers={preview.columns.map((column) => column.name)}
              rows={preview.preview.map((row) =>
                preview.columns.map((column) => {
                  const value = row[column.name];
                  return value === null || value === undefined
                    ? ''
                    : String(value);
                }),
              )}
            />
          </section>
        </>
      )}
    </div>
  );
}
