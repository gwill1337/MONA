import { useState } from "react";
import { apiFetch } from "../../api";
import {
    X,
} from "lucide-react";
interface AddDeviceModalProps {
    onClose: () => void;
    onAdded: () => void;
}

const DEVICE_NAME_RE = /^[a-zA-Z0-9_-]{1,15}$/;

function isValidIp(ip: string): boolean {
    const v = ip.trim();

    const v4parts = v.split(".");
    if (v4parts.length === 4) {
        return v4parts.every(
            (p) => /^\d{1,3}$/.test(p) && Number(p) <= 255 && p === String(Number(p))
        );
    }

    // Lightweight IPv6 sanity check — the backend does the authoritative
    // check with Python's `ipaddress` module, this is just for fast feedback.
    return /^[0-9a-fA-F:]+$/.test(v) && v.includes(":");
}

interface FieldErrors {
    ip?: string;
    name?: string;
}

export function AddDeviceModal({ onClose, onAdded }: AddDeviceModalProps) {
    const [form, setForm] = useState({ ip: "", name: "", is_active: true });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

    const validate = (): boolean => {
        const errs: FieldErrors = {};
        const name = form.name.trim();
        const ip = form.ip.trim();

        if (!name) {
            errs.name = "Name is required.";
        } else if (!DEVICE_NAME_RE.test(name)) {
            errs.name = "Only letters, digits, '_' and '-' are allowed (max 15 chars).";
        }

        if (!ip) {
            errs.ip = "IP address is required.";
        } else if (!isValidIp(ip)) {
            errs.ip = "Enter a valid IPv4 or IPv6 address.";
        }

        setFieldErrors(errs);
        return Object.keys(errs).length === 0;
    };

    const handleSubmit = async () => {
        if (!validate()) return;

        setLoading(true);
        setError("");
        try {
            await apiFetch("/devices", {
                method: "POST",
                data: form,
            });
            onAdded();
            onClose();
        } catch (e: any) {
            const d = e.response?.data ?? {};

            if (Array.isArray(d.detail)) {
                const errs: FieldErrors = {};
                for (const item of d.detail) {
                    const field = item.loc?.[item.loc.length - 1];
                    if (field === "name" || field === "ip") {
                        errs[field as "name" | "ip"] = item.msg;
                    }
                }
                if (Object.keys(errs).length) {
                    setFieldErrors(errs);
                    return;
                }
            }
            setError(typeof d.detail === "string" ? d.detail : e.message ?? "Unknown error");
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
                <div className="h-px w-full bg-linear-to-r from-transparent via-cyan-500 to-transparent" />

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
                                onChange={(e) => {
                                    setForm((f) => ({ ...f, ip: e.target.value }));
                                    if (fieldErrors.ip) setFieldErrors((fe) => ({ ...fe, ip: undefined }));
                                }}
                                className={`w-full bg-slate-800/60 border text-white placeholder-slate-500 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-1 transition-all font-mono ${fieldErrors.ip
                                    ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/30"
                                    : "border-slate-700/70 focus:border-cyan-500/70 focus:ring-cyan-500/30"
                                    }`}
                            />
                            {fieldErrors.ip && (
                                <p className="mt-1.5 text-xs text-red-400">{fieldErrors.ip}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-widest">
                                Device name
                            </label>
                            <input
                                type="text"
                                placeholder="pc-office-01"
                                value={form.name}
                                onChange={(e) => {
                                    setForm((f) => ({ ...f, name: e.target.value }));
                                    if (fieldErrors.name) setFieldErrors((fe) => ({ ...fe, name: undefined }));
                                }}
                                className={`w-full bg-slate-800/60 border text-white placeholder-slate-500 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-1 transition-all font-mono ${fieldErrors.name
                                    ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/30"
                                    : "border-slate-700/70 focus:border-cyan-500/70 focus:ring-cyan-500/30"
                                    }`}
                            />
                            {fieldErrors.name && (
                                <p className="mt-1.5 text-xs text-red-400">{fieldErrors.name}</p>
                            )}
                        </div>
                        <div className="flex items-center justify-between py-1">
                            <span className="text-xs font-medium text-slate-400 uppercase tracking-widest">Active</span>
                            <button
                                type="button"
                                onClick={() => setForm((f) => ({ ...f, is_active: !f.is_active }))}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer focus:outline-none ${form.is_active ? "bg-cyan-500" : "bg-slate-700"
                                    }`}
                            >
                                <span
                                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform ${form.is_active ? "translate-x-6" : "translate-x-1"
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
                            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-700 text-slate-400 text-sm hover:text-white hover:border-slate-600 transition-all cursor-pointer"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSubmit}
                            disabled={loading}
                            className="flex-1 px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20 cursor-pointer"
                        >
                            {loading ? "Adding…" : "Add device"}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}