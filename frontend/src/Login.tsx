import { useState } from "react";
import { Shield, Lock, User } from "lucide-react";
import { useNavigate, useLocation } from "react-router-dom";
import { apiFetch } from "./api";
import type { Login } from "./types/Types";

interface FieldErrors {
    username?: string;
    password?: string;
}

export default function LoginPage() {
    const navigate = useNavigate();
    const location = useLocation();

    const from = location.state?.from?.pathname || "/dashboard";
    const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const validate = (): boolean => {
        const errs: FieldErrors = {};
        if (!username) {
            errs.username = "Username is required"
        }

        if (!password) {
            errs.password = "Password is required"
        }
        setFieldErrors(errs);
        return Object.keys(errs).length === 0;
    }

    async function login() {
        if (!validate()) return;

        setLoading(true);
        setError("");

        try {
            await apiFetch<Login>("/auth/login", {
                method: "POST",
                data: {
                    username,
                    password,
                },
            });

            navigate(from, { replace: true });
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">

            {/* background grid */}
            <div
                className="fixed inset-0 pointer-events-none"
                style={{
                    backgroundImage: `
                        linear-gradient(rgba(148,163,184,0.03) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(148,163,184,0.03) 1px, transparent 1px)
                    `,
                    backgroundSize: "48px 48px",
                }}
            />

            <div className="fixed top-0 left-1/2 -translate-x-1/2 w-150 h-px bg-linear-to-r from-transparent via-cyan-500/40 to-transparent" />
            <div className="relative w-full max-w-md">
                <div className="rounded-2xl border border-slate-700/60 bg-slate-900/70 overflow-hidden shadow-2xl shadow-black/50">
                    <div className="h-px w-full bg-linear-to-r from-transparent via-cyan-500 to-transparent" />
                    <div className="p-8">
                        <div className="flex justify-center mb-6">
                            <div className="p-4 rounded-2xl bg-cyan-500/10 text-cyan-400">
                                <Shield size={36} />
                            </div>
                        </div>

                        <h1 className="text-2xl font-bold text-center">
                            MONA
                        </h1>

                        <p className="text-center text-slate-400 text-sm mt-1 mb-8">
                            Administrator Login
                        </p>

                        <div className="space-y-5">
                            <div>

                                <label className="text-xs uppercase tracking-widest text-slate-400">
                                    Username
                                </label>

                                <div className="relative mt-2">

                                    <User
                                        className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
                                        size={18}
                                    />

                                    <input
                                        value={username}
                                        onChange={(e) => {
                                            setUsername(e.target.value);
                                        }}
                                        className={`w-full bg-slate-800 border rounded-xl pl-11 pr-4 py-3 focus:outline-none transition ${fieldErrors.username
                                            ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/30"
                                            : "border-slate-700 focus:border-cyan-500 focus:ring-cyan-500/30"}`}
                                    />
                                </div>
                                    {fieldErrors.username && (
                                        <p className="mt-1.5 text-xs text-red-400">{fieldErrors.username}</p>
                                    )}
                            </div>
                            <div>

                                <label className="text-xs uppercase tracking-widest text-slate-400">
                                    Password
                                </label>
                                <div className="relative mt-2">
                                    <Lock
                                        className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
                                        size={18}
                                    />

                                    <input
                                        type="password"
                                        value={password}
                                        onChange={(e) => {
                                            setPassword(e.target.value);
                                        }}
                                        className={`w-full bg-slate-800 border rounded-xl pl-11 pr-4 py-3 focus:outline-none transition ${fieldErrors.password
                                            ? "border-red-500/70 focus:border-red-500 focus:ring-red-500/30"
                                            : "border-slate-700 focus:border-cyan-500 focus:ring-cyan-500/30"}`}
                                    />
                                </div>
                                    {fieldErrors.password && (
                                        <p className="mt-1.5 text-xs text-red-400">{fieldErrors.password}</p>
                                    )}
                            </div>

                            {error && (

                                <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-red-400 text-sm">
                                    {error}
                                </div>

                            )}

                            <button
                                disabled={loading}
                                onClick={login}
                                className="w-full py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold transition disabled:opacity-50"
                            >
                                {loading ? "Signing in..." : "Sign In"}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}