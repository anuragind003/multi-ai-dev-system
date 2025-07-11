import React from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from './ThemeContext';
import Button from './Button';

const Navbar: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <nav className="bg-white dark:bg-gray-900 shadow-md py-4">
      <div className="container mx-auto px-4 flex items-center justify-between">
        <Link to="/" className="text-2xl font-bold text-primary dark:text-light">
          My App
        </Link>
        <div className="space-x-4">
          <Link to="/about" className="text-gray-700 dark:text-gray-300 hover:text-primary transition-colors duration-200">
            About
          </Link>
          <Link to="/contact" className="text-gray-700 dark:text-gray-300 hover:text-primary transition-colors duration-200">
            Contact
          </Link>
          <Button onClick={toggleTheme} variant="outline">
            {theme === 'light' ? 'Dark Mode' : 'Light Mode'}
          </Button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;