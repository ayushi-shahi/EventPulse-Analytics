import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import { ToastContainer } from '../common/Toast';
import { useNotification } from '../../hooks/useNotification';

/**
 * Main Layout Component
 */
const Layout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { notifications, removeNotification } = useNotification();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <Navbar onMenuClick={() => setSidebarOpen(true)} />

      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content */}
      <div className="lg:pl-64 pt-16">
        <main className="min-h-[calc(100vh-4rem)] p-4 lg:p-6">
          <Outlet />
        </main>
      </div>

      {/* Toast Notifications */}
      <ToastContainer
        notifications={notifications}
        onClose={removeNotification}
      />
    </div>
  );
};

export default Layout;