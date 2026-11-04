import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from './Login'
import ProtectedRoute from "./ProtectedRoute";
import DeviceAdmin from "./pages/DeviceAdmin";
import { MCP } from "./pages/Mcp";
import Dashboard from "./pages/Dashboard";
import Docs from "./pages/Docs";
import UserBoard from "./pages/UserBoard";
import { MainLayout } from "./components/MainLayout";

export function App() {
    return (
        <BrowserRouter basename="/">
            <Routes>
                <Route
                    path="/login"
                    element={<Login />}
                />
                <Route
                    element={
                        <ProtectedRoute>
                            <MainLayout />
                        </ProtectedRoute>
                    }
                >
                    <Route path="/" element={<DeviceAdmin />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/mcp" element={<MCP />} />
                    <Route path="/docs" element={<Docs />} />
                    <Route path="/userboard" element={<UserBoard />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}