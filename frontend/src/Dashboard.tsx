import { useState, useEffect, useCallback, useRef } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceDot, Legend,
} from "recharts";
import {
  Activity, AlertTriangle, BrainCircuit, ChevronDown,
  CheckSquare, Clock, Cpu, MemoryStick, RefreshCw,
  Server, Square, Trash2, Wifi, WifiOff, X, Zap,
} from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────
interface Device {
  id: number;
  ip: string;
  name: string;
  is_active: boolean;
}
interface MetricPoint {
  timestamp: string;
  cpu: number;
  ram: number;
  device: string;
}
interface Anomaly {
  id: number;
  timestamp: string;
  cpu: number;
  ram: number;
  reason: string;
  score: number;
  device: string;
}
interface ModelInfo {
  status: "ok" | "no_model";
  message?: string;
  model?: {
    trained_at: string;
    trained_by: string;
    points_count: number;
    period_from: string;
    period_to: string;
    note: string | null;
  };
}
interface DashboardData {
  devices: string[];
  metrics: MetricPoint[];
  anomalies: Anomaly[];
}

const API_BASE = "http://localhost:30080";

const DEVICE_COLORS = [
  "#22d3ee", "#a78bfa", "#fb923c", "#34d399",
  "#f472b6", "#facc15", "#60a5fa", "#f87171",
];
function getDeviceColor(i: number) { return DEVICE_COLORS[i % DEVICE_COLORS.length]; }

// ─── URL helpers ──────────────────────────────────────────────────────────────
function getUrlDevices(): string[] {
  const params = new URLSearchParams(window.location.search);
  const raw = params.get("device");
  if (!raw) return [];
  return raw.split(",").map((s) => s.trim()).filter(Boolean);
}

function setUrlDevices(devices: string[]) {
  const params = new URLSearchParams(window.location.search);
  if (devices.length === 0) {
    params.delete("device");
  } else {
    params.set("device", devices.join(","));
  }
  const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
  window.history.replaceState(null, "", newUrl);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatTime(iso: string) {
  // Append Z if no timezone info to treat as UTC and avoid local-shift
  const s = /[Zz]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + "Z";
  return new Date(s).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
function formatDateTime(iso: string) {
  const s = /[Zz]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + "Z";
  return new Date(s).toLocaleString("ru-RU", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

// ─── Custom Tooltip ───────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label, anomalies }: {
  active?: boolean; payload?: any[]; label?: string; anomalies: Anomaly[];
}) {
  if (!active || !payload?.length) return null;
  const matching = anomalies.filter((a) => formatTime(a.timestamp) === label);
  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/98 p-3 shadow-2xl min-w-[180px]">
      <p className="text-[10px] text-slate-400 mb-2 font-mono">{label}</p>
      {payload.map((e: any) => (
        <div key={e.dataKey} className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: e.color }} />
          <span className="text-xs text-slate-300 flex-1 font-mono truncate max-w-[110px]">
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
              <AlertTriangle size={10} className="text-amber-400 mt-0.5 flex-shrink-0" />
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

// ─── Device Selector ──────────────────────────────────────────────────────────
function DeviceSelector({ devices, selected, onChange, deviceColorMap }: {
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
        <Server size={14} className="text-cyan-400 flex-shrink-0" />
        <span className="max-w-[160px] truncate">{label}</span>
        <ChevronDown size={13} className={`text-slate-400 transition-transform flex-shrink-0 ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-2 z-50 w-64 rounded-2xl border border-slate-700/60 bg-slate-900 shadow-2xl shadow-black/70 overflow-hidden">
          <div className="h-px w-full bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent" />
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
                    className="w-2 h-2 rounded-full flex-shrink-0"
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

// ─── Period Selector ──────────────────────────────────────────────────────────
const PERIODS = [
  { label: "1h", value: 1 },
  { label: "6h", value: 6 },
  { label: "24h", value: 24 },
  { label: "7d", value: 168 },
  { label: "All", value: 0 },
];
function PeriodSelector({ value, onChange }: { value: number; onChange: (v: number) => void }) {
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

// ─── Stat Card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, icon, accent = "text-white" }: {
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

// ─── Anomaly Feed ─────────────────────────────────────────────────────────────
function AnomalyFeed({ anomalies, deviceColorMap }: {
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
              <AlertTriangle size={13} className="flex-shrink-0 mt-0.5" style={{ color: sevColor }} />
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

// ─── Train status types ───────────────────────────────────────────────────────
type TrainPhase =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "polling"; taskId: string; elapsed: number }
  | { kind: "success"; text: string }
  | { kind: "error"; text: string };

// ─── Model Panel ─────────────────────────────────────────────────────────────
function ModelPanel({ onTrained }: { onTrained: () => void }) {
  const [modelInfo, setModelInfo]   = useState<ModelInfo | null>(null);
  const [trainHours, setTrainHours] = useState("1");
  const [trainNote, setTrainNote]   = useState("");
  const [phase, setPhase]           = useState<TrainPhase>({ kind: "idle" });
  const [deleting, setDeleting]     = useState(false);
  const [expanded, setExpanded]     = useState(false);
  const pollRef                     = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchModelInfo = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/model-info`);
      setModelInfo(await res.json());
    } catch {}
  }, []);

  useEffect(() => { fetchModelInfo(); }, [fetchModelInfo]);
  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const startPolling = useCallback((taskId: string, prevPoints: number) => {
    let elapsed = 0;
    const INTERVAL = 2000;  // poll every 2s
    const TIMEOUT  = 120000;

    const stop = () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    };

    pollRef.current = setInterval(async () => {
      elapsed += INTERVAL;
      setPhase({ kind: "polling", taskId, elapsed });

      // ── 1. Check Celery task result via /task-status ──────────────────────
      try {
        const tr = await fetch(`${API_BASE}/task-status/${taskId}`);
        if (tr.ok) {
          const ts = await tr.json();
          // state: PENDING | STARTED | SUCCESS | FAILURE | RETRY | REVOKED
          if (ts.state === "SUCCESS") {
            const r = ts.result ?? {};
            if (r.status === "error") {
              // Celery finished but returned a domain error (e.g. not enough data)
              stop();
              setPhase({ kind: "error", text: r.message ?? "Training failed" });
              return;
            }
            // Real success — refresh model-info
            stop();
            await fetchModelInfo();
            const infoRes = await fetch(`${API_BASE}/model-info`);
            const info: ModelInfo = infoRes.ok ? await infoRes.json() : { status: "no_model" };
            setModelInfo(info);
            const pts = info.status === "ok" ? info.model!.points_count : prevPoints;
            setPhase({ kind: "success", text: `Model trained on ${pts} points` });
            onTrained();
            return;
          }
          if (ts.state === "FAILURE") {
            stop();
            const msg = typeof ts.result === "string" ? ts.result : JSON.stringify(ts.result);
            setPhase({ kind: "error", text: `Worker error: ${msg}` });
            return;
          }
          // PENDING / STARTED / RETRY — keep polling
        }
      } catch {
        // /task-status not available yet — fall through to model-info fallback
      }

      // ── 2. Fallback: if task-status endpoint missing, detect via model-info ─
      try {
        const mr = await fetch(`${API_BASE}/model-info`);
        if (mr.ok) {
          const info: ModelInfo = await mr.json();
          if (info.status === "ok" && (info.model?.points_count ?? 0) !== prevPoints) {
            stop();
            setModelInfo(info);
            setPhase({ kind: "success", text: `Model trained on ${info.model!.points_count} points` });
            onTrained();
            return;
          }
        }
      } catch {}

      if (elapsed >= TIMEOUT) {
        stop();
        setPhase({ kind: "error", text: "Training timed out. Check Celery worker logs." });
      }
    }, INTERVAL);
  }, [fetchModelInfo, onTrained]);

  const handleTrain = async () => {
    if (pollRef.current) return;
    const prevPoints = modelInfo?.model?.points_count ?? 0;
    setPhase({ kind: "submitting" });
    try {
      const params = new URLSearchParams({ hours: trainHours, note: trainNote });
      const res = await fetch(`${API_BASE}/train?${params}`, { method: "POST" });
      const d = await res.json();

      if (d.status === "accepted") {
        setPhase({ kind: "polling", taskId: d.task_id ?? "?", elapsed: 0 });
        startPolling(d.task_id ?? "?", prevPoints);
      } else if (d.status === "ok" || d.status === "success") {
        setPhase({ kind: "success", text: d.message ?? "Model trained successfully" });
        await fetchModelInfo();
        onTrained();
      } else {
        setPhase({ kind: "error", text: d.message ?? "Unknown error from server" });
      }
    } catch (e: any) {
      setPhase({ kind: "error", text: `Network error: ${e.message}` });
    }
  };

  const handleDelete = async () => {
    if (!confirm("Reset model and return to auto-mode?")) return;
    setDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/model`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchModelInfo();
      setPhase({ kind: "success", text: "Model deleted. Switched to auto-mode." });
      onTrained();
    } catch (e: any) {
      setPhase({ kind: "error", text: `Failed to delete: ${e.message}` });
    } finally { setDeleting(false); }
  };

  const isTraining = phase.kind === "submitting" || phase.kind === "polling";
  const hasModel   = modelInfo?.status === "ok";

  function StatusBanner() {
    if (phase.kind === "idle") return null;

    if (phase.kind === "submitting") return (
      <div className="flex items-center gap-2 text-xs rounded-lg px-3 py-2.5 bg-slate-800/60 border border-slate-700/40 font-mono text-slate-300">
        <div className="w-3 h-3 border border-slate-500 border-t-cyan-400 rounded-full animate-spin flex-shrink-0" />
        Submitting task to Celery…
      </div>
    );

    if (phase.kind === "polling") {
      const secs = Math.round(phase.elapsed / 1000);
      return (
        <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-3 py-2.5 space-y-1.5">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 border border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin flex-shrink-0" />
            <span className="text-xs text-cyan-300 font-medium">Training in background…</span>
            <span className="ml-auto text-[10px] text-slate-500 font-mono">{secs}s</span>
          </div>
          <p className="text-[10px] text-slate-500 font-mono leading-relaxed">
            task_id: <span className="text-slate-400">{phase.taskId.slice(0, 18)}…</span>
          </p>
          <div className="h-0.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-cyan-500/60 rounded-full transition-all duration-1000"
              style={{ width: `${Math.min((phase.elapsed / 120000) * 100, 95)}%` }}
            />
          </div>
        </div>
      );
    }

    if (phase.kind === "success") return (
      <div className="flex items-center gap-2 text-xs rounded-lg px-3 py-2.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono">
        <span className="flex-shrink-0">✓</span>
        <span className="flex-1">{phase.text}</span>
        <button onClick={() => setPhase({ kind: "idle" })} className="ml-auto text-emerald-600 hover:text-emerald-400 transition-colors">
          <X size={11} />
        </button>
      </div>
    );

    if (phase.kind === "error") return (
      <div className="rounded-lg px-3 py-2.5 bg-red-500/10 border border-red-500/20 space-y-1">
        <div className="flex items-center gap-2">
          <AlertTriangle size={12} className="text-red-400 flex-shrink-0" />
          <span className="text-xs text-red-400 font-medium flex-1">Training failed</span>
          <button onClick={() => setPhase({ kind: "idle" })} className="text-red-700 hover:text-red-400 transition-colors">
            <X size={11} />
          </button>
        </div>
        <p className="text-[10px] text-red-400/70 font-mono">{phase.text}</p>
      </div>
    );

    return null;
  }

  return (
    <div className={`rounded-2xl border transition-all ${
      isTraining ? "border-cyan-500/40 bg-cyan-500/5"
      : hasModel  ? "border-cyan-500/25 bg-cyan-500/5"
                  : "border-amber-500/25 bg-amber-500/5"
    }`}>
      <button onClick={() => setExpanded((e) => !e)} className="w-full flex items-center gap-3 p-4 text-left">
        <div className={`p-1.5 rounded-lg relative ${
          isTraining || hasModel ? "bg-cyan-500/15 text-cyan-400" : "bg-amber-500/15 text-amber-400"
        }`}>
          <BrainCircuit size={15} />
          {isTraining && <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white">
            {isTraining ? "Training…" : hasModel ? "Model active" : "Auto-mode"}
          </p>
          <p className="text-xs text-slate-400 truncate">
            {isTraining
              ? "Celery worker is processing the task"
              : hasModel
              ? `Trained on ${modelInfo!.model!.points_count} pts · ${new Date(modelInfo!.model!.trained_at).toLocaleDateString("ru-RU")}`
              : "No manual model. Train on a clean period."}
          </p>
        </div>
        <ChevronDown size={14} className={`text-slate-500 transition-transform flex-shrink-0 ${expanded ? "rotate-180" : ""}`} />
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-700/30 pt-3">
          {hasModel && modelInfo?.model && (
            <div className="text-[11px] text-slate-400 font-mono space-y-0.5 bg-slate-900/40 rounded-lg p-3">
              <p>Trained: {new Date(modelInfo.model.trained_at).toLocaleString("ru-RU")}</p>
              <p>Period: {new Date(modelInfo.model.period_from).toLocaleString("ru-RU")} → {new Date(modelInfo.model.period_to).toLocaleString("ru-RU")}</p>
              {modelInfo.model.note && <p>Note: {modelInfo.model.note}</p>}
            </div>
          )}

          <div className="space-y-2">
            <p className="text-xs text-slate-400 font-medium">Train on a clean (normal load) period:</p>
            <div className="flex gap-2">
              <div className="flex-shrink-0">
                <label className="text-[10px] text-slate-500 uppercase tracking-widest block mb-1">Hours</label>
                <input type="number" value={trainHours} min="0.1" step="0.5" disabled={isTraining}
                  onChange={(e) => setTrainHours(e.target.value)}
                  className="w-20 bg-slate-800/70 border border-slate-700/70 text-white rounded-lg px-2 py-1.5 text-xs font-mono focus:outline-none focus:border-cyan-500/50 disabled:opacity-40" />
              </div>
              <div className="flex-1">
                <label className="text-[10px] text-slate-500 uppercase tracking-widest block mb-1">Note</label>
                <input type="text" value={trainNote} placeholder="e.g.: normal load" disabled={isTraining}
                  onChange={(e) => setTrainNote(e.target.value)}
                  className="w-full bg-slate-800/70 border border-slate-700/70 text-white placeholder-slate-600 rounded-lg px-2 py-1.5 text-xs font-mono focus:outline-none focus:border-cyan-500/50 disabled:opacity-40" />
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={handleTrain} disabled={isTraining}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-xs transition-all disabled:opacity-50 disabled:cursor-not-allowed">
                {isTraining
                  ? <div className="w-3 h-3 border border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
                  : <Zap size={12} />}
                {phase.kind === "submitting" ? "Submitting…" : isTraining ? "Training…" : "Train model"}
              </button>
              {hasModel && !isTraining && (
                <button onClick={handleDelete} disabled={deleting}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 text-xs transition-all disabled:opacity-50">
                  <Trash2 size={12} />
                  {deleting ? "Deleting…" : "Delete model"}
                </button>
              )}
            </div>
          </div>

          <StatusBanner />
        </div>
      )}
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function Dashboard() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);
  const [hours, setHours] = useState(1);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);
  // Track whether initial URL read happened
  const initializedRef = useRef(false);

  // Stable color map — order determined by devices array from /devices
  const deviceColorMap: Record<string, string> = {};
  devices.forEach((d, i) => { deviceColorMap[d.name] = getDeviceColor(i); });

  // ─── Selected devices → URL sync ─────────────────────────────────────────
  const handleSetSelected = useCallback((next: string[]) => {
    setSelectedDevices(next);
    setUrlDevices(next);
  }, []);

  // ─── Fetch devices list ───────────────────────────────────────────────────
  const fetchDevices = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/devices`);
      const list: Device[] = await res.json();
      setDevices(list);

      if (!initializedRef.current) {
        initializedRef.current = true;
        const fromUrl = getUrlDevices();
        // Filter URL devices to only those that exist
        const valid = fromUrl.filter((n) => list.some((d) => d.name === n));
        if (valid.length > 0) {
          // URL had specific devices — use them and write back cleaned list
          setSelectedDevices(valid);
          setUrlDevices(valid);
        } else {
          // No URL param or none matched — select all, no URL param needed
          const all = list.map((d) => d.name);
          setSelectedDevices(all);
          setUrlDevices([]);
        }
      } else {
        // Subsequent refreshes: keep selection, just remove stale entries
        setSelectedDevices((prev) => {
          const kept = prev.filter((n) => list.some((d) => d.name === n));
          return kept.length > 0 ? kept : list.map((d) => d.name);
        });
      }
    } catch {}
  }, []);

  // ─── Fetch dashboard data (only from /api/dashboard) ─────────────────────
  const fetchDashboard = useCallback(async () => {
    try {
      const params = new URLSearchParams({ hours: String(hours) });
      const res = await fetch(`${API_BASE}/api/dashboard?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d: DashboardData = await res.json();
      setData(d);
    } catch {}
  }, [hours]);

  const fetchAll = useCallback(async () => {
    await fetchDashboard();
    setLastFetched(new Date());
    setLoading(false);
  }, [fetchDashboard]);

  useEffect(() => { fetchDevices(); }, [fetchDevices]);

  useEffect(() => {
    setLoading(true);
    fetchAll();
    const id = setInterval(fetchAll, 20000);
    return () => clearInterval(id);
  }, [fetchAll]);

  // ─── Derived data ─────────────────────────────────────────────────────────
  const filteredMetrics = (data?.metrics ?? []).filter((m) =>
    selectedDevices.includes(m.device)
  );

  const timelineMap: Record<string, Record<string, { cpu: number; ram: number }>> = {};
  filteredMetrics.forEach((m) => {
    const t = formatTime(m.timestamp);
    if (!timelineMap[t]) timelineMap[t] = {};
    timelineMap[t][m.device] = { cpu: m.cpu, ram: m.ram };
  });

  const chartData = Object.entries(timelineMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([time, devs]) => ({
      time,
      ...Object.fromEntries(
        Object.entries(devs).flatMap(([dev, vals]) => [
          [`${dev}__cpu`, vals.cpu],
          [`${dev}__ram`, vals.ram],
        ])
      ),
    }));

  // Anomalies come from /api/dashboard — already have correct device field
  // Filter to selected devices only
  const filteredAnomalies = (data?.anomalies ?? []).filter((a) =>
    selectedDevices.includes(a.device)
  );

  const latestPerDevice: Record<string, MetricPoint> = {};
  filteredMetrics.forEach((m) => {
    if (!latestPerDevice[m.device] || m.timestamp > latestPerDevice[m.device].timestamp)
      latestPerDevice[m.device] = m;
  });

  const avgCpu = Object.values(latestPerDevice).length > 0
    ? Object.values(latestPerDevice).reduce((s, m) => s + m.cpu, 0) / Object.values(latestPerDevice).length
    : null;

  const avgRam = Object.values(latestPerDevice).length > 0
    ? Object.values(latestPerDevice).reduce((s, m) => s + m.ram, 0) / Object.values(latestPerDevice).length
    : null;

  const periodLabel = hours === 0 ? "all time" : hours < 24 ? `${hours}h` : `${hours / 24}d`;

  function AnomalyDots({ field }: { field: "cpu" | "ram" }) {
    return (
      <>
        {filteredAnomalies.map((a) => (
          <ReferenceDot
            key={`${a.id}-${field}`}
            x={formatTime(a.timestamp)}
            y={field === "cpu" ? a.cpu : a.ram}
            r={5}
            fill="#f87171"
            stroke="#450a0a"
            strokeWidth={1.5}
          />
        ))}
      </>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans">
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `linear-gradient(rgba(148,163,184,0.025) 1px,transparent 1px),linear-gradient(90deg,rgba(148,163,184,0.025) 1px,transparent 1px)`,
          backgroundSize: "48px 48px",
        }}
      />
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[700px] h-px bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-8">

        {/* ── Top bar ── */}
        <header className="flex flex-wrap items-center gap-3 mb-8">
          <div className="flex items-center gap-2 mr-2">
            <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400">
              <Activity size={17} />
            </div>
            <h1 className="text-base font-bold tracking-tight text-white">Monitoring</h1>
          </div>

          <DeviceSelector
            devices={devices}
            selected={selectedDevices}
            onChange={handleSetSelected}
            deviceColorMap={deviceColorMap}
          />

          <PeriodSelector value={hours} onChange={setHours} />

          <div className="flex-1" />

          {lastFetched && (
            <span className="hidden md:flex items-center gap-1.5 text-xs text-slate-500">
              <Clock size={12} />
              {lastFetched.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={() => { fetchDevices(); fetchAll(); }}
            className="p-2 rounded-xl border border-slate-700/60 bg-slate-900/60 text-slate-400 hover:text-white hover:border-slate-600 transition-all"
          >
            <RefreshCw size={14} />
          </button>
        </header>

        {/* ── Stats ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
          <StatCard
            label="Avg CPU" value={avgCpu != null ? `${avgCpu.toFixed(1)}%` : "—"}
            icon={<Cpu size={15} />}
            accent={avgCpu != null && avgCpu > 80 ? "text-red-400" : avgCpu != null && avgCpu > 60 ? "text-amber-400" : "text-white"}
          />
          <StatCard
            label="Avg RAM" value={avgRam != null ? `${avgRam.toFixed(1)}%` : "—"}
            icon={<MemoryStick size={15} />}
            accent={avgRam != null && avgRam > 85 ? "text-red-400" : avgRam != null && avgRam > 70 ? "text-amber-400" : "text-white"}
          />
          <StatCard
            label="Anomalies" value={filteredAnomalies.length}
            sub={`in ${periodLabel}`}
            icon={<AlertTriangle size={15} />}
            accent={filteredAnomalies.length > 0 ? "text-amber-400" : "text-white"}
          />
          <StatCard
            label="Devices" value={`${selectedDevices.length} / ${devices.length}`}
            sub="selected / total"
            icon={<Server size={15} />}
          />
        </div>

        {/* ── Main grid ── */}
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_330px] gap-5">

          {/* Left: charts */}
          <div className="space-y-5">

            {/* CPU */}
            <div className="rounded-2xl border border-slate-700/40 bg-slate-900/50 p-5">
              <div className="flex items-center gap-2 mb-4">
                <Cpu size={14} className="text-cyan-400" />
                <h2 className="text-sm font-semibold text-white">CPU usage</h2>
                {filteredAnomalies.length > 0 && (
                  <span className="ml-2 flex items-center gap-1 text-[10px] text-red-400 bg-red-500/10 border border-red-500/20 rounded-full px-2 py-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" />
                    {filteredAnomalies.length} anomalies marked
                  </span>
                )}
                <span className="text-xs text-slate-500 ml-auto">%</span>
              </div>
              {loading ? (
                <div className="flex items-center justify-center h-52">
                  <div className="w-6 h-6 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
                </div>
              ) : chartData.length === 0 ? (
                <div className="flex items-center justify-center h-52 text-slate-600 text-sm">No data</div>
              ) : (
                <ResponsiveContainer width="100%" height={230}>
                  <LineChart data={chartData} syncId="sync-charts" margin={{ top: 4, right: 4, bottom: 0, left: -22 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.05)" />
                    <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} />
                    <Tooltip content={<ChartTooltip anomalies={filteredAnomalies} />} />
                    <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} formatter={(v) => String(v).replace("__cpu", "")} />
                    {selectedDevices.map((dev) => (
                      <Line key={`${dev}__cpu`} type="monotone" dataKey={`${dev}__cpu`} name={`${dev}__cpu`}
                        stroke={deviceColorMap[dev]} strokeWidth={1.5} dot={false} activeDot={{ r: 3 }} connectNulls />
                    ))}
                    <AnomalyDots field="cpu" />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* RAM */}
            <div className="rounded-2xl border border-slate-700/40 bg-slate-900/50 p-5">
              <div className="flex items-center gap-2 mb-4">
                <MemoryStick size={14} className="text-violet-400" />
                <h2 className="text-sm font-semibold text-white">RAM usage</h2>
                <span className="text-xs text-slate-500 ml-auto">%</span>
              </div>
              {loading ? (
                <div className="flex items-center justify-center h-52">
                  <div className="w-6 h-6 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
                </div>
              ) : chartData.length === 0 ? (
                <div className="flex items-center justify-center h-52 text-slate-600 text-sm">No data</div>
              ) : (
                <ResponsiveContainer width="100%" height={230}>
                  <LineChart data={chartData} syncId="sync-charts" margin={{ top: 4, right: 4, bottom: 0, left: -22 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.05)" />
                    <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} />
                    <Tooltip content={<ChartTooltip anomalies={filteredAnomalies} />} />
                    <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} formatter={(v) => String(v).replace("__ram", "")} />
                    {selectedDevices.map((dev) => (
                      <Line key={`${dev}__ram`} type="monotone" dataKey={`${dev}__ram`} name={`${dev}__ram`}
                        stroke={deviceColorMap[dev]} strokeWidth={1.5} dot={false} activeDot={{ r: 3 }} connectNulls />
                    ))}
                    <AnomalyDots field="ram" />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Per-device mini cards */}
            {Object.keys(latestPerDevice).length > 1 && (
              <div className="rounded-2xl border border-slate-700/40 bg-slate-900/50 p-5">
                <h2 className="text-sm font-semibold text-white mb-4">Latest per device</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {Object.entries(latestPerDevice).map(([name, m]) => {
                    const color = deviceColorMap[name];
                    return (
                      <div key={name} className="rounded-xl border bg-slate-900/60 p-3" style={{ borderColor: `${color}28` }}>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: color }} />
                          <span className="text-xs font-mono font-semibold" style={{ color }}>{name}</span>
                          <span className="text-[10px] text-slate-500 ml-auto font-mono">{formatTime(m.timestamp)}</span>
                        </div>
                        {(["cpu", "ram"] as const).map((field) => (
                          <div key={field} className="mb-1 last:mb-0">
                            <div className="flex justify-between mb-0.5">
                              <span className="text-[10px] text-slate-500 uppercase tracking-wider">{field}</span>
                              <span className="text-[10px] font-mono font-bold" style={{ color }}>{m[field].toFixed(1)}%</span>
                            </div>
                            <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all"
                                style={{
                                  width: `${m[field]}%`,
                                  background: m[field] > (field === "cpu" ? 80 : 85) ? "#f87171"
                                    : m[field] > (field === "cpu" ? 60 : 70) ? "#fb923c" : color,
                                }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Right sidebar */}
          <div className="space-y-4 xl:self-start xl:sticky xl:top-6">
            <ModelPanel onTrained={fetchAll} />

            <div className="rounded-2xl border border-slate-700/40 bg-slate-900/50 p-5">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle size={14} className="text-amber-400" />
                <h2 className="text-sm font-semibold text-white">Anomaly log</h2>
                {filteredAnomalies.length > 0 && (
                  <span className="ml-auto bg-amber-500/15 text-amber-400 text-xs font-semibold px-2 py-0.5 rounded-full">
                    {filteredAnomalies.length}
                  </span>
                )}
              </div>
              <AnomalyFeed anomalies={filteredAnomalies} deviceColorMap={deviceColorMap} />
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .custom-scroll::-webkit-scrollbar { width: 4px; }
        .custom-scroll::-webkit-scrollbar-track { background: transparent; }
        .custom-scroll::-webkit-scrollbar-thumb { background: #334155; border-radius: 2px; }
        .custom-scroll::-webkit-scrollbar-thumb:hover { background: #475569; }
      `}</style>
    </div>
  );
}