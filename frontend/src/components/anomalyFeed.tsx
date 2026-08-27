import { Activity, AlertTriangle } from "lucide-react";
import { formatDateTime } from "../helpers/helpers";
import { useEffect, useRef } from "react";
import type { Anomaly } from "../types/Types";

export function AnomalyFeed({ anomalies, deviceColorMap }: {
  anomalies: Anomaly[];
  deviceColorMap: Record<string, string>;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to top whenever anomalies change (newest are prepended)
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [anomalies]);

  if (anomalies.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 gap-2 text-slate-600">
        <Activity size={20} />
        <p className="text-xs">No anomalies detected</p>
      </div>
    );
  }

  // Already sorted newest-first from API (order_by desc), but reverse just in case
  const sorted = [...anomalies].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return (
    <div ref={scrollRef} className="space-y-2 max-h-96 overflow-y-auto pr-1 custom-scroll">
      {sorted.map((a) => {
        const color = deviceColorMap[a.device] ?? "#94a3b8";
        const severity = a.score < -0.15 ? "high" : a.score < -0.05 ? "mid" : "low";
        const sevColor = severity === "high" ? "#f87171" : severity === "mid" ? "#fb923c" : "#facc15";
        return (
          <div
            key={a.id}
            className="rounded-xl border bg-slate-900/60 p-3 hover:bg-slate-800/60 transition-all"
            style={{ borderColor: `${color}22` }}
          >
            <div className="flex items-start gap-2.5">
              <AlertTriangle size={13} className="shrink-0 mt-0.5" style={{ color: sevColor }} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                  <span className="text-xs font-semibold font-mono" style={{ color }}>{a.device}</span>
                  <span className="text-[10px] text-slate-500 font-mono">{formatDateTime(a.timestamp)}</span>
                </div>
                <p className="text-xs text-slate-300">{a.reason}</p>
                <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                  <span className="text-[10px] text-slate-500 font-mono">CPU {a.cpu.toFixed(1)}%</span>
                  <span className="text-[10px] text-slate-500 font-mono">RAM {a.ram.toFixed(1)}%</span>
                  <span className="text-[10px] font-mono ml-auto" style={{ color: sevColor }}>
                    score {a.score.toFixed(4)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}