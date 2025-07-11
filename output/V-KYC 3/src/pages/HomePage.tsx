import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/CommonUI';
import { useAuth } from '../context/AuthContext';

const HomePage: React.FC = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-primary-50 to-background p-4 text-center">
      <h1 className="text-5xl md:text-6xl font-extrabold text-primary mb-6 leading-tight">
        Welcome to EnterpriseApp
      </h1>
      <p className="text-lg md:text-xl text-text-light max-w-2xl mb-10">
        Your comprehensive solution for managing your business operations efficiently and securely.
        Experience a seamless and intuitive platform designed for productivity.
      </p>
      <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
        {isAuthenticated ? (
          <Button as={Link} to="/dashboard" size="lg" variant="primary" aria-label="Go to Dashboard">
            Go to Dashboard
          </Button>
        ) : (
          <>
            <Button as={Link} to="/auth" size="lg" variant="primary" aria-label="Login to your account">
              Login
            </Button>
            <Button as={Link} to="/auth" size="lg" variant="outline" aria-label="Register for a new account">
              Register
            </Button>
          </>
        )}
      </div>
      <div className="mt-12 text-text-light text-sm">
        <p>Built with React, TypeScript, and Tailwind CSS.</p>
        <p className="mt-2">Modern UI/UX, robust routing, and secure authentication.</p>
      </div>
    </div>
  );
};

export default HomePage;