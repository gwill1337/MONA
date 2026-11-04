import { Activity, BookOpenText, LayoutDashboard, Shield, Terminal, Users } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

const navItems = [
    { label: "Admin panel", path: "/", icon: Shield },
    // { label: "Devices", path: "/devices", onClick: () => setAddDeviceShowModal(true) },
    { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { label: "Userboard", path: "/userboard", icon: Users },
    { label: "MCP Server", path: "/mcp", icon: Terminal },
    { label: "Documentation", path: "/docs", icon: BookOpenText },

];

export function Sidebar() {
    const location = useLocation();
    const navigate = useNavigate();

    return (
        <div>
            <aside className="relative md:sticky md:top-0 w-full md:w-72 border-b md:border-b-0 md:border-r border-white/10 bg-[#0F0E0E] py-6 px-3 flex flex-col justify-start gap-8 z-10 shrink-0 h-auto md:h-screen md:overflow-y-auto">
                <div className="space-y-6 px-2">
                    <span
                        className="inline-flex items-center gap-2 cursor-pointer w-fit hover:opacity-90 transition-opacity"
                        onClick={() => navigate("/")}>

                        <Activity size={30} />
                        <h1 className="font-bold text-xl font-syne transition duration-300 hover:translate-y-1">
                            MONA
                        </h1>
                    </span>
                </div>
                <nav className="flex flex-col gap-2">
                    {navItems.map((item, index) => {
                        const isActive = location.pathname === item.path;
                        const IconComponent = item.icon;

                        return (
                            <button
                                key={index}
                                onClick={() => {
                                    navigate(item.path);
                                }}
                                className={`flex items-center gap-2 px-3 py-2 rounded-sm font-semibold text-lg transition-colors cursor-pointer w-full text-left ${isActive
                                    ? " bg-gray-400/10 text-white"
                                    : "text-gray-400 hover:bg-gray-400/10"
                                    }`}
                            >
                                <IconComponent size={18} className={isActive ? "text-white" : "text-gray-400"} />
                                {item.label}
                            </button>
                        );
                    })}
                </nav>
            </aside>
        </div>
    );
}

// "flex items-center gap-2 px-4 py-2.5 rounded-sm hover:bg-gray-700 text-white/80 font-semibold text-sm transition-colors cursor-pointer w-full"