import { useEffect, useState } from "react";
import { Check, User2, } from "lucide-react";
import { apiFetch } from "../../api";
import {
    X,
} from "lucide-react";
import type { User } from "../../types/Types";

interface UserModalProps {
    user: User
    onClose: () => void;
    fetchUsers: () => void;
}


interface FieldErrors {
    username?: string;
    password?: string;
}

export function UserModal({ user, onClose, fetchUsers }: UserModalProps) {
    const [loading, setLoading] = useState(false);
    const [deleteError, setDeleteError] = useState("");
    const [roleError, setRoleError] = useState("");
    const [passwordError, setPasswordError] = useState("");
    const [confirmingDelete, setConfirmingDelete] = useState(false);
    const [confirmingChangeRole, setConfirmingChangeRole] = useState(false);
    const [modalNewUserPassword, setModalNewUserPassword] = useState(false);
    const [newUserPassword, setNewUserPassword] = useState({ password: "" });

    const validate_password = (): boolean => {
        if (!newUserPassword.password) {
            setPasswordError("Password is required");
            return false;
        }
        return true;
    };

    const handleUserDelete = async () => {
        setLoading(true);
        setDeleteError("");
        try {
            await apiFetch(`/user/${user.id}`, {
                method: "DELETE",
            });
            fetchUsers();
            setConfirmingDelete(false);
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

            }
            const message =
                d.message ??
                (typeof d.detail === "string" ? d.detail : d.detail?.message) ??
                e.message ??
                "Unknown error";
            setDeleteError(message);
        } finally {
            setLoading(false);
        }
    };

    const handleUserChangeRole = async () => {
        setLoading(true);
        setRoleError("");
        try {
            const payload = {
                role: user.role === "admin" ? "user" : "admin"
            }
            await apiFetch(`/user/${user.id}/role`, {
                method: "PATCH",
                data: payload,
            });
            fetchUsers();
            setConfirmingChangeRole(false);
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
            }
            const message =
                d.message ??
                (typeof d.detail === "string" ? d.detail : d.detail?.message) ??
                e.message ??
                "Unknown error";
            setRoleError(message);
        } finally {
            setLoading(false);
        }
    };

    const handleUserChangePassword = async () => {
        if (!validate_password()) return;

        setLoading(true);
        setPasswordError("");
        try {
            const payload = {
                username: user.username,
                new_password: newUserPassword.password,
            };
            await apiFetch("/user/change-password", {
                method: "PATCH",
                data: payload,
            });
            setModalNewUserPassword(false);
            setNewUserPassword({ password: "" });
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
            }
            const message =
                d.message ??
                (typeof d.detail === "string" ? d.detail : d.detail?.message) ??
                e.message ??
                "Unknown error";
            setPasswordError(message);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        setConfirmingDelete(false);
        setModalNewUserPassword(false);
        setNewUserPassword({ password: "" });
        setRoleError("");
        setPasswordError("");
        setDeleteError("");
    }, [user]);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div
                className="absolute inset-0 bg-black/25 backdrop-blur-sm"
                onClick={onClose}
            />
            <div className="relative w-full max-w-md mx-4 rounded-2xl border border-slate-700/60 bg-black shadow-2xl shadow-black/60 overflow-hidden">
                <div className="p-6">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-2">
                            <User2 size={52} />
                            <p className="block text-xl font-normal text-white">
                                Username:{} <span className="font-bold">{user.username}</span>
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-slate-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-slate-800 cursor-pointer"
                        >
                            <X size={16} />
                        </button>
                    </div>

                    <div className="space-y-4">
                        <div className="w-full rounded-2xl border py-3 px-4 bg-gray-400/15 border-slate-700">
                            {/* <p className="block text-base font-semibold text-white mb-1.5">
                                Username: {user.username}
                            </p> */}
                            <p className="block text-base font-normal text-white mb-1.5">
                                Role:{} <span className="font-bold">{user.role}</span>
                            </p>
                            <div className="flex gap-1  text-base font-normal text-white mb-1.5">
                                Admin:{}  <span className="font-bold"> {user.role === "admin" ? <Check color="green" /> : <X color="red" />} </span>
                            </div>
                        </div>
                    </div>

                    <div className="flex-col h-auto">
                        <div className="mt-6 flex gap-3">
                            {confirmingChangeRole ? (
                                <div className="absolute inset-0 z-50 flex items-center justify-center rounded-2xl bg-black/25 backdrop-blur-sm">
                                    <div className="w-full max-w-xs mx-4 rounded-2xl border border-red-500/20 bg-slate-900 p-6 text-center shadow-2xl">
                                        <p className="text-white font-semibold mb-5">Change role for this user?</p>
                                        {roleError && (
                                            <p className="mt-4 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 mb-4">
                                                {roleError}
                                            </p>
                                        )}
                                        <div className="flex gap-3 items-center">
                                            <button
                                                onClick={() => setConfirmingChangeRole(false)}
                                                className="flex-1 px-4 py-2.5 rounded-xl border border-white/50 text-black bg-white hover:bg-gray-200 text-sm transition-colors cursor-pointer"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                onClick={handleUserChangeRole}
                                                className="flex-1 px-4 py-2.5 rounded-xl border border-red-700 text-white bg-red-700  text-sm hover:bg-red-600 hover:border-red-600 transition-colors cursor-pointer"
                                            >
                                                {loading ? "Changing role" : "Change role"}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <button

                                    disabled={loading}
                                    onClick={() => setConfirmingChangeRole(true)}
                                    className="flex-1 px-4 py-2.5 rounded-xl border bg-white text-black border-slate-700 hover:bg-gray-200 text-sm hover:border-slate-600 transition-colors cursor-pointer"
                                >
                                    {loading ? "Changing role" : "Change role"}
                                </button>
                            )}
                            {modalNewUserPassword ? (
                                <div className="absolute inset-0 z-50 flex items-center justify-center rounded-2xl bg-black/25 backdrop-blur-sm">
                                    <div className="w-full max-w-xs mx-4 rounded-2xl border border-red-500/20 bg-slate-900 p-6 text-center shadow-2xl">
                                        <p className="text-white font-semibold mb-1">Change password for this user</p>
                                        <p className="text-slate-400 text-sm mb-5">
                                            This action cannot be undone.
                                        </p>
                                        {passwordError && (
                                            <p className="mt-4 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 mb-4">
                                                {passwordError}
                                            </p>
                                        )}
                                        <label className="block text-xs font-medium text-slate-400 mb-1.5 uppercase tracking-widest">
                                            New password
                                        </label>
                                        <input
                                            type="text"
                                            placeholder="New password"
                                            value={newUserPassword.password}
                                            onChange={(e) => {
                                                setNewUserPassword((f) => ({ ...f, password: e.target.value }));
                                                // if (fieldErrors.username) setFieldErrors((fe) => ({ ...fe, username: undefined }));
                                            }}
                                            className={"w-full bg-slate-800/60 border text-white placeholder-slate-500 rounded-xl px-4 py-2.5 text-sm focus:outline-none transition-all font-mono border-slate-700/70 focus:border-white/70 mb-4"}
                                        />
                                        <div className="flex gap-3">
                                            <button
                                                onClick={() => setModalNewUserPassword(false)}
                                                className="flex-1 px-4 py-2.5 rounded-xl border border-white/50 text-black bg-white hover:bg-gray-200 text-sm transition-colors cursor-pointer"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                onClick={handleUserChangePassword}
                                                className="flex-1 px-4 py-2.5 rounded-xl border border-red-700 text-white bg-red-700  text-sm hover:bg-red-600 hover:border-red-600 transition-colors cursor-pointer"
                                            >
                                                {loading ? "Changing" : "Change"}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <button

                                    disabled={loading}
                                    onClick={() => setModalNewUserPassword(true)}
                                    className="flex-1 px-4 py-2.5 rounded-xl border bg-white text-black border-slate-700 hover:bg-gray-200 text-sm hover:border-slate-600 transition-colors cursor-pointer"
                                >
                                    {loading ? "Changing" : "Change password"}
                                </button>
                            )}
                        </div>
                        <div className="mt-6 flex gap-3">
                            <button
                                onClick={onClose}
                                className="flex-1 px-4 py-2.5 rounded-xl border border-white/50 text-black bg-white hover:bg-gray-200 text-sm transition-colors cursor-pointer"
                            >
                                Cancel
                            </button>
                            {confirmingDelete ? (
                                <div className="absolute inset-0 z-50 flex items-center justify-center rounded-2xl bg-black/25 backdrop-blur-sm">
                                    <div className="w-full max-w-xs mx-4 rounded-2xl border border-red-500/20 bg-slate-900 p-6 text-center shadow-2xl">
                                        <p className="text-white font-semibold mb-1">Delete this user?</p>
                                        <p className="text-slate-400 text-sm mb-5">
                                            This action cannot be undone.
                                        </p>
                                        {deleteError && (
                                            <p className="mt-4 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 mb-4">
                                                {deleteError}
                                            </p>
                                        )}
                                        <div className="flex gap-3">
                                            <button
                                                onClick={() => setConfirmingDelete(false)}
                                                className="flex-1 px-4 py-2.5 rounded-xl border border-white/50 text-black bg-white hover:bg-gray-200 text-sm transition-colors cursor-pointer"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                onClick={handleUserDelete}
                                                className="flex-1 px-4 py-2.5 rounded-xl border border-red-700 text-white bg-red-700  text-sm hover:bg-red-600 hover:border-red-600 transition-colors cursor-pointer"
                                            >
                                                {loading ? "Deleting…" : "Delete"}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <button

                                    disabled={loading}
                                    onClick={() => setConfirmingDelete(true)}
                                    className="flex-1 px-4 py-2.5 rounded-xl border border-red-700 text-white bg-red-700  text-sm hover:bg-red-600 hover:border-red-600 transition-colors cursor-pointer"
                                >
                                    {loading ? "Deleting…" : "Delete user"}
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}