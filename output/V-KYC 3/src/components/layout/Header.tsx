import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@hooks/useAuth';
import Button from '@components/ui/Button';

const Header: React.FC = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="bg-primary text-white shadow-md">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <Link to={isAuthenticated ? "/dashboard" : "/"} className="text-2xl font-bold tracking-tight">
          EnterpriseApp
        </Link>

        {/* Mobile menu button */}
        <div className="md:hidden">
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-primary focus:ring-white rounded-md p-2"
            aria-label="Open mobile menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              {isMobileMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Desktop navigation */}
        <nav className="hidden md:flex items-center space-x-6">
          {isAuthenticated ? (
            <>
              <Link to="/dashboard" className="hover:text-primary-light transition-colors text-lg font-medium" aria-label="Go to Dashboard">
                Dashboard
              </Link>
              <span className="text-lg font-medium">Welcome, {user?.username || 'User'}</span>
              <Button onClick={handleLogout} variant="secondary" size="sm" aria-label="Logout">
                Logout
              </Button>
            </>
          ) : (
            <Link to="/login" className="hover:text-primary-light transition-colors text-lg font-medium" aria-label="Go to Login Page">
              Login
            </Link>
          )}
        </nav>
      </div>

      {/* Mobile menu dropdown */}
      {isMobileMenuOpen && (
        <div className="md:hidden bg-primary-dark pb-4">
          <nav className="flex flex-col items-center space-y-4">
            {isAuthenticated ? (
              <>
                <Link
                  to="/dashboard"
                  className="block w-full text-center py-2 hover:bg-primary transition-colors text-lg font-medium"
                  onClick={() => setIsMobileMenuOpen(false)}
                  aria-label="Go to Dashboard"
                >
                  Dashboard
                </Link>
                <span className="block w-full text-center py-2 text-lg font-medium">Welcome, {user?.username || 'User'}</span>
                <Button onClick={() => { handleLogout(); setIsMobileMenuOpen(false); }} variant="secondary" size="md" className="w-3/4" aria-label="Logout">
                  Logout
                </Button>
              </>
            ) : (
              <Link
                to="/login"
                className="block w-full text-center py-2 hover:bg-primary transition-colors text-lg font-medium"
                onClick={() => setIsMobileMenuOpen(false)}
                aria-label="Go to Login Page"
              >
                Login
              </Link>
            )}
          </nav>
        </div>
      )}
    </header>
  );
};

export default Header;