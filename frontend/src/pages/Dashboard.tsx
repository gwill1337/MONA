import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceDot, Legend,
} from "recharts";
import {
  Activity, AlertTriangle, ArrowLeft,
  Clock, Cpu, MemoryStick, RefreshCw,
  Server,
} from "lucide-react";
import { formatTime, getDeviceColor, getUrlDevices, setUrlDevices } from "../helpers/helpers";
import type { DashboardData, MetricPoint } from "../types/Types";
import type { Device } from "./DeviceAdmin";
import { DeviceSelector } from "../components/deviceSelector";
import { PeriodSelector } from "../components/periodSelector";
import { StatCard } from "../components/statCard";
import { ChartTooltip } from "../helpers/toolTip";
import { ModelPanel } from "../components/modelPanel";
import { AnomalyFeed } from "../components/anomalyFeed";

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function Dashboard() {
  const navigate = useNavigate();
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
      const list: Device[] = await apiFetch("/devices");
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
    } catch { }
  }, []);

  // ─── Fetch dashboard data (only from /api/dashboard) ─────────────────────
  const fetchDashboard = useCallback(async () => {
    try {
      const params = new URLSearchParams({ hours: String(hours) });
      const d = await apiFetch<DashboardData>(`/dashboard?${params}`);
      setData(d);
    } catch { }
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
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-175 h-px bg-linear-to-r from-transparent via-cyan-500/30 to-transparent" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-8">

        {/* ── Top bar ── */}
        <header className="flex flex-wrap items-center gap-3 mb-8">
          <button
            onClick={() => navigate("/")}
            title="Back to device registry"
            className="p-2 rounded-xl border border-slate-700/60 bg-slate-900/60 text-slate-400 hover:text-white hover:border-slate-600 transition-all"
          >
            <ArrowLeft size={16} />
          </button>

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
                          <span className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
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