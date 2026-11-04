import { useState } from "react";

const PERIODS = [
  { label: "1h", value: 1 },
  { label: "6h", value: 6 },
  { label: "24h", value: 24 },
  { label: "7d", value: 168 },
  { label: "30d", value: 720 },
];

interface PeriodSelectorProps {
  value: number;
  customRange: { start: string; end: string } | null;
  onChange: (hours: number, custom?: { start: string; end: string } | null) => void;
}

export function PeriodSelector({ value, customRange, onChange }: PeriodSelectorProps) {
  const [showCustom, setShowCustom] = useState(false);
  const [startDate, setStartDate] = useState(customRange?.start || "");
  const [endDate, setEndDate] = useState(customRange?.end || "");

  const handleApplyCustom = () => {
    if (startDate && endDate) {
      const fixedEndDate = endDate.length === 16 ? `${endDate}:59` : endDate;
      onChange(-1, {
        start: new Date(startDate).toISOString(),
        end: new Date(fixedEndDate).toISOString()
      });
    }
  };

  return (
    <div className="flex flex-wrap items-center">
      <div className="inline-flex items-center gap-1 p-1 bg-gray-400/15 rounded-xl border border-slate-700/40">
        {PERIODS.map((p) => (
          <button
            key={p.value}
            onClick={() => { onChange(p.value), setShowCustom(false) }}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${value === p.value && !showCustom && value !== -1 ? "bg-slate-700 text-white" : "text-slate-500 hover:text-slate-300"}`}
          >
            {p.label}
          </button>
        ))}
        <button
          onClick={() => setShowCustom(!showCustom)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${showCustom || value === -1 ? "bg-slate-700 text-white" : "text-slate-500 hover:text-slate-300"}`}
        >
          Custom
        </button>

        {showCustom && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <input
              type="datetime-local"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="bg-black/50 text-slate-300 px-2 py-1 rounded border border-slate-700 focus:outline-none font-mono"
            />
            <span className="text-slate-500">—</span>
            <input
              type="datetime-local"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-black/50 text-slate-300 px-2 py-1 rounded border border-slate-700 focus:outline-none font-mono"
            />
            <button
              onClick={handleApplyCustom}
              className="bg-white hover:bg-gray-300 text-black px-3 py-1 rounded font-semibold transition-all cursor-pointer"
            >
              OK
            </button>
          </div>
        )}

      </div>
    </div>
  );
}