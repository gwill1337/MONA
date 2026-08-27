import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import DeviceAdmin from './pages/DeviceAdmin'
import Dashboard from './pages/Dashboard'
import UserBoard from './pages/UserBoard'
import './index.css'
import ProtectedRoute from './ProtectedRoute'
import Login from './Login'

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <BrowserRouter basename="/">
            <Routes>

                <Route
                    path="/login"
                    element={<Login />}
                />

                <Route
                    path="/"
                    element={
                        <ProtectedRoute>
                            <DeviceAdmin />
                        </ProtectedRoute>
                    }
                />

                {/* <Route
                    path="/admin"
                    element={
                        <DeviceAdmin />
                    }
                /> */}

                <Route
                    path="/dashboard"
                    element={
                        <ProtectedRoute>
                            <Dashboard />
                        </ProtectedRoute>
                    }
                />

                <Route
                    path="/userboard"
                    element={
                        <ProtectedRoute>
                            <UserBoard />
                        </ProtectedRoute>
                    }
                />

                {/* <Route
                    path="/userboard"
                    element={
                        <UserBoard />
                    }
                /> */}

            </Routes>
        </BrowserRouter>
    </StrictMode>,
)