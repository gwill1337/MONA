import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Server,
  Plus,
  Activity,
  X,
  RefreshCw,
  ChevronRight,
  Wifi,
  WifiOff,
  Trash2,
} from "lucide-react";

// ─── Types ──────────────────────────────────────────────────────────────────
interface Device {
  id: number;
  ip: string;
  name: string;
  is_active: boolean;
}

const API_BASE = "http://localhost:30080";

// ─── Pulse dot ──────────────────────────────────────────────────────────────
const PulseDot = ({ active }: { active: boolean }) => (
  <span className="relative flex h-2.5 w-2.5">
    {active && (
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-60" />
    )}
    <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${active ? "bg-emerald-400" : "bg-slate-600"}`} />
  </span>
);

// ─── Confirm Delete Modal ───────────────────────────────────────────────────
interface ConfirmDeleteModalProps {
  device: Device;
  onClose: () => void;
  onConfirm: () => void;
}
function ConfirmDeleteModal({ device, onClose, onConfirm }: ConfirmDeleteModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-sm mx-4 rounded-2xl border border-red-500/30 bg-slate-900 shadow-2xl shadow-black/60 overflow-hidden">
        {/* Header glow bar */}
        <div className="h-px w-full bg-gradient-to-r from-transparent via-red-500 to-transparent" />
        
        <div className="p-6 text-center">
          <div className="mx-auto w-12 h-12 flex items-center justify-center rounded-full bg-red-500/10 text-red-500 mb-4">
            <Trash2 size={24} />
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">Delete {device.name}?</h2>
          <p className="text-sm text-slate-400 mb-6">
            Are you sure you want to remove <span className="text-slate-300 font-mono">{device.ip}</span>? This action cannot be undone.
          </p>
          
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-xl border border-slate-700 text-slate-400 text-sm hover:text-white hover:border-slate-600 transition-all"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 px-4 py-2.5 rounded-xl bg-red-500 hover:bg-red-400 text-white font-semibold text-sm transition-all shadow-lg shadow-red-500/20"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Add Device Modal ────────────────────────────────────────────────────────
interface AddDeviceModalProps {
  onClose: () => void;
  onAdded: () => void;
}
function AddDeviceModal({ onClose, onAdded }: AddDeviceModalProps) {
  const [form, setForm] = useState({ ip: "", name: "", is_active: true });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!form.ip.trim() || !form.name.trim()) {
      setError("IP and name are required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/devices`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `HTTP ${res.status}`);
      }
      onAdded();
      onClose();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-md mx-4 rounded-2xl border border-slate-700/60 bg-slate-900 shadow-2xl shadow-black/60 overflow-hidden">
        <div className="h-px w-full bg-gradient-to-r from-transparent via-cyan-500 to-transparent" />

        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white tracking-tight">Add device</h2>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-slate-800"
            >
              <X size={16} />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-widest">
                IP address
              </label>
              <input
                type="text"
                placeholder="192.168.1.10"
                value={form.ip}
                onChange={(e) => setForm((f) => ({ ...f, ip: e.target.value }))}
                className="w-full bg-slate-800/60 border border-slate-700/70 text-white placeholder-slate-500 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500/70 focus:ring-1 focus:ring-cyan-500/30 transition-all font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-widest">
                Device name
              </label>
              <input
                type="text"
                placeholder="pc-office-01"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full bg-slate-800/60 border border-slate-700/70 text-white placeholder-slate-500 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500/70 focus:ring-1 focus:ring-cyan-500/30 transition-all font-mono"
              />
            </div>
            <div className="flex items-center justify-between py-1">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-widest">Active</span>
              <button
                type="button"
                onClick={() => setForm((f) => ({ ...f, is_active: !f.is_active }))}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                  form.is_active ? "bg-cyan-500" : "bg-slate-700"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${
                    form.is_active ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          </div>

          {error && (
            <p className="mt-4 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <div className="mt-6 flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-xl border border-slate-700 text-slate-400 text-sm hover:text-white hover:border-slate-600 transition-all"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="flex-1 px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20"
            >
              {loading ? "Adding…" : "Add device"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Device Card ─────────────────────────────────────────────────────────────
interface DeviceCardProps {
  device: Device;
  index: number;
  onDelete: (device: Device) => void;
}
function DeviceCard({ device, index, onDelete }: DeviceCardProps) {
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
        className={`h-px w-full bg-gradient-to-r from-transparent to-transparent transition-all duration-300 ${
          device.is_active
            ? "via-cyan-500 group-hover:via-cyan-400"
            : "via-slate-600"
        }`}
      />

      <div className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div
            className={`p-2.5 rounded-xl transition-all duration-200 ${
              device.is_active
                ? "bg-cyan-500/10 text-cyan-400 group-hover:bg-cyan-500/20"
                : "bg-slate-800 text-slate-500"
            }`}
          >
            <Server size={22} />
          </div>
          <div className="flex items-center gap-2">
            <PulseDot active={device.is_active} />
            <span
              className={`text-xs font-medium ${
                device.is_active ? "text-emerald-400" : "text-slate-500"
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

// ─── Stats Bar ───────────────────────────────────────────────────────────────
function StatsBar({ devices }: { devices: Device[] }) {
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

// ─── Main App ────────────────────────────────────────────────────────────────
export default function DeviceAdmin() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [filter, setFilter] = useState<"all" | "online" | "offline">("all");
  const [lastFetched, setLastFetched] = useState<Date | null>(null);
  const [deviceToDelete, setDeviceToDelete] = useState<Device | null>(null);

  const fetchDevices = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/devices`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDevices(data);
      setLastFetched(new Date());
      setError("");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleDeleteConfirm = async () => {
    if (!deviceToDelete) return;
    try {
      const res = await fetch(`${API_BASE}/devices/${deviceToDelete.id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete device");
      
      setDeviceToDelete(null);
      fetchDevices();
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 15000);
    return () => clearInterval(interval);
  }, [fetchDevices]);

  const filtered = devices.filter((d) => {
    if (filter === "online") return d.is_active;
    if (filter === "offline") return !d.is_active;
    return true;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans">
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(rgba(148,163,184,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(148,163,184,0.03) 1px, transparent 1px)`,
          backgroundSize: "48px 48px",
        }}
      />
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[600px] h-px bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />

      <div className="relative max-w-5xl mx-auto px-6 py-10">

        {/* ── Header ── */}
        <header className="mb-10">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-2.5 mb-2">
                <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400">
                  <Server size={22} />
                </div>
                <span className="text-xs font-semibold text-cyan-400/80 uppercase tracking-[0.2em]">
                  Infrastructure
                </span>
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-white">
                Device Registry
              </h1>
              <p className="text-slate-400 text-sm mt-1">
                Manage monitored endpoints
              </p>
            </div>

            <div className="flex items-center gap-3 mt-1">
              {lastFetched && (
                <span className="text-xs text-slate-500 hidden sm:block">
                  synced {lastFetched.toLocaleTimeString()}
                </span>
              )}
              <button
                onClick={fetchDevices}
                className="p-2.5 rounded-xl border border-slate-700/60 bg-slate-900/60 text-slate-400 hover:text-white hover:border-slate-600 transition-all"
                title="Refresh"
              >
                <RefreshCw size={16} />
              </button>
              <button
                onClick={() => setShowModal(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-sm transition-all shadow-lg shadow-cyan-500/20 hover:shadow-cyan-400/30"
              >
                <Plus size={18} />
                Add device
              </button>
            </div>
          </div>
        </header>

        {/* ── Stats ── */}
        {!loading && !error && <StatsBar devices={devices} />}

        {/* ── Filter tabs ── */}
        <div className="flex gap-1 mb-6 p-1 bg-slate-900/60 rounded-xl border border-slate-700/40 w-fit">
          {(["all", "online", "offline"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all capitalize ${
                filter === f
                  ? "bg-slate-700 text-white shadow-sm"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {/* ── Content ── */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-8 h-8 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
            <p className="text-slate-500 text-sm">Connecting to API…</p>
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center">
            <p className="text-red-400 text-sm font-medium mb-1">Failed to load devices</p>
            <p className="text-slate-500 text-xs font-mono">{error}</p>
            <button
              onClick={fetchDevices}
              className="mt-4 text-xs text-red-400 hover:text-red-300 underline underline-offset-2"
            >
              Retry
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-slate-700/40 bg-slate-900/30 p-12 text-center">
            <div className="text-slate-600 mb-3 flex justify-center">
              <Server size={32} />
            </div>
            <p className="text-slate-400 text-sm">
              {filter === "all" ? "No devices registered yet." : `No ${filter} devices.`}
            </p>
            {filter === "all" && (
              <button
                onClick={() => setShowModal(true)}
                className="mt-4 text-xs text-cyan-500 hover:text-cyan-400 underline underline-offset-2"
              >
                Add your first device →
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((d, i) => (
              <DeviceCard key={d.id}
              device={d}
              index={i}
              onDelete={(device) => setDeviceToDelete(device)}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Modal ── */}
      {showModal && (
        <AddDeviceModal
          onClose={() => setShowModal(false)}
          onAdded={fetchDevices}
        />
      )}

      {deviceToDelete && (
        <ConfirmDeleteModal
          device={deviceToDelete}
          onClose={() => setDeviceToDelete(null)}
          onConfirm={handleDeleteConfirm}
        />
      )}
    </div>
  );
}