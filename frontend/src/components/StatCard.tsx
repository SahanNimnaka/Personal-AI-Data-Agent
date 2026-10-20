interface Props {
  label: string;
  value: string;
  accent?: boolean;
}

export default function StatCard({ label, value, accent }: Props) {
  return (
    <div
      className={`rounded-xl border p-4 ${
        accent
          ? 'border-blue-200 bg-blue-50'
          : 'border-slate-200 bg-white'
      }`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold text-slate-800">
        {value}
      </p>
    </div>
  );
}
