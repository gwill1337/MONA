export function StatCard({ label, value, sub, icon, accent = "text-white" }: {
  label: string; value: string | number; sub?: string; icon: React.ReactNode; accent?: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-700/40 bg-slate-900/50 p-4">
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs text-slate-500 uppercase tracking-widest">{label}</span>
        <span className="text-slate-600">{icon}</span>
      </div>
      <p className={`text-2xl font-bold tabular-nums ${accent}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}