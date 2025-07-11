import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@hooks/useAuth';
import Button from '@components/ui/Button';

const Header: React.FC = () => {
  const { isAuthenticated, user, logout, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="bg-white shadow-sm py-4 px-4 sm:px-6 lg:px-8">
      <div className="container mx-auto flex justify-between items-center">
        <Link to="/" className="text-2xl font-bold text-primary" aria-label="Home">
          EnterpriseApp
        </Link>
        <nav className="flex items-center space-x-4">
          {isAuthenticated ? (
            <>
              <Link to="/dashboard" className="text-text-light hover:text-primary transition-colors duration-200" aria-label="Go to Dashboard">
                Dashboard
              </Link>
              <span className="text-text-light hidden sm:inline">Welcome, {user?.name || user?.email}!</span>
              <Button onClick={handleLogout} variant="outline" size="sm" isLoading={isLoading} aria-label="Logout">
                Logout
              </Button>
            </>
          ) : (
            <>
              <Link to="/" className="text-text-light hover:text-primary transition-colors duration-200" aria-label="Go to Home Page">
                Home
              </Link>
              <Link to="/login">
                <Button variant="primary" size="sm" aria-label="Login">
                  Login
                </Button>
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
};

export default Header;