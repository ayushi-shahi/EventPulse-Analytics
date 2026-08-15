import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import { ToastContainer } from '../common/Toast';
import { useNotification } from '../../hooks/useNotification';

/**
 * App shell.
 *
 * Navbar (h-14) and Sidebar (w-64) are both fixed, so the content column
 * offsets itself with padding rather than relying on document flow. Pages
 * render their own content only — no page should ever need a margin hack to
 * position itself inside the shell.
 */
const Layout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { notifications, removeNotification } = useNotification();

  return (
    <div className="min-h-screen bg-ink-950">
      <Navbar onMenuClick={() => setSidebarOpen(true)} />
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="pt-14 lg:pl-64">
        <main className="min-h-[calc(100vh-3.5rem)] px-4 py-5 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>

      <ToastContainer notifications={notifications} onClose={removeNotification} />
    </div>
  );
};

export default Layout;
