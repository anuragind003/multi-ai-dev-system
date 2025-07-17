import React, { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import Button from '@/components/ui/Button';
import LoadingSpinner from '@/components/common/LoadingSpinner';

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { user, logout, isLoading } = useAuth();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      // Redirect handled by ProtectedRoute in App.tsx
    } catch (error) {
      console.error('Logout failed:', error);
      // Optionally show a toast/notification
    }
  };

  const navLinks = [
    { name: 'Dashboard', path: '/dashboard', icon: '📊' },
    { name: 'Profile', path: '/profile', icon: '👤' },
    // Add more links as needed
  ];

  if (isLoading) {
    return <LoadingSpinner />; // Show loading spinner while auth state is being determined
  }

  return (
    <div className="flex min-h-screen bg-background text-text">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 w-64 bg-white shadow-lg transform ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } lg:translate-x-0 lg:static lg:inset-0 transition-transform duration-200 ease-in-out`}
        aria-label="Sidebar navigation"
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <Link to="/dashboard" className="text-2xl font-bold text-primary">
            App Logo
          </Link>
          <button
            className="lg:hidden text-gray-500 hover:text-gray-700 focus:outline-none"
            onClick={() => setIsSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <nav className="mt-5">
          <ul>
            {navLinks.map((link) => (
              <li key={link.path}>
                <NavLink
                  to={link.path}
                  className={({ isActive }) =>
                    `flex items-center px-4 py-2.5 text-text-light hover:bg-primary hover:text-white transition-colors duration-200 ease-in-out
                    ${isActive ? 'bg-primary text-white font-semibold' : ''}`
                  }
                  onClick={() => setIsSidebarOpen(false)} // Close sidebar on link click for mobile
                >
                  <span className="mr-3 text-xl">{link.icon}</span>
                  {link.name}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white shadow-soft p-4 flex justify-between items-center z-20">
          <button
            className="lg:hidden text-gray-500 hover:text-gray-700 focus:outline-none"
            onClick={() => setIsSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <h1 className="text-xl font-semibold text-text hidden sm:block">Welcome, {user?.username || 'User'}!</h1>
          <div className="flex items-center space-x-4">
            <span className="text-text-light hidden sm:block">
              {user?.email} ({user?.role})
            </span>
            <Button onClick={handleLogout} variant="secondary" size="sm" aria-label="Logout">
              Logout
            </Button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>

        {/* Footer */}
        <footer className="bg-white shadow-inner p-4 text-center text-text-light text-sm mt-auto">
          &copy; {new Date().getFullYear()} Enterprise React App. All rights reserved.
        </footer>
      </div>
    </div>
  );
};

export default AppLayout;