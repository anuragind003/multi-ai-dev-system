import React from 'react';
import { useAuth } from '@context/AuthContext';
import { Link } from 'react-router-dom';
import Button from '@components/ui/Button';

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm py-4 px-6 border-b border-gray-200">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Link to={isAuthenticated ? "/dashboard" : "/"} className="text-2xl font-bold text-primary-dark">
            Enterprise App
          </Link>
          <nav>
            {isAuthenticated ? (
              <div className="flex items-center space-x-4">
                <span className="text-gray-700 font-medium hidden sm:inline">
                  Welcome, {user?.username || user?.email || 'User'}!
                </span>
                <Button onClick={logout} variant="secondary" size="sm" aria-label="Logout">
                  Logout
                </Button>
              </div>
            ) : (
              <Link to="/login">
                <Button variant="primary" size="sm" aria-label="Login">
                  Login
                </Button>
              </Link>
            )}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow container mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 text-white py-6 px-6 mt-auto">
        <div className="max-w-7xl mx-auto text-center text-sm">
          <p>&copy; {new Date().getFullYear()} Enterprise App. All rights reserved.</p>
          <p className="mt-1">
            <Link to="/privacy" className="text-gray-400 hover:text-white transition-colors">Privacy Policy</Link>
            <span className="mx-2">|</span>
            <Link to="/terms" className="text-gray-400 hover:text-white transition-colors">Terms of Service</Link>
          </p>
        </div>
      </footer>
    </div>
  );
};

export default AppLayout;