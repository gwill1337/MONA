import { User2, } from "lucide-react";
import type { User } from "../types/Types";

interface UserCardProps {
    user: User;
    index: number;
    onClick: () => void;
}


export function UserCard({ user, index, onClick }: UserCardProps) {
    return (
        <div
            onClick={onClick}
            className="group relative cursor-pointer rounded-2xl border border-slate-700/50 bg-slate-900/60 hover:bg-slate-800/70 hover:border-slate-600/70 transition-all duration-200 overflow-hidden max-w-48"
            style={{ animationDelay: `${index * 60}ms` }}
        >
            <div className="relative p-5">
                <div className="font-semibold text-white text-base tracking-tight mb-1 group-hover:text-cyan-50 transition-colors">
                    <User2 size={45}/>
                </div>
                <p className="absolute top-2 right-5 text-cyan-400 font-semibold">
                    role: {user.role}
                </p>


                <div className="flex items-center justify-between pt-3 border-t border-slate-700/40">
                    <span className="text-white group-hover:text-cyan-500 transition-all duration-200 translate-x-0 group-hover:translate-x-0.5">
                        {user.username}
                    </span>
                </div>
            </div>
        </div>
    );
}