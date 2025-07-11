import React from 'react';
import { Link } from 'react-router-dom';

function Header() {
  return (
    <header className="bg-white shadow-md py-4">
      <div className="container mx-auto px-4 flex items-center justify-between">
        <Link to="/" className="text-2xl font-bold">
          UAT App
        </Link>
        <nav>
          <ul className="flex space-x-4">
            <li>
              <Link to="/test-cases" className="hover:text-blue-500">
                Test Cases
              </Link>
            </li>
            {/* Add more navigation links as needed */}
          </ul>
        </nav>
      </div>
    </header>
  );
}

export default Header;