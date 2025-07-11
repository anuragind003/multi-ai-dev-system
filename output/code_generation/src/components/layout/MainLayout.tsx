import React, { useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Button from '../ui/Button';

interface MainLayoutProps {
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { user, logout } = useAuth();

  const navLinks = [
    { name: 'Home', path: '/' },
    { name: 'Dashboard', path: '/dashboard' },
    // { name: 'Profile', path: '/profile' },
    // { name: 'Settings', path: '/settings' },
  ];

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-30 w-64 bg-white shadow-lg transform ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } md:relative md:translate-x-0 transition-transform duration-300 ease-in-out`}
        aria-label="Sidebar Navigation"
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-border">
          <Link to="/dashboard" className="text-xl font-bold text-primary">
            Portal
          </Link>
          <button
            className="md:hidden text-text-light hover:text-text focus:outline-none"
            onClick={() => setIsSidebarOpen(false)}
            aria-label="Close sidebar"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
        <nav className="p-4">
          <ul>
            {navLinks.map((link) => (
              <li key={link.name} className="mb-2">
                <NavLink
                  to={link.path}
                  className={({ isActive }) =>
                    `flex items-center p-2 rounded-md text-text-light hover:bg-primary hover:text-white transition-colors duration-200 ${
                      isActive ? 'bg-primary text-white' : ''
                    }`
                  }
                  onClick={() => setIsSidebarOpen(false)} // Close sidebar on link click for mobile
                >
                  {link.name}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col md:ml-64">
        {/* Header */}
        <header className="flex items-center justify-between h-16 px-6 bg-white shadow-md z-20">
          <button
            className="md:hidden text-text-light hover:text-text focus:outline-none"
            onClick={() => setIsSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16"></path>
            </svg>
          </button>
          <h1 className="text-xl font-semibold text-text hidden md:block">Welcome, {user?.username || 'User'}!</h1>
          <div className="flex items-center space-x-4">
            <span className="text-text-light hidden sm:block">Hello, {user?.username || 'Guest'}</span>
            <Button onClick={logout} variant="secondary" size="sm">
              Logout
            </Button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 overflow-y-auto">
          {children}
        </main>

        {/* Footer */}
        <footer className="h-16 px-6 bg-white border-t border-border flex items-center justify-center text-text-light text-sm">
          &copy; {new Date().getFullYear()} Portal. All rights reserved.
        </footer>
      </div>
    </div>
  );
};

export default MainLayout;