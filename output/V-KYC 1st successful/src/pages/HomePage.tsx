import React from 'react';
import { Link } from 'react-router-dom';
import Button from '@/components/ui/Button';

const HomePage: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-primary to-indigo-700 text-white p-4">
      <h1 className="text-5xl md:text-7xl font-extrabold text-center mb-6 drop-shadow-lg">
        Welcome to Enterprise App
      </h1>
      <p className="text-lg md:text-xl text-center max-w-2xl mb-10 opacity-90">
        Your comprehensive solution for managing your business operations efficiently and securely.
      </p>
      <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
        <Link to="/login">
          <Button variant="light" size="lg" className="w-full sm:w-auto">
            Get Started
          </Button>
        </Link>
        <Link to="/dashboard">
          <Button variant="outline" size="lg" className="w-full sm:w-auto">
            Go to Dashboard (if logged in)
          </Button>
        </Link>
      </div>
      <div className="mt-12 text-sm opacity-80">
        <p>Built with React, TypeScript, and Tailwind CSS.</p>
      </div>
    </div>
  );
};

export default HomePage;