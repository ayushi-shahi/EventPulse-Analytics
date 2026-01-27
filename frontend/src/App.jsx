import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { WebSocketProvider } from './context/WebSocketContext';
import { NotificationProvider } from './context/NotificationContext';
import { APIKeyProvider } from './context/APIKeyContext';

// Layout
import Layout from './components/layout/Layout';
import ProtectedRoute from './components/layout/ProtectedRoute';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import APIKeys from './pages/APIKeys';
import LiveFeed from './pages/LiveFeed';
import Events from './pages/Events';
import Alerts from './pages/Alerts';

/**
 * Main Application Component
 */
function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NotificationProvider>
          <APIKeyProvider>
            <WebSocketProvider>
              <Routes>
                {/* Public Routes */}
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />

                {/* Protected Routes */}
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <Layout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="dashboard" element={<Dashboard />} />
                  <Route path="api-keys" element={<APIKeys />} />
                  <Route path="live-feed" element={<LiveFeed />} />
                  <Route path="events" element={<Events />} />
                  <Route path="alerts" element={<Alerts />} />
                  <Route path="metrics" element={<Dashboard />} />
                  <Route path="settings" element={<Dashboard />} />
                </Route>

                {/* 404 - Redirect to dashboard */}
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </WebSocketProvider>
          </APIKeyProvider>
        </NotificationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;