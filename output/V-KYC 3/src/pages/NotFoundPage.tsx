import React from 'react';
import { Link } from 'react-router-dom';
import AppLayout from '@components/layout/AppLayout';
import Button from '@components/ui/Button';

const NotFoundPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-160px)] text-center px-4">
        <h1 className="text-9xl font-extrabold text-gray-900 mb-4">404</h1>
        <h2 className="text-4xl font-bold text-gray-800 mb-4">Page Not Found</h2>
        <p className="text-lg text-gray-600 mb-8 max-w-md">
          Oops! The page you're looking for doesn't exist or has been moved.
        </p>
        <Link to="/">
          <Button variant="primary" size="lg" aria-label="Go to Home Page">
            Go to Home
          </Button>
        </Link>
      </div>
    </AppLayout>
  );
};

export default NotFoundPage;