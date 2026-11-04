import { useState } from "react";
import { Lock, User, Activity } from "lucide-react";
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

    const from = location.state?.from?.pathname || "/";
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

            {/* <div className="fixed top-0 left-1/2 -translate-x-1/2 w-150 h-px bg-linear-to-r from-transparent via-cyan-500/40 to-transparent" /> */}
            <div className="relative w-full max-w-md">
                <div className="rounded-2xl border border-slate-700/60 bg-black overflow-hidden shadow-2xl shadow-black/50">
                    <div className="p-8">
                        <div className="flex justify-center items-center mb-3 gap-2">
                            <Activity size={36} />
                            <h1 className="text-2xl font-bold text-center">
                                MONA
                            </h1>
                        </div>


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
                                            ? "border-red-500/70 focus:border-red-500"
                                            : "border-slate-700 focus:border-white/70"}`}
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
                                            ? "border-red-500/70 focus:border-red-500"
                                            : "border-slate-700 focus:border-white/70"}`}
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
                                className="w-full py-3 rounded-xl bg-white hover:bg-gray-200 text-slate-950 font-bold transition-colors disabled:opacity-5 cursor-pointer"
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