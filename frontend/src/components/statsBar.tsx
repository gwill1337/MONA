import type { Device } from "../pages/DeviceAdmin";

export function StatsBar({ devices }: { devices: Device[] }) {
  const total = devices.length;
  const online = devices.filter((d) => d.is_active).length;
  const offline = total - online;

  return (
    <div className="grid grid-cols-3 gap-4 mb-8">
      {[
        { label: "Total", value: total, color: "text-white" },
        { label: "Online", value: online, color: "text-emerald-400" },
        { label: "Offline", value: offline, color: "text-slate-500" },
      ].map((s) => (
        <div
          key={s.label}
          className="rounded-xl border border-slate-700/40 bg-slate-900/40 px-4 py-3 text-center"
        >
          <p className={`text-2xl font-bold tabular-nums ${s.color}`}>{s.value}</p>
          <p className="text-xs text-slate-500 mt-0.5 uppercase tracking-widest">{s.label}</p>
        </div>
      ))}
    </div>
  );
}