interface Props {
  title: string;
  hint?: string;
}

export default function EmptyState({ title, hint }: Props) {
  return (
    <div className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 px-6 py-12 text-center">
      <p className="text-base font-semibold text-slate-500">{title}</p>
      {hint && <p className="mt-1 text-sm text-slate-400">{hint}</p>}
    </div>
  );
}
