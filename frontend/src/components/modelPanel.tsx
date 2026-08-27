import { useCallback, useEffect, useRef, useState } from "react";
import { type TaskStatus, type ModelInfo, type TrainPhase, type TrainResponse, type TaskResultPayload } from "../types/Types";
import { apiFetch } from "../api";
import { AlertTriangle, BrainCircuit, ChevronDown, Trash2, X, Zap } from "lucide-react";

export function ModelPanel({ onTrained }: { onTrained: () => void }) {
    const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
    const [trainHours, setTrainHours] = useState("1");
    const [trainNote, setTrainNote] = useState("");
    const [phase, setPhase] = useState<TrainPhase>({ kind: "idle" });
    const [deleting, setDeleting] = useState(false);
    const [expanded, setExpanded] = useState(false);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const fetchModelInfo = useCallback(async () => {
        try {
            const res = await apiFetch<ModelInfo>("/api/v1/model-info");
            setModelInfo(res);
        } catch { }
    }, []);

    useEffect(() => { fetchModelInfo(); }, [fetchModelInfo]);
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
                    await fetchModelInfo();

                    const infoRes = await apiFetch<ModelInfo>("/model-info");
                    const info: ModelInfo = infoRes ?? { status: "no_model" };

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

            } catch {
                // /task-status not available yet — fall through to model-info fallback
            }

            // ── 2. Fallback: if task-status endpoint missing, detect via model-info ─
            try {
                const info = await apiFetch<ModelInfo>("/model-info");
                if (info.status === "ok" && (info.model?.points_count ?? 0) !== prevPoints) {
                    stop();
                    setModelInfo(info);
                    setPhase({ kind: "success", text: `Model trained on ${info.model!.points_count} points` });
                    onTrained();
                    return;
                }

            } catch { }

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
            const d = await apiFetch<TrainResponse>(`/train?${params}`, {
                method: "POST",
            });

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
            if (e.response?.status === 403) {
                setPhase({ kind: "error", text: "Training the model requires admin privileges" });
            } else {
                const d = e.response?.data ?? {};
                const detail = d.detail;
                const message =
                    typeof detail === "string"
                        ? detail
                        : detail?.message ?? e.message ?? "Unknown error";
                setPhase({ kind: "error", text: `Network error: ${message}` });
            }

        }
    };

    const handleDelete = async () => {
        if (!confirm("Reset model and return to auto-mode?")) return;
        setDeleting(true);
        try {
            await apiFetch("/api/v1/model", {
                method: "DELETE",
            });
            await fetchModelInfo();
            setPhase({ kind: "success", text: "Model deleted. Switched to auto-mode." });
            onTrained();
        } catch (e: any) {
            if (e.response?.status === 403) {
                setPhase({ kind: "error", text: "Deleting the model requires admin privileges" });
            } else {
                const d = e.response?.data ?? {};
                const detail = d.detail;
                const message =
                    typeof detail === "string"
                        ? detail
                        : detail?.message ?? e.message ?? "Unknown error";
                setPhase({ kind: "error", text: `Failed to delete: ${message}` });
            }
        } finally { setDeleting(false); }
    };

    const isTraining = phase.kind === "submitting" || phase.kind === "polling";
    const hasModel = modelInfo?.status === "ok";

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
                                ? `Trained on ${modelInfo!.model!.points_count} pts · ${new Date(modelInfo!.model!.trained_at).toLocaleDateString("ru-RU")}`
                                : "No manual model. Train on a clean period."}
                    </p>
                </div>
                <ChevronDown size={14} className={`text-slate-500 transition-transform shrink-0 ${expanded ? "rotate-180" : ""}`} />
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
                            <div className="shrink-0">
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