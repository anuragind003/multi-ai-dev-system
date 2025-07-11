import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export const Header = () => {
  const { isAuthenticated, logout } = useAuth();

  return (
    <header className="bg-white dark:bg-gray-800 shadow-md py-4 px-6 flex items-center justify-between">
      <Link to="/" className="text-2xl font-bold text-blue-600 dark:text-blue-300">
        Task Manager
      </Link>
      <nav>
        {isAuthenticated ? (
          <div className="flex items-center space-x-4">
            <Link to="/profile" className="hover:text-blue-500">Profile</Link>
            <Link to="/settings" className="hover:text-blue-500">Settings</Link>
            <button onClick={logout} className="hover:text-red-500">Logout</button>
          </div>
        ) : (
          <div className="flex items-center space-x-4">
            <Link to="/login" className="hover:text-blue-500">Login</Link>
            <Link to="/register" className="hover:text-blue-500">Register</Link>
          </div>
        )}
      </nav>
    </header>
  );
};