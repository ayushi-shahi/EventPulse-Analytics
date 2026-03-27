import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { WebSocketProvider } from './context/WebSocketContext';
import { NotificationProvider } from './context/NotificationContext';
import { APIKeyProvider } from './context/APIKeyContext';
import { BellProvider } from './context/BellContext';

import Layout from './components/layout/Layout';
import ProtectedRoute from './components/layout/ProtectedRoute';

import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import APIKeys from './pages/APIKeys';
import LiveFeed from './pages/LiveFeed';
import Events from './pages/Events';
import Alerts from './pages/Alerts';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NotificationProvider>
          <BellProvider>
            <APIKeyProvider>
              <WebSocketProvider>
                <Routes>
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  <Route
                    path="/"
                    element={
                      <ProtectedRoute>
                        <Layout />
                      </ProtectedRoute>
                    }
                  >
                    <Route index element={<Navigate to="dashboard" replace />} />
                    <Route path="dashboard" element={<Dashboard />} />
                    <Route path="api-keys" element={<APIKeys />} />
                    <Route path="live-feed" element={<LiveFeed />} />
                    <Route path="events" element={<Events />} />
                    <Route path="alerts" element={<Alerts />} />
                    <Route path="metrics" element={<Dashboard />} />
                    <Route path="settings" element={<Dashboard />} />
                  </Route>
                  <Route path="*" element={<Navigate to="/login" replace />} />
                </Routes>
              </WebSocketProvider>
            </APIKeyProvider>
          </BellProvider>
        </NotificationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;