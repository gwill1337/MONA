import { Activity, ChevronRight, Server, Trash2, Wifi, WifiOff } from "lucide-react";
import { useNavigate } from "react-router-dom";
import type { Device } from "../pages/DeviceAdmin";

interface DeviceCardProps {
  device: Device;
  index: number;
  onDelete: (device: Device) => void;
}

const PulseDot = ({ active }: { active: boolean }) => (
  <span className="relative flex h-2.5 w-2.5">
    {active && (
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
    )}
    <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${active ? "bg-emerald-400" : "bg-slate-600"}`} />
  </span>
);

export function DeviceCard({ device, index, onDelete }: DeviceCardProps) {
  const navigate = useNavigate();
  const handleClick = () => {
    navigate(`/dashboard?device=${encodeURIComponent(device.name)}`);
  };

  return (
    <div
      onClick={handleClick}
      className="group relative cursor-pointer rounded-2xl border border-slate-700/50 bg-slate-900/60 hover:bg-slate-800/70 hover:border-slate-600/70 transition-all duration-200 overflow-hidden"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div
        className={`h-px w-full bg-linear-to-r from-transparent to-transparent transition-all duration-300 ${device.is_active
            ? "via-cyan-500 group-hover:via-cyan-400"
            : "via-slate-600"
          }`}
      />

      <div className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div
            className={`p-2.5 rounded-xl transition-all duration-200 ${device.is_active
                ? "bg-cyan-500/10 text-cyan-400 group-hover:bg-cyan-500/20"
                : "bg-slate-800 text-slate-500"
              }`}
          >
            <Server size={22} />
          </div>
          <div className="flex items-center gap-2">
            <PulseDot active={device.is_active} />
            <span
              className={`text-xs font-medium ${device.is_active ? "text-emerald-400" : "text-slate-500"
                }`}
            >
              {device.is_active ? "online" : "offline"}
            </span>
          </div>
        </div>

        <p className="font-semibold text-white text-base tracking-tight mb-1 group-hover:text-cyan-50 transition-colors">
          {device.name}
        </p>

        <div className="flex items-center gap-1.5 mb-4">
          {device.is_active ? (
            <span className="text-cyan-500/60"><Wifi size={14} /></span>
          ) : (
            <span className="text-slate-600"><WifiOff size={14} /></span>
          )}
          <span className="text-xs font-mono text-slate-400 group-hover:text-slate-300 transition-colors">
            {device.ip}
          </span>
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-slate-700/40">
          <div className="flex items-center gap-1.5 text-slate-500 group-hover:text-cyan-500 transition-colors">
            <Activity size={16} />
            <span className="text-xs">View dashboard</span>
          </div>
          <span className="text-slate-600 group-hover:text-cyan-500 transition-all duration-200 translate-x-0 group-hover:translate-x-0.5">
            <ChevronRight size={16} />
          </span>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(device);
            }}
            className="text-slate-600 hover:text-red-500 hover:bg-red-500/10 p-1.5 rounded-lg transition-all"
            title="Delete device"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}