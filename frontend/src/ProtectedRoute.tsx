import { Navigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { apiFetch } from "./api";

export default function ProtectedRoute({children}:{children:React.ReactNode}){
    const [loading, setLoading] = useState(true);
    const [ok, setOk] = useState(false);
    const location = useLocation();

    useEffect(() => {
        apiFetch("/api/auth/me")
        .then(res => setOk(res.ok))
        .catch(() => setOk(false))
        .finally(() => setLoading(false));
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center text-white">
                Loading...
            </div>
        );
    }

    if (!ok) {
        return <Navigate to="/login" state={{ from: location }} replace/>;
    }

    return children;
}