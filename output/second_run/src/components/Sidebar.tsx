import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export const Sidebar = () => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return null;
  }

  return (
    <aside className="bg-gray-200 dark:bg-gray-700 w-64 py-4 px-6 hidden md:block">
      <nav>
        <ul>
          <li className="mb-2">
            <Link to="/dashboard" className="block py-2 px-4 rounded hover:bg-gray-300 dark:hover:bg-gray-600">
              Dashboard
            </Link>
          </li>
          <li className="mb-2">
            <Link to="/profile" className="block py-2 px-4 rounded hover:bg-gray-300 dark:hover:bg-gray-600">
              Profile
            </Link>
          </li>
          <li className="mb-2">
            <Link to="/settings" className="block py-2 px-4 rounded hover:bg-gray-300 dark:hover:bg-gray-600">
              Settings
            </Link>
          </li>
        </ul>
      </nav>
    </aside>
  );
};