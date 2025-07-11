import React from 'react';
import { Link } from 'react-router-dom';

const NotFound: React.FC = () => {
  return (
    <div className="container mx-auto p-4 text-center">
      <h1 className="text-3xl font-bold mb-4">404 - Not Found</h1>
      <p className="text-gray-500 mb-4">Sorry, the page you are looking for does not exist.</p>
      <Link to="/" className="text-blue-500 hover:underline">
        Go back to home
      </Link>
    </div>
  );
};

export default NotFound;