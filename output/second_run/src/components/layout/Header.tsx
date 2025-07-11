import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const Header = () => {
  const { isAuthenticated, logout } = useAuth();

  return (
    <header className="bg-white dark:bg-gray-800 shadow-md py-4 px-6 flex items-center justify-between">
      <Link to="/" className="text-2xl font-semibold text-gray-800 dark:text-white">
        Task Management
      </Link>
      <nav>
        {isAuthenticated ? (
          <button onClick={logout} className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded">
            Logout
          </button>
        ) : (
          <div className="flex space-x-4">
            <Link to="/login" className="text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
              Login
            </Link>
            <Link to="/register" className="text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
              Register
            </Link>
          </div>
        )}
      </nav>
    </header>
  );
};

export default Header;