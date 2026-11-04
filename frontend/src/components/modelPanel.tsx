import { useCallback, useEffect, useRef, useState } from "react";
import {
    type TaskStatus, type TrainPhase, type TrainResponse, type TaskResultPayload, type ModelInfoResponse,
    type ModelListResponse, type ModelItem,
} from "../types/Types";
import { apiFetch } from "../api";
import { parseTs } from "../helpers/helpers";
import { AlertTriangle, BrainCircuit, ChevronDown, RotateCcw, Trash2, X, Zap } from "lucide-react";

// Backend timestamps may come without a timezone — parseTs treats them as UTC
const fmtDateTime = (iso: string) => new Date(parseTs(iso)).toLocaleString("ru-RU");
const fmtDate = (iso: string) => new Date(parseTs(iso)).toLocaleDateString("ru-RU");

type LastAction = "train" | "activate" | "delete";

export function ModelPanel({ onTrained }: { onTrained: () => void }) {
    const [modelInfo, setModelInfo] = useState<ModelInfoResponse | null>(null);
    const [models, setModels] = useState<ModelItem[]>([]);
    const [trainHours, setTrainHours] = useState("1");
    const [trainNote, setTrainNote] = useState("");
    const [phase, setPhase] = useState<TrainPhase>({ kind: "idle" });
    const [lastAction, setLastAction] = useState<LastAction>("train");
    const [busy, setBusy] = useState(false);
    const [expanded, setExpanded] = useState(false);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const fetchModelInfo = useCallback(async () => {
        try {
            // apiFetch already prepends API + API_VERSION
            const res = await apiFetch<ModelInfoResponse>("/model-info");
            setModelInfo(res);
        } catch { }
    }, []);

    const fetchModels = useCallback(async () => {
        try {
            const res = await apiFetch<ModelListResponse>("/models");
            setModels(res.items);
        } catch { }
    }, []);

    useEffect(() => { fetchModelInfo(); fetchModels(); }, [fetchModelInfo, fetchModels]);
    useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

    const startPolling = useCallback((taskId: string, prevPoints: number) => {
        let elapsed = 0;
        const INTERVAL = 2000;  // poll every 2s
        const TIMEOUT = 120000;

        const stop = () => {
            if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        };

        pollRef.current = setInterval(async () => {
            elapsed += INTERVAL;
            setPhase({ kind: "polling", taskId, elapsed });

            // ── 1. Check Celery task result via /task-status ──────────────────────
            try {
                const ts = await apiFetch<TaskStatus>(`/task-status/${taskId}`);
                // state: PENDING | STARTED | SUCCESS | FAILURE | RETRY | REVOKED
                if (ts.state === "SUCCESS") {
                    const res = typeof ts.result === "object" && ts.result !== null
                        ? (ts.result as TaskResultPayload)
                        : {};

                    if (res.status === "error") {
                        stop();
                        setPhase({
                            kind: "error",
                            text: res.message ?? "Training failed"
                        });
                        return;
                    }

                    stop();

                    const infoRes = await apiFetch<ModelInfoResponse>("/model-info");
                    const info: ModelInfoResponse = infoRes ?? { status: "no_model", message: "No model" };

                    setModelInfo(info);
                    await fetchModels();

                    const pts = info.status === "ok" ? info.model.points_count : prevPoints;
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

            } catch {
                // /task-status not available yet — fall through to model-info fallback
            }

            // ── 2. Fallback: if task-status endpoint missing, detect via model-info ─
            try {
                const info = await apiFetch<ModelInfoResponse>("/model-info");
                if (info.status === "ok" && (info.model?.points_count ?? 0) !== prevPoints) {
                    stop();
                    setModelInfo(info);
                    await fetchModels();
                    setPhase({ kind: "success", text: `Model trained on ${info.model.points_count} points` });
                    onTrained();
                    return;
                }

            } catch { }

            if (elapsed >= TIMEOUT) {
                stop();
                setPhase({ kind: "error", text: "Training timed out. Check Celery worker logs." });
            }
        }, INTERVAL);
    }, [onTrained, fetchModels]);

    const handleTrain = async () => {
        if (pollRef.current) return;
        setLastAction("train");
        const prevPoints = modelInfo?.status === "ok" ? modelInfo.model.points_count : 0;
        setPhase({ kind: "submitting" });
        try {
            const params = new URLSearchParams({ hours: trainHours, note: trainNote });
            const d = await apiFetch<TrainResponse>(`/train?${params}`, {
                method: "POST",
            });

            if (d.status === "accepted") {
                setPhase({ kind: "polling", taskId: d.task_id ?? "?", elapsed: 0 });
                startPolling(d.task_id ?? "?", prevPoints);
            } else if (d.status === "ok" || d.status === "success") {
                setPhase({ kind: "success", text: d.message ?? "Model trained successfully" });
                await Promise.all([fetchModelInfo(), fetchModels()]);
                onTrained();
            } else {
                setPhase({ kind: "error", text: d.message ?? "Unknown error from server" });
            }
        } catch (e: any) {
            if (e.status === 403) {
                setPhase({ kind: "error", text: "Training the model requires admin privileges" });
            } else {
                setPhase({ kind: "error", text: `error: ${e.message}` });
            }
        }
    };

    // Shared runner for admin actions that change which model is used
    const runModelAction = async (
        action: LastAction,
        request: () => Promise<unknown>,
        successText: string,
        forbiddenText: string,
    ) => {
        setLastAction(action);
        setBusy(true);
        try {
            await request();
            await Promise.all([fetchModelInfo(), fetchModels()]);
            setPhase({ kind: "success", text: successText });
            onTrained();
        } catch (e: any) {
            // apiFetch throws ApiError { message, status }
            if (e.status === 403) {
                setPhase({ kind: "error", text: forbiddenText });
            } else {
                setPhase({ kind: "error", text: e.message ?? "Unknown error" });
            }
        } finally { setBusy(false); }
    };

    const handleActivate = (m: ModelItem) =>
        runModelAction(
            "activate",
            () => apiFetch(`/models/${m.id}/activate`, { method: "POST" }),
            "Model activated.",
            "Switching models requires admin privileges",
        );

    const handleAutoMode = () => {
        if (!confirm("Switch to auto-mode? Saved models will be kept.")) return;
        runModelAction(
            "activate",
            () => apiFetch("/models/deactivate", { method: "POST" }),
            "Switched to auto-mode.",
            "Switching models requires admin privileges",
        );
    };

    const handleDeleteOne = (m: ModelItem) => {
        const warn = m.is_active ? "\nIt is active — the system will switch to auto-mode." : "";
        if (!confirm(`Delete model from ${fmtDateTime(m.trained_at)}?${warn}`)) return;
        runModelAction(
            "delete",
            () => apiFetch(`/models/${m.id}`, { method: "DELETE" }),
            m.is_active ? "Model deleted. Switched to auto-mode." : "Model deleted.",
            "Deleting the model requires admin privileges",
        );
    };

    const isTraining = phase.kind === "submitting" || phase.kind === "polling";
    const hasModel = modelInfo?.status === "ok";
    const locked = isTraining || busy;

    function StatusBanner() {
        if (phase.kind === "idle") return null;

        if (phase.kind === "submitting") return (
            <div className="flex items-center gap-2 text-xs rounded-lg px-3 py-2.5 bg-slate-800/60 border border-slate-700/40 font-mono text-slate-300">
                <div className="w-3 h-3 border border-slate-500 border-t-cyan-400 rounded-full animate-spin shrink-0" />
                Submitting task to Celery…
            </div>
        );

        if (phase.kind === "polling") {
            const secs = Math.round(phase.elapsed / 1000);
            return (
                <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-3 py-2.5 space-y-1.5">
                    <div className="flex items-center gap-2">
                        <div className="w-3 h-3 border border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin shrink-0" />
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
                <span className="shrink-0">✓</span>
                <span className="flex-1">{phase.text}</span>
                <button onClick={() => setPhase({ kind: "idle" })} className="ml-auto text-emerald-600 hover:text-emerald-400 transition-colors">
                    <X size={11} />
                </button>
            </div>
        );

        if (phase.kind === "error") return (
            <div className="rounded-lg px-3 py-2.5 bg-red-500/10 border border-red-500/20 space-y-1">
                <div className="flex items-center gap-2">
                    <AlertTriangle size={12} className="text-red-400 shrink-0" />
                    <span className="text-xs text-red-400 font-medium flex-1">
                        {lastAction === "delete" ? "Delete failed"
                            : lastAction === "activate" ? "Switch failed"
                                : "Training failed"}
                    </span>
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
        <div className={`rounded-2xl border transition-all ${isTraining ? "border-cyan-500/40 bg-cyan-500/5"
            : hasModel ? "border-cyan-500/25 bg-cyan-500/5"
                : "border-amber-500/25 bg-amber-500/5"
            }`}>
            <button onClick={() => setExpanded((e) => !e)} className="w-full flex items-center gap-3 p-4 text-left">
                <div className={`p-1.5 rounded-lg relative ${isTraining || hasModel ? "bg-cyan-500/15 text-cyan-400" : "bg-amber-500/15 text-amber-400"
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
                                ? `Trained on ${modelInfo.model.points_count} pts · ${fmtDate(modelInfo.model.trained_at)}`
                                : models.length > 0
                                    ? `No active model · ${models.length} saved`
                                    : "No manual model. Train on a clean period."}
                    </p>
                </div>
                <ChevronDown size={14} className={`text-slate-500 transition-transform shrink-0 ${expanded ? "rotate-180" : ""}`} />
            </button>

            {expanded && (
                <div className="px-4 pb-4 space-y-3 border-t border-slate-700/30 pt-3">
                    {modelInfo?.status === "ok" && (
                        <div className="text-[11px] text-slate-400 font-mono space-y-0.5 bg-slate-900/40 rounded-lg p-3">
                            <p>Trained: {fmtDateTime(modelInfo.model.trained_at)}</p>
                            <p>
                                Period:{" "}
                                {modelInfo.model.period_from
                                    ? fmtDateTime(modelInfo.model.period_from)
                                    : "—"}
                                {" → "}
                                {modelInfo.model.period_to
                                    ? fmtDateTime(modelInfo.model.period_to)
                                    : "—"}
                            </p>
                            {modelInfo.model.note && <p>Note: {modelInfo.model.note}</p>}
                        </div>
                    )}

                    <div className="space-y-2">
                        <p className="text-xs text-slate-400 font-medium">Train on a clean (normal load) period:</p>
                        <div className="flex gap-2">
                            <div className="shrink-0">
                                <label className="text-[10px] text-slate-500 uppercase tracking-widest block mb-1">Hours</label>
                                <input type="number" value={trainHours} min="0.1" step="0.5" disabled={locked}
                                    onChange={(e) => setTrainHours(e.target.value)}
                                    className="w-20 bg-slate-800/70 border border-slate-700/70 text-white rounded-lg px-2 py-1.5 text-xs font-mono focus:outline-none focus:border-gray-400/50 disabled:opacity-40" />
                            </div>
                            <div className="flex-1">
                                <label className="text-[10px] text-slate-500 uppercase tracking-widest block mb-1">Note</label>
                                <input type="text" value={trainNote} placeholder="e.g.: normal load" disabled={locked}
                                    onChange={(e) => setTrainNote(e.target.value)}
                                    className="w-full bg-slate-800/70 border border-slate-700/70 text-white placeholder-slate-600 rounded-lg px-2 py-1.5 text-xs font-mono focus:outline-none focus:border-gray-400/50 disabled:opacity-40" />
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <button onClick={handleTrain} disabled={locked}
                                className="flex items-center gap-1.5 px-3 py-2 mt-2 rounded-lg bg-white  hover:bg-gray-200 text-slate-950 font-semibold text-xs transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer">
                                {isTraining
                                    ? <div className="w-3 h-3 border border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
                                    : <Zap size={12} />}
                                {phase.kind === "submitting" ? "Submitting…" : isTraining ? "Training…" : "Train model"}
                            </button>
                            {hasModel && !isTraining && (
                                <button onClick={handleAutoMode} disabled={busy}
                                    className="flex items-center gap-1.5 px-3 py-2 mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 text-xs transition-all disabled:opacity-50">
                                    <RotateCcw size={12} />
                                    Auto-mode
                                </button>
                            )}
                        </div>
                    </div>

                    <StatusBanner />

                    {models.length > 0 && (
                        <div className="space-y-1.5">
                            <p className="text-xs text-slate-400 font-medium">Saved models ({models.length}):</p>
                            <div className="space-y-1">
                                {models.map((m) => (
                                    <div key={m.id}
                                        className={`flex items-center gap-2 rounded-lg border px-2.5 py-2 text-[11px] font-mono ${m.is_active
                                            ? "border-cyan-500/40 bg-cyan-500/10 text-slate-200"
                                            : "border-slate-700/40 bg-slate-900/40 text-slate-400"}`}>
                                        <div className="flex-1 min-w-0">
                                            <p className="truncate">{fmtDateTime(m.trained_at)} · {m.points_count} pts</p>
                                            {m.note && <p className="truncate text-slate-500">{m.note}</p>}
                                        </div>
                                        {m.is_active
                                            ? <span className="shrink-0 px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-[10px] uppercase tracking-wider">active</span>
                                            : (
                                                <button onClick={() => handleActivate(m)} disabled={locked}
                                                    className="shrink-0 px-2 py-0.5 rounded border border-slate-600/60 text-slate-300 hover:bg-slate-700/50 transition-all disabled:opacity-40 cursor-pointer">
                                                    Use
                                                </button>
                                            )}
                                        <button onClick={() => handleDeleteOne(m)} disabled={locked}
                                            className="shrink-0 p-1 rounded text-red-400/70 hover:text-red-400 hover:bg-red-500/10 transition-all disabled:opacity-40 cursor-pointer"
                                            title="Delete model">
                                            <Trash2 size={11} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}