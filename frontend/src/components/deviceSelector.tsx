import { useEffect, useRef, useState } from "react";
import type { Device } from "../pages/DeviceAdmin";
import { CheckSquare, ChevronDown, Server, Square, Wifi, WifiOff } from "lucide-react";

export function DeviceSelector({ devices, selected, onChange, deviceColorMap }: {
  devices: Device[];
  selected: string[];
  onChange: (s: string[]) => void;
  deviceColorMap: Record<string, string>;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const toggle = (name: string) => {
    if (selected.includes(name)) {
      if (selected.length === 1) return;
      onChange(selected.filter((d) => d !== name));
    } else {
      onChange([...selected, name]);
    }
  };

  const allSelected = devices.length > 0 && devices.every((d) => selected.includes(d.name));

  const label = allSelected
    ? "All devices"
    : selected.length === 1
    ? selected[0]
    : `${selected.length} devices`;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-700/60 bg-slate-900/80 text-sm text-slate-200 hover:border-slate-600 transition-all"
      >
        <Server size={14} className="text-cyan-400 shrink-0" />
        <span className="max-w-40 truncate">{label}</span>
        <ChevronDown size={13} className={`text-slate-400 transition-transform shrink-0 ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-2 z-50 w-64 rounded-2xl border border-slate-700/60 bg-slate-900 shadow-2xl shadow-black/70 overflow-hidden">
          <div className="h-px w-full bg-linear-to-r from-transparent via-cyan-500/40 to-transparent" />
          <div className="p-2">
            {/* All toggle */}
            <button
              onClick={() =>
                allSelected
                  ? onChange(devices.length > 0 ? [devices[0].name] : [])
                  : onChange(devices.map((d) => d.name))
              }
              className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all mb-1"
            >
              {allSelected
                ? <CheckSquare size={14} className="text-cyan-400" />
                : <Square size={14} />}
              <span>All devices</span>
            </button>
            <div className="h-px bg-slate-800 mb-1" />
            {devices.map((device) => {
              const checked = selected.includes(device.name);
              const color = deviceColorMap[device.name];
              return (
                <button
                  key={device.id}
                  onClick={() => toggle(device.name)}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm hover:bg-slate-800 transition-all"
                >
                  {checked
                    ? <CheckSquare size={14} style={{ color }} />
                    : <Square size={14} className="text-slate-600" />}
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: color, opacity: checked ? 1 : 0.3 }}
                  />
                  <span className={`flex-1 text-left text-xs font-mono ${checked ? "text-white" : "text-slate-500"}`}>
                    {device.name}
                  </span>
                  {device.is_active
                    ? <Wifi size={11} className="text-emerald-400" />
                    : <WifiOff size={11} className="text-slate-600" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}