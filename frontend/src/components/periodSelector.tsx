const PERIODS = [
  { label: "1h", value: 1 },
  { label: "6h", value: 6 },
  { label: "24h", value: 24 },
  { label: "7d", value: 168 },
  { label: "All", value: 0 },
];
export function PeriodSelector({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-1 p-1 bg-slate-900/60 rounded-xl border border-slate-700/40">
      {PERIODS.map((p) => (
        <button
          key={p.value}
          onClick={() => onChange(p.value)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            value === p.value ? "bg-slate-700 text-white" : "text-slate-500 hover:text-slate-300"
          }`}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}