import { useState } from "react";
import { apiFetch } from "../../api";
import {
    X,
} from "lucide-react";
interface AddUserModalProps {
    onClose: () => void;
    fetchUsers: () => void;
}

const USER_NAME_RE = /^[a-zA-Z0-9_-]{1,15}$/;

interface FieldErrors {
    username?: string;
    password?: string;
}

export function AddUserModal({ onClose, fetchUsers }: AddUserModalProps) {
    const [form, setForm] = useState({ username: "", password: "", admin_privileges: false });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

    const validate = (): boolean => {
        const errs: FieldErrors = {};
        const username = form.username.trim();
        const password = form.password.trim();

        if (!username) {
            errs.username = "Name is required.";
        } else if (!USER_NAME_RE.test(username)) {
            errs.username = "Only letters, digits, '_' and '-' are allowed (max 15 chars).";
        }

        if (!password) {
            errs.password = "password is required.";
        }

        setFieldErrors(errs);
        return Object.keys(errs).length === 0;
    };

    const handleSubmit = async () => {
        if (!validate()) return;

        setLoading(true);
        setError("");
        try {
            const payload = {
                username: form.username.trim(),
                password: form.password.trim(),
                role: form.admin_privileges ? "admin" : "user",
            };
            await apiFetch("/user", {
                method: "POST",
                data: payload,
            });
            fetchUsers();
            onClose();
        } catch (e: any) {
            const d = e.response?.data ?? {};

            if (Array.isArray(d.detail)) {
                const errs: FieldErrors = {};
                for (const item of d.detail) {
                    const field = item.loc?.[item.loc.length - 1];
                    if (field === "username" || field === "password") {
                        errs[field as "username" | "password"] = item.msg;
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
                className="absolute inset-0 bg-black/25 backdrop-blur-sm"
                onClick={onClose}
            />
            <div className="relative w-full max-w-md mx-4 rounded-2xl border border-slate-700/60 bg-black shadow-2xl shadow-black/60 overflow-hidden">

                <div className="p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-lg font-semibold text-white tracking-tight">Add user</h2>
                        <button
                            onClick={onClose}
                            className="text-slate-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-slate-800 cursor-pointer"
                        >
                            <X size={16} />
                        </button>
                    </div>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-widest">
                                Username
                            </label>
                            <input
                                type="text"
                                placeholder="username"
                                value={form.username}
                                onChange={(e) => {
                                    setForm((f) => ({ ...f, username: e.target.value }));
                                    if (fieldErrors.username) setFieldErrors((fe) => ({ ...fe, username: undefined }));
                                }}
                                className={`w-full bg-slate-800/60 border text-white placeholder-slate-500 rounded-xl px-4 py-2.5 text-sm focus:outline-none transition-all font-mono ${fieldErrors.username
                                    ? "border-red-500/70 focus:border-red-500 "
                                    : "border-slate-700/70 focus:border-white/65 "
                                    }`}
                            />
                            {fieldErrors.username && (
                                <p className="mt-1.5 text-xs text-red-400">{fieldErrors.username}</p>
                            )}
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-widest">
                                Password
                            </label>
                            <input
                                type="password"
                                placeholder="password"
                                value={form.password}
                                onChange={(e) => {
                                    setForm((f) => ({ ...f, password: e.target.value }));
                                    if (fieldErrors.password) setFieldErrors((fe) => ({ ...fe, password: undefined }));
                                }}
                                className={`w-full bg-slate-800/60 border text-white placeholder-slate-500 rounded-xl px-4 py-2.5 text-sm focus:outline-none transition-all font-mono ${fieldErrors.password
                                    ? "border-red-500/70 focus:border-red-500"
                                    : "border-slate-700/70 focus:border-white/65"
                                    }`}
                            />
                            {fieldErrors.password && (
                                <p className="mt-1.5 text-xs text-red-400">{fieldErrors.password}</p>
                            )}
                        </div>
                        <div className="flex items-center justify-between py-1">
                            <span className="text-xs font-medium text-slate-400 uppercase tracking-widest">Admin Privileges</span>
                            <button
                                type="button"
                                onClick={() => setForm((f) => ({ ...f, admin_privileges: !f.admin_privileges }))}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none cursor-pointer ${form.admin_privileges ? "bg-white" : "bg-slate-700"
                                    }`}
                            >
                                <span
                                    className={`inline-block h-4 w-4 transform rounded-full shadow-sm transition duration-200 ${form.admin_privileges ? "translate-x-6 bg-black" : "translate-x-1 bg-white"}`}
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
                            className="flex-1 px-4 py-2.5 rounded-xl border text-sm border-slate-700 text-slate-400 hover:text-white hover:bg-red-500/35 hover:border-red-500/50 transition-colors cursor-pointer"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSubmit}
                            disabled={loading}
                            className="flex-1 px-4 py-2.5 rounded-xl bg-white hover:bg-gray-300/90 text-slate-950 font-semibold text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20 cursor-pointer"
                        >
                            {loading ? "Adding…" : "Add user"}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}