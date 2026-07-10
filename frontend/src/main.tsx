import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import DeviceAdmin from './DeviceAdmin'
import Dashboard from './Dashboard'
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
        path="/admin"
        element={
            <ProtectedRoute>
                <DeviceAdmin />
            </ProtectedRoute>
        }
    />

    <Route
        path="/dashboard"
        element={
            <ProtectedRoute>
                <Dashboard />
            </ProtectedRoute>
        }
    />

</Routes>
    </BrowserRouter>
  </StrictMode>,
)