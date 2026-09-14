import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../api";
import {
  Server,
  Plus,
  RefreshCw,
} from "lucide-react";
import { AddDeviceModal } from "../components/modals/addDeviceModal";
import { ConfirmDeleteModal } from "../components/modals/confirmDeleteModal";
import { DeviceCard } from "../components/deviceCard";
import { StatsBar } from "../components/statsBar";
import { useNavigate } from "react-router-dom";
// import { AddUserModal } from "../components/modals/addUserModal";

// ─── Types ──────────────────────────────────────────────────────────────────
export interface Device {
  id: number;
  ip: string;
  name: string;
  is_active: boolean;
}

// ─── Main App ────────────────────────────────────────────────────────────────
export default function DeviceAdmin() {
  const navigate = useNavigate();
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAddDeviceModal, setAddDeviceShowModal] = useState(false);
  const [filter, setFilter] = useState<"all" | "online" | "offline">("all");
  const [lastFetched, setLastFetched] = useState<Date | null>(null);
  const [deviceToDelete, setDeviceToDelete] = useState<Device | null>(null);

  const fetchDevices = useCallback(async () => {
    try {
      const data = await apiFetch<Device[]>("/devices");
      setDevices(data);
      setLastFetched(new Date());
      setError("");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // const fetchUsers = useCallback(async () => {
  //   try {
  //     const data = await apiFetch<User[]>("/api/v1//users");
  //     setLastFetched(new Date());
  //     setError("");
  //   } catch (e: any) {
  //     setError(e.message);
  //   } finally {
  //     setLoading(false);
  //   }
  // }, []);

  const handleDeleteConfirm = async () => {
    if (!deviceToDelete) return;
    try {
      await apiFetch(`/devices/${deviceToDelete.id}`, {
        method: "DELETE",
      });

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
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-150 h-px bg-linear-to-r from-transparent via-cyan-500/40 to-transparent" />

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
                className="p-2.5 rounded-xl border border-slate-700/60 bg-slate-900/60 text-slate-400 hover:text-white hover:border-slate-600 transition-all cursor-pointer"
                title="Refresh"
              >
                <RefreshCw size={16} />
              </button>
              <button
                onClick={() => setAddDeviceShowModal(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-sm transition-all shadow-lg shadow-cyan-500/20 hover:shadow-cyan-400/30 cursor-pointer"
              >
                <Plus size={18} />
                Add device
              </button>
              <button
                onClick={() => navigate("/userboard")}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-sm transition-all shadow-lg shadow-cyan-500/20 hover:shadow-cyan-400/30 cursor-pointer"
              >
                Userboard
              </button>
              <button
                onClick={() => navigate("/dashboard")}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-sm transition-all shadow-lg shadow-cyan-500/20 hover:shadow-cyan-400/30 cursor-pointer"
              >
                Dashboard
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
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all capitalize ${filter === f
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
                onClick={() => setAddDeviceShowModal(true)}
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
      {showAddDeviceModal && (
        <AddDeviceModal
          onClose={() => setAddDeviceShowModal(false)}
          onAdded={fetchDevices}
        />
      )}

      {/* {showAddUserModal && (
        <AddUserModal
          onClose={() => setAddUserShowModal(false)}
        // onAdded={fetchUsers}
        />
      )} */}

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