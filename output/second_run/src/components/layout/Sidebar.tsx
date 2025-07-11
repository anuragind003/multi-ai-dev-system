import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const Sidebar = () => {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  const isActive = (path: string) => location.pathname === path;

  if (!isAuthenticated) {
    return null;
  }

  return (
    <aside className="bg-gray-100 dark:bg-gray-800 w-64 py-4 px-6 hidden md:block">
      <nav>
        <ul>
          <li className="mb-2">
            <Link
              to="/dashboard"
              className={`block py-2 px-4 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 ${isActive('/dashboard') ? 'bg-gray-200 dark:bg-gray-700 font-semibold' : ''
                }`}
            >
              Dashboard
            </Link>
          </li>
          <li className="mb-2">
            <Link
              to="/profile"
              className={`block py-2 px-4 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 ${isActive('/profile') ? 'bg-gray-200 dark:bg-gray-700 font-semibold' : ''
                }`}
            >
              Profile
            </Link>
          </li>
          <li className="mb-2">
            <Link
              to="/settings"
              className={`block py-2 px-4 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 ${isActive('/settings') ? 'bg-gray-200 dark:bg-gray-700 font-semibold' : ''
                }`}
            >
              Settings
            </Link>
          </li>
        </ul>
      </nav>
    </aside>
  );
};

export default Sidebar;