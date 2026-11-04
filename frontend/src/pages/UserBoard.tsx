import { Plus, } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { AddUserModal } from "../components/modals/addUserModal";
import type { User } from "../types/Types";
import { apiFetch } from "../api";
import { UserCard } from "../components/userCard";
import { UserModal } from "../components/modals/userModal";

export default function UserBoard() {
    const [showAddUserModal, setAddUserShowModal] = useState(false);

    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [selectedUser, setSelectedUser] = useState<User | null>(null);

    const fetchUsers = useCallback(async () => {
        try {
            const data = await apiFetch<User[]>("/users");
            setUsers(data);
            setError("");
        } catch (e: any) {
            if (e.status === 403) {
                setError("This page requires admin privileges");
            } else {
                setError(e.message);
            }
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUsers();
        const interval = setInterval(fetchUsers, 15000);
        return () => clearInterval(interval);
    }, [fetchUsers]);

    return (
        <div className="min-h-screen bg-black text-white font-sans flex flex-col md:flex-row relative">

            <main className="flex-1 px-6 py-10 w-full">
                <div className="relative max-w-5xl mx-auto px-6 mt-5">
                    <header className="flex items-start justify-between mb-9 gap-4 flex-wrap">
                        <div className="flex items-center gap-4">
                            <div>
                                <h1 className="text-3xl font-bold tracking-tight text-white">
                                    Users Registry
                                </h1>
                                <p className="text-slate-400 text-sm mt-1">
                                    Manage Users
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-3 mt-1">
                            <button
                                onClick={() => setAddUserShowModal(true)}
                                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white hover:bg-gray-200 text-slate-950 font-semibold text-sm transition-colors cursor-pointer"
                            >
                                <Plus size={18} />
                                Add user
                            </button>
                        </div>
                    </header>

                    {/* Content */}
                    {
                        loading ? (
                            <div className="flex flex-col items-center justify-center py-24 gap-4">
                                <div className="w-8 h-8 border-2 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
                                <p className="text-slate-500 text-sm">Connecting to API…</p>
                            </div>
                        ) : error ? (
                            <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center">
                                <p className="text-red-400 text-sm font-medium mb-1">Failed to load devices</p>
                                <p className="text-slate-500 text-xs font-mono">{error}</p>
                                <button
                                    onClick={fetchUsers}
                                    className="mt-4 text-xs text-red-400 hover:text-red-300 underline underline-offset-2"
                                >
                                    Retry
                                </button>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                                {users.map((d, i) => (
                                    <UserCard key={d.username}
                                        user={d}
                                        index={i}
                                        onClick={() => setSelectedUser(d)}
                                    />
                                ))}
                            </div>
                        )
                    }
                </div >
            </main>

            {showAddUserModal && (
                <AddUserModal
                    onClose={() => setAddUserShowModal(false)}
                    fetchUsers={() => fetchUsers()}
                />
            )
            }

            {
                selectedUser && (
                    <div>
                        <UserModal
                            user={selectedUser}
                            onClose={() => setSelectedUser(null)}
                            fetchUsers={() => fetchUsers()}
                        />
                    </div>
                )
            }

        </div >
    );
}