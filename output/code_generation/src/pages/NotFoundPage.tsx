// src/pages/NotFoundPage.tsx
import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/CommonUI';

const NotFoundPage: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-160px)] text-center px-4">
      <h1 className="text-6xl font-bold text-primary mb-4">404</h1>
      <h2 className="text-3xl font-semibold text-text mb-4">Page Not Found</h2>
      <p className="text-lg text-text-light mb-8">
        Oops! The page you are looking for does not exist. It might have been moved or deleted.
      </p>
      <Link to="/dashboard">
        <Button variant="primary" size="lg" aria-label="Go to Dashboard">
          Go to Dashboard
        </Button>
      </Link>
    </div>
  );
};

export default NotFoundPage;