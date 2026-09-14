import { AlertTriangle } from "lucide-react";
import { formatTime } from "./helpers";
import type { Anomaly } from "../types/Types";

export function ChartTooltip({ active, payload, label, anomalies }: {
  active?: boolean; payload?: any[]; label?: string; anomalies: Anomaly[];
}) {
  if (!active || !payload?.length) return null;
  const matching = anomalies.filter((a) => formatTime(a.timestamp) === label);
  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/98 p-3 shadow-2xl min-w-45">
      <p className="text-[10px] text-slate-400 mb-2 font-mono">{label}</p>
      {payload.map((e: any) => (
        <div key={e.dataKey} className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full shrink-0" style={{ background: e.color }} />
          <span className="text-xs text-slate-300 flex-1 font-mono truncate max-w-27.5">
            {String(e.name).replace(/__cpu|__ram/, "")}
          </span>
          <span className="text-xs font-mono font-semibold text-white">
            {typeof e.value === "number" ? e.value.toFixed(1) : e.value}%
          </span>
        </div>
      ))}
      {matching.length > 0 && (
        <div className="mt-2 pt-2 border-t border-slate-700/50 space-y-1">
          {matching.map((a) => (
            <div key={a.id} className="flex items-start gap-1.5">
              <AlertTriangle size={10} className="text-amber-400 mt-0.5 shrink-0" />
              <div>
                <span className="text-[10px] font-mono text-amber-400">{a.device}: </span>
                <span className="text-[10px] text-slate-400">{a.reason}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}