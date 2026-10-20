export default function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-slate-600" role="status">
      <span className="size-5 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600" />
      <span className="text-sm">{label}</span>
    </div>
  );
}
